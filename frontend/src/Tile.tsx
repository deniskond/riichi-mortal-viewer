import type { CSSProperties } from 'react'

// Tiles live in a 60x86 box: a 60x80 ivory plate (public/tiles/front.svg) with the
// symbol (public/tiles/<tile>.svg) inset on top, plus a 6px orange back edge below.
// Artwork: FluffyStuff/riichi-mahjong-tiles "Regular" set, public domain (CC0).
const FACE_H = 80
const BOX_H = 86
const INSET = 0.08

export const tileHeight = (w: number) => (w * BOX_H) / 60

const src = (tile: string) => `/tiles/${tile}.svg`

// Warm the browser cache so tiles don't pop in while stepping through a game.
const ALL = [
  ...['m', 'p', 's'].flatMap((s) => [1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => `${n}${s}`)),
  '5mr', '5pr', '5sr', 'E', 'S', 'W', 'N', 'P', 'F', 'C', 'front',
]
if (typeof window !== 'undefined') for (const t of ALL) new Image().src = src(t)

export interface TileProps {
  tile: string
  w?: number
  sideways?: boolean
  back?: boolean
  dim?: boolean
  mark?: 'best' | 'actual' | 'both' | 'last' | null
  title?: string
  style?: CSSProperties
  onClick?: () => void
}

export function Tile({ tile, w = 30, sideways, back, dim, mark, title, style, onClick }: TileProps) {
  const h = tileHeight(w)
  const width = sideways ? h : w
  const height = sideways ? w : h
  const body = back ? (
    <g>
      <rect x={0} y={0} width={60} height={BOX_H} rx={7} fill="#c9741d" />
      <rect x={0} y={0} width={60} height={FACE_H} rx={7} fill="#f2a43a" />
    </g>
  ) : (
    <g>
      <rect x={0} y={10} width={60} height={BOX_H - 10} rx={7} fill="#d98a2b" />
      <image href={src('front')} x={0} y={0} width={60} height={FACE_H} preserveAspectRatio="none" />
      <image
        href={src(tile)}
        x={60 * INSET}
        y={FACE_H * INSET}
        width={60 * (1 - 2 * INSET)}
        height={FACE_H * (1 - 2 * INSET)}
        preserveAspectRatio="none"
      />
    </g>
  )
  return (
    <span
      className={`tile${mark ? ` mark-${mark}` : ''}${dim ? ' dim' : ''}${onClick ? ' clickable' : ''}`}
      style={{ width, height, ...style }}
      title={title ?? tile}
      onClick={onClick}
    >
      <svg viewBox={sideways ? `0 0 ${BOX_H} 60` : `0 0 60 ${BOX_H}`} width={width} height={height}>
        <g transform={sideways ? 'translate(0,60) rotate(-90)' : undefined}>{body}</g>
      </svg>
    </span>
  )
}
