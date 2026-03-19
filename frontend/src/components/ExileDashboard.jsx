/**
 * ExileDashboard — Full-screen exile mode component.
 * Replaces main game dashboard when in_exile == true.
 * 8C: Desaturated palette, exile destination, successor feed, NPC reach-out.
 */
import { useState, useMemo } from 'react'
import ReturnAttemptModal from './ReturnAttemptModal'
import BackchannelModal from './BackchannelModal'

const EXILE_DESTINATIONS = {
  usa:    { city: 'Washington D.C.', flavor: 'A comfortable arrangement. Someone made calls.' },
  eu:     { city: 'Brussels', flavor: 'Dignified asylum. The visa was waiting.' },
  arabia: { city: 'Riyadh', flavor: 'A villa. Sadam has rooms for useful people.' },
  dprg:   { city: 'Pyongyang', flavor: 'Safe. Isolated. The hospitality has conditions.' },
  russia: { city: 'Moscow', flavor: 'Volkov decided you were worth something. For now.' },
  china:  { city: 'Shanghai', flavor: 'Comfortable. Watched. Wei\'s infrastructure is thorough.' },
}

const NPC_LIST = [
  { key: 'usa',    label: 'Bill Hartwell',  flag: '\u{1F1FA}\u{1F1F8}' },
  { key: 'arabia', label: 'Sadam',          flag: '\u{1F6E2}\u{FE0F}' },
  { key: 'eu',     label: 'Marsha',         flag: '\u{1F1EA}\u{1F1FA}' },
  { key: 'dprg',   label: 'Ji-won Ryang',   flag: '\u{26A1}' },
  { key: 'russia', label: 'Nikolai Volkov', flag: '\u{1F1F7}\u{1F1FA}' },
  { key: 'china',  label: 'Wei Jianming',   flag: '\u{1F1E8}\u{1F1F3}' },
]

const BACKING_PRICES = {
  usa:    'Western alignment commitment. No DPRG deals in the next era.',
  eu:     'Reform commitments in writing. Press freedom, judicial independence.',
  arabia: 'Energy partnership restored at current terms. Exclusive supply.',
  dprg:   'Isolation from Western security frameworks. No USA military deals.',
  russia: 'Energy exclusivity. No NATO-adjacent arrangements.',
  china:  'Infrastructure partnership. Long-term development framework. No conditions on governance.',
}

// Fix 2 (8E): Backing exclusion map — which NPCs get locked out
const BACKING_EXCLUSIONS = {
  usa: ['DPRG', 'Russia'],
  russia: ['USA', 'EU'],
  dprg: ['USA', 'EU'],
  china: ['USA'],
  eu: [],
  arabia: [],
}

// Fix F: Reach-out cost table (mirrors api.py EXILE_REACH_OUT_COSTS)
const EXILE_REACH_OUT_COSTS = {
  usa: 1.0, eu: 0.8, arabia: 1.2, dprg: 1.5, russia: 1.0, china: 0.8,
}

// 9A: Wealth action definitions (mirrors EXILE_WEALTH_ACTIONS in api.py)
const WEALTH_ACTIONS_9A = [
  { key: 'propaganda_campaign', label: 'Propaganda Campaign', cost: 1.0, progress: 8, cooldown: 3, desc: 'Spread messaging through exile media networks.' },
  { key: 'bribe_official', label: 'Bribe Official', cost: 1.5, progress: 10, cooldown: 0, desc: 'Buy cooperation from a successor government insider.' },
  { key: 'fund_protests', label: 'Fund Protests', cost: 2.0, progress: 12, cooldown: 5, desc: 'Finance organized dissent against the successor.' },
  { key: 'stir_unrest', label: 'Stir Unrest', cost: 3.0, progress: 18, cooldown: 7, desc: 'Incite civil disruption. High risk, high reward.' },
  { key: 'general_greasing', label: 'General Greasing', cost: 1.5, progress: 8, cooldown: 4, desc: 'Oil the machinery. Keep your network warm.' },
  { key: 'hire_fixer', label: 'Hire Fixer', cost: 2.5, progress: 0, cooldown: 0, desc: 'Unlock a faction channel for covert contact.', isFixer: true },
]
const FACTION_ACTIONS_9A = [
  { key: 'military_contact', label: 'Military Contact', cost: 2.0, progress: 25, faction: 'military', desc: 'Establish a committed line to military figures.', needsCommitment: true },
  { key: 'opposition_coalition', label: 'Opposition Coalition', cost: 0, progress: 15, requiresApproval: 25, desc: 'Rally the opposition behind your return. Free but requires support.' },
]
const FIXER_TARGETS = [
  { key: 'military', label: 'Military' },
  { key: 'oligarchs', label: 'Oligarchs' },
  { key: 'opposition', label: 'Opposition' },
]

// 9A: NPC backing tier data (mirrors NPC_BACKING_TIERS in api.py)
const NPC_BACKING_TIERS_9A = {
  usa: [
    { tier: 1, label: 'Informal Contact', bonus: 5, relReq: 20, cost: 0, flavor: 'A quiet line. Nothing official.' },
    { tier: 2, label: 'Quiet Support', bonus: 10, relReq: 35, cost: 1.0, flavor: 'Hartwell is making calls on your behalf.' },
    { tier: 3, label: 'Active Backing', bonus: 18, relReq: 50, cost: 2.0, flavor: 'State Department is involved. Strings attached.' },
    { tier: 4, label: 'Full Sponsorship', bonus: 25, relReq: 65, cost: 3.0, flavor: 'Washington wants you back in power. Their terms.' },
    { tier: 5, label: 'Regime Change Support', bonus: 35, relReq: 75, cost: 5.0, flavor: 'The full apparatus. You will owe everything.' },
  ],
  eu: [
    { tier: 1, label: 'Humanitarian Concern', bonus: 4, relReq: 20, cost: 0, flavor: 'Marsha filed a concern. It is noted.' },
    { tier: 2, label: 'Diplomatic Channel', bonus: 8, relReq: 30, cost: 0.5, flavor: 'Brussels is talking about you in meetings.' },
    { tier: 3, label: 'Sanctions Pressure', bonus: 15, relReq: 45, cost: 1.5, flavor: 'The EU is applying pressure. Reform conditions.' },
    { tier: 4, label: 'Full EU Support', bonus: 22, relReq: 60, cost: 2.5, flavor: 'Comprehensive support package. Democracy clauses.' },
    { tier: 5, label: 'EU Integration Path', bonus: 30, relReq: 70, cost: 4.0, flavor: 'Full integration pathway. Institutional overhaul required.' },
  ],
  arabia: [
    { tier: 1, label: 'Hospitality', bonus: 3, relReq: 15, cost: 0, flavor: 'Sadam offers a room. Nothing more.' },
    { tier: 2, label: 'Financial Support', bonus: 8, relReq: 30, cost: 0, flavor: 'Money is not the problem. Loyalty is.' },
    { tier: 3, label: 'Active Investment', bonus: 14, relReq: 40, cost: 0, flavor: 'Sadam is investing in your return. His terms.' },
    { tier: 4, label: 'Strategic Partnership', bonus: 20, relReq: 55, cost: 0, flavor: 'Full partnership. Energy exclusivity. No questions.' },
  ],
  dprg: [
    { tier: 1, label: 'Quiet Acknowledgment', bonus: 3, relReq: 25, cost: 0, flavor: 'Ji-won knows you exist. That is something.' },
    { tier: 2, label: 'Information Sharing', bonus: 7, relReq: 35, cost: 0.5, flavor: 'Intelligence flows both ways now.' },
    { tier: 3, label: 'Material Support', bonus: 12, relReq: 50, cost: 1.0, flavor: 'Weapons, training, logistics. The price is isolation.' },
  ],
  russia: [
    { tier: 1, label: 'Back Channel', bonus: 4, relReq: 20, cost: 0, flavor: 'Volkov has a line open. He is listening.' },
    { tier: 2, label: 'Quiet Backing', bonus: 9, relReq: 35, cost: 0.5, flavor: 'Moscow is interested. Cautiously.' },
    { tier: 3, label: 'Active Support', bonus: 16, relReq: 45, cost: 1.5, flavor: 'Volkov is moving pieces. Energy deals expected.' },
    { tier: 4, label: 'Strategic Alliance', bonus: 22, relReq: 60, cost: 2.5, flavor: 'Full Russian backing. Western doors close.' },
    { tier: 5, label: 'Full Integration', bonus: 30, relReq: 70, cost: 4.0, flavor: 'You become a Russian asset. Total dependency.' },
  ],
  china: [
    { tier: 1, label: 'Diplomatic Interest', bonus: 4, relReq: 15, cost: 0, flavor: 'Wei is watching. That is all for now.' },
    { tier: 2, label: 'Development Partner', bonus: 9, relReq: 30, cost: 0, flavor: 'Infrastructure talks. Long-term framework.' },
    { tier: 3, label: 'Strategic Investment', bonus: 15, relReq: 45, cost: 0, flavor: 'Massive investment commitment. No governance conditions.' },
    { tier: 4, label: 'Comprehensive Partnership', bonus: 22, relReq: 55, cost: 0, flavor: 'Full economic integration. Belt and Road.' },
    { tier: 5, label: 'Full Dependency', bonus: 30, relReq: 65, cost: 0, flavor: 'Everything flows through Beijing. Everything.' },
  ],
}

// 9A: Exclusions at tier 3+ (mirrors NPC_BACKING_EXCLUSIONS_9A)
const NPC_EXCLUSIONS_9A = {
  usa: ['dprg', 'russia'],
  eu: ['dprg'],
  arabia: [],
  dprg: ['usa', 'eu'],
  russia: ['usa', 'eu'],
  china: ['usa'],
}

// 9A: Tier caps per NPC
const NPC_TIER_CAPS_9A = { arabia: 4, dprg: 3 }

function getReachOutCost(npcKey, exileTrigger, relations) {
  let cost = EXILE_REACH_OUT_COSTS[npcKey] || 1.0
  if (exileTrigger === 'voted_out') cost *= 0.8
  if ((relations ?? 30) < 20) cost *= 1.5
  return Math.round(cost * 10) / 10  // round to 1 decimal
}

function getDailyBurn(apparatusSurvived) {
  return apparatusSurvived ? 0.5 : 0.2  // 0.2 base + 0.3 apparatus
}


// Fix C: Wealth-tiered exile flavor text -- 3 tiers per NPC destination
const EXILE_FLAVOR = {
  usa: {
    comfortable: 'A Georgetown townhouse. Consultants return your calls. Your book deal is already being discussed.',
    functional: 'A corporate apartment in Foggy Bottom. You have meetings. You have options.',
    desperate: 'A budget hotel near Dulles. You have forty-eight hours to make yourself useful to someone.',
  },
  eu: {
    comfortable: 'A canal-side flat in Brussels. The think-tank circuit welcomes you. Marsha arranged it.',
    functional: 'A modest EU-quarter apartment. You have a desk, a phone, and conditional residency.',
    desperate: 'A hostel in the Marolles. Your asylum claim is pending. Nobody is returning calls.',
  },
  arabia: {
    comfortable: 'A villa compound in the diplomatic quarter. Sadam calls it hospitality. The staff report to him.',
    functional: 'An apartment in the KAFD district. Comfortable. Monitored. The arrangement has terms.',
    desperate: 'A room above a souk. You are tolerated. The visa is month-to-month.',
  },
  dprg: {
    comfortable: 'A state guesthouse on Changjon Street. The meals are excellent. The doors lock from outside.',
    functional: 'A Pyongyang apartment block, foreign section. The minder is polite. The phone does not dial out.',
    desperate: 'A concrete room. Heated. Ji-won says you should be grateful. She is not wrong.',
  },
  russia: {
    comfortable: 'A dacha outside Moscow. Volkov sends vodka and newspapers. Both are tests.',
    functional: 'A flat in the Arbat district. You can walk freely. Someone always walks behind you.',
    desperate: 'A room near Leningradsky station. The radiator works. Volkov has stopped calling.',
  },
  china: {
    comfortable: "A Pudong high-rise. Wei's people handle everything. The view is extraordinary. The walls listen.",
    functional: "A Jing'an district apartment. Clean, modern, surveilled. You have a handler who calls herself a liaison.",
    desperate: 'A room in a development zone. The Wi-Fi works. Nobody visits. Wei has moved on to other projects.',
  },
}

function getWealthTier(wealth) {
  if (wealth > 20) return 'comfortable'
  if (wealth >= 5) return 'functional'
  return 'desperate'
}

// 9A Section 5: Exile depth — measures how embedded the player is in exile networks
function getExileDepth(gs) {
  let depth = 0
  // NPC backing tiers (0-5 each, 6 NPCs — max 30)
  const tiers = gs.npc_assistance_tiers || {}
  for (const t of Object.values(tiers)) depth += (t || 0)
  // Faction contacts (3 per unlocked, 5 per committed — max ~24)
  const factions = gs.faction_contacts || {}
  for (const f of Object.values(factions)) {
    if (f?.committed) depth += 5
    else if (f?.unlocked) depth += 3
  }
  // Return progress contribution (0-20)
  const prog = gs.return_progress || 0
  const thresh = gs.return_threshold || 100
  depth += Math.min(20, Math.round(prog / Math.max(thresh, 1) * 20))
  // Backchannel history depth (1 per exchange, max 10)
  const bch = gs.backchannel_history || []
  depth += Math.min(10, bch.length)
  // Detection penalty (-2 per event)
  depth -= ((gs.detection_events || []).length) * 2
  // Exile days bonus (1 per 5 days, max 5)
  depth += Math.min(5, Math.floor((gs.exile_day || 0) / 5))
  return Math.max(0, Math.min(100, depth))
}

// 9A Section 5: Depth tier labels
function getDepthLabel(depth) {
  if (depth >= 50) return { label: 'Deep Network', color: 'var(--success)' }
  if (depth >= 30) return { label: 'Established', color: 'var(--accent)' }
  if (depth >= 15) return { label: 'Building', color: 'var(--warning)' }
  return { label: 'Isolated', color: 'var(--muted)' }
}

export default function ExileDashboard({ gs, sessionId, onExileAction, onGsUpdate, loading, messages, exileDialogue, onDismissDialogue }) {
  const [selectedNpc, setSelectedNpc] = useState(null)
  const [showBackingModal, setShowBackingModal] = useState(null)
  // Fix D: Covert op confirmation state
  const [showCovertConfirm, setShowCovertConfirm] = useState(null) // 'destabilize' | 'maintenance' | 'return_prep'
  const [covertTargetNpc, setCovertTargetNpc] = useState(null) // NPC key for return_prep
  // Fix F: Reach-out confirmation state
  const [showReachConfirm, setShowReachConfirm] = useState(null) // NPC key

  // 9A: Return attempt modal state
  const [showReturnModal, setShowReturnModal] = useState(false)
  // 9A Section 5: Backchannel state
  const [backchannelNpc, setBackchannelNpc] = useState(null)

  // 9A: Wealth action state
  const [actionToast, setActionToast] = useState(null) // detection toast
  const [fixerTarget, setFixerTarget] = useState(null) // hire_fixer target faction
  const [commitmentText, setCommitmentText] = useState('') // military_contact commitment

  if (!gs) return null

  // Fix B: Derive destination from highest relations if exile_destination is null (DEV panel toggle)
  const derivedDestination = useMemo(() => {
    if (gs.exile_destination) return gs.exile_destination
    const rels = gs.relations || {}
    const npcs = ['usa', 'arabia', 'eu', 'dprg', 'russia', 'china']
    let topNpc = 'usa'
    let topVal = 0
    for (const n of npcs) {
      if ((rels[n] ?? 0) > topVal) { topVal = rels[n]; topNpc = n }
    }
    console.log(`[exile] Destination calculated: ${EXILE_DESTINATIONS[topNpc]?.city} (highest NPC: ${topNpc}, relations: ${topVal})`)
    return topNpc
  }, [gs.exile_destination, gs.relations])

  const dest = EXILE_DESTINATIONS[derivedDestination] || { city: 'Unknown' }
  const wealth = gs.personal_wealth ?? 0
  const wealthTier = getWealthTier(wealth)
  const flavorText = EXILE_FLAVOR[derivedDestination]?.[wealthTier] || ''
  const dailyDrain = gs.exile_apparatus_survived ? 0.5 : 0.2
  const runway = dailyDrain > 0 ? Math.floor(wealth / dailyDrain) : 999
  const rel = gs.relations || {}
  const closedDoors = gs.backing_doors_closed || []

  // Voted out flavor
  const isVotedOut = gs.exile_trigger === 'voted_out'

  // 9A: Return status computations
  const departureHeat = gs.departure_heat || 0
  const HEAT_LABELS = ['\u2014', 'Quiet', 'Managed', 'Contested', 'Violent', 'Fugitive']
  const HEAT_COLORS = ['#555', '#4caf6e', '#4a9eff', '#e5a34a', '#e57a4a', '#e54a4a']
  const heatLabel = HEAT_LABELS[departureHeat] || '\u2014'
  const heatColor = HEAT_COLORS[departureHeat] || '#555'
  const returnProgress = gs.return_progress || 0
  const returnThreshold = gs.return_threshold || 100
  const progressPct = Math.min(returnProgress / Math.max(returnThreshold, 1) * 100, 100)
  const progressBarColor = progressPct < 33 ? '#555' : progressPct < 66 ? '#e5a34a' : '#4caf6e'
  const attemptsUsed = gs.return_attempts || 0
  const atThreshold = returnProgress >= returnThreshold
  const readinessText = atThreshold
    ? 'The conditions are in place.'
    : progressPct >= 66
    ? 'The moment may be approaching.'
    : progressPct >= 33
    ? 'Conditions are building. More work needed.'
    : 'The ground is not yet prepared.'

  // 9A: Wealth action handler
  const handleWealthAction = async (actionKey, target = null, offer = null) => {
    try {
      const res = await onExileAction('9a_wealth_action', { action_key: actionKey, target, offer })
      console.log(`[FIX] exile action cost deducted wealth_before=${exileWealth} cost=${res?.cost ?? '?'} wealth_after=${res?.new_wealth ?? '?'}`)
      if (res?.detected) {
        setActionToast('Action detected by successor intelligence.')
        setTimeout(() => setActionToast(null), 4000)
      }
      setFixerTarget(null)
      setCommitmentText('')
    } catch (e) {
      // Error already handled by parent
    }
  }

  // 9A: NPC backing handler
  const handleNpcBacking = async (npcId, tier) => {
    try {
      await onExileAction('9a_npc_backing', { npc_id: npcId, tier })
    } catch (e) {
      // Error already handled by parent
    }
  }

  // 9A: NPC assistance state
  const npcTiers = gs.npc_assistance_tiers || {}

  // 9A: Check if a tier upgrade is blocked by exclusions
  const isExcluded = (npcId, targetTier) => {
    if (targetTier < 3) return false
    // Check if any excluded NPC is already at tier 3+
    const excludes = NPC_EXCLUSIONS_9A[npcId] || []
    for (const ex of excludes) {
      if ((npcTiers[ex] || 0) >= 3) return true
    }
    return false
  }

  // 9A: Get exclusion warning text
  const getExclusionWarning = (npcId) => {
    const excludes = NPC_EXCLUSIONS_9A[npcId] || []
    if (excludes.length === 0) return null
    const names = excludes.map(id => NPC_LIST.find(n => n.key === id)?.label || id)
    return `Tier 3+ blocks: ${names.join(', ')}`
  }

  // 9A: Cooldown/wealth helpers
  const cooldowns = gs.wealth_action_cooldowns || {}
  const exileDay = gs.exile_day || 0
  const exileWealth = gs.exile_wealth_at_collapse ?? gs.personal_wealth ?? 0
  const factionContacts = gs.faction_contacts || {}
  const playerApproval = gs.approval ?? 0

  // 9A Section 5: Exile depth computation
  const exileDepth = getExileDepth(gs)
  const depthInfo = getDepthLabel(exileDepth)

  return (
    <div className="exile-dashboard">
      {/* Header */}
      <div className="exile-header">
        <div className="exile-title">
          EXILE &mdash; {dest.city}
        </div>
        <div className="exile-day">Day {gs.exile_day || 0}</div>
      </div>

      {/* Fix C: Destination flavor — wealth-tiered */}
      {flavorText && (
        <div className="exile-flavor">{flavorText}</div>
      )}

      {/* Voted out note */}
      {isVotedOut && (
        <div className="exile-voted-out-note">
          You accepted the result. Not everyone does.
        </div>
      )}

      {/* Historian note */}
      {gs.exile_historian_note && (
        <div className="exile-historian-note">
          <em>{gs.exile_historian_note}</em>
        </div>
      )}

      {/* Wealth display */}
      <div className="exile-wealth-bar">
        <div className="exile-wealth-amount">${wealth.toFixed(1)}B remaining</div>
        <div className="exile-wealth-burn">
          burning ${dailyDrain.toFixed(1)}B/day &mdash; ~{runway} days of runway
        </div>
      </div>

      {/* Fix G: Apparatus status indicator — always visible */}
      {gs.exile_apparatus_survived ? (
        <div className="exile-apparatus exile-apparatus-active">
          🕵️ Shadow apparatus: ACTIVE &mdash; $0.3B/day
          <span className="exile-apparatus-risk">
            Detection risk &times;{gs.exile_apparatus_detection_risk_modifier?.toFixed(1) || '1.0'} &mdash; use with caution
          </span>
        </div>
      ) : (
        <div className="exile-apparatus exile-apparatus-down">
          🕵️ Shadow apparatus: COMPROMISED &mdash; covert ops unavailable
        </div>
      )}

      {/* Successor feed */}
      <div className="exile-successor-card">
        <div className="exile-successor-header">
          SUCCESSOR: {gs.successor_name || 'Unknown'}
          <span className="exile-successor-disposition">
            ({gs.successor_disposition || 'unknown'})
          </span>
        </div>
        {(gs.successor_events_fired || []).length > 0 && (
          <div className="exile-successor-events">
            {(gs.successor_events_fired || []).map((key, i) => (
              <div key={key} className="exile-successor-event">
                {key}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Two-column layout: NPC cards + Actions */}
      <div className="exile-main-grid">
        {/* NPC Cards */}
        <div className="exile-npc-list">
          <div className="exile-section-title">DIPLOMATIC CONTACTS</div>
          {NPC_LIST.map(npc => {
            const npcRel = Math.round(rel[npc.key] ?? 30)
            const isDoorClosed = closedDoors.includes(npc.key)
            const isBacker = gs.exile_backing === npc.key

            return (
              <div key={npc.key} className={`exile-npc-card ${isBacker ? 'exile-npc-backer' : ''}`}>
                <div className="exile-npc-header">
                  <span className="exile-npc-flag">{npc.flag}</span>
                  <span className="exile-npc-name">{npc.label}</span>
                  <span className="exile-npc-rel">{npcRel}/100</span>
                </div>
                <div className="exile-npc-actions">
                  <button
                    className="exile-btn exile-btn-reach"
                    disabled={loading || wealth < 0.5}
                    onClick={() => setShowReachConfirm(npc.key)}
                  >
                    REACH OUT
                  </button>
                  {sessionId && (
                    <button
                      className="exile-btn exile-btn-covert"
                      disabled={loading}
                      onClick={() => setBackchannelNpc(npc.key)}
                      style={{ fontSize: '0.68rem', padding: '0.2rem 0.4rem' }}
                    >
                      BACKCHANNEL
                    </button>
                  )}
                  {isDoorClosed && (
                    <span className="exile-door-closed" title="This door has been closed by your backing choice">
                      CLOSED
                    </span>
                  )}
                  {isBacker && (
                    <span className="exile-backer-badge">YOUR BACKER</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* Actions panel */}
        <div className="exile-actions-panel">
          <div className="exile-section-title">EXILE ACTIONS</div>

          {/* Wait */}
          <button
            className="exile-btn exile-btn-wait"
            disabled={loading}
            onClick={() => onExileAction('wait')}
          >
            WAIT
            <span className="exile-btn-desc">Let conditions shift. The world keeps moving without you.</span>
          </button>

          {/* Fix D: Covert Operations — updated labels, costs, confirmation dialogs */}
          <div className="exile-covert-section">
            <div className="exile-covert-title">COVERT OPERATIONS</div>
            {gs.exile_apparatus_survived ? (
              <>
                <button
                  className="exile-btn exile-btn-covert"
                  disabled={loading || wealth < 1.5}
                  onClick={() => setShowCovertConfirm('destabilize')}
                >
                  DESTABILIZE ($1.5B)
                  <span className="exile-btn-desc">Sow instability in Europa. Weakens the successor government.</span>
                </button>
                <button
                  className="exile-btn exile-btn-covert"
                  disabled={loading || wealth < 0.8}
                  onClick={() => setShowCovertConfirm('maintenance')}
                >
                  MAINTAIN NETWORK ($0.8B)
                  <span className="exile-btn-desc">Keep your contacts warm. Slows NPC relation decay in exile.</span>
                </button>
                <button
                  className="exile-btn exile-btn-covert"
                  disabled={loading || wealth < 2.0}
                  onClick={() => setShowCovertConfirm('return_prep')}
                >
                  PREPARE RETURN ($2.0B)
                  <span className="exile-btn-desc">Lay groundwork for a comeback. Reduces return cost with one NPC.</span>
                </button>
              </>
            ) : (
              <div className="exile-apparatus-compromised">
                Shadow apparatus compromised &mdash; covert operations unavailable.
              </div>
            )}
          </div>

          {/* 9A: Return Status Panel */}
          <div className="exile-return-section">
            {isVotedOut ? (
              <div className="exile-return-placeholder">
                Democratic return \u2014 coming in future update
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="exile-section-title" style={{ margin: 0 }}>RETURN STATUS</div>
                  <span style={{
                    fontSize: '0.66rem', fontWeight: 600,
                    padding: '0.1rem 0.4rem', borderRadius: '4px',
                    background: `color-mix(in srgb, ${depthInfo.color} 15%, transparent)`,
                    color: depthInfo.color
                  }}>
                    {depthInfo.label} ({exileDepth})
                  </span>
                </div>

                {/* Collapse type */}
                <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginBottom: '0.3rem' }}>
                  You were removed by: <strong style={{ color: 'var(--text)' }}>
                    {gs.successor_archetype || 'Unknown Regime'}
                  </strong>
                </div>

                {/* Departure heat badge */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>Departure heat:</span>
                  <span style={{
                    fontSize: '0.7rem', fontWeight: 600,
                    padding: '0.1rem 0.45rem', borderRadius: '4px',
                    background: heatColor, color: '#fff'
                  }}>
                    {heatLabel}
                  </span>
                </div>

                {/* Return Progress bar */}
                <div style={{ marginBottom: '0.4rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--muted)', marginBottom: '0.2rem' }}>
                    <span>Return progress</span>
                    <span>{Math.round(returnProgress)} / {Math.round(returnThreshold)}</span>
                  </div>
                  <div style={{
                    height: '8px', background: 'var(--surface2)', borderRadius: '4px', overflow: 'hidden'
                  }}>
                    <div style={{
                      height: '100%', width: `${progressPct}%`,
                      background: progressBarColor, borderRadius: '4px',
                      transition: 'width 0.3s ease'
                    }} />
                  </div>
                </div>

                {/* Attempts remaining as dots */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>Attempts:</span>
                  <span style={{ fontSize: '0.9rem', letterSpacing: '0.2rem' }}>
                    {[0, 1, 2].map(i => (
                      <span key={i} style={{ color: i < attemptsUsed ? 'var(--border)' : 'var(--text)' }}>
                        {i < attemptsUsed ? '\u25CB' : '\u25CF'}
                      </span>
                    ))}
                  </span>
                  <span style={{ fontSize: '0.68rem', color: 'var(--muted)' }}>
                    ({3 - attemptsUsed} remaining)
                  </span>
                </div>

                {/* Qualitative readiness text */}
                <div style={{
                  fontSize: '0.76rem',
                  color: atThreshold ? 'var(--success)' : 'var(--muted)',
                  fontStyle: 'italic', marginTop: '0.2rem'
                }}>
                  {readinessText}
                </div>

                {/* 9A: Attempt Return button */}
                {attemptsUsed < 3 && returnProgress >= 20 && (
                  <button
                    className="exile-btn exile-btn-accept"
                    disabled={loading}
                    onClick={() => setShowReturnModal(true)}
                    style={{
                      width: '100%', marginTop: '0.5rem', padding: '0.5rem',
                      fontSize: '0.82rem', fontWeight: 700, letterSpacing: '0.05rem',
                      background: atThreshold
                        ? 'linear-gradient(135deg, var(--success), #3a9a5e)'
                        : 'var(--surface2)',
                      border: atThreshold
                        ? '1px solid var(--success)'
                        : '1px solid var(--border)',
                      color: atThreshold ? '#fff' : 'var(--text)'
                    }}
                  >
                    {atThreshold ? '⚔️ ATTEMPT RETURN' : '⚔️ ATTEMPT RETURN (risky)'}
                  </button>
                )}
                {attemptsUsed >= 3 && (
                  <div style={{
                    fontSize: '0.74rem', color: 'var(--danger)', fontStyle: 'italic',
                    marginTop: '0.4rem', textAlign: 'center'
                  }}>
                    All return attempts exhausted.
                  </div>
                )}
              </>
            )}
          </div>

          {/* 9A: Wealth Actions Panel */}
          {!isVotedOut && (
            <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border)' }}>
              <div className="exile-section-title">WEALTH ACTIONS</div>

              {/* Detection toast */}
              {actionToast && (
                <div style={{
                  fontSize: '0.74rem', color: '#e54a4a', background: 'rgba(229,74,74,0.08)',
                  padding: '0.3rem 0.5rem', borderRadius: '4px', marginBottom: '0.4rem',
                  border: '1px solid rgba(229,74,74,0.2)'
                }}>
                  🔍 {actionToast}
                </div>
              )}

              {/* Standard wealth actions */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                {WEALTH_ACTIONS_9A.map(action => {
                  const onCooldown = cooldowns[action.key] && exileDay < cooldowns[action.key]
                  const cooldownDay = cooldowns[action.key] || 0
                  const cantAfford = exileWealth < action.cost
                  const disabled = loading || onCooldown || cantAfford

                  return (
                    <div key={action.key}>
                      <button
                        className="exile-btn exile-btn-covert"
                        disabled={disabled}
                        title={cantAfford ? `Insufficient wealth. Need ${action.cost}B` : onCooldown ? `On cooldown until day ${cooldownDay}` : action.desc}
                        onClick={() => {
                          if (action.isFixer) {
                            setFixerTarget(prev => prev !== null ? null : 'military')
                          } else {
                            handleWealthAction(action.key)
                          }
                        }}
                        style={{ width: '100%', textAlign: 'left', position: 'relative' }}
                      >
                        <span style={{ fontWeight: 600 }}>{action.label}</span>
                        <span style={{ marginLeft: '0.4rem', fontSize: '0.72rem', color: 'var(--muted)' }}>
                          {action.cost > 0 ? `${action.cost}B` : 'Free'}
                        </span>
                        {action.progress > 0 && (
                          <span style={{
                            marginLeft: '0.3rem', fontSize: '0.66rem', fontWeight: 600,
                            background: 'rgba(76,175,110,0.15)', color: 'var(--success)',
                            padding: '0.05rem 0.3rem', borderRadius: '3px'
                          }}>+{action.progress} pts</span>
                        )}
                        {action.isFixer && (
                          <span style={{
                            marginLeft: '0.3rem', fontSize: '0.66rem', fontWeight: 600,
                            background: 'rgba(74,158,255,0.15)', color: 'var(--accent)',
                            padding: '0.05rem 0.3rem', borderRadius: '3px'
                          }}>unlocks channel</span>
                        )}
                        {action.cooldown > 0 && (
                          <span className="exile-btn-desc">
                            {action.cooldown} day cooldown
                          </span>
                        )}
                        {onCooldown && (
                          <span style={{
                            position: 'absolute', right: '0.5rem', top: '50%', transform: 'translateY(-50%)',
                            fontSize: '0.66rem', color: 'var(--warning)',
                          }}>Available day {cooldownDay}</span>
                        )}
                      </button>

                      {/* hire_fixer: inline target selector */}
                      {action.isFixer && fixerTarget !== null && (
                        <div style={{
                          padding: '0.4rem', background: 'var(--surface2)', borderRadius: '0 0 6px 6px',
                          marginTop: '-2px', borderTop: 'none'
                        }}>
                          <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginBottom: '0.3rem' }}>
                            Select faction to unlock:
                          </div>
                          <div style={{ display: 'flex', gap: '0.3rem', marginBottom: '0.3rem' }}>
                            {FIXER_TARGETS.map(ft => {
                              const alreadyOpen = factionContacts[ft.key]?.unlocked
                              return (
                                <button
                                  key={ft.key}
                                  className={`exile-btn exile-btn-npc-select ${fixerTarget === ft.key ? 'selected' : ''}`}
                                  disabled={alreadyOpen}
                                  onClick={() => setFixerTarget(ft.key)}
                                  style={{ flex: 1, fontSize: '0.72rem', padding: '0.25rem' }}
                                  title={alreadyOpen ? 'Already unlocked' : ''}
                                >
                                  {ft.label} {alreadyOpen ? '✓' : ''}
                                </button>
                              )
                            })}
                          </div>
                          <button
                            className="exile-btn exile-btn-accept"
                            disabled={loading || !fixerTarget || factionContacts[fixerTarget]?.unlocked || cantAfford}
                            onClick={() => handleWealthAction('hire_fixer', fixerTarget)}
                            style={{ width: '100%', fontSize: '0.74rem', padding: '0.3rem' }}
                          >
                            Confirm — Hire Fixer (${action.cost}B)
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>

              {/* Faction contact actions — show only when channel is unlocked */}
              {FACTION_ACTIONS_9A.map(action => {
                const factionUnlocked = action.faction ? factionContacts[action.faction]?.unlocked : true
                const approvalMet = action.requiresApproval ? playerApproval >= action.requiresApproval : true
                if (action.faction && !factionUnlocked) return null

                const cantAfford = exileWealth < action.cost
                const disabled = loading || cantAfford || !approvalMet

                return (
                  <div key={action.key} style={{ marginTop: '0.3rem' }}>
                    {action.needsCommitment ? (
                      <div style={{
                        border: '1px solid var(--border)', borderRadius: '6px',
                        padding: '0.5rem', background: 'var(--surface2)'
                      }}>
                        <div style={{ fontSize: '0.78rem', fontWeight: 600, marginBottom: '0.2rem' }}>
                          {action.label}
                          <span style={{ marginLeft: '0.3rem', fontSize: '0.68rem', color: 'var(--muted)' }}>
                            ${action.cost}B + commitment
                          </span>
                          <span style={{
                            marginLeft: '0.3rem', fontSize: '0.66rem', fontWeight: 600,
                            background: 'rgba(76,175,110,0.15)', color: 'var(--success)',
                            padding: '0.05rem 0.3rem', borderRadius: '3px'
                          }}>+{action.progress} pts</span>
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginBottom: '0.3rem' }}>
                          {action.desc}
                        </div>
                        <input
                          type="text"
                          placeholder="Your commitment to the military..."
                          value={commitmentText}
                          onChange={e => setCommitmentText(e.target.value)}
                          style={{
                            width: '100%', padding: '0.3rem 0.4rem', fontSize: '0.74rem',
                            background: 'var(--bg)', color: 'var(--text)', border: '1px solid var(--border)',
                            borderRadius: '4px', marginBottom: '0.3rem'
                          }}
                        />
                        <button
                          className="exile-btn exile-btn-accept"
                          disabled={disabled || !commitmentText.trim()}
                          onClick={() => handleWealthAction(action.key, null, commitmentText.trim())}
                          style={{ width: '100%', fontSize: '0.74rem', padding: '0.3rem' }}
                        >
                          Confirm Contact
                        </button>
                      </div>
                    ) : (
                      <button
                        className="exile-btn exile-btn-covert"
                        disabled={disabled}
                        title={!approvalMet ? `Requires approval ≥ ${action.requiresApproval}. Current: ${playerApproval}` : cantAfford ? `Insufficient wealth` : action.desc}
                        onClick={() => handleWealthAction(action.key)}
                        style={{ width: '100%', textAlign: 'left' }}
                      >
                        <span style={{ fontWeight: 600 }}>{action.label}</span>
                        <span style={{ marginLeft: '0.4rem', fontSize: '0.72rem', color: 'var(--muted)' }}>
                          {action.requiresApproval ? `Approval ${playerApproval}/${action.requiresApproval}` : action.cost > 0 ? `${action.cost}B` : 'Free'}
                        </span>
                        <span style={{
                          marginLeft: '0.3rem', fontSize: '0.66rem', fontWeight: 600,
                          background: 'rgba(76,175,110,0.15)', color: 'var(--success)',
                          padding: '0.05rem 0.3rem', borderRadius: '3px'
                        }}>+{action.progress} pts</span>
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* 9A: NPC Backing Panel */}
          {!isVotedOut && (
            <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border)' }}>
              <div className="exile-section-title">NPC ASSISTANCE</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginBottom: '0.4rem' }}>
                Build support from world leaders. Higher tiers grant more return progress but may close other doors.
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {NPC_LIST.map(npc => {
                  const tiers = NPC_BACKING_TIERS_9A[npc.key]
                  if (!tiers) return null
                  const currentTier = npcTiers[npc.key] || 0
                  const maxTier = NPC_TIER_CAPS_9A[npc.key] || 5
                  const atCap = currentTier >= maxTier
                  const atMax = currentTier >= tiers.length
                  const nextTierData = !atCap && !atMax ? tiers[currentTier] : null
                  const currentTierData = currentTier > 0 ? tiers[currentTier - 1] : null
                  const npcRel = Math.round(rel[npc.key] ?? 30)
                  const relMet = nextTierData ? npcRel >= nextTierData.relReq : false
                  const canAfford = nextTierData ? exileWealth >= nextTierData.cost : false
                  const excluded = nextTierData && nextTierData.tier >= 3 ? isExcluded(npc.key, nextTierData.tier) : false
                  const exclusionWarn = getExclusionWarning(npc.key)

                  return (
                    <div key={npc.key} style={{
                      border: '1px solid var(--border)', borderRadius: '6px',
                      padding: '0.5rem', background: 'var(--surface2)'
                    }}>
                      {/* NPC header */}
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <span style={{ fontSize: '1rem' }}>{npc.flag}</span>
                          <span style={{ fontSize: '0.78rem', fontWeight: 600 }}>{npc.label}</span>
                          <span style={{ fontSize: '0.68rem', color: 'var(--muted)' }}>({npcRel}/100)</span>
                        </div>
                        {currentTier > 0 && (
                          <span style={{
                            fontSize: '0.66rem', fontWeight: 600,
                            padding: '0.1rem 0.4rem', borderRadius: '4px',
                            background: currentTier >= 3 ? 'rgba(76,175,110,0.15)' : 'rgba(74,158,255,0.15)',
                            color: currentTier >= 3 ? 'var(--success)' : 'var(--accent)'
                          }}>
                            Tier {currentTier}: {currentTierData?.label}
                          </span>
                        )}
                      </div>

                      {/* Current bonus display */}
                      {currentTier > 0 && (
                        <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginBottom: '0.3rem' }}>
                          Contributing +{currentTierData?.bonus || 0} return progress
                        </div>
                      )}

                      {/* Next tier upgrade */}
                      {nextTierData && !excluded ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', flexWrap: 'wrap' }}>
                          <button
                            className="exile-btn exile-btn-covert"
                            disabled={loading || !relMet || !canAfford}
                            onClick={() => handleNpcBacking(npc.key, nextTierData.tier)}
                            title={!relMet
                              ? `Requires relations ≥ ${nextTierData.relReq}. Current: ${npcRel}`
                              : !canAfford
                              ? `Requires $${nextTierData.cost}B. Current: $${exileWealth.toFixed(1)}B`
                              : nextTierData.flavor}
                            style={{ flex: 1, textAlign: 'left', fontSize: '0.74rem' }}
                          >
                            <span style={{ fontWeight: 600 }}>
                              {currentTier === 0 ? 'Establish' : 'Upgrade to'} Tier {nextTierData.tier}
                            </span>
                            <span style={{ marginLeft: '0.3rem', fontSize: '0.68rem', color: 'var(--muted)' }}>
                              {nextTierData.label}
                            </span>
                          </button>
                          <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
                            {nextTierData.cost > 0 && (
                              <span style={{
                                fontSize: '0.66rem', padding: '0.1rem 0.3rem', borderRadius: '3px',
                                background: canAfford ? 'rgba(74,158,255,0.1)' : 'rgba(229,74,74,0.1)',
                                color: canAfford ? 'var(--accent)' : 'var(--danger)'
                              }}>${nextTierData.cost}B</span>
                            )}
                            {nextTierData.cost === 0 && (
                              <span style={{
                                fontSize: '0.66rem', padding: '0.1rem 0.3rem', borderRadius: '3px',
                                background: 'rgba(76,175,110,0.1)', color: 'var(--success)'
                              }}>Free</span>
                            )}
                            <span style={{
                              fontSize: '0.66rem', padding: '0.1rem 0.3rem', borderRadius: '3px',
                              background: 'rgba(76,175,110,0.15)', color: 'var(--success)'
                            }}>+{nextTierData.bonus} pts</span>
                            <span style={{
                              fontSize: '0.66rem', padding: '0.1rem 0.3rem', borderRadius: '3px',
                              background: relMet ? 'rgba(76,175,110,0.1)' : 'rgba(229,74,74,0.1)',
                              color: relMet ? 'var(--success)' : 'var(--danger)'
                            }}>Rel ≥ {nextTierData.relReq}</span>
                          </div>
                        </div>
                      ) : excluded ? (
                        <div style={{ fontSize: '0.7rem', color: 'var(--danger)', fontStyle: 'italic' }}>
                          Blocked — conflicting tier 3+ commitment
                        </div>
                      ) : atCap ? (
                        <div style={{ fontSize: '0.7rem', color: 'var(--warning)', fontStyle: 'italic' }}>
                          Maximum tier reached for this NPC (cap: {maxTier})
                        </div>
                      ) : atMax ? (
                        <div style={{ fontSize: '0.7rem', color: 'var(--success)', fontStyle: 'italic' }}>
                          Maximum tier reached
                        </div>
                      ) : null}

                      {/* Exclusion warning for tiers approaching 3 */}
                      {nextTierData && nextTierData.tier >= 3 && !excluded && exclusionWarn && (
                        <div style={{
                          fontSize: '0.66rem', color: 'var(--warning)', marginTop: '0.2rem',
                          fontStyle: 'italic'
                        }}>
                          ⚠ {exclusionWarn}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Fix E: NPC dialogue display */}
          {exileDialogue && (
            <div className="exile-npc-dialogue">
              <div className="exile-dialogue-header">
                {NPC_LIST.find(n => n.key === exileDialogue.npc)?.flag}{' '}
                {NPC_LIST.find(n => n.key === exileDialogue.npc)?.label || exileDialogue.npc}
              </div>
              <div className="exile-dialogue-text">{exileDialogue.text}</div>
              <button className="exile-dialogue-dismiss" onClick={onDismissDialogue}>Dismiss</button>
            </div>
          )}

          {/* Messages feed */}
          {messages && messages.length > 0 && (
            <div className="exile-messages">
              <div className="exile-section-title">LOG</div>
              {messages.map((msg, i) => (
                <div key={i} className="exile-message">{msg}</div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Fix D: Covert operation confirmation modal */}
      {showCovertConfirm && (
        <div className="exile-modal-overlay" onClick={() => { setShowCovertConfirm(null); setCovertTargetNpc(null) }}>
          <div className="exile-modal" onClick={e => e.stopPropagation()}>
            <div className="exile-modal-title">
              {showCovertConfirm === 'destabilize' && 'DESTABILIZE'}
              {showCovertConfirm === 'maintenance' && 'MAINTAIN NETWORK'}
              {showCovertConfirm === 'return_prep' && 'PREPARE RETURN'}
            </div>
            <div className="exile-modal-price">
              <strong>Cost:</strong>{' '}
              {showCovertConfirm === 'destabilize' && '$1.5B'}
              {showCovertConfirm === 'maintenance' && '$0.8B'}
              {showCovertConfirm === 'return_prep' && '$2.0B'}
            </div>
            {showCovertConfirm === 'return_prep' && (
              <div className="exile-covert-npc-select">
                <div className="exile-modal-label">Select target NPC:</div>
                <div className="exile-covert-npc-grid">
                  {NPC_LIST.map(npc => (
                    <button
                      key={npc.key}
                      className={`exile-btn exile-btn-npc-select ${covertTargetNpc === npc.key ? 'selected' : ''}`}
                      onClick={() => setCovertTargetNpc(npc.key)}
                    >
                      {npc.flag} {npc.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="exile-modal-warning">
              {showCovertConfirm === 'destabilize' && 'Detection risk applies. If caught, all NPC relations suffer.'}
              {showCovertConfirm === 'maintenance' && 'Low risk operation. Pauses NPC relation drift.'}
              {showCovertConfirm === 'return_prep' && 'Medium risk. If detected, target NPC relations drop.'}
            </div>
            <div className="exile-modal-actions">
              <button
                className="exile-btn exile-btn-accept"
                disabled={loading || (showCovertConfirm === 'return_prep' && !covertTargetNpc)}
                onClick={() => {
                  onExileAction('covert_op', covertTargetNpc, showCovertConfirm)
                  setShowCovertConfirm(null)
                  setCovertTargetNpc(null)
                }}
              >
                Confirm
              </button>
              <button
                className="exile-btn exile-btn-cancel"
                onClick={() => { setShowCovertConfirm(null); setCovertTargetNpc(null) }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fix F: Reach-out cost confirmation modal */}
      {showReachConfirm && (() => {
        const npc = NPC_LIST.find(n => n.key === showReachConfirm)
        const npcRel = Math.round((rel[showReachConfirm] ?? 30))
        const estCost = getReachOutCost(showReachConfirm, gs.exile_trigger, npcRel)
        const dailyBurn = getDailyBurn(gs.exile_apparatus_survived)
        const totalCost = Math.round((estCost + dailyBurn) * 10) / 10
        return (
          <div className="exile-modal-overlay" onClick={() => setShowReachConfirm(null)}>
            <div className="exile-modal" onClick={e => e.stopPropagation()}>
              <div className="exile-modal-title">
                REACH OUT: {npc?.flag} {npc?.label}
              </div>
              <div className="exile-modal-price">
                <strong>Total Cost:</strong> ${totalCost.toFixed(1)}B
              </div>
              <div className="exile-modal-detail">
                Reach-out: ${estCost.toFixed(1)}B + daily burn: ${dailyBurn.toFixed(1)}B
              </div>
              <div className="exile-modal-detail">
                Current relations: {npcRel}/100
              </div>
              {gs.exile_trigger === 'voted_out' && (
                <div className="exile-modal-detail exile-modal-discount">
                  Voted-out discount applied (20% reduction)
                </div>
              )}
              {npcRel < 20 && (
                <div className="exile-modal-detail exile-modal-surcharge">
                  Low relations surcharge (+50%)
                </div>
              )}
              <div className="exile-modal-actions">
                <button
                  className="exile-btn exile-btn-accept"
                  disabled={loading || wealth < totalCost}
                  onClick={() => {
                    onExileAction('reach_out', showReachConfirm)
                    setShowReachConfirm(null)
                  }}
                >
                  Confirm
                </button>
                <button
                  className="exile-btn exile-btn-cancel"
                  onClick={() => setShowReachConfirm(null)}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )
      })()}

      {/* 9A Section 5: Backchannel Modal during exile */}
      {backchannelNpc && sessionId && (
        <BackchannelModal
          npcKey={backchannelNpc}
          npcLabel={NPC_LIST.find(n => n.key === backchannelNpc)?.label || backchannelNpc}
          gs={gs}
          sessionId={sessionId}
          onClose={() => setBackchannelNpc(null)}
          onGsUpdate={onGsUpdate}
        />
      )}

      {/* 9A: Return Attempt Modal */}
      {showReturnModal && (
        <ReturnAttemptModal
          gs={gs}
          loading={loading}
          onAttempt={async () => {
            const res = await onExileAction('9a_attempt_return')
            return res
          }}
          onClose={(deferredGs) => {
            setShowReturnModal(false)
            // FIX B: Apply deferred game state after modal closes (successful return)
            if (deferredGs) {
              console.log('[FIXB] applying deferred game state — in_exile:', deferredGs.in_exile)
              onGsUpdate(deferredGs)
            }
          }}
        />
      )}

      {/* Backing modal */}
      {showBackingModal && (
        <div className="exile-modal-overlay" onClick={() => setShowBackingModal(null)}>
          <div className="exile-modal" onClick={e => e.stopPropagation()}>
            <div className="exile-modal-title">
              Accept Backing: {NPC_LIST.find(n => n.key === showBackingModal)?.label}
            </div>
            <div className="exile-modal-price">
              <strong>Price:</strong> {BACKING_PRICES[showBackingModal]}
            </div>
            <div className="exile-modal-warning">
              This choice is permanent.
              {(BACKING_EXCLUSIONS[showBackingModal] || []).length > 0 && (
                <div className="exile-modal-exclusion">
                  Accepting {NPC_LIST.find(n => n.key === showBackingModal)?.label} backing will permanently close backing from: {BACKING_EXCLUSIONS[showBackingModal].join(', ')}.
                </div>
              )}
            </div>
            <div className="exile-modal-actions">
              <button
                className="exile-btn exile-btn-accept"
                disabled={loading}
                onClick={() => {
                  onExileAction('accept_backing', showBackingModal)
                  setShowBackingModal(null)
                }}
              >
                ACCEPT
              </button>
              <button
                className="exile-btn exile-btn-cancel"
                onClick={() => setShowBackingModal(null)}
              >
                CANCEL
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
