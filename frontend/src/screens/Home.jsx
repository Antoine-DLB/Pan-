import { useState } from 'react'

const NAME_KEY = 'fws_name'

export default function Home({ send, connected }) {
  const [name, setName] = useState(localStorage.getItem(NAME_KEY) || '')
  const [code, setCode] = useState('')

  const saveName = () => localStorage.setItem(NAME_KEY, name.trim())

  const create = () => {
    saveName()
    send({ action: 'create', name })
  }

  const join = () => {
    saveName()
    send({ action: 'join', code: code.trim().toUpperCase(), name })
  }

  const ready = connected && name.trim().length > 0

  return (
    <div className="screen home">
      <h1 className="title">Far West Showdown</h1>
      <p className="subtitle">Jeu de cartes western · 4 à 7 joueurs</p>

      <label className="field">
        <span>Ton pseudo</span>
        <input
          value={name}
          maxLength={20}
          placeholder="Calamity Jeanne"
          onChange={(e) => setName(e.target.value)}
        />
      </label>

      <button className="btn primary" disabled={!ready} onClick={create}>
        Créer une partie
      </button>

      <div className="separator">ou</div>

      <div className="join-row">
        <input
          value={code}
          maxLength={5}
          placeholder="CODE"
          className="code-input"
          onChange={(e) => setCode(e.target.value.toUpperCase())}
        />
        <button
          className="btn"
          disabled={!ready || code.trim().length !== 5}
          onClick={join}
        >
          Rejoindre
        </button>
      </div>

      {!connected && <p className="muted">Connexion au serveur…</p>}
    </div>
  )
}
