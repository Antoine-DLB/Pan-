import useGameSocket from './hooks/useGameSocket'
import Home from './screens/Home'
import Lobby from './screens/Lobby'
import Game from './screens/Game'

export default function App() {
  const { connected, session, lobby, gameState, events, error, send, reset } =
    useGameSocket()

  let screen
  if (gameState && session) {
    screen = (
      <Game
        state={gameState}
        session={session}
        events={events}
        send={send}
        reset={reset}
      />
    )
  } else if (session && lobby) {
    screen = <Lobby session={session} lobby={lobby} send={send} reset={reset} />
  } else {
    screen = <Home send={send} connected={connected} />
  }

  return (
    <>
      {!connected && (session || lobby || gameState) && (
        <div className="banner">Reconnexion en cours…</div>
      )}
      {error && <div className="toast">{error}</div>}
      {screen}
    </>
  )
}
