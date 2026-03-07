/**
 * NPC dialogue panel — shows 4 NPC messages for the current turn.
 *
 * The live API format (from npc_engine._format_* wrappers) is:
 *   Line 1: "🇺🇸 USA (State Department):"   ← name + optional (subtitle)
 *   Line 2: '"dialogue text here"'           ← text, may have surrounding quotes
 *
 * Arabia / DPRG may also have inline stage directions on line 2:
 *   Line 2: '*lighting cigar* "text"'
 *   or just: '*lighting cigar* text'
 *
 * The fallback (static) format uses ─ separators but we handle both.
 *
 * We extract:
 *   subtitle — e.g. "State Department", "Brotherhood Offer"
 *   text     — raw dialogue, quotes stripped
 * Then render *stage directions* as <em> italic.
 *
 * Priority 2: Intelligence system — click-to-activate per NPC per turn.
 *   Costs $0.5B personal per activation. Cached per NPC per turn.
 *   Tier 0 = insufficient access (relation < 40).
 *   Tier label shown: "🕵️ TIER 2 INTEL — Operational"
 */

import { useState, useEffect, useRef } from 'react'
import { api } from '../api'

const NPC_ORDER = [
  { key: 'usa',    label: 'Bill Hartwell',  flag: '🇺🇸' },
  { key: 'arabia', label: 'Sadam',            flag: '🛢️' },
  { key: 'eu',     label: 'Marsha',           flag: '🇪🇺' },
  { key: 'dprg',   label: 'Ji-won Ryang',     flag: '⚡' },
]

// Known NPC name prefixes that Claude sometimes adds verbatim — strip these
const NPC_PREFIX_RE = /^(?:🇺🇸\s*)?(?:USA|BILL)[^:]*:\s*/i
const ARABIA_PREFIX_RE = /^(?:🛢️?\s*)?SADAM[^:]*:\s*/i
const EU_PREFIX_RE = /^(?:🇪🇺\s*)?(?:EU|MARSHA)[^:]*:\s*/i
const DPRG_PREFIX_RE = /^(?:⚡\s*)?(?:JI-WON|JIWON)[^:]*:\s*/i
const ALL_PREFIXES = [NPC_PREFIX_RE, ARABIA_PREFIX_RE, EU_PREFIX_RE, DPRG_PREFIX_RE]

function stripNpcPrefix(text) {
  for (const re of ALL_PREFIXES) {
    text = text.replace(re, '')
  }
  return text.trim()
}

/**
 * Parse a raw npc_engine string into { subtitle, text }.
 * Handles both the live API format (2 lines, no ─) and the
 * CLI fallback format (with ─ separators).
 */
function parseNpcString(raw) {
  if (!raw) return { subtitle: '', text: '…' }

  const lines = raw.split('\n').map(l => l.trim()).filter(Boolean)

  // ── Case A: live API format — no ─ lines ──────────────────────────────
  const hasDashes = lines.some(l => l.match(/^─+$/))

  let subtitle = ''
  let textLines = []

  if (!hasDashes && lines.length >= 1) {
    const firstLine = lines[0]
    if (firstLine.endsWith(':')) {
      const parenMatch = firstLine.match(/\(([^)]+)\)/)
      if (parenMatch) subtitle = parenMatch[1]
      textLines = lines.slice(1)
    } else {
      textLines = lines
    }
  } else {
    // ── Case B: CLI fallback format with ─ separators ──────────────────
    const nameLine = lines.find(l => l.includes(':') && !l.match(/^─+$/))
    if (nameLine) {
      const parenMatch = nameLine.match(/\(([^)]+)\)/)
      if (parenMatch) subtitle = parenMatch[1]
    }
    const dashIndices = lines
      .map((l, i) => (l.match(/^─+$/) ? i : -1))
      .filter(i => i >= 0)
    const lastDashIdx = dashIndices[dashIndices.length - 1]
    textLines = lastDashIdx !== undefined ? lines.slice(lastDashIdx + 1) : lines
  }

  let text = textLines.join(' ').trim()

  if (text.startsWith('"') && text.endsWith('"')) {
    text = text.slice(1, -1).trim()
  }

  text = stripNpcPrefix(text)

  if (text.startsWith('"') && text.endsWith('"')) {
    text = text.slice(1, -1).trim()
  }

  return { subtitle, text: text || '…' }
}

/**
 * fixes_13 Fix 8: Strip *stage directions* from all Claude-generated text.
 * e.g. "*lighting cigar* Hello" → "Hello"
 * Applied globally to dialogue, negotiation, and intel intercepts.
 */
function stripStageDirections(text) {
  if (!text) return text
  return text.replace(/\*[^*]+\*/g, '').replace(/\s{2,}/g, ' ').trim()
}

/**
 * Render text with stage directions stripped.
 * Kept as named export-compatible function for use across components.
 */
function renderWithStageDirections(text) {
  const cleaned = stripStageDirections(text)
  return <span>{cleaned}</span>
}

// Intel tier label display
const TIER_LABELS = {
  0: '🕵️ INSUFFICIENT ACCESS',
  1: '🕵️ TIER 1 INTEL — Surface',
  2: '🕵️ TIER 2 INTEL — Operational',
  3: '🕵️ TIER 3 INTEL — Deep Cover',
}

/**
 * Single NPC intel dossier — click-to-activate per NPC per turn.
 * Priority 2: Costs $0.5B personal per activation. Cached per turn.
 * Shows a "Gather Intel" button until activated, then shows the brief.
 */
function IntelDossier({ npcKey, sessionId, gs, onGsUpdate, intelligenceLevel = 0 }) {
  const [intelData, setIntelData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Determine tier from current gs.relations
  // FIX J: Use ?? instead of || so relation 0 isn't treated as falsy
  const relation = gs?.relations?.[npcKey] ?? 50
  // FIX 9: No access block — all relations get at least tier 1 (Surface)
  const tier = relation >= 80 ? 3 : relation >= 60 ? 2 : 1

  // Check if cached intel exists for this turn
  useEffect(() => {
    const cached = gs?.intel?.[npcKey]
    if (cached && cached.turn_generated === gs?.current_turn) {
      setIntelData(cached)
    } else {
      setIntelData(null)
    }
  }, [npcKey, gs?.current_turn]) // eslint-disable-line react-hooks/exhaustive-deps

  // fixes_20 Fix C: Log once per turn, not on every re-render
  useEffect(() => {
    if (intelligenceLevel < 3) {
      console.log(`[INTELLIGENCE] Intel locked for ${npcKey}: intelligence level ${intelligenceLevel} < 3`)
    }
  }, [npcKey, gs?.current_turn, intelligenceLevel])

  async function handleActivate() {
    if (loading) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.getIntel(sessionId, npcKey)
      setIntelData(res)
      // Sync updated game_state (personal_wealth changed) to parent
      if (res.game_state && onGsUpdate) {
        onGsUpdate(res.game_state)
      }
    } catch (err) {
      setError(err.message || 'Intel gathering failed')
    } finally {
      setLoading(false)
    }
  }

  // Already activated this turn — show the brief
  if (intelData) {
    const tierLabel = TIER_LABELS[intelData.tier ?? tier] || TIER_LABELS[1]
    return (
      <div className={`intel-dossier ${intelData.tier === 0 ? 'intel-dossier-locked' : ''}`}>
        <span className="intel-dossier-label">{tierLabel}</span>
        {intelData.text}
      </div>
    )
  }

  // Session 6: Intel locked unless Intelligence axis >= 3 (was Security)
  if (intelligenceLevel < 3) {
    return (
      <div className="intel-dossier intel-dossier-inactive" style={{ opacity: 0.5 }}>
        <button
          className="intel-gather-btn intel-gather-btn-disabled"
          disabled
          title="Requires Intelligence level 3 (Cabinet → Infrastructure → Intelligence)"
          onClick={() => {}}
        >
          🔒 Get Intel — Requires Intelligence Level 3
        </button>
      </div>
    )
  }

  // Not yet activated — show "Gather Intel" button with tiered cost
  // fixes_12 Fix 9: Intel costs from national budget, not personal wealth
  const nationalBudget = gs?.budget || 0
  // Session 3 Addendum: Tiered cost by relation level
  const intelCost = relation >= 60 ? 0.5 : relation >= 30 ? 1.0 : 1.5
  const canAfford = nationalBudget >= intelCost

  return (
    <div className="intel-dossier intel-dossier-inactive">
      {error && <div className="intel-error">{error}</div>}
      <button
        className={`intel-gather-btn ${canAfford ? '' : 'intel-gather-btn-disabled'}`}
        onClick={canAfford ? handleActivate : undefined}
        disabled={!canAfford || loading}
        title={canAfford
          ? `Gather ${TIER_LABELS[tier]?.replace('🕵️ ', '') || 'intel'} — costs $${intelCost.toFixed(1)}B from budget`
          : `Need $${intelCost.toFixed(1)}B budget (have $${nationalBudget.toFixed(1)}B)`
        }
      >
        {loading
          ? '🕵️ Gathering…'
          : `🕵️ Gather Intel — $${intelCost.toFixed(1)}B`
        }
      </button>
    </div>
  )
}

// Priority 4: Leverage tier labels and colours
const LEVERAGE_TIERS = {
  Weak:     { color: '#888',    icon: '⚖️' },
  Moderate: { color: '#b0b040', icon: '⚖️' },
  Strong:   { color: '#60c060', icon: '⚖️' },
  Dominant: { color: '#40d0ff', icon: '⚖️' },
}

/**
 * Compute leverage for one NPC from game_state (mirrors GameState.get_leverage).
 * Done client-side to avoid extra API call.
 */
function computeLeverage(gs, npcId) {
  if (!gs) return null
  const relation = gs.relations?.[npcId] ?? 50
  const sided = Math.min(10, gs.times_sided_with?.[npcId] ?? 0)

  // Active deals
  const dealHistory = gs.deal_history || []
  const activeDeals = Math.min(3, dealHistory.filter(
    d => d.npc === npcId && !d.broken && (d.expires_turn || 0) >= (gs.current_turn || 1)
  ).length)

  // Rival hostility
  const rivals = {
    usa: ['arabia', 'dprg'],
    arabia: ['usa', 'eu'],
    eu: ['dprg', 'arabia'],
    dprg: ['usa', 'eu'],
  }
  let rivalHostility = 0
  for (const rival of (rivals[npcId] || [])) {
    const rRel = gs.relations?.[rival] ?? 50
    if (rRel < 30) rivalHostility += (30 - rRel) / 30.0
  }
  rivalHostility = Math.min(1.0, rivalHostility)

  const leverageEvents = gs.leverage_events?.[npcId] || []
  const specialCount = Math.min(3, leverageEvents.length)

  const score = Math.max(0, Math.min(100, Math.round(
    (relation / 100.0) * 40.0 +
    (sided / 10.0) * 20.0 +
    (activeDeals / 3.0) * 15.0 +
    rivalHostility * 15.0 +
    (specialCount / 3.0) * 10.0
  )))

  let tier
  if (score >= 75) tier = 'Dominant'
  else if (score >= 50) tier = 'Strong'
  else if (score >= 25) tier = 'Moderate'
  else tier = 'Weak'

  return { score, tier }
}

/**
 * Props:
 *   dialogue        : array of 4 raw NPC strings
 *   onNegotiate     : (npcKey, communiqueText?) => void — optional, if provided shows Negotiate buttons
 *   negotiatingNpc  : string | null — which NPC panel is currently open
 *   intelActive     : bool — true when Intelligence Apparatus upgrade is purchased
 *   sessionId       : string — needed for dynamic intel fetch
 *   gs              : game_state object — needed for relation tier + intel cache
 *   onGsUpdate      : (newGs) => void — callback to sync game_state after intel purchase
 */
export default function DialoguePanel({
  dialogue,
  onNegotiate,
  negotiatingNpc,
  intelActive = false,
  intelligenceLevel = 0,
  sessionId,
  gs,
  onGsUpdate,
}) {
  const [leverageLoading, setLeverageLoading] = useState(false)
  const [leverageMsg, setLeverageMsg] = useState(null)

  if (!dialogue || dialogue.length === 0) return null

  // Session 6: Leverage demand handler
  async function handleLeverageResponse(leverageType, accept) {
    setLeverageLoading(true)
    try {
      const res = await api.leverageResponse(sessionId, leverageType, accept)
      const msgs = res.messages || []
      setLeverageMsg(msgs.join('\n'))
      onGsUpdate && onGsUpdate(res.game_state)
      console.log(`[LEVERAGE] Response: type=${leverageType}, accept=${accept}, messages:`, msgs)
    } catch (e) {
      setLeverageMsg(`Error: ${e.message}`)
    } finally {
      setLeverageLoading(false)
    }
  }

  // fixes_16 Fix A: Log pending_npc_contacts once per turn (not per render)
  const _allPendingContacts = gs?.pending_npc_contacts || []
  const _currentTurn = gs?.current_turn
  useEffect(() => {
    console.log('[DialoguePanel] FIX A: pending_npc_contacts at turn start =', gs?.pending_npc_contacts)
    // fixes_19 Fix A: Also log INCOMING contacts once per turn
    const pendingContacts = gs?.pending_npc_contacts || []
    for (const c of pendingContacts) {
      console.log(`[DialoguePanel] FIX C: Rendering INCOMING for: ${c.npc}`, c)
    }
  }, [_currentTurn]) // eslint-disable-line react-hooks/exhaustive-deps

  // fixes_19 Fix A: Log negotiate costs once per turn or when political axis changes
  const _politicalAxisLevel = gs?.cabinet_axes?.political || 0
  useEffect(() => {
    const activeAdvisors = Array.isArray(gs?.advisors) ? gs.advisors : []
    const diplomat = activeAdvisors.find(a => a.archetype === 'diplomat')
    for (const { key } of NPC_ORDER) {
      const rel = gs?.relations?.[key] ?? 50
      const baseNegCost = rel >= 60 ? 0.3 : rel >= 30 ? 0.5 : 0.8
      let negMult = 1.0
      let negDiscountLabel = ''
      if (diplomat) {
        if (diplomat.competence >= 80) { negMult = 0; negDiscountLabel = 'Diplomat' }
        else { negMult *= 0.5; negDiscountLabel = 'Diplomat -50%' }
      }
      if (_politicalAxisLevel >= 8) {
        negMult *= 0.5
        negDiscountLabel = negDiscountLabel ? negDiscountLabel + ' + Political -50%' : 'Political -50%'
      } else if (_politicalAxisLevel >= 5) {
        negMult *= 0.75
        negDiscountLabel = negDiscountLabel ? negDiscountLabel + ' + Political -25%' : 'Political -25%'
      }
      const discountedCost = Math.round(baseNegCost * negMult * 100) / 100
      if (negDiscountLabel) console.log(`[DialoguePanel] Fix 22+23: ${key} negotiate cost $${baseNegCost}B → $${discountedCost}B (${negDiscountLabel})`)
    }
  }, [_currentTurn, _politicalAxisLevel]) // eslint-disable-line react-hooks/exhaustive-deps

  // Session 7B: Compute urgency tier for each NPC (factors in ignored communiqués)
  const ignoredMap = gs?.ignored_communiques || {}
  const briefingTiers = {}
  for (const { key } of NPC_ORDER) {
    const rel = gs?.relations?.[key] ?? 50
    const hasSanctions = key === 'usa' && gs?.usa_sanctions_active
    const hasEmbargo = key === 'arabia' && gs?.arabia_embargo_active
    const ignoreCount = ignoredMap[key]?.ignore_count || 0
    if (hasSanctions || hasEmbargo || rel < 25 || ignoreCount >= 2) {
      briefingTiers[key] = 'urgent'
    } else if (ignoreCount === 1) {
      briefingTiers[key] = 'developing'
    } else {
      briefingTiers[key] = 'incoming'
    }
  }

  // Session 7B: Emit briefing tier counts
  useEffect(() => {
    if (!gs) return
    const counts = { urgent: 0, incoming: 0, intelligence: 0, developing: 0 }
    for (const tier of Object.values(briefingTiers)) {
      counts[tier] = (counts[tier] || 0) + 1
    }
    console.log('[BRIEFING] Items rendered:', counts)
  }, [gs?.current_turn]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="panel dialogue-panel">
      <div className="panel-header">
        Diplomatic Communiqués
        {intelActive && (
          <span className="intel-active-badge">🕵️ INTEL ACTIVE</span>
        )}
      </div>
      {leverageMsg && (
        <div className="alert" style={{ background: 'rgba(200,168,75,0.12)', borderColor: '#c8a84b', margin: '0.3rem 0', padding: '0.4rem 0.6rem', fontSize: '0.75rem' }}>
          {leverageMsg}
        </div>
      )}
      {NPC_ORDER.map(({ key, label, flag }, i) => {
        const { subtitle, text } = parseNpcString(dialogue[i])
        const isNegotiating = negotiatingNpc === key
        const leverage = computeLeverage(gs, key)
        const leverageStyle = leverage ? LEVERAGE_TIERS[leverage.tier] : null
        // Session 5: Check for pending NPC-initiated contacts
        const pendingContacts = gs?.pending_npc_contacts || []
        const incomingContact = pendingContacts.find(c => c.npc === key)
        // FIX C: INCOMING rendering log moved to useEffect above (fixes_19 Fix A)

        // fixes_13 Fix 7: INCOMING replaces regular communiqué — show private channel text instead
        const incomingText = incomingContact ? (incomingContact.dialogue || incomingContact.reason) : null

        // fixes_13 Fix 10: INCOMING negotiation is free
        // fixes_13 Fix 22+23: Diplomat + Political axis discounts
        const rel = gs?.relations?.[key] ?? 50
        const baseNegCost = rel >= 60 ? 0.3 : rel >= 30 ? 0.5 : 0.8
        let negMult = 1.0
        let negDiscountLabel = ''
        const activeAdvisors = Array.isArray(gs?.advisors) ? gs.advisors : []
        const diplomat = activeAdvisors.find(a => a.archetype === 'diplomat')
        if (diplomat) {
          if (diplomat.competence >= 80) {
            negMult = 0
            negDiscountLabel = 'Diplomat'
          } else {
            negMult *= 0.5
            negDiscountLabel = 'Diplomat -50%'
          }
        }
        const politicalAxis = gs?.cabinet_axes?.political || 0
        if (politicalAxis >= 8) {
          negMult *= 0.5
          negDiscountLabel = negDiscountLabel ? negDiscountLabel + ' + Political -50%' : 'Political -50%'
        } else if (politicalAxis >= 5) {
          negMult *= 0.75
          negDiscountLabel = negDiscountLabel ? negDiscountLabel + ' + Political -25%' : 'Political -25%'
        }
        const discountedCost = Math.round(baseNegCost * negMult * 100) / 100
        const negCost = incomingContact ? 0 : discountedCost
        // Fix 22+23 negotiate cost log moved to useEffect below (fixes_19 Fix A)

        const tier = briefingTiers[key] || 'incoming'
        const ignoreCount = ignoredMap[key]?.ignore_count || 0
        const escalationClass = ignoreCount >= 3 ? 'npc-row-escalated-3' :
                                ignoreCount >= 2 ? 'npc-row-escalated-2' :
                                ignoreCount >= 1 ? 'npc-row-escalated-1' : ''

        return (
          <div
            key={key}
            className={`npc-row ${incomingContact?.leverage_type ? 'npc-row-leverage' : incomingContact ? 'npc-row-incoming' : ''} ${escalationClass}`}
            title={ignoreCount > 0 ? `${ignoreCount} day${ignoreCount !== 1 ? 's' : ''} without response` : undefined}
          >
            <div className="npc-row-header">
              <span className={`npc-name ${key}`}>
                {/* Session 7B: Urgency tier tag */}
                <span className={`briefing-tag briefing-tag-${tier}`}>
                  {tier === 'urgent' && ignoreCount >= 3 ? 'CONFRONTATION' :
                   tier === 'urgent' && ignoreCount >= 2 ? 'OVERDUE' :
                   tier === 'urgent' ? 'URGENT' :
                   tier === 'developing' ? 'NO RESPONSE' : 'INCOMING'}
                </span>
                {flag} {label}
                {/* fixes_13 Fix 7: Show "Private Channel" instead of department subtitle for INCOMING */}
                {incomingContact ? (
                  <span className="npc-incoming-badge">{incomingContact.leverage_type ? '⚡ LEVERAGE DEMAND' : '⚡ INCOMING — Private Channel'}</span>
                ) : subtitle ? (
                  <span style={{ fontWeight: 400, opacity: 0.65, marginLeft: '0.4rem', fontSize: '0.65rem' }}>
                    — {subtitle}
                  </span>
                ) : null}
                {/* Priority 4: Leverage badge */}
                {leverage && leverage.score > 0 && (
                  <span
                    className="leverage-badge"
                    style={{ color: leverageStyle?.color }}
                    title={`Leverage: ${leverage.tier} (${leverage.score}/100)`}
                  >
                    {leverageStyle?.icon} {leverage.tier}
                  </span>
                )}
              </span>
              {/* Session 6: Leverage demands show Accept/Decline instead of Negotiate */}
              {incomingContact?.leverage_type ? (
                <span style={{ display: 'flex', gap: '0.3rem' }}>
                  <button
                    className="negotiate-btn"
                    style={{ background: 'rgba(76,175,80,0.25)', borderColor: '#4caf50' }}
                    onClick={() => !leverageLoading && handleLeverageResponse(incomingContact.leverage_type, true)}
                    disabled={leverageLoading}
                  >
                    Accept
                  </button>
                  <button
                    className="negotiate-btn"
                    style={{ background: 'rgba(244,67,54,0.15)', borderColor: '#f44336' }}
                    onClick={() => !leverageLoading && handleLeverageResponse(incomingContact.leverage_type, false)}
                    disabled={leverageLoading}
                  >
                    Decline
                  </button>
                </span>
              ) : onNegotiate && (() => {
                const budget = gs?.budget || 0
                const canAfford = budget >= negCost || negCost === 0
                return (
                  <button
                    className={`negotiate-btn ${isNegotiating ? 'negotiate-btn-active' : ''} ${!canAfford && !isNegotiating ? 'negotiate-btn-disabled' : ''}`}
                    onClick={() => canAfford || isNegotiating ? onNegotiate(isNegotiating ? null : key, isNegotiating ? null : (incomingText || text)) : null}
                    title={isNegotiating ? 'Close negotiation' : negCost === 0 ? (incomingContact ? 'Open diplomatic channel — Free (INCOMING)' : negDiscountLabel ? `Open diplomatic channel — Free (${negDiscountLabel})` : 'Open diplomatic channel — Free') : canAfford ? `Open diplomatic channel — $${negCost.toFixed(1)}B from budget${negDiscountLabel ? ` (${negDiscountLabel})` : ''}` : `Need $${negCost.toFixed(1)}B budget`}
                  >
                    {isNegotiating ? 'Close ✕' : negCost === 0 ? (incomingContact ? 'Negotiate — Free →' : `Negotiate — Free (${negDiscountLabel}) →`) : negDiscountLabel ? `Negotiate — $${negCost.toFixed(1)}B (${negDiscountLabel}) →` : `Negotiate — $${negCost.toFixed(1)}B →`}
                  </button>
                )
              })()}
            </div>
            {/* fixes_13 Fix 7: INCOMING replaces regular text; Fix 8: strip stage directions from all text */}
            <span className="npc-text">{renderWithStageDirections(incomingText || text)}</span>
            {/* Priority 2: Click-to-activate intelligence dossier */}
            {/* fixes_12 Fix 8: Always render IntelDossier; shows locked state when Security < 3 */}
            {intelActive && sessionId && gs && (
              <IntelDossier
                key={`intel-${key}-${gs?.current_turn}`}
                npcKey={key}
                sessionId={sessionId}
                gs={gs}
                onGsUpdate={onGsUpdate}
                intelligenceLevel={intelligenceLevel}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
