/**
 * Four colored relation badges shown below dialogue panel.
 * Priority 6: Shows ★ when a relations 100 unlock is active for that NPC.
 */
export default function RelationBadges({ relations, sanctions, embargo, unlocks }) {
  if (!relations) return null

  const npcs = [
    { key: 'usa',    label: 'USA' },
    { key: 'arabia', label: 'ARABIA' },
    { key: 'eu',     label: 'EU' },
    { key: 'dprg',   label: 'DPRG' },
  ]

  const UNLOCK_LABELS = {
    usa: 'Special Relationship',
    arabia: 'Blood Brothers',
    eu: 'Full Integration',
    dprg: 'Shadow Alliance',
  }

  return (
    <div className="rel-row">
      {npcs.map(({ key, label }) => {
        const hasUnlock = unlocks?.[key]
        return (
          <span key={key} className={`rel-badge ${key} ${hasUnlock ? 'rel-badge-unlocked' : ''}`}>
            {label} {typeof relations[key] === 'number' ? Math.round(relations[key]) : (relations[key] ?? '—')}
            {key === 'usa' && sanctions ? ' ⚠️' : ''}
            {key === 'arabia' && embargo ? ' ⚠️' : ''}
            {hasUnlock && (
              <span className="rel-unlock-star" title={UNLOCK_LABELS[key]}>★</span>
            )}
          </span>
        )
      })}
    </div>
  )
}
