export default function HealthBar({ hp, maxHp }) {
  return (
    <div className="hearts" aria-label={`${hp} points de vie sur ${maxHp}`}>
      {Array.from({ length: maxHp }, (_, i) => (
        <span key={i} className={i < hp ? 'full' : 'empty'}>
          ♥
        </span>
      ))}
    </div>
  )
}
