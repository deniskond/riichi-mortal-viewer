import type { Analysis, Frame, Kyoku, Meld, PondTile } from './types'
import { Tile } from './Tile'

export const BOARD = 720 // the mat: center panel + discard ponds
export const SIDE = 84 // strips outside the mat holding the opponents' hands
const CENTER = 255
const POND_W = 37
const OPP_W = 50 // same as the player's own hand

const WINDS = 'ESWN'
const ROT = [0, -90, 180, 90] // relative seat 0=me(bottom),1=right,2=top,3=left

const SIDEWAYS = 86 / 60 // width of a sideways tile, in tile widths

/**
 * Largest tile width (<= max) at which a hand row fits in `avail` px.
 * Row width is linear in the tile width w: per-tile terms go to `a`, fixed px to `b`.
 * `layout` gives the row's fixed spacing: gap between hand tiles, extra px/units before
 * the drawn slot, px before the meld group, gap between melds, and meld tile scale.
 */
export function fitTileWidth(
  nHand: number, melds: Meld[], max: number, avail: number,
  layout: { gap: number; drawnPx: number; drawnUnits: number; meldLead: number; meldGap: number; meldScale: number },
) {
  let a = nHand + 1 + layout.drawnUnits // hand tiles + the always-reserved drawn slot
  let b = nHand * layout.gap + layout.drawnPx
  if (melds.length) {
    b += layout.meldLead + layout.meldGap * (melds.length - 1)
    for (const m of melds) {
      const slots = m.type === 'ankan' || m.type === 'daiminkan' ? 4 : 3
      const units = m.type === 'ankan' ? 4 : slots - 1 + SIDEWAYS
      a += units * layout.meldScale
      b += slots - 1
    }
  }
  return Math.max(16, Math.min(max, (avail - b) / a))
}

type RowLayout = Parameters<typeof fitTileWidth>[4]

// Hand tiles have one fixed size: a closed hand (13 tiles + drawn slot) fills the mat side exactly.
export function handTileWidth(max: number, avail: number, layout: RowLayout) {
  return fitTileWidth(13, [], max, avail, layout)
}

/**
 * Meld tiles shrink so the row (hand at fixed width `w` + melds) still fills `avail`.
 * The hand count is the nominal 13 - 3 per call, so meld size is stable within a hand.
 */
export function meldTileWidth(w: number, melds: Meld[], avail: number, layout: RowLayout) {
  if (!melds.length) return w
  const nHand = Math.max(1, 13 - 3 * melds.length)
  const handPx = (nHand + 1 + layout.drawnUnits) * w + nHand * layout.gap + layout.drawnPx
  let units = 0
  let fixed = layout.meldLead + layout.meldGap * (melds.length - 1)
  for (const m of melds) {
    const slots = m.type === 'ankan' || m.type === 'daiminkan' ? 4 : 3
    units += m.type === 'ankan' ? 4 : slots - 1 + SIDEWAYS
    fixed += slots - 1
  }
  return Math.max(16, Math.min(w, (avail - handPx - fixed) / units))
}

export function seatWind(seat: number, oya: number) {
  return WINDS[(seat - oya + 4) % 4]
}

function Pond({ pond, lastIdx }: { pond: PondTile[]; lastIdx: number | null }) {
  const rows: PondTile[][] = []
  for (let i = 0; i < pond.length; i += 6) rows.push(pond.slice(i, Math.min(i + 6, pond.length)))
  // Tenhou-style: rows of 6, extra discards keep extending the 3rd row
  const merged = rows.length > 3 ? [...rows.slice(0, 2), rows.slice(2).flat()] : rows
  let k = 0
  return (
    <div className="pond">
      {merged.map((row, ri) => (
        <div className="pond-row" key={ri}>
          {row.map((d) => {
            const idx = k++
            return (
              <Tile
                key={idx}
                tile={d.tile}
                w={POND_W}
                sideways={d.riichi}
                mark={idx === lastIdx ? 'last' : null}
                style={d.tsumogiri ? { filter: 'brightness(0.86)' } : undefined}
                title={`${d.tile}${d.tsumogiri ? ' (tsumogiri)' : ''}${d.riichi ? ' (riichi)' : ''}${d.called ? ' (called)' : ''}`}
              />
            )
          })}
        </div>
      ))}
    </div>
  )
}

export function MeldView({ meld, owner, w }: { meld: Meld; owner: number; w: number }) {
  const rel = (meld.from - owner + 4) % 4
  if (meld.type === 'ankan') {
    return (
      <span className="meld">
        {meld.tiles.map((t, i) => <Tile key={i} tile={t} w={w} back={i === 0 || i === 3} />)}
      </span>
    )
  }
  const called = meld.tiles[0]
  const rest = meld.tiles.slice(1, meld.type === 'kakan' ? 3 : undefined)
  const pos = rel === 3 ? 0 : rel === 2 ? 1 : rest.length
  const tiles = [...rest]
  tiles.splice(pos, 0, called)
  return (
    <span className="meld">
      {tiles.map((t, i) => (
        <span key={i} className={meld.type === 'kakan' && i === pos ? 'kakan-stack' : undefined}>
          <Tile tile={t} w={w} sideways={i === pos} />
          {meld.type === 'kakan' && i === pos && <Tile tile={meld.tiles[3]} w={w} sideways />}
        </span>
      ))}
    </span>
  )
}

function SeatLayer({ an, kyoku, frame, seat }: { an: Analysis; kyoku: Kyoku; frame: Frame; seat: number }) {
  const rel = (seat - an.player_id + 4) % 4
  const ev = frame.event
  const lastIdx = ev.type === 'discard' && ev.actor === seat ? frame.ponds[seat].length - 1 : null
  const wind = seatWind(seat, kyoku.oya)
  const active = ev.actor === seat && ev.type !== 'end'
  return (
    <div className="seat-layer" style={{ transform: `rotate(${ROT[rel]}deg)` }}>
      <div className={`center-score${active ? ' active' : ''}`} style={{ top: BOARD / 2 + CENTER / 2 - 39 }}>
        <span className={`wind${wind === 'E' ? ' dealer' : ''}`}>{wind}</span>
        <span className="score">{frame.scores[seat]}</span>
      </div>
      {frame.riichi[seat] && (
        <span className="riichi-stick" style={{ top: BOARD / 2 + CENTER / 2 - 54, width: CENTER * 0.5 }} />
      )}
      <div className="pond-wrap" style={{ top: BOARD / 2 + CENTER / 2 + 8, width: 6 * (POND_W + 1) - 1, transform: 'translateX(-50%)' }}>
        <Pond pond={frame.ponds[seat]} lastIdx={lastIdx} />
      </div>
    </div>
  )
}

/** An opponent's hand, drawn outside the mat and rotated to face its owner. */
function OppHand({ frame, seat, rel, showHands }: { frame: Frame; seat: number; rel: number; showHands: boolean }) {
  const hand = frame.hands[seat]
  const melds = frame.melds[seat]
  const layout = { gap: 1, drawnPx: 1, drawnUnits: 0.15, meldLead: 10 + 1, meldGap: 6, meldScale: 1 }
  const w = handTileWidth(OPP_W, BOARD, layout)
  const mw = meldTileWidth(w, melds, BOARD, layout)
  const afterCall = !hand.drawn && hand.tiles.length % 3 === 2
  return (
    <div className="opp-strip" style={{ transform: `translate(-50%, -50%) rotate(${ROT[rel]}deg)` }}>
      {hand.tiles.map((t, i) => <Tile key={i} tile={t} w={w} back={!showHands} />)}
      {/* the drawn-tile slot is always reserved so the hand doesn't shift on draw/discard */}
      {/* right after a chi/pon the hand already holds the tile to discard: no slot */}
      {!afterCall && (
        <Tile tile={hand.drawn ?? '1m'} w={w} back={!showHands} style={{ marginLeft: w * 0.15, visibility: hand.drawn ? undefined : 'hidden' }} />
      )}
      {melds.length > 0 && (
        <span className="melds" style={afterCall ? { marginLeft: 10 + w * 0.15 } : undefined}>
          {melds.map((m, i) => <MeldView key={i} meld={m} owner={seat} w={mw} />)}
        </span>
      )}
    </div>
  )
}

function ResultOverlay({ an, kyoku, frame }: { an: Analysis; kyoku: Kyoku; frame: Frame }) {
  const r = frame.event.result!
  const pid = an.player_id
  const who = (p: number) => (p === pid ? 'You' : an.names[p])
  return (
    <div className="result-overlay">
      <div className="result-title">{kyoku.label} — {r.label}</div>
      {r.wins.map((w, i) => (
        <div key={i} className="result-win">
          <div><b>{who(w.winner)}</b> {w.tsumo ? 'tsumo' : <>ron from <b>{who(w.from)}</b></>}</div>
          <div className="points">{w.points}</div>
          <div className="yaku">{w.yaku.map((y, j) => <span key={j}>{y.name}{y.han ? ` ${y.han}` : ''}</span>)}</div>
        </div>
      ))}
      <div className="deltas">
        {r.deltas.map((d, p) => (
          <div key={p} className={p === pid ? 'me' : undefined}>
            <span>{who(p)}</span>
            <span className={d > 0 ? 'pos' : d < 0 ? 'neg' : ''}>{d > 0 ? `+${d}` : d}</span>
            <span className="after">{frame.scores_after?.[p]}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function Board({ an, kyoku, frame, showHands }: {
  an: Analysis; kyoku: Kyoku; frame: Frame; showHands: boolean
}) {
  const roundName = `${['East', 'South', 'West', 'North'][Math.floor(kyoku.kyoku / 4)]} ${(kyoku.kyoku % 4) + 1}`
  const pid = an.player_id
  const isEnd = frame.event.type === 'end'
  const nameTags: { seat: number; cls: string }[] = [0, 1, 2, 3].map((rel) => ({
    seat: (pid + rel) % 4,
    cls: ['tag-me', 'tag-right', 'tag-top', 'tag-left'][rel],
  }))
  const opp = (rel: number) => (
    <div className="opp-cell"><OppHand frame={frame} seat={(pid + rel) % 4} rel={rel} showHands={showHands} /></div>
  )
  return (
    <div className="table" style={{ gridTemplateColumns: `${SIDE}px ${BOARD}px ${SIDE}px`, gridTemplateRows: `${SIDE}px ${BOARD}px` }}>
      <div />{opp(2)}<div />
      {opp(3)}
    <div className="board" style={{ width: BOARD, height: BOARD }}>
      <div className="board-lines" />
      <div className="dora-box">
        <div className="dora-tiles">
          {[0, 1, 2, 3, 4].map((i) =>
            i < frame.dora.length
              ? <Tile key={i} tile={frame.dora[i]} w={38} />
              : <Tile key={i} tile="1m" w={38} back />,
          )}
        </div>
        {isEnd && frame.ura && frame.ura.length > 0 && (
          <div className="dora-tiles ura">
            <span>Ura</span>
            {frame.ura.map((t, i) => <Tile key={i} tile={t} w={32} />)}
          </div>
        )}
        <div className="sticks">
          <span title="Honba">⬤ ×{kyoku.honba}</span>
          <span title="Riichi sticks on table">▮ ×{frame.kyotaku}</span>
        </div>
      </div>

      <div className="center-panel" style={{ width: CENTER, height: CENTER }}>
        <div className="round-name">{roundName}{kyoku.honba ? `-${kyoku.honba}` : ''}</div>
        <div className="tiles-left">×{frame.tiles_left}</div>
      </div>

      {[0, 1, 2, 3].map((seat) => (
        <SeatLayer key={seat} an={an} kyoku={kyoku} frame={frame} seat={seat} />
      ))}

      {nameTags.map(({ seat, cls }) => (
        <div key={seat} className={`name-tag ${cls}${seat === pid ? ' me' : ''}`}>
          <div className="nm">{seat === pid ? `${an.names[seat]} (you)` : an.names[seat]}</div>
          <div className="sub">
            {seatWind(seat, kyoku.oya)} · {an.dan?.[seat] ?? ''} {an.rate ? `R${Math.round(an.rate[seat])}` : ''}
          </div>
        </div>
      ))}

      {isEnd && <ResultOverlay an={an} kyoku={kyoku} frame={frame} />}
    </div>
      {opp(1)}
    </div>
  )
}
