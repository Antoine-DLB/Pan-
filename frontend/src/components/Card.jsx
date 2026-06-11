import { SUIT_SYMBOLS } from '../constants'

export default function Card({ card, small, selected, disabled, onClick }) {
  const red = card.suit === 'hearts' || card.suit === 'diamonds'
  const classes = [
    'card',
    card.type,
    small ? 'small' : '',
    selected ? 'selected' : '',
    disabled ? 'disabled' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={classes} onClick={disabled ? undefined : onClick}>
      <div>
        <div className="card-name">{card.name}</div>
        {card.range != null && <div className="card-range">Portée {card.range}</div>}
      </div>
      <div className={`card-corner ${red ? 'red' : 'black'}`}>
        {card.value}
        {SUIT_SYMBOLS[card.suit]}
      </div>
    </div>
  )
}
