/**
 * NpcCard — Single NPC relationship card for the right sidebar.
 * Shows portrait, name, relation bar (color-coded), and one-line status.
 * Border color reflects relationship health.
 * Session 7A Step 1.  Session 8A: All 6 NPCs are active (no passive concept).
 * Session 7D Step 2: Backchannel button with detection risk.
 * Session 10B-2: Urgent badges, expandable cables, GET INTEL with inline result.
 */
import { useState } from 'react'

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

// Detect urgent conditions per NPC
function getUrgentState(npcKey, gs) {
  if (!gs) return null
  if (npcKey === 'usa' && gs.usa_sanctions_active) return { label: 'SANCTIONS', severity: 'high' }
  if (npcKey === 'arabia' && gs.arabia_embargo_active) return { label: 'EMBARGO', severity: 'high' }
  if (npcKey === 'russia' && gs.volkov_trap_stage > 0) return { label: 'VOLKOV TRAP', severity: 'critical' }
  // Low relations = diplomatic crisis
  const rel = (gs.relations || {})[npcKey] ?? 50
  if (rel < 15) return { label: 'CRISIS', severity: 'critical' }
  if (rel < 25) return { label: 'TENSION', severity: 'high' }
  return null
}

export default function NpcCard({ npcKey, label, flag, relation, subtitle, hasWarning, isPlaceholder, color, onContact, onContactRequest, contactDisabled, contactLoading, contactResult, onBackchannel, backchannelDisabled, onGetIntel, intelLoading, intelResult, cable, gs, onRequestBriefing, briefingLoading }) {
  const [cableExpanded, setCableExpanded] = useState(false)

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

  // Urgent state
  const urgent = getUrgentState(npcKey, gs)

  // Model C: determine contact mode based on relations and crisis
  const isCrisis = (
    (npcKey === 'usa' && gs?.usa_sanctions_active) ||
    (npcKey === 'arabia' && gs?.arabia_embargo_active) ||
    (npcKey === 'russia' && (gs?.volkov_trap_stage ?? 0) > 0) ||
    relation < 15
  )
  // TODO: modify gate by soft_power_score
  const canDirectContact = relation >= 40 || isCrisis
  const alreadyRequested = !!(gs?.contact_requested || {})[npcKey]

  // Cable display — teaser at 120 chars, sentence-aware truncation
  const cableText = cable || ''
  const showExpandToggle = cableText.length > 120
  const cableTeaser = showExpandToggle ? cableText.slice(0, 117) + '...' : cableText

  return (
    <div className={`npc-card ${healthClass} ${urgent ? 'npc-card-urgent' : ''}`}>
      <div className="npc-card-header">
        <div
          className="npc-portrait"
          style={{ background: portraitBg, borderColor: isPlaceholder ? '#333' : portraitBg }}
        >
          {flag}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="npc-card-name" style={isPlaceholder ? { color: '#555' } : {}}>
            {label}
          </div>
          {subtitle && (
            <div className="npc-card-subtitle">{subtitle}</div>
          )}
        </div>
        {/* Urgent badge */}
        {urgent && (
          <span className={`npc-urgent-badge urgent-${urgent.severity}`}>
            {urgent.label}
          </span>
        )}
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

          {/* INCOMING badge — always visible when type is incoming */}
          {(gs?.diplomatic_cable_types || {})[npcKey] === 'incoming' && (
            <span className="npc-incoming-badge">INCOMING</span>
          )}

          {/* Diplomatic cable / briefing display */}
          {cableText ? (
            <div className={`npc-cable-area ${cableExpanded ? 'expanded' : ''}`}>
              <span className="npc-cable-text">
                {cableExpanded ? cableText : cableTeaser}
              </span>
              {showExpandToggle && (
                <button
                  className="npc-cable-toggle-link"
                  onClick={(e) => { e.stopPropagation(); setCableExpanded(!cableExpanded) }}
                >
                  {cableExpanded ? 'Show less ▲' : 'Read more ▼'}
                </button>
              )}
            </div>
          ) : (
            /* No cable — show Request Briefing button */
            onRequestBriefing && (
              <button
                className="npc-briefing-btn"
                onClick={() => onRequestBriefing(npcKey)}
                disabled={briefingLoading || (gs?.budget || 0) < 0.3}
              >
                {briefingLoading
                  ? '📋 Generating briefing...'
                  : (gs?.budget || 0) < 0.3
                    ? '📋 Insufficient budget'
                    : '📋 REQUEST BRIEFING — $0.3B'}
              </button>
            )
          )}

          {/* Action buttons */}
          <div className="npc-action-buttons">
            {/* Model C: Contact / Request Meeting based on relations */}
            {canDirectContact ? (
              onContact && (
                <>
                  <button
                    className={`npc-contact-btn ${isCrisis ? 'crisis' : ''}`}
                    onClick={() => onContact(npcKey)}
                    disabled={contactDisabled || contactLoading}
                    title={contactDisabled ? 'Contact unavailable' : `Open diplomatic channel with ${label}`}
                  >
                    {contactLoading ? 'Connecting...' : isCrisis ? '⚠ URGENT CONTACT' : 'CONTACT'}
                  </button>
                  <span className="npc-contact-cost">Negotiation fee: ${relation >= 60 ? '0.3' : relation >= 30 ? '0.5' : '0.8'}B</span>
                </>
              )
            ) : (
              onContactRequest && (
                <button
                  className={`npc-contact-btn request-meeting ${alreadyRequested ? 'requested' : ''}`}
                  onClick={() => !alreadyRequested && onContactRequest(npcKey)}
                  disabled={contactDisabled || contactLoading || alreadyRequested}
                  title={alreadyRequested ? 'Meeting already requested today' : `Request diplomatic meeting with ${label}`}
                >
                  {contactLoading ? 'Requesting...' : alreadyRequested ? '✓ Meeting Requested' : 'Request Meeting'}
                </button>
              )
            )}
            {/* Contact result inline */}
            {contactResult && (
              <div className={`npc-contact-result ${contactResult.type || ''}`}>
                <div className="npc-contact-result-text">{contactResult.text}</div>
                {contactResult.gate_message && (
                  <div className="npc-contact-gate-msg">{contactResult.gate_message}</div>
                )}
              </div>
            )}
            {/* Backchannel button */}
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
            {/* GET INTEL button */}
            {onGetIntel && gs && (() => {
              const intelGated = (gs.intelligence_tier ?? 0) < MIN_INTEL_TIER
              const alreadyGathered = (gs.intel_ops_today || []).some(op => op.target === npcKey)
              return (
                <>
                  <button
                    className={`npc-intel-btn ${intelGated || alreadyGathered ? 'locked' : ''}`}
                    onClick={() => onGetIntel(npcKey)}
                    disabled={intelGated || intelLoading || alreadyGathered}
                  >
                    {intelGated
                      ? `🔒 INTEL — Requires Intel Tier ${MIN_INTEL_TIER}`
                      : alreadyGathered
                        ? '📡 Intel gathered today'
                        : intelLoading
                          ? '📡 INTERCEPTING...'
                          : `📡 GET INTEL — $${INTEL_COST}B`}
                  </button>
                  {!intelGated && !alreadyGathered && (
                    <div className="npc-intel-risk-text">Detection risk: 10%</div>
                  )}
                </>
              )
            })()}
          </div>

          {/* Intel result inline */}
          {intelResult && (
            <div className={`npc-intel-result ${intelResult.detected ? 'detected' : ''}`}>
              <div className="npc-intel-result-header">
                {intelResult.detected ? '⚠ DETECTED — ' : '📡 '}Intel Report
              </div>
              <div className="npc-intel-result-text">{intelResult.text}</div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
