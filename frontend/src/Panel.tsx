import type { Analysis, Decision, Frame, MjaiAction, Severity } from './types'
import { BOARD, handTileWidth, meldTileWidth, MeldView } from './Board'
import { Tile } from './Tile'

export const SEV_LABEL: Record<Severity, string> = {
  ok: 'Match', minor: 'Close call', moderate: 'Mistake', major: 'Big mistake',
}

const pct = (p: number) => (p >= 0.995 ? '100%' : p < 0.001 ? '<0.1%' : `${(p * 100).toFixed(p < 0.1 ? 1 : 0)}%`)

function slotFor(action: MjaiAction, hand: { tiles: string[]; drawn: string | null }): number | null {
  if (action.type !== 'dahai' || !action.pai) return null
  if (action.tsumogiri && hand.drawn) return hand.tiles.length // drawn slot
  const i = hand.tiles.indexOf(action.pai)
  if (i >= 0) return i
  if (hand.drawn === action.pai) return hand.tiles.length
  return null
}

export function MyHand({ an, frame, decisions }: { an: Analysis; frame: Frame; decisions: Decision[] }) {
  const pid = an.player_id
  const hand = frame.hands[pid]
  const dahai = decisions.find((d) => d.options.some((o) => o.action.type === 'dahai'))
  const probs: Record<number, number> = {}
  let best: number | null = null
  let actual: number | null = null
  if (dahai) {
    for (const o of dahai.options) {
      const s = slotFor(o.action, hand)
      if (s !== null && probs[s] === undefined) probs[s] = o.prob
    }
    best = slotFor(dahai.expected, hand)
    actual = slotFor(dahai.actual, hand)
  }
  const markOf = (i: number) =>
    i === best && i === actual ? 'both' : i === best ? 'best' : i === actual ? 'actual' : null
  // Fixed tile size: a closed hand fills the mat's width; meld tiles shrink to keep the row inside it.
  const layout = { gap: 2, drawnPx: 14 + 2, drawnUnits: 0, meldLead: 16, meldGap: 6, meldScale: 1 }
  const W = handTileWidth(50, BOARD, layout)
  const MW = meldTileWidth(W, frame.melds[pid], BOARD, layout)
  // Right after a chi/pon the hand already holds the tile to discard: no drawn slot.
  // The melds shift by the slot's extra margin so the row keeps its width.
  const afterCall = !hand.drawn && hand.tiles.length % 3 === 2
  const cell = (t: string, i: number, extra?: object) => (
    <span className="hand-cell" key={i} style={extra}>
      <span className={`prob-label${probs[i] !== undefined && probs[i] >= 0.01 ? '' : ' empty'}`}>
        {probs[i] !== undefined && probs[i] >= 0.01 ? pct(probs[i]) : ''}
      </span>
      <Tile tile={t} w={W} mark={markOf(i)} />
    </span>
  )
  return (
    <div className="my-hand">
      <div className="tiles">
        {hand.tiles.map((t, i) => cell(t, i))}
        {hand.drawn
          ? cell(hand.drawn, hand.tiles.length, { marginLeft: 14 })
          : !afterCall && cell('1m', -1, { marginLeft: 14, visibility: 'hidden' })}
      </div>
      {frame.melds[pid].length > 0 && (
        <div className="melds" style={afterCall ? { marginLeft: 14 } : undefined}>
          {frame.melds[pid].map((m, i) => <MeldView key={i} meld={m} owner={pid} w={MW} />)}
        </div>
      )}
    </div>
  )
}

function DecisionCard({ d }: { d: Decision }) {
  const top = d.options.filter((o, i) => i < 6 && (o.prob >= 0.005 || i === 0))
  const actualInTop = top.some((o) => o.label === d.actual_label)
  const shown = actualInTop ? top : [...top, d.options.find((o) => o.label === d.actual_label)!].filter(Boolean)
  return (
    <div className={`decision sev-${d.severity}`}>
      <div className="decision-head">
        <span className={`badge sev-${d.severity}`}>{SEV_LABEL[d.severity]}</span>
        <span className="muted">turn {d.junme} · shanten {d.shanten ?? '?'}{d.furiten ? ' · furiten' : ''}</span>
      </div>
      {!d.is_equal && (
        <div className="verdict">
          <div><span className="you">You:</span> {d.actual_label} <b>{pct(d.actual_prob)}</b></div>
          <div><span className="ai">Mortal:</span> {d.expected_label} <b>{pct(d.expected_prob ?? 0)}</b></div>
          {d.q_loss !== null && <div className="muted">Q-loss {d.q_loss.toFixed(3)}</div>}
        </div>
      )}
      <div className="options">
        {shown.map((o, i) => {
          const isActual = o.label === d.actual_label
          const isBest = o.label === d.expected_label
          return (
            <div key={i} className={`opt${isActual ? ' is-actual' : ''}${isBest ? ' is-best' : ''}`}>
              <div className="opt-bar" style={{ width: `${Math.max(o.prob * 100, 0.5)}%` }} />
              <span className="opt-label">
                {o.action.type === 'dahai' && o.action.pai && <Tile tile={o.action.pai} w={16} />}
                {o.label}
                {o.ukeire !== undefined && (
                  <span className="ukeire" title={`Accepts: ${o.accept?.join(' ')}`}>
                    {o.shanten_after === 0 ? 'tenpai' : `${o.shanten_after}-sh`} · {o.ukeire} tiles
                  </span>
                )}
              </span>
              <span className="opt-prob">{pct(o.prob)}</span>
              <span className="opt-q">{o.q !== null ? o.q.toFixed(2) : ''}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function Panel({ an, decisions, mistakes, currentId, onJump, filter, setFilter, placement }: {
  an: Analysis
  decisions: Decision[]
  mistakes: Decision[]
  currentId: string | null
  onJump: (d: Decision) => void
  filter: Record<'major' | 'moderate' | 'minor', boolean>
  setFilter: (f: Record<'major' | 'moderate' | 'minor', boolean>) => void
  placement: number
}) {
  const agree = an.total_matches / an.total_reviewed
  const byKyoku = new Map<number, Decision[]>()
  for (const m of mistakes) {
    if (!byKyoku.has(m.kyoku_index)) byKyoku.set(m.kyoku_index, [])
    byKyoku.get(m.kyoku_index)!.push(m)
  }
  return (
    <aside className="panel">
      <section className="summary">
        <div className="summary-row">
          <div><div className="big">{(agree * 100).toFixed(1)}%</div><div className="muted">agreement</div></div>
          <div><div className="big">{(an.rating * 100).toFixed(1)}</div><div className="muted">Mortal rating</div></div>
          <div><div className="big">#{placement}</div><div className="muted">{an.final_scores?.[an.player_id]}</div></div>
        </div>
        <div className="muted small">{an.engine} {an.model_tag} · {an.rule} · {an.total_matches}/{an.total_reviewed} decisions matched</div>
        <div className="filters">
          {(['major', 'moderate', 'minor'] as const).map((s) => (
            <label key={s} className={`chip sev-${s}${filter[s] ? ' on' : ''}`}>
              <input type="checkbox" checked={filter[s]} onChange={(e) => setFilter({ ...filter, [s]: e.target.checked })} />
              {SEV_LABEL[s]} · {an.mistake_counts[s]}
            </label>
          ))}
        </div>
      </section>

      <section className="current">
        <h3>This decision</h3>
        {decisions.length === 0 && <div className="muted">No decision for you here. Use ↑/↓ to jump between your decisions.</div>}
        {decisions.map((d) => <DecisionCard key={d.id} d={d} />)}
      </section>

      <section className="mistake-list">
        <h3>Mistakes ({mistakes.length})</h3>
        {[...byKyoku.entries()].map(([ki, ms]) => (
          <div key={ki} className="mk-group">
            <div className="mk-kyoku">{an.kyokus[ki].label} <span className="muted">— {an.kyokus[ki].result.label}</span></div>
            {ms.map((m) => (
              <button key={m.id} className={`mk-row${m.id === currentId ? ' current' : ''}`} onClick={() => onJump(m)}>
                <span className={`dot sev-${m.severity}`} />
                <span className="mk-turn">T{m.junme}</span>
                <span className="mk-text">{m.actual_label} → <b>{m.expected_label}</b></span>
                <span className="mk-prob">{pct(m.actual_prob)}</span>
              </button>
            ))}
          </div>
        ))}
      </section>
    </aside>
  )
}
