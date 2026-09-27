export interface Edit {
  value: string
  start: number
  end: number
}

// A toolbar button on a textarea selection: wrap it in the marker, or unwrap if already wrapped.
export function toggleMarker(value: string, start: number, end: number, marker: string): Edit {
  const size = marker.length
  const selected = value.slice(start, end)

  if (selected.length >= size * 2 && selected.startsWith(marker) && selected.endsWith(marker)) {
    const inner = selected.slice(size, -size)
    return {
      value: value.slice(0, start) + inner + value.slice(end),
      start,
      end: start + inner.length,
    }
  }
  if (value.slice(start - size, start) === marker && value.slice(end, end + size) === marker) {
    return {
      value: value.slice(0, start - size) + selected + value.slice(end + size),
      start: start - size,
      end: end - size,
    }
  }

  // "**word **" does not render in Max: the spaces stay outside the markers.
  const lead = selected.length - selected.trimStart().length
  const trail = selected.length - selected.trimEnd().length
  const from = start + lead
  const to = Math.max(from, end - trail)
  const word = value.slice(from, to)
  return {
    value: value.slice(0, from) + marker + word + marker + value.slice(to),
    start: from + size,
    end: from + size + word.length,
  }
}

const LINK_PLACEHOLDER = 'ссылка'
const URL_PLACEHOLDER = 'https://'

export function insertLink(value: string, start: number, end: number): Edit {
  const text = value.slice(start, end) || LINK_PLACEHOLDER
  const link = `[${text}](${URL_PLACEHOLDER})`
  // The placeholder address is selected: a pasted link replaces it whole.
  const urlStart = start + text.length + 3
  return {
    value: value.slice(0, start) + link + value.slice(end),
    start: urlStart,
    end: urlStart + URL_PLACEHOLDER.length,
  }
}
