import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Board, BOARD, SIDE } from './Board'
import { MyHand, Panel, SEV_LABEL } from './Panel'
import type { Analysis, Decision, GameSummary } from './types'

type Filter = Record<'major' | 'moderate' | 'minor', boolean>

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init)
  if (!r.ok) {
    let msg = `HTTP ${r.status}`
    try { msg = (await r.json()).detail ?? msg } catch { /* ignore */ }
    throw new Error(msg)
  }
  return r.json()
}

export default function App() {
  const [games, setGames] = useState<GameSummary[]>([])
  const [an, setAn] = useState<Analysis | null>(null)
  const [ki, setKi] = useState(0)
  const [fi, setFi] = useState(0)
  const [src, setSrc] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [showHands, setShowHands] = useState(true)
  const [filter, setFilter] = useState<Filter>({ major: true, moderate: true, minor: false })
  const [zoom, setZoom] = useState(1)

  const refreshGames = useCallback(() => api<GameSummary[]>('/api/games').then(setGames).catch(() => {}), [])

  const openGame = useCallback(async (id: string, k = 0, f = 0) => {
    setErr(null)
    try {
      const a = await api<Analysis>(`/api/games/${id}`)
      const kk = Math.min(Math.max(k, 0), a.kyokus.length - 1)
      setAn(a); setKi(kk); setFi(Math.min(Math.max(f, 0), a.kyokus[kk].frames.length - 1))
    } catch (e) { setErr(String((e as Error).message)) }
  }, [])

  useEffect(() => {
    refreshGames()
    const q = new URLSearchParams(location.search)
    const g = q.get('game')
    if (g) openGame(g, Number(q.get('k') ?? 0), Number(q.get('f') ?? 0))
  }, [refreshGames, openGame])

  // Fit the board column to the window: measure its unzoomed size and scale it to the space left.
  const leftRef = useRef<HTMLDivElement>(null)
  const zoomRef = useRef(1)
  const fit = useCallback(() => {
    const el = leftRef.current
    if (!el) return
    const r = el.getBoundingClientRect()
    // The table's unzoomed width is known, so its measured width tells how rects scale with zoom.
    const table = el.querySelector('.table')?.getBoundingClientRect().width
    const scale = table ? table / (BOARD + 2 * SIDE) : 1
    const natW = Math.max(r.width / scale, BOARD + 2 * SIDE)
    const natH = r.height / scale
    const panel = el.parentElement?.querySelector('.panel')?.getBoundingClientRect().width ?? 400
    const h = (window.innerHeight - r.top - 12) / natH
    const w = (window.innerWidth - panel - 50) / natW
    const z = Math.max(0.5, Math.min(1.6, h, w))
    if (Math.abs(z - zoomRef.current) > 0.002) { zoomRef.current = z; setZoom(z) }
  }, [])
  useLayoutEffect(() => {
    fit()
    window.addEventListener('resize', fit)
    return () => window.removeEventListener('resize', fit)
  })

  const analyze = async () => {
    if (!src.trim()) return
    setBusy(true); setErr(null)
    try {
      const { id } = await api<{ id: string }>('/api/analyze', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source: src }),
      })
      await refreshGames()
      await openGame(id)
      setSrc('')
    } catch (e) { setErr(String((e as Error).message)) } finally { setBusy(false) }
  }

  useEffect(() => {
    if (an) history.replaceState(null, '', `?game=${an.id}&k=${ki}&f=${fi}`)
  }, [an, ki, fi])

  const kyoku = an?.kyokus[ki]
  const frame = kyoku?.frames[Math.min(fi, kyoku.frames.length - 1)]

  const allDecisions = useMemo(() => an?.kyokus.flatMap((k) => k.decisions) ?? [], [an])
  const mistakes = useMemo(
    () => allDecisions.filter((d) => d.severity !== 'ok' && filter[d.severity as keyof Filter]),
    [allDecisions, filter],
  )
  const hereDecisions = useMemo(() => kyoku?.decisions.filter((d) => d.frame === fi) ?? [], [kyoku, fi])
  const decisionFrames = useMemo(
    () => [...new Set(kyoku?.decisions.map((d) => d.frame).filter((f): f is number => f !== null) ?? [])].sort((a, b) => a - b),
    [kyoku],
  )

  const jump = useCallback((d: Decision) => { setKi(d.kyoku_index); setFi(d.frame ?? 0) }, [])

  const step = useCallback((delta: number) => {
    if (!an || !kyoku) return
    const n = fi + delta
    if (n < 0) {
      if (ki > 0) { setKi(ki - 1); setFi(an.kyokus[ki - 1].frames.length - 1) }
    } else if (n >= kyoku.frames.length) {
      if (ki < an.kyokus.length - 1) { setKi(ki + 1); setFi(0) }
    } else setFi(n)
  }, [an, kyoku, fi, ki])

  const stepDecision = useCallback((dir: 1 | -1) => {
    if (!an) return
    const flat = allDecisions.filter((d) => d.frame !== null)
    const pos = (d: Decision) => d.kyoku_index * 10000 + d.frame!
    const cur = ki * 10000 + fi
    const target = dir > 0 ? flat.find((d) => pos(d) > cur) : [...flat].reverse().find((d) => pos(d) < cur)
    if (target) jump(target)
  }, [an, allDecisions, ki, fi, jump])

  const stepMistake = useCallback((dir: 1 | -1) => {
    const pos = (d: Decision) => d.kyoku_index * 10000 + (d.frame ?? 0)
    const cur = ki * 10000 + fi
    const target = dir > 0 ? mistakes.find((d) => pos(d) > cur) : [...mistakes].reverse().find((d) => pos(d) < cur)
    if (target) jump(target)
  }, [mistakes, ki, fi, jump])

  const gotoKyoku = useCallback((n: number) => {
    if (!an) return
    if (n >= 0 && n < an.kyokus.length) { setKi(n); setFi(0) }
  }, [an])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName === 'INPUT') return
      if (e.key === 'ArrowRight') step(1)
      else if (e.key === 'ArrowLeft') step(-1)
      else if (e.key === 'ArrowDown') stepDecision(1)
      else if (e.key === 'ArrowUp') stepDecision(-1)
      else if (e.key === 'PageDown') gotoKyoku(ki + 1)
      else if (e.key === 'PageUp') gotoKyoku(ki - 1)
      else if (e.key === 'm') stepMistake(1)
      else if (e.key === 'M') stepMistake(-1)
      else return
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [step, stepDecision, stepMistake, gotoKyoku, ki])

  const placement = an ? 1 + an.final_scores.filter((s) => s > an.final_scores[an.player_id]).length : 0
  const curTurn = kyoku?.decisions.filter((d) => d.frame !== null && d.frame <= fi).at(-1)?.junme ?? 0

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">Mahjong<span>Review</span></div>
        <input
          className="src"
          placeholder="Paste mjai.ekyu.moe result URL (…/progress?task=… or …/report/….json)"
          value={src}
          onChange={(e) => setSrc(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && analyze()}
        />
        <button className="btn gold" onClick={analyze} disabled={busy}>{busy ? 'Analyzing…' : 'Analyze'}</button>
        <select className="games" value={an?.id ?? ''} onChange={(e) => e.target.value && openGame(e.target.value)}>
          <option value="">Saved games ({games.length})</option>
          {games.map((g) => (
            <option key={g.id} value={g.id}>
              #{g.place} · {g.score} · {((g.matches / g.reviewed) * 100).toFixed(0)}% · {g.mistakes.major} big · {g.id}
            </option>
          ))}
        </select>
        <label className="toggle"><input type="checkbox" checked={showHands} onChange={(e) => setShowHands(e.target.checked)} /> Show opponents' hands</label>
      </header>
      {err && <div className="error">{err}</div>}

      {!an && (
        <div className="welcome">
          <h2>Review a game with Mortal</h2>
          <ol>
            <li>Open <a href="https://mjai.ekyu.moe" target="_blank" rel="noreferrer">mjai.ekyu.moe</a>, paste your tenhou / Mahjong Soul log, choose the Mortal engine and submit.</li>
            <li>When it finishes, copy the result URL from the address bar.</li>
            <li>Paste it above and press <b>Analyze</b>.</li>
          </ol>
        </div>
      )}

      {an && kyoku && frame && (
        <main className="main">
          <div className="left" ref={leftRef} style={{ zoom }}>
            <Board an={an} kyoku={kyoku} frame={frame} showHands={showHands} />
            <MyHand an={an} frame={frame} decisions={hereDecisions} />
            <div className="timeline">
              {kyoku.decisions.filter((d) => d.frame !== null).map((d) => (
                <button
                  key={d.id}
                  className={`tl sev-${d.severity}${d.frame === fi ? ' current' : ''}`}
                  title={`T${d.junme}: ${d.actual_label}${d.is_equal ? '' : ` → ${d.expected_label}`} (${SEV_LABEL[d.severity]})`}
                  onClick={() => jump(d)}
                />
              ))}
            </div>
            <div className="controls">
              <button className="btn" onClick={() => gotoKyoku(ki - 1)} title="PageUp">⏮</button>
              <select className="ctl-label" value={ki} onChange={(e) => gotoKyoku(Number(e.target.value))}>
                {an.kyokus.map((k, i) => <option key={i} value={i}>{k.label}</option>)}
              </select>
              <button className="btn" onClick={() => gotoKyoku(ki + 1)} title="PageDown">⏭</button>
              <span className="sep" />
              <button className="btn" onClick={() => stepDecision(-1)} title="↑">⏪</button>
              <span className="ctl-label">Turn {curTurn}</span>
              <button className="btn" onClick={() => stepDecision(1)} title="↓">⏩</button>
              <span className="sep" />
              <button className="btn" onClick={() => step(-1)} title="←">◀</button>
              <span className="muted small">{fi + 1}/{kyoku.frames.length}</span>
              <button className="btn" onClick={() => step(1)} title="→">▶</button>
              <span className="sep" />
              <button className="btn" onClick={() => stepMistake(-1)} title="Shift+M">◀ Mistake</button>
              <button className="btn gold" onClick={() => stepMistake(1)} title="M">Mistake ▶</button>
              <span className="sep" />
              <span className="muted small">{decisionFrames.length} decisions this hand</span>
            </div>
          </div>
          <Panel
            an={an}
            decisions={hereDecisions}
            mistakes={mistakes}
            currentId={hereDecisions[0]?.id ?? null}
            onJump={jump}
            filter={filter}
            setFilter={setFilter}
            placement={placement}
          />
        </main>
      )}
    </div>
  )
}
