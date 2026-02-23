/**
 * Four colored relation badges shown below dialogue panel.
 */
export default function RelationBadges({ relations, sanctions, embargo }) {
  if (!relations) return null

  const npcs = [
    { key: 'usa',    label: 'USA' },
    { key: 'arabia', label: 'ARABIA' },
    { key: 'eu',     label: 'EU' },
    { key: 'dprg',   label: 'DPRG' },
  ]

  return (
    <div className="rel-row">
      {npcs.map(({ key, label }) => (
        <span key={key} className={`rel-badge ${key}`}>
          {label} {typeof relations[key] === 'number' ? Math.round(relations[key]) : (relations[key] ?? '—')}
          {key === 'usa' && sanctions ? ' ⚠️' : ''}
          {key === 'arabia' && embargo ? ' ⚠️' : ''}
        </span>
      ))}
    </div>
  )
}
