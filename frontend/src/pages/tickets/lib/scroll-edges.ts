export interface ScrollEdges {
  // Something is hidden past the left edge / past the right edge.
  start: boolean
  end: boolean
}

// Browsers report fractional scroll positions on zoomed or high-density screens.
const TOLERANCE = 1

// Where to scroll the row so that the chip ends up in its middle.
export function centeredScrollLeft(box: {
  scrollLeft: number
  rowLeft: number
  rowWidth: number
  chipLeft: number
  chipWidth: number
}): number {
  const chipInRow = box.scrollLeft + (box.chipLeft - box.rowLeft)
  return Math.max(0, chipInRow - (box.rowWidth - box.chipWidth) / 2)
}

export function scrollEdges(row: {
  scrollLeft: number
  clientWidth: number
  scrollWidth: number
}): ScrollEdges {
  return {
    start: row.scrollLeft > TOLERANCE,
    end: row.scrollLeft + row.clientWidth < row.scrollWidth - TOLERANCE,
  }
}
