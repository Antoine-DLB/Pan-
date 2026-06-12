import { SUIT_SYMBOLS } from '../constants'
import useLongPress from '../hooks/useLongPress'
import { CARD_ART } from './cardArt'

export default function Card({ card, small, selected, disabled, onClick, onPeek }) {
  const press = useLongPress(
    () => onPeek && onPeek(card),
    () => onPeek && onPeek(null),
  )

  const handleClick = () => {
    if (press.didFire()) return // a long press is a peek, not a play
    if (!disabled && onClick) onClick()
  }

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
    <div className={classes} onClick={handleClick} {...press.handlers}>
      <div className="card-name">{card.name}</div>
      {CARD_ART[card.id] && (
        <img
          className="card-art"
          src={CARD_ART[card.id]}
          alt=""
          draggable="false"
        />
      )}
      <div className="card-bottom">
        {card.range != null && <span className="card-range">Portée {card.range}</span>}
        <span className={`card-corner ${red ? 'red' : 'black'}`}>
          {card.value}
          {SUIT_SYMBOLS[card.suit]}
        </span>
      </div>
    </div>
  )
}
