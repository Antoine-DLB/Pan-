import { useRef } from 'react'

// Long-press helper: calls show() after `delay` ms of continuous press and
// hide() on release. didFire() lets the caller swallow the click that
// follows a long press so the card is not played by accident.
export default function useLongPress(show, hide, delay = 350) {
  const timer = useRef(null)
  const fired = useRef(false)

  const start = () => {
    fired.current = false
    clearTimeout(timer.current)
    timer.current = setTimeout(() => {
      fired.current = true
      show()
    }, delay)
  }

  const end = () => {
    clearTimeout(timer.current)
    if (fired.current) hide()
  }

  const didFire = () => {
    const f = fired.current
    fired.current = false
    return f
  }

  return {
    didFire,
    handlers: {
      onPointerDown: start,
      onPointerUp: end,
      onPointerLeave: end,
      onPointerCancel: end,
      onContextMenu: (e) => e.preventDefault(),
    },
  }
}
