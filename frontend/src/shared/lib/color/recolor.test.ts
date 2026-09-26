import { describe, expect, it } from 'vitest'
import { recolorLottie } from './recolor'

const animation = () => ({
  layers: [
    {
      shapes: [
        { ty: 'st', c: { k: [0, 0, 0, 1] } },
        {
          ty: 'fl',
          c: {
            k: [
              { t: 0, s: [0, 0, 0, 0.5] },
              { t: 10, s: [1, 1, 1, 0.5] },
            ],
          },
        },
        { ty: 'tr', c: { k: [9, 9, 9] } },
      ],
    },
  ],
})

type Shape = { c: { k: unknown } }

describe('recolorLottie', () => {
  it('paints strokes and fills, keeps alpha, leaves other shapes', () => {
    const out = recolorLottie(animation(), '#ff0000') as ReturnType<typeof animation>
    const [stroke, fill, transform] = out.layers[0].shapes as Shape[]
    expect(stroke.c.k).toEqual([1, 0, 0, 1])
    expect(fill.c.k).toEqual([
      { t: 0, s: [1, 0, 0, 0.5] },
      { t: 10, s: [1, 0, 0, 0.5] },
    ])
    expect(transform.c.k).toEqual([9, 9, 9])
  })

  it('does not mutate the input', () => {
    const input = animation()
    recolorLottie(input, '#ff0000')
    expect(input.layers[0].shapes[0].c.k).toEqual([0, 0, 0, 1])
  })

  it('returns the input untouched for an invalid colour', () => {
    const input = animation()
    expect(recolorLottie(input, 'red')).toBe(input)
  })
})
