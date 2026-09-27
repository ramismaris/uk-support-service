// While an area scrolls, its scrollbar shows even without hover (a wheel over another element,
// keyboard, touchpad momentum); it hides again shortly after the scrolling stops.
const VISIBLE_AFTER_SCROLL_MS = 800

export function showScrollbarsWhileScrolling(): void {
  const timers = new WeakMap<Element, number>()
  document.addEventListener(
    'scroll',
    (event) => {
      const target = event.target
      const element = target instanceof Element ? target : document.documentElement
      element.setAttribute('data-scrolling', '')
      window.clearTimeout(timers.get(element))
      timers.set(
        element,
        window.setTimeout(() => element.removeAttribute('data-scrolling'), VISIBLE_AFTER_SCROLL_MS),
      )
    },
    { capture: true, passive: true },
  )
}
