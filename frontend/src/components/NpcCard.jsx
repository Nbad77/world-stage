/**
 * NpcCard — Single NPC relationship card for the right sidebar.
 * Shows portrait, name, relation bar (color-coded), and one-line status.
 * Border color reflects relationship health.
 * Session 7A Step 1.  Session 8A: All 6 NPCs are active (no passive concept).
 * Session 7D Step 2: Backchannel button with detection risk.
 */

// Client-side detection risk calculator (mirrors npc_engine.calculate_detection_risk)
const BASE_RISK = { usa: 0.25, arabia: 0.20, eu: 0.15, dprg: 0.10, russia: 0.20, china: 0.18 }
const OPSEC_MULT = { 0: 1.0, 1: 0.7, 2: 0.45 }

function calcDetectionRisk(npcKey, gs) {
  const base = BASE_RISK[npcKey] ?? 0.20
  const opsec = gs?.opsec_level ?? 0
  const mult = OPSEC_MULT[opsec] ?? 1.0
  let risk = base * mult

  // NPC-specific modifiers
  const rel = gs?.relations || {}
  if (npcKey === 'usa' && (rel.usa ?? 50) < 30) risk *= 1.3
  if (npcKey === 'eu' && (rel.eu ?? 50) < 30) risk *= 1.2
  if (npcKey === 'dprg') risk *= 0.8

  return Math.min(1.0, risk)
}

function riskTier(risk) {
  if (risk < 0.15) return { label: 'LOW',      color: '#4db6ac' }
  if (risk < 0.30) return { label: 'MODERATE', color: '#ffb74d' }
  if (risk < 0.50) return { label: 'HIGH',     color: '#ff8a65' }
  return              { label: 'CRITICAL', color: '#ef5350' }
}

const MIN_INTEL_TIER = 1
const INTEL_COST = 1.5

export default function NpcCard({ npcKey, label, flag, relation, subtitle, hasWarning, isPlaceholder, color, onContact, contactDisabled, onBackchannel, backchannelDisabled, onGetIntel, intelLoading, cable, gs }) {
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
          {/* Contact button — all NPCs */}
          {onContact && (
            <button
              className="npc-contact-btn"
              onClick={() => onContact(npcKey)}
              disabled={contactDisabled}
              title={contactDisabled ? 'Contact unavailable' : `Open diplomatic channel with ${label}`}
            >
              Contact
            </button>
          )}
          {/* Session 7D: Backchannel button — all NPCs */}
          {onBackchannel && gs && (() => {
            const risk = calcDetectionRisk(npcKey, gs)
            const tier = riskTier(risk)
            return (
              <button
                className="npc-backchannel-btn"
                onClick={() => onBackchannel(npcKey)}
                disabled={backchannelDisabled}
                title={backchannelDisabled ? 'Backchannel unavailable' : `Open covert channel with ${label}`}
                style={{ '--risk-color': tier.color }}
              >
                🔒 BACKCHANNEL — <span className="backchannel-risk-label" style={{ color: tier.color }}>{tier.label}</span>
              </button>
            )
          })()}
          {/* 10B-2: GET INTEL button */}
          {onGetIntel && gs && (() => {
            const intelGated = (gs.intelligence_tier ?? 0) < MIN_INTEL_TIER
            return (
              <button
                className={`npc-intel-btn ${intelGated ? 'locked' : ''}`}
                onClick={() => onGetIntel(npcKey)}
                disabled={intelGated || intelLoading}
              >
                {intelGated
                  ? `🔒 INTEL — Requires Intel Tier ${MIN_INTEL_TIER}`
                  : intelLoading
                    ? '📡 INTERCEPTING...'
                    : `📡 GET INTEL — $${INTEL_COST}B budget`}
              </button>
            )
          })()}
          {/* 10B-2: Diplomatic cable teaser */}
          <div className="npc-cable-teaser">
            <span className="npc-cable-text">{cable || 'No recent communications.'}</span>
          </div>
        </>
      )}
    </div>
  )
}
