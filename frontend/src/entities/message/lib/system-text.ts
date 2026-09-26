// Bot texts start with a status emoji meant for Max; the panel shows its own icon instead.
const LEADING_EMOJI = /^(?:\p{Extended_Pictographic}️?\s*)+/u

export function systemText(text: string | null): string {
  return (text ?? '').replace(LEADING_EMOJI, '')
}
