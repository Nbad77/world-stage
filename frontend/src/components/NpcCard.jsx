/**
 * NpcCard — Single NPC relationship card for the right sidebar.
 * Shows portrait, name, relation bar (color-coded), and one-line status.
 * Border color reflects relationship health.
 * Session 7A Step 1.
 */
export default function NpcCard({ npcKey, label, flag, relation, subtitle, hasWarning, isPlaceholder, color }) {
  // Determine health tier
  const healthClass = isPlaceholder ? 'placeholder'
    : relation >= 60 ? 'health-good'
    : relation >= 30 ? 'health-warn'
    : 'health-bad'

  // Bar fill color
  const barColor = isPlaceholder ? '#333'
    : relation >= 60 ? 'var(--success)'
    : relation >= 30 ? 'var(--warning)'
    : 'var(--danger)'

  // Status text derived from relation level
  const statusText = isPlaceholder ? ''
    : relation >= 80 ? 'Strong ally'
    : relation >= 60 ? 'Cooperative'
    : relation >= 40 ? 'Neutral'
    : relation >= 25 ? 'Strained'
    : 'Hostile'

  // Portrait background color
  const portraitBg = isPlaceholder ? '#1a1a1a' : (color || 'var(--ws-chrome)')

  return (
    <div className={`npc-card ${healthClass}`}>
      <div className="npc-card-header">
        <div
          className="npc-portrait"
          style={{ background: portraitBg, borderColor: isPlaceholder ? '#333' : portraitBg }}
        >
          {flag}
        </div>
        <div>
          <div className="npc-card-name" style={isPlaceholder ? { color: '#555' } : {}}>
            {label}
          </div>
          {subtitle && (
            <div className="npc-card-subtitle">{subtitle}</div>
          )}
        </div>
      </div>

      {isPlaceholder ? (
        <div className="npc-card-coming">Coming Soon</div>
      ) : (
        <>
          <div className="npc-rel-bar-track">
            <div
              className="npc-rel-bar-fill"
              style={{ width: `${Math.max(0, Math.min(100, relation))}%`, background: barColor }}
            />
          </div>
          <div className="npc-card-status">
            {statusText} ({Math.round(relation)})
          </div>
          {hasWarning && (
            <div className="npc-card-warning">
              {npcKey === 'usa' ? '⚠ Sanctions active' : '⚠ Embargo active'}
            </div>
          )}
        </>
      )}
    </div>
  )
}
