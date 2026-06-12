import { useCallback, useEffect, useRef, useState } from 'react'

// Session tokens are kept in localStorage so a page reload rejoins the game.
// For testing several players on one device, a "?p=2" query param gives each
// tab its own token slot.
const SLOT = new URLSearchParams(window.location.search).get('p')
const TOKEN_KEY = SLOT ? `fws_token_${SLOT}` : 'fws_token'

// Single WebSocket connection to the server: auto-reconnects with exponential
// backoff and resumes the session with the stored token after a page reload.
export default function useGameSocket() {
  const [connected, setConnected] = useState(false)
  const [session, setSession] = useState(null)
  const [lobby, setLobby] = useState(null)
  const [gameState, setGameState] = useState(null)
  const [events, setEvents] = useState(null) // {seq, list} — animations/sounds
  const [error, setError] = useState(null)
  const wsRef = useRef(null)
  const retryRef = useRef(0)
  const stoppedRef = useRef(false)
  const eventSeqRef = useRef(0)

  const send = useCallback((payload) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload))
    }
  }, [])

  useEffect(() => {
    stoppedRef.current = false

    function connect() {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const ws = new WebSocket(`${proto}//${window.location.host}/ws`)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        retryRef.current = 0
        const token = localStorage.getItem(TOKEN_KEY)
        if (token) {
          ws.send(JSON.stringify({ action: 'reconnect', token }))
        }
      }

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        switch (msg.type) {
          case 'session':
            localStorage.setItem(TOKEN_KEY, msg.token)
            setSession(msg)
            break
          case 'lobby':
            setLobby(msg)
            break
          case 'state':
            setGameState(msg.state)
            if (msg.events && msg.events.length > 0) {
              eventSeqRef.current += 1
              setEvents({ seq: eventSeqRef.current, list: msg.events })
            }
            break
          case 'error':
            setError(msg.message)
            break
          case 'session_expired':
            localStorage.removeItem(TOKEN_KEY)
            break
          default:
            break
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (stoppedRef.current) return
        const delay = Math.min(1000 * 2 ** retryRef.current, 10000)
        retryRef.current += 1
        setTimeout(() => {
          if (!stoppedRef.current) connect()
        }, delay)
      }
    }

    connect()
    return () => {
      stoppedRef.current = true
      wsRef.current?.close()
    }
  }, [])

  // errors are transient toasts
  useEffect(() => {
    if (!error) return undefined
    const timer = setTimeout(() => setError(null), 4000)
    return () => clearTimeout(timer)
  }, [error])

  const reset = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    window.location.reload()
  }, [])

  return { connected, session, lobby, gameState, events, error, send, reset }
}
