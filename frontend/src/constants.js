export const ROLE_LABELS = {
  sheriff: 'Shérif',
  deputy: 'Adjoint',
  outlaw: 'Hors-la-loi',
  renegade: 'Renégat',
}

export const TEAM_LABELS = {
  law: 'Le camp du Shérif',
  outlaws: 'Les Hors-la-loi',
  renegade: 'Le Renégat',
}

export const SUIT_SYMBOLS = {
  hearts: '♥',
  diamonds: '♦',
  clubs: '♣',
  spades: '♠',
}

// Cards that need a target, and how eligible targets are filtered.
export const TARGET_MODES = {
  shot: 'range',   // within weapon range
  panic: 'close',  // distance <= 1
  cat_balou: 'any',
  duel: 'any',
  jail: 'jail',    // anyone but the sheriff (and not already jailed)
}
