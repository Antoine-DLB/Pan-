// Full-screen, non-blocking colt animation played when a shot event arrives.
export default function ShotAnimation({ gatling, shooterName }) {
  return (
    <div className="bang-overlay" aria-hidden="true">
      <svg className={`colt ${gatling ? 'gatling' : ''}`} viewBox="0 0 130 70">
        <g className="gun" fill="#1e1610">
          <rect x="8" y="22" width="62" height="13" rx="4" />
          <circle cx="36" cy="36" r="11" />
          <path d="M27 44 L48 44 L39 68 L21 68 Z" />
          <rect x="48" y="38" width="5" height="10" rx="2" />
        </g>
        <g className="flash">
          <path
            d="M72 22 l16 -10 -7 10 17 -2 -15 8 18 6 -19 0 8 10 -16 -8 z"
            fill="#ffd35c"
          />
          <path d="M74 25 l10 -5 -4 6 9 0 -9 4 5 6 -10 -5 z" fill="#fff3c4" />
        </g>
      </svg>
      <div className="bang-text">{gatling ? 'RATATATA !' : 'PAN !'}</div>
      {shooterName && <div className="bang-source">{shooterName}</div>}
    </div>
  )
}
