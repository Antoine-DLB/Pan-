import HealthBar from './HealthBar'
import useLongPress from '../hooks/useLongPress'
import { ROLE_LABELS } from '../constants'

// Equipment chip on a player: long-press shows the card's effect.
export function MiniCard({ card, onPeek }) {
  const press = useLongPress(
    () => onPeek && onPeek(card),
    () => onPeek && onPeek(null),
  )
  return (
    <span className="mini-card" {...press.handlers}>
      {card.name}
    </span>
  )
}

export default function PlayerArc({ players, targeting, eligibleIds, onTarget, onPeek }) {
  return (
    <div className="opponents">
      {players.map((p) => {
        const targetable = targeting && p.alive && eligibleIds.has(p.id)
        const classes = [
          'opponent',
          p.is_turn ? 'turn' : '',
          p.alive ? '' : 'dead',
          targeting ? (targetable ? 'targetable' : 'untargetable') : '',
        ]
          .filter(Boolean)
          .join(' ')
        return (
          <div
            key={p.id}
            className={classes}
            onClick={targetable ? () => onTarget(p) : undefined}
          >
            <div className="name-row">
              {p.is_turn ? '▶ ' : ''}
              {p.name}
            </div>
            {p.role && <span className="role-badge">{ROLE_LABELS[p.role]}</span>}
            {p.alive ? (
              <HealthBar hp={p.hp} maxHp={p.max_hp} />
            ) : (
              <span className="role-badge">Éliminé</span>
            )}
            <div className="meta">
              <span>🂠 {p.hand_count}</span>
              {p.distance != null && <span>dist. {p.distance}</span>}
            </div>
            {p.table.length > 0 && (
              <div className="mini-cards">
                {p.table.map((c) => (
                  <MiniCard key={c.uid} card={c} onPeek={onPeek} />
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
