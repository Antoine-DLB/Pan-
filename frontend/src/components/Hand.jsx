import Card from './Card'

export default function Hand({ cards, selectedUids, isPlayable, onTap }) {
  return (
    <div className="hand">
      {cards.map((card) => (
        <Card
          key={card.uid}
          card={card}
          selected={selectedUids.has(card.uid)}
          disabled={!isPlayable(card)}
          onClick={() => onTap(card)}
        />
      ))}
      {cards.length === 0 && <p className="muted">Main vide</p>}
    </div>
  )
}
