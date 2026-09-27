import { describe, expect, it } from 'vitest'
import type { Message, MessageFile } from '@/entities/message'
import { chatPhotos } from './chat-photos'

const file = (id: number, mime = 'image/jpeg'): MessageFile => ({
  id,
  mime,
  size: 1000,
  original_name: null,
  url: `/files/${id}`,
})

const message = (overrides: Partial<Message>): Message => ({
  id: 1,
  ticket_id: 1000,
  sender_type: 'CLIENT',
  author: null,
  text: null,
  files: [],
  created_at: '2026-09-26T10:01:00Z',
  ...overrides,
})

const anna = { id: 1, first_name: 'Анна', last_name: null }

describe('chatPhotos', () => {
  it('collects photos of all messages in chat order', () => {
    const photos = chatPhotos(
      [
        message({ id: 1, files: [file(1), file(2)] }),
        message({ id: 2, sender_type: 'STAFF', author: anna, files: [file(3)] }),
      ],
      'Иван Петров',
    )
    expect(photos.map((photo) => photo.file.id)).toEqual([1, 2, 3])
  })

  it('signs resident photos with the resident name and staff photos with the author', () => {
    const photos = chatPhotos(
      [
        message({ id: 1, files: [file(1)] }),
        message({ id: 2, sender_type: 'STAFF', author: anna, files: [file(2)] }),
      ],
      'Иван Петров',
    )
    expect(photos.map((photo) => photo.author)).toEqual(['Иван Петров', 'Анна'])
  })

  it('skips documents', () => {
    const photos = chatPhotos([message({ files: [file(1, 'application/pdf'), file(2)] })], 'Иван')
    expect(photos.map((photo) => photo.file.id)).toEqual([2])
  })
})
