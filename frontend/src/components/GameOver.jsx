import { ROLE_LABELS, TEAM_LABELS } from '../constants'

export default function GameOver({ state, reset }) {
  const winners = new Set(state.winners)
  return (
    <div className="modal-backdrop">
      <div className="modal gameover">
        <h3>Fin de la partie</h3>
        <div className="team">{TEAM_LABELS[state.winning_team]} l'emporte !</div>
        <ul className="reveal-list">
          {state.players.map((p) => (
            <li key={p.id} className={winners.has(p.id) ? 'winner' : ''}>
              <span>{p.name}</span>
              <span>{ROLE_LABELS[p.role]}</span>
            </li>
          ))}
        </ul>
        <button className="btn primary" onClick={reset}>
          Nouvelle partie
        </button>
      </div>
    </div>
  )
}
