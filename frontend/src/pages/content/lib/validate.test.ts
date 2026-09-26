import { describe, expect, it } from 'vitest'
import { validateSection } from './validate'

const photo = { id: 1, url: '/f/1' }
const phone = (title = 'Диспетчер', number = '+7 900 000-00-00') => ({ title, phone: number })

describe('validateSection', () => {
  it('accepts filled drafts', () => {
    expect(validateSection('welcome', { text: 'Здравствуйте', photo })).toEqual({})
    expect(validateSection('emergency', { text: '112' })).toEqual({})
    expect(
      validateSection('payment', { text: 'Оплата', url: 'https://pay.ru', buttonText: 'Оплатить' }),
    ).toEqual({})
    expect(validateSection('contacts', { text: 'Звоните', phones: [phone()] })).toEqual({})
    expect(validateSection('contacts', { text: 'Звоните', phones: [] })).toEqual({})
  })

  it('requires text and limits it', () => {
    expect(validateSection('services', { text: '   ' })).toEqual({ text: 'Заполните текст' })
    expect(validateSection('services', { text: 'а'.repeat(3001) })).toEqual({
      text: 'Не длиннее 3000 символов',
    })
  })

  it('requires a photo for the welcome', () => {
    expect(validateSection('welcome', { text: 'Привет', photo: null })).toEqual({
      photo: 'Добавьте фото',
    })
  })

  it('checks the payment link and button', () => {
    expect(
      validateSection('payment', { text: 'Оплата', url: 'ftp://pay.ru', buttonText: 'Оплатить' }),
    ).toEqual({ url: 'Ссылка должна начинаться с http:// или https://' })
    expect(
      validateSection('payment', { text: 'Оплата', url: 'https://pay.ru', buttonText: '' }),
    ).toEqual({ buttonText: 'Заполните текст кнопки' })
    expect(
      validateSection('payment', {
        text: 'Оплата',
        url: 'https://pay.ru',
        buttonText: 'к'.repeat(65),
      }),
    ).toEqual({ buttonText: 'Не длиннее 64 символов' })
  })

  it('checks the contact phones', () => {
    expect(
      validateSection('contacts', { text: 'Т', phones: Array.from({ length: 11 }, () => phone()) }),
    ).toEqual({ phones: 'Не больше 10 телефонов' })
    expect(validateSection('contacts', { text: 'Т', phones: [phone(' ')] })).toEqual({
      'phones.0.title': 'Заполните подпись',
    })
    expect(
      validateSection('contacts', { text: 'Т', phones: [phone('Д', '1'.repeat(31))] }),
    ).toEqual({
      'phones.0.phone': 'Не длиннее 30 символов',
    })
  })

  it('trims the payment link and limits it', () => {
    const payment = (url: string) => ({ text: 'Оплата', url, buttonText: 'Оплатить' })
    expect(validateSection('payment', payment('  https://pay.ru '))).toEqual({})
    expect(validateSection('payment', payment(`https://pay.ru/${'a'.repeat(2034)}`))).toEqual({
      url: 'Не длиннее 2048 символов',
    })
  })
})
