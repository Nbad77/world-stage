/**
 * MobileNpcDrawer — bottom-sheet NPC contact panel for narrow viewports.
 * Surfaces the same actions as desktop NpcCard:
 *   RECEIVE COMMUNIQUÉ · CONTACT · BACKCHANNEL · GET INTEL
 * Cost helpers (calcIntelCost, calcNegotiateCost) are duplicated here
 * intentionally — desktop NpcCard.jsx is sovereign this session.
 */
import { useEffect } from 'react'

/* ── Cost / risk helpers (mirror NpcCard.jsx — do not import) ────────── */
const BASE_RISK = { usa: 0.25, arabia: 0.20, eu: 0.15, dprg: 0.10, russia: 0.20, china: 0.18 }
const OPSEC_MULT = { 0: 1.0, 1: 0.7, 2: 0.45 }
const MIN_INTEL_TIER = 1

function calcDetectionRisk(npcKey, gs) {
  const base = BASE_RISK[npcKey] ?? 0.20
  const opsec = gs?.opsec_level ?? 0
  const mult = OPSEC_MULT[opsec] ?? 1.0
  let risk = base * mult
  const rel = gs?.relations || {}
  if (npcKey === 'usa' && (rel.usa ?? 50) < 30) risk *= 1.3
  if (npcKey === 'eu' && (rel.eu ?? 50) < 30) risk *= 1.2
  if (npcKey === 'dprg') risk *= 0.8
  return Math.min(1.0, risk)
}

function calcIntelCost(relation, gs) {
  let base
  if (relation >= 60) base = 0.5
  else if (relation >= 30) base = 1.0
  else base = 1.5
  const spyChief = gs?.advisors?.spy_chief
  if (spyChief?.assigned_this_turn) {
    const comp = spyChief.competence ?? 70
    if (comp >= 80) return 0
    return +(base * 0.6).toFixed(1)
  }
  return base
}

function calcNegotiateCost(relation, gs) {
  let base
  if (relation >= 60) base = 0.3
  else if (relation >= 30) base = 0.5
  else base = 0.8
  const diplomat = gs?.advisors?.diplomat
  if (diplomat?.assigned_this_turn) {
    const comp = diplomat.competence ?? 70
    if (comp >= 80) return 0
    base = +(base * 0.5).toFixed(2)
  }
  const polAxis = gs?.cabinet_axes?.political ?? 0
  if (polAxis >= 8) base = +(base * 0.5).toFixed(2)
  else if (polAxis >= 5) base = +(base * 0.75).toFixed(2)
  return base
}

function backchannelThreshold(npcId) {
  // Mirror existing tier 0 floors from npc_engine NPC_DEAL_TIERS
  // bill<20, eu<15, sadam<10, dprg<25, volkov<15, wei<10
  return ({ bill: 20, eu: 15, sadam: 10, dprg: 25, volkov: 15, wei: 10 })[npcId] ?? 15
}

export default function MobileNpcDrawer({
  npcId, meta, gs, onClose,
  onContact, onContactRequest, onBackchannel, onGetIntel, onRequestBriefing,
  contactLoading, contactResult, intelLoading, intelResult,
  briefingLoading, contactsDisabled, backchannelDisabled,
}) {
  useEffect(() => {
    const isOpen = !!npcId
    console.log('[MOBILE_DRAWER] open=', isOpen, 'npc=', npcId)
  }, [npcId])

  if (!npcId || !meta) return null

  const relKey = meta.relKey
  const relation = Math.round((gs?.relations || {})[relKey] ?? 50)
  const recalled = !!(gs?.ambassador_recalled || {})[npcId]
  const cableType = (gs?.diplomatic_cable_types || {})[relKey]

  const negotiateCost = calcNegotiateCost(relation, gs)
  const intelCost = calcIntelCost(relation, gs)
  const detectionPct = Math.round(calcDetectionRisk(relKey, gs) * 100)

  const intelGated = (gs?.intelligence_tier ?? 0) < MIN_INTEL_TIER
  const intelAlready = (gs?.intel_ops_today || []).some(op => op.target === relKey)

  const bcThreshold = backchannelThreshold(npcId)
  const bcLocked = relation < bcThreshold
  const isCrisis = (
    (relKey === 'usa' && gs?.usa_sanctions_active) ||
    (relKey === 'arabia' && gs?.arabia_embargo_active) ||
    (relKey === 'russia' && (gs?.volkov_trap_stage ?? 0) > 0) ||
    relation < 15
  )
  const canDirectContact = relation >= 40 || isCrisis
  const alreadyRequested = !!(gs?.contact_requested || {})[relKey]

  return (
    <div className="mobile-drawer-overlay" onClick={onClose}>
      <div className="mobile-drawer" onClick={e => e.stopPropagation()}>
        <div className="mobile-drawer-handle" />
        <button className="mobile-drawer-close" onClick={onClose} aria-label="Close">×</button>

        <div className="mobile-drawer-header">
          <div className="mobile-card-row">
            <div
              className="mobile-avatar"
              style={{ background: meta.avatarBg, color: meta.avatarText }}
            >{meta.avatar}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="mobile-drawer-name">{meta.name}</div>
              <div className="mobile-drawer-country">{meta.country} · Rel {relation}</div>
            </div>
          </div>
          {recalled && (
            <div className="mobile-npc-recalled-banner" style={{ marginTop: 8 }}>
              AMBASSADOR RECALLED
            </div>
          )}
        </div>

        <div className="mobile-drawer-body">
          {/* RECEIVE COMMUNIQUÉ — only if no cable yet */}
          {!cableType && onRequestBriefing && (
            <button
              className="mobile-npc-action-btn"
              onClick={() => onRequestBriefing(relKey)}
              disabled={briefingLoading || (gs?.budget || 0) < 0.3}
            >
              <span>📨 RECEIVE COMMUNIQUÉ</span>
              <span className="mobile-npc-action-cost">
                {briefingLoading ? '…' : (gs?.budget || 0) < 0.3 ? 'low budget' : '$0.3B'}
              </span>
            </button>
          )}

          {/* CONTACT or REQUEST MEETING */}
          {!recalled && (canDirectContact ? (
            onContact && (
              <button
                className="mobile-npc-action-btn"
                onClick={() => onContact(relKey)}
                disabled={contactsDisabled || contactLoading}
              >
                <span>{isCrisis ? '⚠ URGENT CONTACT' : 'CONTACT'}</span>
                <span className="mobile-npc-action-cost">
                  {contactLoading ? '…' : negotiateCost === 0 ? 'FREE' : `$${negotiateCost}B`}
                </span>
              </button>
            )
          ) : (
            onContactRequest && (
              <button
                className="mobile-npc-action-btn"
                onClick={() => !alreadyRequested && onContactRequest(relKey)}
                disabled={contactsDisabled || contactLoading || alreadyRequested}
              >
                <span>{alreadyRequested ? '✓ MEETING REQUESTED' : 'REQUEST MEETING'}</span>
                <span className="mobile-npc-action-cost">
                  {contactLoading ? '…' : ''}
                </span>
              </button>
            )
          ))}

          {/* BACKCHANNEL */}
          {!recalled && onBackchannel && (
            <button
              className="mobile-npc-action-btn"
              onClick={() => !bcLocked && onBackchannel(relKey)}
              disabled={backchannelDisabled || bcLocked}
              title={bcLocked ? `Requires relations ≥ ${bcThreshold}` : 'Open covert channel'}
            >
              <span>🔒 BACKCHANNEL</span>
              <span className="mobile-npc-action-cost">
                {bcLocked ? `req rel ${bcThreshold}` : `risk ${detectionPct}%`}
              </span>
            </button>
          )}

          {/* GET INTEL */}
          {onGetIntel && (
            <button
              className="mobile-npc-action-btn"
              onClick={() => !intelGated && !intelAlready && onGetIntel(relKey)}
              disabled={intelGated || intelAlready || intelLoading}
            >
              <span>📡 GET INTEL</span>
              <span className="mobile-npc-action-cost">
                {intelGated ? `req tier ${MIN_INTEL_TIER}`
                  : intelAlready ? 'gathered today'
                  : intelLoading ? '…'
                  : `${intelCost === 0 ? 'FREE' : `$${intelCost}B`} · ${detectionPct}%`}
              </span>
            </button>
          )}

          {/* Inline contact result */}
          {contactResult && (
            <div className="mobile-card" style={{ marginTop: 12 }}>
              <div className="mobile-card-body">{contactResult.text || JSON.stringify(contactResult)}</div>
              {contactResult.gate_message && (
                <div className="mobile-regime-hint">{contactResult.gate_message}</div>
              )}
            </div>
          )}

          {/* Inline intel result */}
          {intelResult && (
            <div className="mobile-card" style={{ marginTop: 12 }}>
              <div className="mobile-card-role">
                {intelResult.detected ? '⚠ DETECTED — Intel Report' : '📡 Intel Report'}
              </div>
              <div className="mobile-card-body">{intelResult.text || JSON.stringify(intelResult)}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
