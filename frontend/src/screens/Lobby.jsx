export default function Lobby({ session, lobby, send, reset }) {
  const isHost = session.player_id === lobby.host_id
  const count = lobby.players.length

  return (
    <div className="screen lobby">
      <h2>Salle d'attente</h2>
      <div className="room-code" aria-label="Code de la partie">
        {lobby.code}
      </div>
      <p className="muted">Partage ce code avec les autres joueurs</p>

      <ul className="player-list">
        {lobby.players.map((p) => (
          <li key={p.id} className={p.connected ? '' : 'offline'}>
            <span className={`dot ${p.connected ? 'on' : 'off'}`} />
            {p.name}
            {p.id === lobby.host_id && <span className="tag">hôte</span>}
            {p.id === session.player_id && <span className="tag you">toi</span>}
          </li>
        ))}
      </ul>

      <p className="muted">{count}/7 joueurs · minimum 4</p>

      {isHost ? (
        <button
          className="btn primary"
          disabled={!lobby.can_start}
          onClick={() => send({ action: 'start' })}
        >
          {lobby.can_start ? 'Lancer la partie' : 'En attente de joueurs…'}
        </button>
      ) : (
        <p className="muted">En attente du lancement par l'hôte…</p>
      )}

      <button className="btn link" onClick={reset}>
        Quitter
      </button>
    </div>
  )
}
