import { describe, expect, it } from 'vitest'
import { botPreview } from './preview'

const back = { label: '« В меню' }

describe('botPreview', () => {
  it('shows the welcome with the photo and the main menu', () => {
    const preview = botPreview('welcome', { text: 'Привет', photo: { id: 1, url: '/p' } })
    expect(preview.photoUrl).toBe('/p')
    expect(preview.text).toBe('Привет')
    expect(preview.buttons.map((button) => button.label)).toEqual([
      'Подать заявку',
      'Мои заявки',
      'Аварийные службы',
      'Услуги УК',
      'Оплата ЖКХ',
      'Задать вопрос',
    ])
  })

  it('adds only the back button to plain sections', () => {
    expect(botPreview('emergency', { text: '112' })).toEqual({
      photoUrl: null,
      text: '112',
      buttons: [back],
    })
  })

  it('shows the payment link button', () => {
    expect(
      botPreview('payment', { text: 'Оплата', url: 'https://pay.ru', buttonText: 'Оплатить' })
        .buttons,
    ).toEqual([{ label: 'Оплатить', url: 'https://pay.ru' }, back])
  })

  it('lists the contact phones after an empty line, like the bot', () => {
    const preview = botPreview('contacts', {
      text: 'Звоните',
      phones: [
        { title: 'Диспетчер', phone: '1' },
        { title: 'Бухгалтерия', phone: '2' },
      ],
    })
    expect(preview.text).toBe('Звоните\n\nДиспетчер: 1\nБухгалтерия: 2')
    expect(preview.buttons).toEqual([{ label: 'Написать вопрос' }, back])
  })

  it('shows just the text without phones', () => {
    expect(botPreview('contacts', { text: 'Звоните', phones: [] }).text).toBe('Звоните')
  })
})
