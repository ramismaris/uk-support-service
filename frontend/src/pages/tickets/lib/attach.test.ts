import { describe, expect, it } from 'vitest'
import { attachTitle, isImage, pastedImages } from './attach'

const photo = { type: 'image/jpeg' }
const pdf = { type: 'application/pdf' }

describe('attachTitle', () => {
  it('names a single photo', () => {
    expect(attachTitle([photo])).toBe('Отправить фото')
  })

  it('counts several photos', () => {
    expect(attachTitle([photo, photo, photo])).toBe('Отправить 3 фото')
  })

  it('names a document', () => {
    expect(attachTitle([pdf])).toBe('Отправить файл')
  })

  it('counts files when photos and a document are mixed', () => {
    expect(attachTitle([photo, pdf])).toBe('Отправить файлы: 2')
  })
})

describe('isImage', () => {
  it('tells photos from documents by type', () => {
    expect(isImage(photo)).toBe(true)
    expect(isImage(pdf)).toBe(false)
  })
})

describe('pastedImages', () => {
  it('keeps only pictures from the clipboard', () => {
    expect(pastedImages([photo, pdf, photo])).toEqual([photo, photo])
  })

  it('finds nothing in plain text paste', () => {
    expect(pastedImages([])).toEqual([])
  })
})
