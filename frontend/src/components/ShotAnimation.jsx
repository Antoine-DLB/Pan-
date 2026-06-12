// Full-screen, non-blocking colt animation played when a shot event arrives.
export default function ShotAnimation({ gatling, shooterName }) {
  return (
    <div className="bang-overlay" aria-hidden="true">
      <div className="screen-flash" />
      <svg className={`colt ${gatling ? 'gatling' : ''}`} viewBox="0 0 260 130">
        <g className="gun">
          <path d="M30 38 L17 26 L30 20 L39 35 Z" fill="#2f3640" />
          <rect x="24" y="44" width="84" height="20" rx="6" fill="#2f3640" />
          <rect x="24" y="47" width="84" height="6" rx="3" fill="#46525e" />
          <rect x="98" y="33" width="8" height="14" rx="3" fill="#2f3640" />
          <rect x="42" y="38" width="34" height="33" rx="9" fill="#3d4a55" />
          <circle cx="53" cy="49" r="3.6" fill="#222b33" />
          <circle cx="66" cy="49" r="3.6" fill="#222b33" />
          <circle cx="59.5" cy="62" r="3.6" fill="#222b33" />
          <path
            d="M36 71 C32 90 41 108 57 114 L71 106 C66 92 68 79 73 71 Z"
            fill="#8a5a33"
          />
          <path
            d="M41 75 C39 88 45 99 55 105 L61 102 C56 91 58 81 61 74 Z"
            fill="#a06b3d"
            opacity="0.5"
          />
          <path
            d="M76 72 q14 2 14 14 q0 9 -11 9"
            fill="none"
            stroke="#2f3640"
            strokeWidth="5"
            strokeLinecap="round"
          />
        </g>
        <g className="flash">
          <path
            d="M108 50 L168 22 L140 50 L186 40 L146 56 L184 70 L142 62 L166 92 L112 64 Z"
            fill="#e0a83c"
          />
          <path
            d="M110 52 L150 33 L132 51 L160 46 L134 56 L156 66 L132 60 L146 80 L112 62 Z"
            fill="#f6c45e"
          />
          <path
            d="M112 53 L138 41 L127 52 L144 50 L128 57 L140 63 L126 60 L132 70 L113 60 Z"
            fill="#fff3c4"
          />
        </g>
        <g className="smoke" fill="#d8d3c8">
          <circle cx="150" cy="26" r="10" opacity="0.55" />
          <circle cx="172" cy="16" r="13" opacity="0.4" />
          <circle cx="198" cy="10" r="16" opacity="0.25" />
        </g>
      </svg>
      <div className="bang-text">{gatling ? 'RATATATA !' : 'PAN !'}</div>
      {shooterName && <div className="bang-source">{shooterName}</div>}
    </div>
  )
}
