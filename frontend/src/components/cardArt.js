// Map card id -> bundled illustration URL. Every SVG in assets/cards/ is
// picked up automatically: to reskin a card, replace its file (any format
// Vite can bundle) while keeping the same base name (card id).
const modules = import.meta.glob('../assets/cards/*.svg', {
  eager: true,
  query: '?url',
  import: 'default',
})

export const CARD_ART = Object.fromEntries(
  Object.entries(modules).map(([path, url]) => [
    path.split('/').pop().replace('.svg', ''),
    url,
  ]),
)
