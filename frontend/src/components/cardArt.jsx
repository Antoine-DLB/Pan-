// Hand-drawn SVG pictograms for every playable card (original artwork).
// Icons use fill="currentColor" so the card CSS controls the color.
// To swap in bitmap illustrations later, replace entries of CARD_ART with
// <img src={...} alt="" /> using the same card ids.

const Pistol = () => (
  <g>
    <rect x="4" y="14" width="36" height="8" rx="3" />
    <circle cx="19" cy="23" r="8" />
    <path d="M14 28 L27 28 L21 44 L10 44 Z" />
    <rect x="28" y="24" width="4" height="8" rx="2" />
  </g>
)

const Rifle = ({ barrel }) => (
  <g>
    <rect x="3" y="20" width={barrel} height="5" rx="2" />
    <rect x={3 + barrel - 3} y="18" width="10" height="9" rx="2" />
    <path
      d={`M${3 + barrel + 5} 19 l7 0 l9 17 l-8 5 l-9 -15 l-3 0 z`}
    />
  </g>
)

export const CARD_ART = {
  shot: (
    <g>
      <Pistol />
      <path d="M41 12 l5 -4 -2 5 4 1 -5 2 1 5 -4 -4 z" opacity="0.9" />
    </g>
  ),
  dodge: (
    <g>
      <g fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round">
        <path d="M6 12 Q20 8 34 12" />
        <path d="M6 22 Q22 18 36 22" />
        <path d="M6 32 Q20 28 30 32" />
      </g>
      <path d="M34 26 L46 32 L34 40 Z" />
    </g>
  ),
  beer: (
    <g>
      <rect x="10" y="14" width="20" height="26" rx="3" />
      <path d="M30 20 h6 a5 5 0 0 1 5 5 v6 a5 5 0 0 1 -5 5 h-6 v-5 h5 a1 1 0 0 0 1 -1 v-4 a1 1 0 0 0 -1 -1 h-5 z" />
      <rect x="8" y="8" width="24" height="7" rx="3.5" opacity="0.75" />
    </g>
  ),
  panic: (
    <g>
      <rect x="7" y="10" width="16" height="24" rx="2" transform="rotate(-12 15 22)" />
      <rect x="22" y="13" width="16" height="24" rx="2" opacity="0.8" transform="rotate(10 30 25)" />
      <path d="M30 4 L44 8 L34 16 Z" opacity="0.9" />
    </g>
  ),
  cat_balou: (
    <g>
      <circle cx="12" cy="37" r="5" fill="none" stroke="currentColor" strokeWidth="4" />
      <circle cx="27" cy="41" r="5" fill="none" stroke="currentColor" strokeWidth="4" />
      <g stroke="currentColor" strokeWidth="5" strokeLinecap="round">
        <path d="M15 33 L39 7" />
        <path d="M29 36 L11 7" />
      </g>
    </g>
  ),
  stagecoach: (
    <g>
      <rect x="7" y="10" width="28" height="15" rx="2" />
      <rect x="11" y="13" width="7" height="6" fill="#00000055" />
      <rect x="22" y="13" width="7" height="6" fill="#00000055" />
      <circle cx="14" cy="34" r="7" fill="none" stroke="currentColor" strokeWidth="4" />
      <circle cx="33" cy="34" r="7" fill="none" stroke="currentColor" strokeWidth="4" />
    </g>
  ),
  wells_fargo: (
    <g>
      <path d="M8 20 a16 11 0 0 1 32 0 z" />
      <rect x="8" y="21" width="32" height="17" rx="2" />
      <rect x="20" y="23" width="8" height="9" rx="1" fill="#00000055" />
    </g>
  ),
  gatling: (
    <g>
      <rect x="4" y="12" width="30" height="5" rx="2.5" />
      <rect x="4" y="19" width="30" height="5" rx="2.5" />
      <rect x="4" y="26" width="30" height="5" rx="2.5" />
      <circle cx="37" cy="21" r="8" />
      <path d="M20 32 L29 45 H11 Z" />
    </g>
  ),
  indians: (
    <g>
      <g stroke="currentColor" strokeWidth="4" strokeLinecap="round">
        <path d="M9 39 L39 9" />
        <path d="M9 9 L39 39" />
      </g>
      <path d="M33 5 L44 4 L43 15 Z" />
      <path d="M43 33 L44 44 L33 43 Z" />
      <path d="M5 33 L4 44 L15 43 Z" />
      <path d="M15 5 L4 4 L5 15 Z" />
    </g>
  ),
  duel: (
    <g>
      <rect x="2" y="20" width="13" height="8" rx="4" />
      <rect x="33" y="20" width="13" height="8" rx="4" />
      <path d="M24 13 l2.5 6 6 -2 -4 6 4 6 -6 -2 -2.5 6 -2.5 -6 -6 2 4 -6 -4 -6 6 2 z" />
    </g>
  ),
  general_store: (
    <g>
      <rect x="9" y="22" width="30" height="18" />
      <path d="M6 12 h36 l4 9 H2 z" />
      <rect x="20" y="27" width="8" height="13" fill="#00000055" />
    </g>
  ),
  saloon: (
    <g>
      <path d="M5 8 h38 v4 H5 z" />
      <rect x="6" y="12" width="4" height="30" rx="2" />
      <rect x="38" y="12" width="4" height="30" rx="2" />
      <rect x="13" y="14" width="10" height="22" rx="2" />
      <rect x="25" y="14" width="10" height="22" rx="2" />
    </g>
  ),
  volcanic: (
    <g>
      <g transform="translate(7 0)">
        <Pistol />
      </g>
      <g stroke="currentColor" strokeWidth="3" strokeLinecap="round">
        <path d="M2 10 L7 10" />
        <path d="M0 17 L5 17" />
        <path d="M2 24 L7 24" />
      </g>
    </g>
  ),
  schofield: (
    <g>
      <Pistol />
      <circle cx="19" cy="23" r="3" fill="#00000055" />
    </g>
  ),
  remington: <Rifle barrel={20} />,
  rev_carabine: <Rifle barrel={25} />,
  winchester: <Rifle barrel={30} />,
  mustang: (
    <path d="M24 5 a17 17 0 0 1 17 17 c0 8.5 -4.5 15 -9 21 l-6.5 -4.5 c4.5 -5.5 8 -10.5 8 -16.5 a9.5 9.5 0 0 0 -19 0 c0 6 3.5 11 8 16.5 L16 43 c-4.5 -6 -9 -12.5 -9 -21 A17 17 0 0 1 24 5 z" />
  ),
  scope: (
    <g transform="rotate(-30 24 24)">
      <rect x="4" y="19" width="13" height="10" rx="3" />
      <rect x="17" y="20.5" width="13" height="7" rx="2" />
      <rect x="30" y="22" width="12" height="4" rx="2" />
    </g>
  ),
  barrel: (
    <g>
      <path d="M14 6 h20 c3.5 9 3.5 27 0 36 h-20 c-3.5 -9 -3.5 -27 0 -36 z" />
      <rect x="10" y="15" width="28" height="3.5" fill="#00000055" />
      <rect x="10" y="29" width="28" height="3.5" fill="#00000055" />
    </g>
  ),
  jail: (
    <g>
      <rect x="7" y="7" width="34" height="34" rx="3" fill="none" stroke="currentColor" strokeWidth="4" />
      <g stroke="currentColor" strokeWidth="4" strokeLinecap="round">
        <path d="M17 9 V39" />
        <path d="M24 9 V39" />
        <path d="M31 9 V39" />
      </g>
    </g>
  ),
  dynamite: (
    <g>
      <rect x="16" y="16" width="13" height="28" rx="4" transform="rotate(18 22 30)" />
      <path d="M28 14 q5 -8 12 -7" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <path d="M40 3 l2 4 4 -1 -3 4 3 4 -4 -1 -2 4 -1.5 -4.5 -4.5 0.5 3 -4 -3 -4 4.5 0.5 z" />
    </g>
  ),
}

export default function CardArt({ cardId }) {
  const art = CARD_ART[cardId]
  if (!art) return null
  return (
    <svg className="card-art" viewBox="0 0 48 48" aria-hidden="true">
      {art}
    </svg>
  )
}
