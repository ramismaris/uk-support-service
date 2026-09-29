import { describe, expect, it } from 'vitest'
import { composerDraftKey, parseComposerText } from './composer-draft'

describe('composerDraftKey', () => {
  it('keeps a separate draft for every ticket', () => {
    expect(composerDraftKey(1000)).toBe('composer:1000')
    expect(composerDraftKey(1001)).not.toBe(composerDraftKey(1000))
  })
})

describe('parseComposerText', () => {
  it('reads a stored text', () => {
    expect(parseComposerText('Добрый день')).toBe('Добрый день')
  })

  it('rejects anything else', () => {
    expect(parseComposerText(5)).toBeNull()
    expect(parseComposerText(null)).toBeNull()
    expect(parseComposerText({ text: 'а' })).toBeNull()
  })
})
