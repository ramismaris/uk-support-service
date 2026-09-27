export interface AlbumCell {
  index: number
  rowSpan: 1 | 2
}

export interface AlbumLayout {
  columns: 1 | 2
  cells: AlbumCell[]
  // Photos beyond the grid; the last cell shows "+N" over them.
  hidden: number
}

const MAX_CELLS = 4

// Like Telegram: 1 alone, 2 side by side, 3 as one tall and two stacked, 4+ as a 2×2 grid.
export function albumLayout(count: number): AlbumLayout {
  if (count <= 0) {
    return { columns: 1, cells: [], hidden: 0 }
  }
  if (count === 1) {
    return { columns: 1, cells: [{ index: 0, rowSpan: 1 }], hidden: 0 }
  }
  if (count === 3) {
    return {
      columns: 2,
      cells: [
        { index: 0, rowSpan: 2 },
        { index: 1, rowSpan: 1 },
        { index: 2, rowSpan: 1 },
      ],
      hidden: 0,
    }
  }
  const shown = Math.min(count, MAX_CELLS)
  return {
    columns: 2,
    cells: Array.from({ length: shown }, (_, index) => ({ index, rowSpan: 1 })),
    hidden: count - shown,
  }
}
