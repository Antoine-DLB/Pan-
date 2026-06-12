import { useEffect, useMemo, useState } from 'react'
import Card from '../components/Card'
import GameOver from '../components/GameOver'
import Hand from '../components/Hand'
import HealthBar from '../components/HealthBar'
import PlayerArc, { MiniCard } from '../components/PlayerArc'
import ReactionModal from '../components/ReactionModal'
import ShotAnimation from '../components/ShotAnimation'
import { ROLE_LABELS, TARGET_MODES } from '../constants'

export default function Game({ state, events, send, reset }) {
  const [selected, setSelected] = useState(null) // card in preview/confirm
  const [discardSel, setDiscardSel] = useState([])
  const [chooser, setChooser] = useState(null) // steal: pick hand vs table card
  const [peek, setPeek] = useState(null) // long-pressed card description
  const [bang, setBang] = useState(null) // shot animation

  const me = state.you
  const pending = state.pending
  const finished = state.phase === 'finished'
  const myTurn = state.turn_player_id === me.id && !finished

  // opponents in seat order, starting from the player after me
  const opponents = useMemo(() => {
    const idx = state.players.findIndex((p) => p.id === me.id)
    return [...state.players.slice(idx + 1), ...state.players.slice(0, idx)]
  }, [state.players, me.id])

  const nameOf = (id) => state.players.find((p) => p.id === id)?.name || '???'

  // reset transient UI state on every server-driven transition
  useEffect(() => {
    setSelected(null)
    setDiscardSel([])
    setChooser(null)
    setPeek(null)
  }, [state.phase, state.turn_player_id, pending?.type, pending?.responder_id])

  // shot events -> colt animation
  useEffect(() => {
    if (!events) return undefined
    const shot = events.list.find((e) => e.type === 'shot')
    if (!shot) return undefined
    setBang({
      key: events.seq,
      gatling: shot.gatling,
      shooter: nameOf(shot.source_id),
    })
    const timer = setTimeout(() => setBang(null), 1000)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events])

  const needsTarget = selected ? Boolean(TARGET_MODES[selected.id]) : false

  const eligibleIds = useMemo(() => {
    if (!selected || !needsTarget) return new Set()
    const mode = TARGET_MODES[selected.id]
    const set = new Set()
    for (const p of opponents) {
      if (!p.alive) continue
      if (mode === 'range' && !p.in_range) continue
      if (mode === 'close' && p.distance > 1) continue
      if (
        mode === 'jail' &&
        (p.role === 'sheriff' || p.table.some((c) => c.id === 'jail'))
      )
        continue
      set.add(p.id)
    }
    return set
  }, [selected, needsTarget, opponents])

  function isPlayable(card) {
    if (finished || !me.alive) return false
    if (state.phase === 'discard' && myTurn) return true
    if (!myTurn || state.phase !== 'play' || pending) return false
    if (card.id === 'dodge') return false
    if (card.id === 'shot' && !me.can_play_shot) return false
    return true
  }

  function tapCard(card) {
    if (state.phase === 'discard' && myTurn) {
      setDiscardSel((sel) =>
        sel.includes(card.uid)
          ? sel.filter((uid) => uid !== card.uid)
          : [...sel, card.uid],
      )
      return
    }
    if (!myTurn || state.phase !== 'play' || pending) return
    // first tap selects (preview + description), confirmation happens in the
    // play panel or by tapping a target — never play a card on a single tap
    setSelected(selected?.uid === card.uid ? null : card)
  }

  function confirmPlay() {
    if (!selected) return
    send({ action: 'play_card', card: selected.uid })
    setSelected(null)
  }

  function tapTarget(target) {
    if (!selected) return
    const stealing = selected.id === 'panic' || selected.id === 'cat_balou'
    if (stealing && target.table.length > 0) {
      setChooser({ target, card: selected })
      setSelected(null)
      return
    }
    send({ action: 'play_card', card: selected.uid, target: target.id })
    setSelected(null)
  }

  const overLimit = Math.max(0, me.hand.length - me.hp)
  const selectedUids = new Set(
    state.phase === 'discard' ? discardSel : selected ? [selected.uid] : [],
  )

  let banner
  if (finished) {
    banner = 'Partie terminée'
  } else if (pending) {
    banner =
      pending.responder_id === me.id
        ? 'À toi de réagir !'
        : `Réaction de ${nameOf(pending.responder_id)}…`
  } else if (myTurn) {
    banner = selected
      ? needsTarget
        ? `Choisis une cible pour « ${selected.name} »`
        : `Confirme pour jouer « ${selected.name} »`
      : {
          draw: 'À toi : pioche 2 cartes',
          play: 'À toi de jouer !',
          discard: `Défausse ${overLimit} carte(s)`,
        }[state.phase]
  } else {
    banner = `Tour de ${nameOf(state.turn_player_id)}`
  }

  return (
    <div className="game">
      <PlayerArc
        players={opponents}
        targeting={needsTarget}
        eligibleIds={eligibleIds}
        onTarget={tapTarget}
        onPeek={setPeek}
      />

      <div className="board">
        <div className="piles">
          <div className="pile deck">
            Pioche
            <br />
            {state.deck_count}
          </div>
          {state.discard_top && (
            <Card card={state.discard_top} small disabled onPeek={setPeek} />
          )}
        </div>
        <div className="turn-banner">{banner}</div>
        <div className="log-line">{state.log[state.log.length - 1]}</div>
        <div className="actions">
          {myTurn && state.phase === 'draw' && !pending && (
            <button className="btn primary" onClick={() => send({ action: 'draw' })}>
              Piocher 2 cartes
            </button>
          )}
          {myTurn && state.phase === 'play' && !pending && !selected && (
            <button className="btn" onClick={() => send({ action: 'end_turn' })}>
              Terminer le tour
            </button>
          )}
          {myTurn && state.phase === 'discard' && (
            <button
              className="btn primary"
              disabled={discardSel.length < overLimit}
              onClick={() => send({ action: 'discard', cards: discardSel })}
            >
              Défausser ({discardSel.length}/{overLimit})
            </button>
          )}
        </div>
      </div>

      <div className="me">
        {selected && (
          <div className="play-panel">
            <div className="play-desc">
              <strong>{selected.name}</strong>
              <span>{selected.effect}</span>
            </div>
            <div className="actions">
              {!needsTarget && (
                <button className="btn primary" onClick={confirmPlay}>
                  Jouer
                </button>
              )}
              <button className="btn link" onClick={() => setSelected(null)}>
                Annuler
              </button>
            </div>
          </div>
        )}
        <div className="status-row">
          <span className="role-badge">{ROLE_LABELS[me.role]}</span>
          {me.alive ? (
            <HealthBar hp={me.hp} maxHp={me.max_hp} />
          ) : (
            <span className="muted">Éliminé — mode spectateur</span>
          )}
          <span className="muted">portée {me.attack_range}</span>
        </div>
        {me.table.length > 0 && (
          <div className="mini-cards">
            {me.table.map((c) => (
              <MiniCard key={c.uid} card={c} onPeek={setPeek} />
            ))}
          </div>
        )}
        <Hand
          cards={me.hand}
          selectedUids={selectedUids}
          isPlayable={isPlayable}
          onTap={tapCard}
          onPeek={setPeek}
        />
      </div>

      {peek && (
        <div className="peek">
          <strong>{peek.name}</strong>
          {peek.range != null && <span className="muted"> · portée {peek.range}</span>}
          <p>{peek.effect}</p>
        </div>
      )}

      {chooser && (
        <div className="modal-backdrop" onClick={() => setChooser(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>
              {chooser.card.name} → {chooser.target.name}
            </h3>
            {chooser.target.hand_count > 0 && (
              <button
                className="btn"
                onClick={() => {
                  send({
                    action: 'play_card',
                    card: chooser.card.uid,
                    target: chooser.target.id,
                  })
                  setChooser(null)
                }}
              >
                Une carte au hasard de sa main
              </button>
            )}
            <p className="muted">ou une carte en jeu :</p>
            <div className="card-row">
              {chooser.target.table.map((c) => (
                <Card
                  key={c.uid}
                  card={c}
                  small
                  onPeek={setPeek}
                  onClick={() => {
                    send({
                      action: 'play_card',
                      card: chooser.card.uid,
                      target: chooser.target.id,
                      target_card: c.uid,
                    })
                    setChooser(null)
                  }}
                />
              ))}
            </div>
            <button className="btn link" onClick={() => setChooser(null)}>
              Annuler
            </button>
          </div>
        </div>
      )}

      {bang && (
        <ShotAnimation
          key={bang.key}
          gatling={bang.gatling}
          shooterName={bang.shooter}
        />
      )}

      {pending && me.alive && !finished && (
        <ReactionModal state={state} send={send} onPeek={setPeek} />
      )}
      {finished && <GameOver state={state} reset={reset} />}
    </div>
  )
}
