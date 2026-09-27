import { albumLayout } from '../lib/album'
import type { MessageFile } from '../model/types'

export function PhotoAlbum({
  photos,
  onOpen,
}: {
  photos: MessageFile[]
  onOpen?: (fileId: number) => void
}) {
  const layout = albumLayout(photos.length)
  const single = layout.columns === 1

  return (
    <div className={`grid gap-0.5 ${single ? 'grid-cols-1' : 'grid-cols-2'}`}>
      {layout.cells.map((cell, position) => {
        const photo = photos[cell.index]!
        const last = position === layout.cells.length - 1
        return (
          <button
            key={photo.id}
            type="button"
            aria-label="Открыть фото"
            className={`relative block overflow-hidden bg-press ${cell.rowSpan === 2 ? 'row-span-2' : ''}`}
            onClick={() => onOpen?.(photo.id)}
          >
            <img
              src={photo.url}
              alt={photo.original_name ?? 'Фото'}
              loading="lazy"
              className={`w-full object-cover ${
                single
                  ? 'max-h-96 min-h-32'
                  : // The tall cell takes the height of the two rows beside it.
                    cell.rowSpan === 2
                    ? 'absolute inset-0 h-full'
                    : 'h-32'
              }`}
            />
            {last && layout.hidden > 0 && (
              <span className="absolute inset-0 flex items-center justify-center bg-black/50 text-2xl font-medium text-white">
                +{layout.hidden}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
