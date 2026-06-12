import Card from './Card'

// Modal shown when a reaction is expected. The responder gets action buttons;
// for the general store every player sees the revealed cards.
export default function ReactionModal({ state, send, onPeek }) {
  const pending = state.pending
  const me = state.you
  const iRespond = pending.responder_id === me.id

  const nameOf = (id) =>
    state.players.find((p) => p.id === id)?.name || '???'

  if (!iRespond && pending.type !== 'general_store') return null

  const dodge = me.hand.find((c) => c.id === 'dodge')
  const shot = me.hand.find((c) => c.id === 'shot')
  const beer = me.hand.find((c) => c.id === 'beer')

  let title = ''
  let body = null

  if (pending.type === 'shot') {
    title = pending.gatling
      ? `${nameOf(pending.source_id)} arrose tout le monde !`
      : `${nameOf(pending.source_id)} te tire dessus !`
    body = (
      <>
        {dodge && (
          <button
            className="btn primary"
            onClick={() => send({ action: 'react', react: 'dodge', card: dodge.uid })}
          >
            Jouer une Esquive
          </button>
        )}
        {pending.can_barrel && (
          <button
            className="btn"
            onClick={() => send({ action: 'react', react: 'barrel' })}
          >
            Tenter le Tonneau
          </button>
        )}
        <button
          className="btn danger"
          onClick={() => send({ action: 'react', react: 'take' })}
        >
          Encaisser (-1 PV)
        </button>
      </>
    )
  } else if (pending.type === 'indians') {
    title = `Embuscade de ${nameOf(pending.source_id)} !`
    body = (
      <>
        {shot && (
          <button
            className="btn primary"
            onClick={() =>
              send({ action: 'react', react: 'discard_shot', card: shot.uid })
            }
          >
            Défausser un Tir
          </button>
        )}
        <button
          className="btn danger"
          onClick={() => send({ action: 'react', react: 'take' })}
        >
          Subir (-1 PV)
        </button>
      </>
    )
  } else if (pending.type === 'duel') {
    const opponentId =
      pending.source_id === me.id ? pending.other_id : pending.source_id
    title = `Duel contre ${nameOf(opponentId)} !`
    body = (
      <>
        {shot && (
          <button
            className="btn primary"
            onClick={() =>
              send({ action: 'react', react: 'discard_shot', card: shot.uid })
            }
          >
            Riposter (défausser un Tir)
          </button>
        )}
        <button
          className="btn danger"
          onClick={() => send({ action: 'react', react: 'take' })}
        >
          Abandonner (-1 PV)
        </button>
      </>
    )
  } else if (pending.type === 'death') {
    title = 'Dernier souffle…'
    body = (
      <>
        <p>Tu es sur le point de mourir.</p>
        {beer && (
          <button
            className="btn primary"
            onClick={() => send({ action: 'react', react: 'beer', card: beer.uid })}
          >
            Boire une Gnôle (+1 PV)
          </button>
        )}
        <button
          className="btn danger"
          onClick={() => send({ action: 'react', react: 'die' })}
        >
          Mourir
        </button>
      </>
    )
  } else if (pending.type === 'general_store') {
    title = iRespond
      ? 'Bazar — choisis une carte'
      : `Bazar — ${nameOf(pending.responder_id)} choisit…`
    body = (
      <div className="card-row">
        {pending.cards.map((card) => (
          <Card
            key={card.uid}
            card={card}
            small
            disabled={!iRespond}
            onClick={() => send({ action: 'pick_store', card: card.uid })}
            onPeek={onPeek}
          />
        ))}
      </div>
    )
  }

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <h3>{title}</h3>
        {iRespond && <div className="countdown" key={pending.responder_id} />}
        {body}
      </div>
    </div>
  )
}
