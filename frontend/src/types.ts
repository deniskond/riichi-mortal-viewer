export type Severity = 'ok' | 'minor' | 'moderate' | 'major'

export interface PondTile {
  tile: string
  tsumogiri: boolean
  riichi: boolean
  called: boolean
}

export interface Meld {
  type: 'chi' | 'pon' | 'daiminkan' | 'ankan' | 'kakan'
  tiles: string[]
  from: number
  called_index: number | null
}

export interface MjaiAction {
  type: string
  actor?: number
  pai?: string
  tsumogiri?: boolean
  consumed?: string[]
  target?: number
}

export interface Win {
  winner: number
  from: number
  tsumo: boolean
  points: string
  yaku: { name: string; han: number | null }[]
}

export interface KyokuResult {
  type: 'win' | 'draw' | 'unknown'
  label: string
  deltas: number[]
  wins: Win[]
}

export interface FrameEvent {
  type: string
  actor?: number
  tile?: string
  from?: number
  tsumogiri?: boolean
  riichi?: boolean
  result?: KyokuResult
}

export interface Frame {
  event: FrameEvent
  tiles_left: number
  scores: number[]
  kyotaku: number
  dora: string[]
  riichi: boolean[]
  hands: { tiles: string[]; drawn: string | null }[]
  melds: Meld[][]
  ponds: PondTile[][]
  scores_after?: number[]
  ura?: string[]
}

export interface DecisionOption {
  action: MjaiAction
  label: string
  prob: number
  q: number | null
  shanten_after?: number
  ukeire?: number
  accept?: string[]
}

export interface Decision {
  id: string
  kyoku_index: number
  frame: number | null
  junme: number
  tiles_left: number
  kind: string
  actual: MjaiAction
  actual_label: string
  expected: MjaiAction
  expected_label: string
  is_equal: boolean
  actual_prob: number
  expected_prob: number | null
  q_loss: number | null
  severity: Severity
  shanten: number | null
  furiten: boolean | null
  options: DecisionOption[]
}

export interface Kyoku {
  kyoku: number
  honba: number
  oya: number
  label: string
  start_scores: number[]
  result: KyokuResult
  frames: Frame[]
  decisions: Decision[]
  placement_probs?: number[][]
}

export interface Analysis {
  id: string
  player_id: number
  names: string[]
  dan?: string[]
  rate?: number[]
  rule: string
  engine: string
  model_tag: string
  rating: number
  total_reviewed: number
  total_matches: number
  mistake_counts: Record<'major' | 'moderate' | 'minor', number>
  final_scores: number[]
  kyokus: Kyoku[]
  mistakes: string[]
}

export interface GameSummary {
  id: string
  rule: string
  rating: number
  matches: number
  reviewed: number
  mistakes: Record<'major' | 'moderate' | 'minor', number>
  place: number
  score: number
}
