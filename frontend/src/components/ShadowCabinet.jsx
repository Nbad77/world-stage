/**
 * ShadowCabinet — Session 5 complete rewrite.
 * Three-drawer architecture:
 *   DRAWER 1 — INFRASTRUCTURE: Five axis tracks with invest/defund controls.
 *   DRAWER 2 — OPERATIONS: Per-turn brigade deployments (Security >= 3 gate).
 *   DRAWER 3 — SPECIAL: Ministry of Information, Foreign Intel, tax levers, one-time purchases.
 *
 * Props:
 *   gs               : game_state object
 *   sessionId        : string
 *   onClose          : () => void
 *   onUpgradePurchased : (newGs, info?) => void
 *   onRestart        : () => void
 */

import { useState, useEffect } from 'react'
import { api } from '../api'
import AdvisorPanel from './AdvisorPanel'
import AdministrationTab from './AdministrationTab'

// ── Axis definitions ────────────────────────────────────────────────────────

// Session 6: Security split into Military + Intelligence
const AXES = [
  {
    id: 'military',
    label: 'Military',
    icon: '⚔️',
    desc: 'Standing army, defense procurement, force projection.',
    unlocks: [
      { level: 3, label: 'Defense Procurement — +5 military per purchase' },
      { level: 6, label: 'Standing Army — military decay halved' },
      { level: 9, label: 'Force Projection — military threat as negotiation tool' },
      { level: 10, label: 'Arms Export — sell weapons to NPC ally' },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    icon: '🕵️',
    desc: 'State intelligence, intercepts, covert operations.',
    unlocks: [
      { level: 3, label: 'State Intelligence Bureau — Tier 1/2 intercepts' },
      { level: 5, label: 'Intelligence Sharing — +12 relations with one NPC' },
      { level: 6, label: 'Shadow Apparatus — Tier 3 intercepts, covert ops' },
      { level: 9, label: 'Full Spectrum — neutralize NPC covert actions' },
      { level: 10, label: 'Counterintelligence Veil — NPC intel muddied' },
    ],
  },
  {
    id: 'resource_dev',
    label: 'Resource Development',
    icon: '🏗️',
    desc: 'Legitimate economic development. The clean path.',
    unlocks: [
      { level: 3, label: 'Export Contract — one-time +$8B national' },
      { level: 5, label: 'GDP Credibility — NPC ceilings +20%' },
      { level: 6, label: 'Sovereign Collateral Loan — $10B available' },
      { level: 8, label: 'Strategic Resource Partner — one NPC ceiling +50%' },
      { level: 9, label: 'Resource Independence — oil imports eliminated' },
      { level: 10, label: 'Better Bond Terms — reduced interest rates' },
    ],
  },
  {
    id: 'media',
    label: 'Media Control',
    icon: '📺',
    desc: 'State media, propaganda, press censorship.',
    unlocks: [
      { level: 3, label: 'Approval floor 10%' },
      { level: 5, label: 'Approval floor 15%, penalties -20%' },
      { level: 8, label: 'Total media control' },
    ],
  },
  {
    id: 'judicial',
    label: 'Judicial Capture',
    icon: '⚖️',
    desc: 'Court control, legal immunity, opposition prosecution.',
    unlocks: [
      { level: 4, label: 'Corruption scandals eliminated' },
      { level: 7, label: 'Complete legal immunity' },
    ],
  },
  {
    id: 'political',
    label: 'Political Control',
    icon: '🏛️',
    desc: 'Opposition suppression, party control, constitutional changes.',
    unlocks: [
      { level: 3, label: 'Opposition weakened' },
      { level: 6, label: 'Opposition dissolved — coup risk eliminated' },
      { level: 9, label: 'One-party state' },
    ],
  },
  {
    id: 'extraction',
    label: 'Extraction Network',
    icon: '💰',
    desc: 'Wealth siphoning, shell companies, offshore accounts.',
    unlocks: [
      { level: 5, label: 'Large skim penalty halved' },
      { level: 5, label: 'One-time: +$7B personal injection' },
      { level: 7, label: 'Skim ceiling removed' },
    ],
  },
]

// 9.5A-Shadow: Only these axes appear in the POWER BASE drawer
const POWER_BASE_AXES = ['media', 'judicial', 'domestic_surveillance', 'extraction', 'militia']

// 9.5A-Shadow: domestic_surveillance axis definition (new axis)
const DOMESTIC_SURVEILLANCE_DEF = {
  id: 'domestic_surveillance',
  label: 'Domestic Surveillance',
  icon: '📷',
  desc: 'Informant networks, wiretaps, digital monitoring.',
  unlocks: [
    { level: 3, label: 'Digital monitoring — basic threat detection' },
    { level: 6, label: 'Pervasive surveillance — protest detection, dissident tracking' },
    { level: 9, label: 'Total awareness — preemptive threat neutralization' },
  ],
}

// 9.5A-Shadow: Militia / Loyalty Brigades axis definition
const MILITIA_DEF = {
  id: 'militia',
  label: 'Militia / Loyalty Brigades',
  icon: '⚔️',
  desc: 'Personal armed forces, loyalty enforcers, regime protection.',
  unlocks: [
    { level: 3, label: 'Loyalty patrols — basic regime enforcement' },
    { level: 6, label: 'Organized brigades — protest suppression, intimidation' },
    { level: 9, label: 'Integrated force — parallel military structure' },
  ],
}

const AXIS_COSTS = {
  military:      [1, 1, 2, 3, 3, 4, 5, 6, 7, 8],
  intelligence:  [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
  resource_dev:  [1, 2, 3, 3, 4, 5, 5, 6, 7, 8],
  media:         [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
  judicial:      [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
  political:     [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
  extraction:    [1, 1, 1, 2, 2, 3, 3, 4, 5, 6],
  domestic_surveillance: [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
  militia:       [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
}

const AXIS_MAINTENANCE = {
  military:      [3, 0.5],
  intelligence:  [3, 0.4],
  resource_dev:  [3, 0.3],
  media:         [3, 0.3],
  judicial:      [4, 0.4],
  political:     [3, 0.3],
  extraction:    [3, 0.2],
  domestic_surveillance: [3, 0.3],
  militia:       [3, 0.3],
}

const AXIS_FLOORS = { military: 2, intelligence: 1, resource_dev: 0, media: 2, judicial: 2, political: 2, extraction: 1, domestic_surveillance: 0, militia: 0 }

// ── Brigade Operations ──────────────────────────────────────────────────────

// 10C: Propaganda Campaign (id 1) removed — replaced by Media axis
// 10C: Domestic Suppression (id 2) removed — replaced by Surveillance axis
const OPERATIONS = [
  {
    id: 3,
    label: 'Foreign Influence Op',
    icon: '🕵️',
    cost: 1.5,
    effect: '+5 relations with target',
    minIntelligence: 3,
    needsTarget: true,
    budgetType: 'PERSONAL',
  },
  {
    id: 4,
    label: 'Covert Security',
    icon: '🖤',
    cost: 2.5,
    effect: '-10 detection heat, +3% stability',
    minIntelligence: 3,
    budgetType: 'PERSONAL',
  },
]

// fixes_13 Fix 26: Black Operations suite at Security 6
const BLACK_OPS = [
  {
    id: 'fabricate_crisis',
    label: 'Fabricate Crisis',
    icon: '🖤',
    cost: 4.0,
    effect: 'Target NPC pressure suspended 2 turns',
    risk: '35% detection',
    needsTarget: true,
    budgetType: 'PERSONAL',
  },
  {
    id: 'reputation_laundering',
    label: 'Reputation Laundering',
    icon: '🖤',
    cost: 3.0,
    effect: 'Heat -15',
    risk: 'No detection risk',
    needsTarget: false,
    budgetType: 'PERSONAL',
  },
  {
    id: 'blackmail',
    label: 'Blackmail Operation',
    icon: '🖤',
    cost: 5.0,
    effect: 'Extract one-time concession (requires Tier 3 intel)',
    risk: '40% detection, NPC -5 permanent',
    needsTarget: true,
    requiresTier: 3,
    onePerNpc: true,
    budgetType: 'PERSONAL',
  },
  {
    id: 'false_flag',
    label: 'False Flag',
    icon: '🖤',
    cost: 6.0,
    effect: 'Blame action on target — bilateral -10',
    risk: '50% detection (if caught: both NPCs -20)',
    needsTarget: true,
    budgetType: 'PERSONAL',
  },
  {
    id: 'political_sabotage',
    label: 'Political Sabotage',
    icon: '🖤',
    cost: 3.0,
    effect: 'Pressure suspended 1 turn + cross-NPC penalty -50%',
    risk: '25% detection (requires Tier 2 intel)',
    needsTarget: true,
    requiresTier: 2,
    budgetType: 'PERSONAL',
  },
]

// ── Regime descriptions ─────────────────────────────────────────────────────

const REGIME_DESCRIPTIONS = {
  'Managed Democracy':     'Elections are held. Results are managed.',
  'Soft Authoritarianism': 'Opposition exists. It does not threaten.',
  'Patronage State':       'Loyalty is purchased. Disloyalty is expensive.',
  'Kleptocracy':           'The treasury and the personal account blur.',
  'Totalitarian Regime':   'The state is you. You are the state.',
}

const POWER_DESCRIPTIONS = {
  'Mass-Dependent': 'Survival requires popular legitimacy.',
  'Mixed':          'Some constituencies, some elites.',
  'Elite-Captured': 'Oligarchs keep you in power. You keep them profitable.',
}

// ── Component ───────────────────────────────────────────────────────────────

// ── AdvisorDrawer: Active advisors + hiring pool ─────────────────────────────

// v2 hiring cost display logic per archetype
const HIRE_COST_LABELS = {
  finance_minister: '$0.5B national',
  technocrat: '$0.5B national',
  diplomat: '$0.5B national',
  general: '$0.5B national',
  spy_chief: '$1B national',
  propagandist: '$0.5B personal',
  militia_commander: '$0.5B personal',
  oligarch: '$1B personal',
  fixer: '$1B personal',
}

function AdvisorDrawer({ gs, sessionId, loading: parentLoading, setLoading: setParentLoading, onUpgradePurchased }) {
  const [pool, setPool] = useState(gs?.advisor_pool || [])
  const [poolLoading, setPoolLoading] = useState(false)
  const [poolError, setPoolError] = useState(null)
  const [hireLoading, setHireLoading] = useState(null)

  // Refresh pool from server (v2: dynamic, shows all eligible)
  async function refreshPool() {
    setPoolLoading(true)
    setPoolError(null)
    try {
      const res = await api.getAdvisorPool(sessionId)
      setPool(res.pool || [])
    } catch (e) {
      setPoolError(e.message)
    } finally {
      setPoolLoading(false)
    }
  }

  // Load pool on mount
  useEffect(() => {
    refreshPool()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleHire(advisorId) {
    const hireTarget = pool.find(a => a.id === advisorId)
    const archetype = hireTarget?.archetype || advisorId
    console.log(`[advisor] HIRE CLICKED: ${archetype} — pool count before: ${pool.length}`)
    setHireLoading(advisorId)
    setPoolError(null)
    try {
      const res = await api.hireAdvisor(sessionId, advisorId)
      const newPool = res.advisor_pool || []
      const hiredName = hireTarget?.name || advisorId
      console.log(`[advisor] HIRE COMPLETE: ${hiredName} added to roster — pool count after: ${newPool.length}`)
      setPool(newPool)
      if (res.game_state && onUpgradePurchased) onUpgradePurchased(res.game_state)
    } catch (e) {
      setPoolError(e.message)
      setTimeout(() => setPoolError(null), 3000)
    } finally {
      setHireLoading(null)
    }
  }

  const staffCount = Object.keys(gs?.advisors || {}).filter(k => {
    const a = gs.advisors[k]
    return a && typeof a === 'object' && a.archetype
  }).length

  return (
    <div className="sc-drawer-content">
      <div className="sc-drawer-header">ADVISORS</div>
      <div className="sc-drawer-subtitle">
        Your inner circle. Assign up to 2 per day. Trust determines loyalty. Betrayal is permanent.
      </div>

      {/* Staff roster */}
      <AdvisorPanel
        gs={gs}
        sessionId={sessionId}
        onGsUpdate={(newGs) => {
          if (onUpgradePurchased) onUpgradePurchased(newGs)
          // Refresh pool after dismiss/eliminate (archetype may return to pool)
          refreshPool()
        }}
      />

      {/* Hiring Pool */}
      <div className="advisor-pool-section">
        <div className="advisor-pool-header">
          <span className="advisor-pool-title">AVAILABLE TO HIRE</span>
          <span className="advisor-pool-slots">{staffCount} on staff</span>
        </div>

        {poolError && <div className="advisor-error">{poolError}</div>}

        {pool.length === 0 && !poolLoading && (
          <div className="advisor-pool-empty">
            All eligible archetypes are on staff or eliminated.
            <button className="advisor-pool-refresh-btn" onClick={refreshPool}>Refresh</button>
          </div>
        )}

        {poolLoading && <div className="advisor-pool-empty">Loading pool...</div>}

        <div className="advisor-pool-list">
          {pool.map(adv => {
            const costLabel = HIRE_COST_LABELS[adv.archetype] || '$0.5B'
            return (
              <div key={adv.id} className="advisor-pool-card">
                <div className="advisor-pool-card-top">
                  <span className="advisor-card-icon">{adv.icon || '👤'}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="advisor-card-name">{adv.name}</div>
                    <div className="advisor-archetype-label">{adv.label}</div>
                  </div>
                </div>
                {/* Competence / Loyalty preview */}
                <div className="advisor-pool-stats">
                  <span>C: {adv.competence ?? '—'}</span>
                  <span>L: {adv.loyalty ?? '—'}</span>
                </div>
                <button
                  className="advisor-pool-hire-btn"
                  onClick={() => handleHire(adv.id)}
                  disabled={hireLoading === adv.id}
                >
                  {hireLoading === adv.id ? 'Hiring...' : `Hire — ${costLabel}`}
                </button>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}


export default function ShadowCabinet({ gs, sessionId, onClose, onUpgradePurchased, onRestart }) {
  const [activeDrawer, setActiveDrawer] = useState(0) // 0=infra, 1=ops, 2=special
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)
  const [confirmAbandon, setConfirmAbandon] = useState(false)
  const [selectedTarget, setSelectedTarget] = useState('usa')
  const [armsExportTarget, setArmsExportTarget] = useState('usa')
  const [offshoreAmount, setOffshoreAmount] = useState(5)

  // 9.5A-Shadow: Skim rate state
  const savedSkim = gs?.skim_rate ?? 0
  const [skimRate, setSkimRate] = useState(savedSkim)
  const [skimSaving, setSkimSaving] = useState(false)
  const [skimFlash, setSkimFlash] = useState(null)

  // 9.5C: Loyal leadership UI state
  const [loyalLoading, setLoyalLoading] = useState(null)
  const [loyalFlash, setLoyalFlash] = useState(null)

  // Sync skim from gs
  useEffect(() => {
    setSkimRate(gs?.skim_rate ?? 0)
  }, [gs?.skim_rate])

  const axes = gs?.cabinet_axes || { military: 0, intelligence: 0, resource_dev: 0, media: 0, judicial: 0, political: 0, extraction: 0 }
  const personalWealth = gs?.personal_wealth || 0
  const regimeType = gs?.state_identity?.regime_type || 'Managed Democracy'
  const powerBase = gs?.state_identity?.power_base || 'Mass-Dependent'
  // Session 6: Security split into Military + Intelligence
  // 9.5A-Shadow: Read from commitment tier fields
  const militaryLevel = gs?.military_tier ?? (axes.military || 0)
  const intelligenceLevel = gs?.intelligence_tier ?? (axes.intelligence || 0)

  // fixes_11 Fix 2: Check if a brigade operation was already deployed this turn
  const opsThisTurn = gs?.brigade_operations_this_turn || []
  const currentTurn = gs?.current_turn || 1
  const deployedThisTurn = opsThisTurn.some(o => o.turn === currentTurn && o.operation !== 0)

  // ── Axis invest/defund handler ──────────────────────────────────────────
  // 9.5A-Shadow: Skim rate handler
  async function handleSkimApply() {
    if (skimSaving) return
    setSkimSaving(true)
    setSkimFlash(null)
    try {
      const res = await api.shadowSetSkim(sessionId, skimRate)
      if (res.success) {
        if (res.game_state) onUpgradePurchased(res.game_state)
        setSkimFlash(res.message || 'Skim rate updated')
      } else {
        setSkimFlash(res.error || 'Failed')
      }
      setTimeout(() => setSkimFlash(null), 3000)
    } catch (e) {
      setSkimFlash('Failed: ' + e.message)
      setTimeout(() => setSkimFlash(null), 3000)
    } finally {
      setSkimSaving(false)
    }
  }


  // 9.5C-FIX: Shadow axes route to /shadow/upgrade|downgrade, others to /cabinet_invest
  const SHADOW_AXES = ['media', 'judicial', 'domestic_surveillance', 'extraction']
  const MILITIA_AXIS = 'militia'

  async function handleAxisAction(axisId, direction) {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    const isShadow = SHADOW_AXES.includes(axisId) || axisId === MILITIA_AXIS
    console.log('[POWER BASE] axis action:', { axisId, direction, endpoint: isShadow ? 'shadow' : 'cabinet' })
    try {
      let res
      if (isShadow) {
        res = direction === 'invest'
          ? await api.shadowUpgrade(sessionId, axisId)
          : await api.shadowDowngrade(sessionId, axisId)
      } else {
        res = await api.cabinetInvest(sessionId, axisId, direction)
      }
      // Session 6: Console log for new axis changes
      if (axisId === 'military' || axisId === 'intelligence' || axisId === 'resource_dev') {
        console.log(`[${axisId.toUpperCase()}] ${direction}: ${res.message}`)
      }
      setSuccessMsg(res.message)
      onUpgradePurchased && onUpgradePurchased(res.game_state, {
        label: `${direction} ${axisId}`,
        messages: [res.message],
      })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── Brigade operation handler ───────────────────────────────────────────
  async function handleOperation(opId) {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const res = await api.brigadeOperation(sessionId, opId, selectedTarget)
      setSuccessMsg(res.messages?.[0] || 'Operation executed')
      onUpgradePurchased && onUpgradePurchased(res.game_state, {
        label: `brigade op ${opId}`,
        messages: res.messages || [],
      })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // fixes_13 Fix 26: Black Operations handler
  async function handleBlackOp(opId) {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const res = await api.blackOperation(sessionId, opId, selectedTarget)
      const allMsgs = res.messages || []
      setSuccessMsg(allMsgs.join('\n'))
      if (res.detected) {
        setError('⚠️ OPSEC FAILURE — Operation was detected')
      }
      onUpgradePurchased && onUpgradePurchased(res.game_state, {
        label: `black op: ${opId}`,
        messages: allMsgs,
      })
      console.log(`[ShadowCabinet] Fix 26: Black op '${opId}' targeting ${selectedTarget}, detected=${res.detected}`)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── Session 6: Generic axis action handler ─────────────────────────────
  async function handleAxisAction2(axisName, apiFn, actionId, extraArgs = {}) {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const res = await apiFn(sessionId, actionId, ...Object.values(extraArgs))
      const allMsgs = res.messages || []
      setSuccessMsg(allMsgs.join('\n'))
      onUpgradePurchased && onUpgradePurchased(res.game_state, {
        label: `${axisName}: ${actionId}`,
        messages: allMsgs,
      })
      console.log(`[${axisName.toUpperCase()}] Action '${actionId}', messages:`, allMsgs)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }
  function handleMilitaryAction(actionId) {
    handleAxisAction2('military', api.militaryAction, actionId, { target: selectedTarget })
  }
  function handleIntelAction(actionId) {
    handleAxisAction2('intelligence', api.intelligenceAction, actionId, { target: selectedTarget })
  }
  function handleMediaAction(actionId) {
    handleAxisAction2('media', api.mediaAction, actionId, { target: selectedTarget })
  }
  function handleJudicialAction(actionId) {
    handleAxisAction2('judicial', api.judicialAction, actionId, { target: selectedTarget })
  }
  function handlePoliticalAction(actionId) {
    handleAxisAction2('political', api.politicalAction, actionId)
  }
  function handleExtractionAction(actionId, amount = 0) {
    handleAxisAction2('extraction', api.extractionAction, actionId, { amount, target: selectedTarget })
  }
  function handleResourceDevAction(actionId) {
    handleAxisAction2('resource_dev', api.resourceDevAction, actionId, { target: selectedTarget })
  }

  // ── 10C: Generic operations handler ──────────────────────────────────────
  async function handleOp10c(apiMethod, ...args) {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const res = await api[apiMethod](sessionId, ...args)
      if (res.game_state && onUpgradePurchased) onUpgradePurchased(res.game_state)
      setSuccessMsg(res.messages?.[0] || res.intel || 'Operation complete')
    } catch (e) {
      setError(e.message || 'Operation failed')
      setTimeout(() => setError(null), 4000)
    } finally {
      setLoading(false)
    }
  }

  // ── Legacy upgrade purchase (for SPECIAL drawer) ────────────────────────
  async function handlePurchase(upgradeId) {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const res = await api.purchaseUpgrade(sessionId, upgradeId)
      setSuccessMsg(res.messages?.[0] || 'Upgrade purchased')
      onUpgradePurchased && onUpgradePurchased(res.game_state, {
        label: res.upgrade_label || upgradeId,
        messages: res.messages || [],
      })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── Domestic action handler ─────────────────────────────────────────────
  async function handleDomesticAction(actionId) {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const res = await api.domesticAction(sessionId, actionId)
      if (res.success) {
        setSuccessMsg(res.changes?.join(', ') || 'Action enacted')
        onUpgradePurchased && onUpgradePurchased(res.game_state, {
          label: actionId,
          messages: res.changes || [],
        })
      } else {
        setError(res.changes?.join(', ') || 'Action failed')
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── Tax rate handler ────────────────────────────────────────────────────
  async function handleTaxChange(taxType, newValue) {
    setLoading(true)
    setError(null)
    try {
      const body = { [taxType]: newValue }
      const res = await api.setTaxRates(sessionId, body)
      setSuccessMsg(res.changes?.join(', ') || 'Tax rate updated')
      onUpgradePurchased && onUpgradePurchased(res.game_state, {
        label: `tax_${taxType}`,
        messages: res.changes || [],
      })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // Compute maintenance cost display
  function getMaintenanceCost(axisId) {
    const level = axes[axisId] || 0
    const [freeThresh, costPer] = AXIS_MAINTENANCE[axisId] || [3, 0.3]
    if (level <= freeThresh) return 0
    return ((level - freeThresh) * costPer).toFixed(1)
  }

  // ── Drawer tabs ─────────────────────────────────────────────────────────
  // fixes_11 Fix 3: Added ADVISORS as 4th drawer tab
  const drawerTabs = [
    { id: 0, label: 'POWER BASE', icon: '🕶️' },
    { id: 1, label: 'OPERATIONS', icon: '⚔️', locked: false },
    { id: 2, label: 'ADMINISTRATION', icon: '🧠' },
  ]

  return (
    <div className="shadow-cabinet-overlay" onClick={onClose}>
      <div className="shadow-cabinet-drawer" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="sc-header">
          <span className="sc-title">🗄️ CABINET</span>
          <button className="sc-close-btn" onClick={onClose}>✕</button>
        </div>

        {/* Regime identity section */}
        <div className="sc-section">
          <div className="sc-regime-block">
            <div className="sc-regime-name">{regimeType}</div>
            <div className="sc-regime-desc">{REGIME_DESCRIPTIONS[regimeType] || ''}</div>
            <div className="sc-power-name">Power Base: {powerBase}</div>
            <div className="sc-power-desc">{POWER_DESCRIPTIONS[powerBase] || ''}</div>
          </div>
        </div>

        {/* Personal wealth */}
        <div className="sc-section" style={{ paddingTop: 0 }}>
          <div className="sc-wealth">${personalWealth.toFixed(1)}B personal funds</div>
        </div>

        {/* 9.5A-Shadow: Personal wealth + shadow drain summary */}
        <div className="sc-budget-summary">
          <span className="sc-budget-tag" style={{ color: '#c8a84b' }}>
            🏦 PW: ${personalWealth.toFixed(1)}B
          </span>
          {(gs?.total_daily_shadow_cost || 0) > 0 && (
            <span className="sc-budget-tag" style={{ color: '#c8a84b' }}>
              🕶️ Shadow: -${(gs?.total_daily_shadow_cost || 0).toFixed(1)}B/day
            </span>
          )}
          {(gs?.skim_rate || 0) > 0 && (
            <span className="sc-budget-tag" style={{ color: '#c8a84b' }}>
              💰 Skim: {((gs?.skim_rate || 0) * 100).toFixed(0)}%
            </span>
          )}
        </div>

        {/* Feedback messages */}
        {successMsg && <div className="sc-success">{successMsg}</div>}
        {error && <div className="sc-error">{error}</div>}

        {/* Drawer tabs */}
        <div className="sc-drawer-tabs">
          {drawerTabs.map(tab => (
            <button
              key={tab.id}
              className={`sc-drawer-tab ${activeDrawer === tab.id ? 'sc-drawer-tab-active' : ''} ${tab.locked ? 'sc-drawer-tab-locked' : ''}`}
              onClick={() => !tab.locked && setActiveDrawer(tab.id)}
              title={tab.locked ? 'Requires Security axis level 3' : tab.label}
            >
              <span className="sc-tab-icon">{tab.icon}</span>
              <span className="sc-tab-label">{tab.label}</span>
              {tab.locked && <span className="sc-tab-lock">🔒</span>}
            </button>
          ))}
        </div>

        {/* ═══════════════════════════════════════════════════════════════════
            DRAWER 1 — INFRASTRUCTURE
        ═══════════════════════════════════════════════════════════════════ */}
        {activeDrawer === 0 && (
          <div className="sc-drawer-content">
            <div className="sc-drawer-header" style={{ color: '#c8a84b' }}>POWER BASE</div>
            <div className="sc-drawer-subtitle">
              Covert state power. All funded from personal wealth.
            </div>
            {[...AXES.filter(a => POWER_BASE_AXES.includes(a.id)), DOMESTIC_SURVEILLANCE_DEF, MILITIA_DEF].map(axis => {
              const level = axes[axis.id] || 0
              const costs = AXIS_COSTS[axis.id] || []
              const nextCost = level < 10 ? costs[level] : null
              // 9.5A-Shadow: All power base axes use personal wealth
              const usesNational = false
              const budgetSource = 'PERSONAL'
              const availableFunds = personalWealth
              const canInvest = nextCost !== null && availableFunds >= nextCost
              const floor = AXIS_FLOORS[axis.id] || 1
              const canDefund = level > 0 && level > floor
              const maint = getMaintenanceCost(axis.id)
              // Tooltip for personal investments when personal wealth = $0
              const investTooltip = level >= 10
                ? 'Max level'
                : !canInvest && !usesNational && personalWealth <= 0
                  ? 'Requires personal funds — skim national budget first to build personal wealth'
                  : !canInvest
                    ? `Need $${nextCost}B ${usesNational ? 'national' : 'personal'}`
                    : `Invest: $${nextCost}B ${usesNational ? 'national budget' : 'personal wealth'}`
              return (
                <div key={axis.id} className="sc-axis-track">
                  <div className="sc-axis-header">
                    <span className="sc-axis-icon">{axis.icon}</span>
                    <span className="sc-axis-label">{axis.label}</span>
                    <span className="sc-axis-level">{level}/10</span>
                  </div>
                  <div className="sc-axis-desc">{axis.desc}</div>
                  {/* Level bar */}
                  <div className="sc-axis-bar">
                    {Array.from({ length: 10 }, (_, i) => (
                      <div
                        key={i}
                        className={`sc-axis-pip ${i < level ? 'sc-axis-pip-filled' : ''} ${i < floor && level > 0 ? 'sc-axis-pip-floor' : ''}`}
                        title={i < floor && level > 0 ? `Permanent floor (level ${floor})` : `Level ${i + 1}`}
                      />
                    ))}
                  </div>
                  {/* Maintenance cost */}
                  {parseFloat(maint) > 0 && (
                    <div className="sc-axis-maint">Maintenance: ${maint}B/turn</div>
                  )}
                  {/* Unlock indicators */}
                  <div className="sc-axis-unlocks">
                    {axis.unlocks.map((u, i) => (
                      <div key={i} className={`sc-axis-unlock ${level >= u.level ? 'sc-axis-unlock-active' : ''}`}>
                        <span className="sc-unlock-marker">{level >= u.level ? '✓' : `Lv${u.level}`}</span>
                        <span className="sc-unlock-text">{u.label}</span>
                      </div>
                    ))}
                  </div>
                  {/* Controls */}
                  <div className="sc-axis-controls">
                    <button
                      className={`sc-axis-btn sc-axis-btn-defund ${!canDefund ? 'sc-axis-btn-disabled' : ''}`}
                      onClick={() => canDefund && !loading && handleAxisAction(axis.id, 'defund')}
                      disabled={!canDefund || loading}
                      title={canDefund ? 'Reduce by 1 level' : `Cannot go below floor (${floor})`}
                    >
                      − Defund
                    </button>
                    <button
                      className={`sc-axis-btn sc-axis-btn-invest ${!canInvest ? 'sc-axis-btn-disabled' : ''}`}
                      onClick={() => canInvest && !loading && handleAxisAction(axis.id, 'invest')}
                      disabled={!canInvest || loading}
                      title={investTooltip}
                    >
                      <span className={`sc-op-budget-type ${usesNational ? 'sc-budget-national' : 'sc-budget-personal'}`} style={{ marginRight: '0.3rem', fontSize: '0.6rem' }}>{budgetSource}</span>
                      + Invest{nextCost !== null ? ` ($${nextCost}B)` : ''}
                    </button>
                  </div>
                </div>
              )
            })}
            {/* ══ SKIM RATE SLIDER ══ */}
            <div className="sc-axis-track" style={{ borderTop: '1px solid rgba(200,168,75,0.3)', marginTop: '0.75rem', paddingTop: '0.75rem' }}>
              <div className="sc-axis-header">
                <span className="sc-axis-icon">💰</span>
                <span className="sc-axis-label">Budget Diversion (Skim)</span>
                <span className="sc-axis-level" style={{ color: skimRate > 0.10 ? '#ff6b6b' : '#c8a84b' }}>
                  {(skimRate * 100).toFixed(0)}%
                </span>
              </div>
              <div className="sc-axis-desc">
                Divert national budget to personal wealth. Higher rates increase detection risk.
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: '0.5rem 0' }}>
                <input
                  type="range"
                  min={0}
                  max={0.50}
                  step={0.01}
                  value={skimRate}
                  onChange={e => setSkimRate(parseFloat(e.target.value))}
                  disabled={skimSaving}
                  style={{ flex: 1, accentColor: '#c8a84b' }}
                />
                <span style={{ color: '#c8a84b', minWidth: '3rem', textAlign: 'right', fontSize: '0.85rem' }}>
                  {(skimRate * 100).toFixed(0)}%
                </span>
              </div>
              <div style={{ fontSize: '0.7rem', color: '#888', marginBottom: '0.3rem' }}>
                {skimRate === 0 && 'No diversion. Clean governance.'}
                {skimRate > 0 && skimRate <= 0.05 && 'Low diversion. Minimal detection risk.'}
                {skimRate > 0.05 && skimRate <= 0.10 && '⚠️ Above 5%: generates detection heat each turn.'}
                {skimRate > 0.10 && skimRate <= 0.20 && '⚠️⚠️ Above 10%: significant heat generation.'}
                {skimRate > 0.20 && '🛑 Above 20%: extremely risky — rapid NPC detection.'}
              </div>
              {skimRate > 0 && (() => {
                const grossRevenue = (gs?.last_gross_revenue > 0)
                  ? gs.last_gross_revenue
                  : (gs?.last_net_revenue > 0
                    ? gs.last_net_revenue / (1 - (gs?.skim_rate || 0))
                    : null)
                const skimDollars = grossRevenue
                  ? (grossRevenue * skimRate).toFixed(2)
                  : '—'
                console.log('[FIX] skim display:', {grossRevenue, skimRate, skimDollars, last_gross: gs?.last_gross_revenue})
                return (
                  <div style={{ fontSize: '0.75rem', color: '#c8a84b' }}>
                    {skimDollars !== '—'
                      ? `${(skimRate * 100).toFixed(0)}% — $${skimDollars}B/day`
                      : `${(skimRate * 100).toFixed(0)}% — (play first turn to calculate)`}
                  </div>
                )
              })()}
              {Math.abs(skimRate - savedSkim) > 0.005 && (
                <button
                  className="sc-axis-btn sc-axis-btn-invest"
                  onClick={handleSkimApply}
                  disabled={skimSaving}
                  style={{ marginTop: '0.4rem', width: '100%' }}
                >
                  {skimSaving ? 'Saving...' : 'Set Skim Rate'}
                </button>
              )}
              {skimFlash && (
                <div style={{ fontSize: '0.75rem', marginTop: '0.3rem', color: skimFlash.includes('Failed') ? '#ff6b6b' : '#50c878' }}>
                  {skimFlash}
                </div>
              )}
            </div>

            {/* ══ 9.5C: LOYAL LEADERSHIP ══ */}
            {(() => {
              const polTier = gs?.political_tier ?? 0
              const pw = gs?.personal_wealth ?? 0
              const genInstalled = gs?.loyal_generals_installed ?? false
              const genReversing = gs?.loyal_generals_reversing ?? false
              const genReversalDay = gs?.loyal_generals_reversal_day ?? 0
              const intelInstalled = gs?.loyal_intel_chief_installed ?? false
              const intelReversing = gs?.loyal_intel_chief_reversing ?? false
              const intelReversalDay = gs?.loyal_intel_chief_reversal_day ?? 0
              const currentDay = gs?.current_day ?? 1
              const eduTier = gs?.education_tier ?? gs?.education_level ?? 0

              console.log('[9.5C] loyal leadership panel:', {
                generals: genInstalled, intel: intelInstalled,
                gen_reversing: genReversing, intel_reversing: intelReversing
              })

              const genDaysLeft = genReversing ? Math.max(0, 3 - (currentDay - genReversalDay)) : 0
              const intelDaysLeft = intelReversing ? Math.max(0, 3 - (currentDay - intelReversalDay)) : 0

              async function handleLoyalAction(role, action) {
                const key = `${role === 'generals' ? 'gen' : 'intel'}_${action}`
                setLoyalLoading(key)
                setLoyalFlash(null)
                try {
                  const res = action === 'install'
                    ? await api.loyalInstall(sessionId, role)
                    : await api.loyalReverse(sessionId, role)
                  if (res.success && res.game_state) onUpgradePurchased(res.game_state)
                  setLoyalFlash(res.success ? 'Done' : (res.error || 'Failed'))
                  setTimeout(() => setLoyalFlash(null), 3000)
                } catch (e) {
                  setLoyalFlash('Failed: ' + e.message)
                  setTimeout(() => setLoyalFlash(null), 3000)
                } finally {
                  setLoyalLoading(null)
                }
              }

              // Only show if political tier >= 2 (close to unlock) or any loyal installed
              if (polTier < 2 && !genInstalled && !intelInstalled) return null

              return (
                <div style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
                  <div style={{ color: '#c8a84b', fontWeight: 700, fontSize: '0.78rem', marginBottom: '0.5rem', letterSpacing: '0.5px' }}>
                    LOYAL LEADERSHIP
                  </div>

                  {/* ── Loyal Generals Card ── */}
                  <div style={{ background: 'rgba(15,25,35,0.6)', border: '1px solid rgba(200,168,75,0.15)', borderRadius: '6px', padding: '0.6rem', marginBottom: '0.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.8rem' }}>⚔️ Loyal Generals</span>
                      <span style={{
                        fontSize: '0.65rem', padding: '1px 6px', borderRadius: '3px',
                        background: genReversing ? 'rgba(150,150,150,0.2)' : genInstalled ? 'rgba(251,191,36,0.15)' : 'rgba(150,150,150,0.1)',
                        color: genReversing ? '#999' : genInstalled ? '#fbbf24' : '#666',
                      }}>
                        {genReversing ? `REVERSING (${genDaysLeft}d)` : genInstalled ? 'INSTALLED' : 'NOT INSTALLED'}
                      </span>
                    </div>

                    {!genInstalled && !genReversing && (
                      <>
                        <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginBottom: '0.3rem' }}>
                          Install politically reliable generals. Coup risk -30%. Military capability reduced.
                        </div>
                        <div style={{ fontSize: '0.65rem', color: '#888', marginBottom: '0.3rem' }}>
                          Requires: Political T3+ · $3B personal
                        </div>
                        <button
                          className="sc-axis-btn sc-axis-btn-invest"
                          style={{ width: '100%', fontSize: '0.72rem' }}
                          disabled={polTier < 3 || pw < 3.0 || !!loyalLoading}
                          onClick={() => handleLoyalAction('generals', 'install')}
                        >
                          {loyalLoading === 'gen_install' ? 'Installing...' : 'INSTALL — $3B'}
                        </button>
                      </>
                    )}

                    {genInstalled && !genReversing && (
                      <>
                        <div style={{ fontSize: '0.7rem', lineHeight: 1.5 }}>
                          <div style={{ color: '#4ade80' }}>✓ Coup amplifier -30%</div>
                          <div style={{ color: '#fbbf24' }}>⚠ Military cap reduced</div>
                          <div style={{ color: '#fbbf24' }}>⚠ Decay rate +10%</div>
                        </div>
                        <button
                          className="sc-axis-btn sc-axis-btn-defund"
                          style={{ width: '100%', fontSize: '0.72rem', marginTop: '0.3rem' }}
                          disabled={pw < 2.0 || !!loyalLoading}
                          onClick={() => handleLoyalAction('generals', 'reverse')}
                        >
                          {loyalLoading === 'gen_reverse' ? 'Reversing...' : 'REVERSE — $2B · 3-day transition'}
                        </button>
                      </>
                    )}
                  </div>

                  {/* ── Loyal Intel Chief Card ── */}
                  <div style={{ background: 'rgba(15,25,35,0.6)', border: '1px solid rgba(200,168,75,0.15)', borderRadius: '6px', padding: '0.6rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.8rem' }}>🕵️ Loyal Intel Chief</span>
                      <span style={{
                        fontSize: '0.65rem', padding: '1px 6px', borderRadius: '3px',
                        background: intelReversing ? 'rgba(150,150,150,0.2)' : intelInstalled ? 'rgba(251,191,36,0.15)' : 'rgba(150,150,150,0.1)',
                        color: intelReversing ? '#999' : intelInstalled ? '#fbbf24' : '#666',
                      }}>
                        {intelReversing ? `REVERSING (${intelDaysLeft}d)` : intelInstalled ? 'INSTALLED' : 'NOT INSTALLED'}
                      </span>
                    </div>

                    {!intelInstalled && !intelReversing && (
                      <>
                        <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginBottom: '0.3rem' }}>
                          Install a trusted ally as intel chief. Coup protection +20%. Intercept quality may be... optimistic.
                        </div>
                        <div style={{ fontSize: '0.65rem', color: '#888', marginBottom: '0.3rem' }}>
                          Requires: Political T3+ · $2.5B personal
                        </div>
                        <button
                          className="sc-axis-btn sc-axis-btn-invest"
                          style={{ width: '100%', fontSize: '0.72rem' }}
                          disabled={polTier < 3 || pw < 2.5 || !!loyalLoading}
                          onClick={() => handleLoyalAction('intel_chief', 'install')}
                        >
                          {loyalLoading === 'intel_install' ? 'Installing...' : 'INSTALL — $2.5B'}
                        </button>
                      </>
                    )}

                    {intelInstalled && !intelReversing && (
                      <>
                        <div style={{ fontSize: '0.7rem', lineHeight: 1.5 }}>
                          <div style={{ color: '#4ade80' }}>✓ Coup/defection protection +20%</div>
                          <div style={{ color: '#fbbf24' }}>⚠ Intel reliability uncertain</div>
                          <div style={{ color: '#fbbf24' }}>⚠ Detection risk on ops +15%</div>
                          {eduTier >= 2 && (
                            <div style={{ color: '#f87171' }}>⚠ Coup warnings suppressed</div>
                          )}
                        </div>
                        <button
                          className="sc-axis-btn sc-axis-btn-defund"
                          style={{ width: '100%', fontSize: '0.72rem', marginTop: '0.3rem' }}
                          disabled={pw < 2.0 || !!loyalLoading}
                          onClick={() => handleLoyalAction('intel_chief', 'reverse')}
                        >
                          {loyalLoading === 'intel_reverse' ? 'Reversing...' : 'REVERSE — $2B · 3-day transition'}
                        </button>
                      </>
                    )}
                  </div>

                  {loyalFlash && (
                    <div style={{ fontSize: '0.72rem', marginTop: '0.3rem', textAlign: 'center',
                      color: loyalFlash.includes('Failed') ? '#ff6b6b' : '#50c878' }}>
                      {loyalFlash}
                    </div>
                  )}
                </div>
              )
            })()}

          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════
            DRAWER 2 — OPERATIONS
        ═══════════════════════════════════════════════════════════════════ */}
        {activeDrawer === 1 && (
          <div className="sc-drawer-content">
            <div className="sc-drawer-header">OPERATIONS</div>
            <div className="sc-drawer-subtitle">
              Strategic operations. Max 2 per turn: 1 legitimate + 1 shadow.
            </div>
            {/* 10C: Operations cap indicator */}
            <div style={{ display: 'flex', gap: '1rem', margin: '0.4rem 0 0.6rem', padding: '0.4rem 0.6rem', background: 'rgba(200,168,75,0.08)', borderRadius: '4px', fontSize: '0.72rem' }}>
              <span>
                LEGITIMATE: {[...Array(1)].map((_, i) => (
                  <span key={i} style={{ color: (gs?.ops_legitimate_this_turn || 0) > i ? '#c8a84b' : '#555' }}>●</span>
                ))} {(gs?.ops_legitimate_this_turn || 0) >= 1 ? '0 remaining' : '1 remaining'}
              </span>
              <span>
                SHADOW: {[...Array(1)].map((_, i) => (
                  <span key={i} style={{ color: (gs?.ops_shadow_this_turn || 0) > i ? '#c8a84b' : '#555' }}>●</span>
                ))} {(gs?.ops_shadow_this_turn || 0) >= 1 ? '0 remaining' : '1 remaining'}
              </span>
            </div>
            {/* Target NPC selector */}
            <div className="sc-ops-target">
              <span className="sc-ops-target-label">Target NPC:</span>
              {['usa', 'arabia', 'eu', 'dprg', 'russia', 'china'].map(npc => (
                <button
                  key={npc}
                  className={`sc-ops-target-btn ${selectedTarget === npc ? 'sc-ops-target-active' : ''}`}
                  onClick={() => setSelectedTarget(npc)}
                >
                  {npc.toUpperCase()}
                </button>
              ))}
            </div>
            {OPERATIONS.map(op => {
              // Session 6: Operations gated by Military or Intelligence level
              const locked = op.minMilitary ? militaryLevel < op.minMilitary
                           : op.minIntelligence ? intelligenceLevel < op.minIntelligence
                           : false
              const canAfford = op.budgetType === 'PERSONAL'
                ? (gs?.personal_wealth || 0) >= op.cost
                : (gs?.budget || 0) >= op.cost
              return (
                <div key={op.id} className={`sc-op-card ${locked ? 'sc-op-locked' : ''}`}>
                  <div className="sc-op-header">
                    <span className="sc-op-icon">{op.icon}</span>
                    <span className="sc-op-label">{op.label}</span>
                    {/* fixes_13 Fix 25: State/Personal budget type label */}
                    <span className={`sc-op-budget-type ${op.budgetType === 'STATE' ? 'sc-budget-state' : 'sc-budget-personal'}`}>
                      {op.budgetType}
                    </span>
                    <span className="sc-op-cost">${op.cost}B</span>
                  </div>
                  <div className="sc-op-effect">{op.effect}</div>
                  {op.needsTarget && (
                    <div className="sc-op-target-note">Target: {selectedTarget.toUpperCase()}</div>
                  )}
                  {locked ? (
                    <div className="sc-op-lock-msg">Requires {op.minMilitary ? `Military level ${op.minMilitary}` : `Intelligence level ${op.minIntelligence}`}</div>
                  ) : deployedThisTurn ? (
                    <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>
                      Deployed this turn
                    </button>
                  ) : (
                    <button
                      className={`sc-op-deploy-btn ${!canAfford ? 'sc-axis-btn-disabled' : ''}`}
                      onClick={() => canAfford && !loading && handleOperation(op.id)}
                      disabled={!canAfford || loading}
                    >
                      {canAfford ? `Deploy — $${op.cost}B ${op.budgetType === 'PERSONAL' ? 'personal' : ''}` : `Need $${op.cost}B ${op.budgetType === 'PERSONAL' ? 'personal' : 'budget'}`}
                    </button>
                  )}
                </div>
              )
            })}

            {/* 10C: MILITARY ACTIONS — gated by military_tier */}
            <div className="sc-drawer-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
              ⚔️ MILITARY ACTIONS
            </div>

            {/* Force Projection — Military Tier 3+ */}
            {(gs?.military_tier || 0) >= 3 ? (
              <div className="sc-op-card">
                <div className="sc-op-header">
                  <span className="sc-op-icon">💪</span>
                  <span className="sc-op-label">Force Projection</span>
                  <span className="sc-op-budget-type sc-budget-state">FREE</span>
                </div>
                <div className="sc-op-effect">Military threat: target NPC ceilings +25%, target -8 relations</div>
                <div className="sc-op-risk">⚠️ {gs?.modernization_tranche_3 ? '2' : '3'}-day cooldown</div>
                {gs?.force_projection_cooldown > 0 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>
                    Cooldown: {gs.force_projection_cooldown} day(s)
                  </button>
                ) : (gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                ) : (
                  <button className="sc-op-deploy-btn" onClick={() => !loading && handleOp10c('opsForceProjection', selectedTarget)} disabled={loading}>
                    Project Force vs {selectedTarget.toUpperCase()}
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked">
                <div className="sc-op-header"><span className="sc-op-icon">💪</span><span className="sc-op-label">Force Projection</span></div>
                <div className="sc-op-lock-msg">Requires Military Tier 3</div>
              </div>
            )}

            {/* Arms Export — Military Tier 2+ */}
            {(gs?.military_tier || 0) >= 2 ? (
              <div className="sc-op-card">
                <div className="sc-op-header">
                  <span className="sc-op-icon">📦</span>
                  <span className="sc-op-label">Arms Export</span>
                  <span className="sc-op-budget-type sc-budget-state">NATIONAL</span>
                </div>
                <div className="sc-op-effect">Export weapons for revenue and relations (diminishing returns)</div>
                <div className="sc-ops-target" style={{ margin: '0.3rem 0' }}>
                  <span className="sc-ops-target-label">Export to:</span>
                  {['usa', 'arabia', 'eu', 'dprg', 'russia', 'china'].map(npc => (
                    <button key={npc} className={`sc-ops-target-btn ${armsExportTarget === npc ? 'sc-ops-target-active' : ''}`} onClick={() => setArmsExportTarget(npc)}>
                      {npc.toUpperCase()}
                    </button>
                  ))}
                </div>
                {(gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                ) : (
                  <button className="sc-op-deploy-btn" onClick={() => !loading && handleOp10c('opsArmsExport', armsExportTarget)} disabled={loading}>
                    Export to {armsExportTarget.toUpperCase()}
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked">
                <div className="sc-op-header"><span className="sc-op-icon">📦</span><span className="sc-op-label">Arms Export</span></div>
                <div className="sc-op-lock-msg">Requires Military Tier 2</div>
              </div>
            )}

            {/* Modernization Tranche 1 — Tech 2+, Mil 3+ */}
            {!gs?.modernization_tranche_1 ? (
              <div className={`sc-op-card ${(gs?.tech_level || 0) < 2 || (gs?.military_tier || 0) < 3 ? 'sc-op-locked' : ''}`}>
                <div className="sc-op-header">
                  <span className="sc-op-icon">🔧</span>
                  <span className="sc-op-label">Modernization T1</span>
                  <span className="sc-op-budget-type sc-budget-state">NATIONAL</span>
                  <span className="sc-op-cost">$5B</span>
                </div>
                <div className="sc-op-effect">Permanent: military decay rate -20%</div>
                {(gs?.tech_level || 0) < 2 || (gs?.military_tier || 0) < 3 ? (
                  <div className="sc-op-lock-msg">Requires Tech 2.0+ and Military Tier 3+</div>
                ) : (gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                ) : (gs?.budget || 0) < 5 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $5B national</button>
                ) : (
                  <button className="sc-op-deploy-btn" onClick={() => !loading && handleOp10c('opsModernization', 1)} disabled={loading}>
                    Modernize — $5B national
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card" style={{ opacity: 0.6 }}>
                <div className="sc-op-header"><span className="sc-op-icon">🔧</span><span className="sc-op-label">Modernization T1</span></div>
                <div className="sc-op-effect">✅ Complete — military decay -20%</div>
              </div>
            )}

            {/* Modernization Tranche 2 — hidden until T1 complete */}
            {gs?.modernization_tranche_1 && !gs?.modernization_tranche_2 && (
              <div className={`sc-op-card ${(gs?.tech_level || 0) < 4 || (gs?.military_tier || 0) < 5 ? 'sc-op-locked' : ''}`}>
                <div className="sc-op-header">
                  <span className="sc-op-icon">🔧</span>
                  <span className="sc-op-label">Modernization T2</span>
                  <span className="sc-op-budget-type sc-budget-state">NATIONAL</span>
                  <span className="sc-op-cost">$8B</span>
                </div>
                <div className="sc-op-effect">Permanent: intercept quality +15%, detection risk -10%</div>
                {(gs?.tech_level || 0) < 4 || (gs?.military_tier || 0) < 5 ? (
                  <div className="sc-op-lock-msg">Requires Tech 4.0+ and Military Tier 5+</div>
                ) : (gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                ) : (gs?.budget || 0) < 8 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $8B national</button>
                ) : (
                  <button className="sc-op-deploy-btn" onClick={() => !loading && handleOp10c('opsModernization', 2)} disabled={loading}>
                    Modernize — $8B national
                  </button>
                )}
              </div>
            )}
            {gs?.modernization_tranche_2 && (
              <div className="sc-op-card" style={{ opacity: 0.6 }}>
                <div className="sc-op-header"><span className="sc-op-icon">🔧</span><span className="sc-op-label">Modernization T2</span></div>
                <div className="sc-op-effect">✅ Complete — intercept +15%, detection -10%</div>
              </div>
            )}

            {/* Modernization Tranche 3 — hidden until T2 complete */}
            {gs?.modernization_tranche_2 && !gs?.modernization_tranche_3 && (
              <div className={`sc-op-card ${(gs?.tech_level || 0) < 6 || (gs?.military_tier || 0) < 7 ? 'sc-op-locked' : ''}`}>
                <div className="sc-op-header">
                  <span className="sc-op-icon">🔧</span>
                  <span className="sc-op-label">Modernization T3</span>
                  <span className="sc-op-budget-type sc-budget-state">NATIONAL</span>
                  <span className="sc-op-cost">$12B</span>
                </div>
                <div className="sc-op-effect">Permanent: tier upgrade costs -20%, FP cooldown reduced</div>
                {(gs?.tech_level || 0) < 6 || (gs?.military_tier || 0) < 7 ? (
                  <div className="sc-op-lock-msg">Requires Tech 6.0+ and Military Tier 7+</div>
                ) : (gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                ) : (gs?.budget || 0) < 12 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $12B national</button>
                ) : (
                  <button className="sc-op-deploy-btn" onClick={() => !loading && handleOp10c('opsModernization', 3)} disabled={loading}>
                    Modernize — $12B national
                  </button>
                )}
              </div>
            )}
            {gs?.modernization_tranche_3 && (
              <div className="sc-op-card" style={{ opacity: 0.6 }}>
                <div className="sc-op-header"><span className="sc-op-icon">🔧</span><span className="sc-op-label">Modernization T3</span></div>
                <div className="sc-op-effect">✅ Complete — upgrade costs -20%, FP cooldown 2 days</div>
              </div>
            )}

            {/* 10C: INTELLIGENCE ACTIONS — gated by intelligence_tier */}
            <div className="sc-drawer-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
              🕵️ INTELLIGENCE ACTIONS
            </div>

            {/* Intel Sharing — Intel Tier 2+ */}
            {(() => {
              const intelTier = gs?.intelligence_tier || 0
              const agreements = gs?.intel_sharing_agreements || {}
              const agreementsList = Object.entries(agreements)
              return (
                <>
                  {agreementsList.length > 0 && (
                    <div className="sc-op-card" style={{ fontSize: '0.7rem', padding: '0.4rem' }}>
                      <div style={{ fontWeight: 700, marginBottom: '0.3rem' }}>ACTIVE AGREEMENTS</div>
                      {agreementsList.map(([npc, info]) => (
                        <div key={npc} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                          <span>{npc.toUpperCase()} — Level {info.level}</span>
                          <span>Day {info.day_started}</span>
                          <button className="sc-op-deploy-btn" style={{ fontSize: '0.6rem', padding: '0.1rem 0.3rem' }}
                            onClick={() => !loading && handleOp10c('opsIntelSharingEnd', npc, false)} disabled={loading}>End</button>
                        </div>
                      ))}
                    </div>
                  )}
                  {intelTier >= 2 ? (
                    <div className="sc-op-card">
                      <div className="sc-op-header"><span className="sc-op-icon">🤝</span><span className="sc-op-label">Intel Sharing</span><span className="sc-op-budget-type sc-budget-state">FREE</span></div>
                      <div className="sc-op-effect">Share intel: L1 +8, L2 +15, L3 +20 relations</div>
                      {(gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                        <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                      ) : (
                        <div style={{ display: 'flex', gap: '0.3rem' }}>
                          {[1, 2, 3].map(lvl => (
                            <button key={lvl} className="sc-op-deploy-btn" style={{ flex: 1, fontSize: '0.65rem' }}
                              onClick={() => !loading && handleOp10c('opsIntelSharing', selectedTarget, lvl)} disabled={loading}>
                              L{lvl} with {selectedTarget.toUpperCase()}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🤝</span><span className="sc-op-label">Intel Sharing</span></div><div className="sc-op-lock-msg">Requires Intel Tier 2</div></div>
                  )}
                </>
              )
            })()}

            {/* Crisis Intel Package — Intel Tier 2+ */}
            {(gs?.intelligence_tier || 0) >= 2 ? (
              <div className="sc-op-card">
                <div className="sc-op-header"><span className="sc-op-icon">📋</span><span className="sc-op-label">Crisis Intel Package</span><span className="sc-op-budget-type sc-budget-personal">$1.5B</span></div>
                <div className="sc-op-effect">Share crisis intelligence: +12 relations with NPC in crisis</div>
                {(gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                ) : (
                  <div style={{ display: 'flex', gap: '0.3rem' }}>
                    <button className="sc-op-deploy-btn" style={{ flex: 1 }} onClick={() => !loading && handleOp10c('opsCrisisIntel', selectedTarget, 'personal')} disabled={loading}>
                      Personal — {selectedTarget.toUpperCase()}
                    </button>
                    <button className="sc-op-deploy-btn" style={{ flex: 1 }} onClick={() => !loading && handleOp10c('opsCrisisIntel', selectedTarget, 'national')} disabled={loading}>
                      National — {selectedTarget.toUpperCase()}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">📋</span><span className="sc-op-label">Crisis Intel Package</span></div><div className="sc-op-lock-msg">Requires Intel Tier 2</div></div>
            )}

            {/* Targeted Intercept — Intel Tier 3+ */}
            {(gs?.intelligence_tier || 0) >= 3 ? (
              <div className="sc-op-card">
                <div className="sc-op-header"><span className="sc-op-icon">📡</span><span className="sc-op-label">Targeted Intercept</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$2B</span></div>
                <div className="sc-op-effect">Intercept NPC communications for actionable intelligence</div>
                {(gs?.targeted_intercept_cooldown || 0) > 0 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Cooldown: {gs.targeted_intercept_cooldown} day(s)</button>
                ) : (gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                ) : (gs?.personal_wealth || 0) < 2 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $2B personal</button>
                ) : (
                  <button className="sc-op-deploy-btn" onClick={() => !loading && handleOp10c('opsTargetedIntercept', selectedTarget)} disabled={loading}>
                    Intercept {selectedTarget.toUpperCase()} — $2B personal
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">📡</span><span className="sc-op-label">Targeted Intercept</span></div><div className="sc-op-lock-msg">Requires Intel Tier 3</div></div>
            )}

            {/* Kompromat Collection — Intel Tier 3+ */}
            {(() => {
              const intelTier = gs?.intelligence_tier || 0
              const collections = gs?.kompromat_collection_active || {}
              const holdings = gs?.kompromat_holdings || {}
              return (
                <>
                  {/* Show active collections */}
                  {Object.entries(collections).map(([npc, info]) => (
                    <div key={`komp-collect-${npc}`} className="sc-op-card" style={{ borderLeft: '3px solid #c8a84b' }}>
                      <div className="sc-op-header"><span className="sc-op-icon">🕵️</span><span className="sc-op-label">COLLECTION IN PROGRESS</span></div>
                      <div className="sc-op-effect">{npc.toUpperCase()} — Day {(gs?.current_day || 0) - (info.day_started || 0)} of 7</div>
                    </div>
                  ))}
                  {/* Show held kompromat */}
                  {Object.entries(holdings).filter(([, h]) => h.active).map(([npc, h]) => (
                    <div key={`komp-hold-${npc}`} className="sc-op-card sc-op-black" style={{ borderLeft: '3px solid #c8a84b' }}>
                      <div className="sc-op-header"><span className="sc-op-icon">📁</span><span className="sc-op-label">KOMPROMAT: {npc.toUpperCase()}</span></div>
                      <div className="sc-op-effect">ACTIVE — {h.uses_remaining} uses remaining</div>
                      <div style={{ display: 'flex', gap: '0.3rem', marginTop: '0.3rem' }}>
                        <button className="sc-op-deploy-btn" style={{ flex: 1, fontSize: '0.65rem' }} onClick={() => !loading && handleOp10c('opsKompUse', npc, 'suppress')} disabled={loading}>Suppress</button>
                        <button className="sc-op-deploy-btn" style={{ flex: 1, fontSize: '0.65rem' }} onClick={() => !loading && handleOp10c('opsKompUse', npc, 'concession')} disabled={loading}>Concession</button>
                        <button className="sc-op-deploy-btn sc-op-deploy-black" style={{ flex: 1, fontSize: '0.65rem' }} onClick={() => !loading && handleOp10c('opsKompUse', npc, 'burn')} disabled={loading}>BURN</button>
                      </div>
                    </div>
                  ))}
                  {intelTier >= 3 ? (
                    <div className="sc-op-card">
                      <div className="sc-op-header"><span className="sc-op-icon">🕵️</span><span className="sc-op-label">Kompromat Collection</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$1.5B</span></div>
                      <div className="sc-op-effect">7-day covert collection (15% daily detection risk)</div>
                      {(gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                        <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                      ) : (gs?.personal_wealth || 0) < 1.5 ? (
                        <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $1.5B personal</button>
                      ) : (
                        <button className="sc-op-deploy-btn" onClick={() => !loading && handleOp10c('opsKompStart', selectedTarget)} disabled={loading}>
                          Collect on {selectedTarget.toUpperCase()} — $1.5B personal
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🕵️</span><span className="sc-op-label">Kompromat Collection</span></div><div className="sc-op-lock-msg">Requires Intel Tier 3</div></div>
                  )}
                </>
              )
            })()}

            {/* Loyalty Assessment — Intel 2+ OR Surveillance 3+ */}
            {((gs?.intelligence_tier || 0) >= 2 || (gs?.domestic_surveillance_tier || 0) >= 3) ? (
              <div className="sc-op-card">
                <div className="sc-op-header"><span className="sc-op-icon">🔍</span><span className="sc-op-label">Loyalty Assessment</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$1B</span></div>
                <div className="sc-op-effect">Assess advisor's true loyalty (15% detection risk)</div>
                {(gs?.ops_shadow_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Shadow op used this turn</button>
                ) : (gs?.personal_wealth || 0) < 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $1B personal</button>
                ) : (
                  <div style={{ display: 'flex', gap: '0.2rem', flexWrap: 'wrap' }}>
                    {Object.keys(gs?.advisors || {}).map(advId => (
                      <button key={advId} className="sc-op-deploy-btn" style={{ fontSize: '0.6rem', padding: '0.2rem 0.4rem' }}
                        onClick={() => !loading && handleOp10c('opsLoyaltyAssessment', advId)} disabled={loading}>
                        {advId}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🔍</span><span className="sc-op-label">Loyalty Assessment</span></div><div className="sc-op-lock-msg">Requires Intel Tier 2 or Surveillance Tier 3</div></div>
            )}

            {/* Loyalty Enforcement — Surveillance Tier 5+ */}
            {(gs?.domestic_surveillance_tier || 0) >= 5 ? (
              <div className="sc-op-card sc-op-black">
                <div className="sc-op-header"><span className="sc-op-icon">🔒</span><span className="sc-op-label">Loyalty Enforcement</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$2B</span></div>
                <div className="sc-op-effect">Coerce advisor loyalty +15 (25% detection — advisor dismissed if caught)</div>
                {(gs?.ops_shadow_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Shadow op used this turn</button>
                ) : (gs?.personal_wealth || 0) < 2 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $2B personal</button>
                ) : (
                  <div style={{ display: 'flex', gap: '0.2rem', flexWrap: 'wrap' }}>
                    {Object.keys(gs?.advisors || {}).map(advId => (
                      <button key={advId} className="sc-op-deploy-btn sc-op-deploy-black" style={{ fontSize: '0.6rem', padding: '0.2rem 0.4rem' }}
                        onClick={() => !loading && handleOp10c('opsLoyaltyEnforcement', advId)} disabled={loading}>
                        {advId}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🔒</span><span className="sc-op-label">Loyalty Enforcement</span></div><div className="sc-op-lock-msg">Requires Surveillance Tier 5</div></div>
            )}

            {/* Counter-Intel Sweep — Intel Tier 2+ */}
            {(gs?.intelligence_tier || 0) >= 2 ? (
              <div className="sc-op-card">
                <div className="sc-op-header"><span className="sc-op-icon">🛡️</span><span className="sc-op-label">Counter-Intel Sweep</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$2B</span></div>
                <div className="sc-op-effect">Detection heat -15, reveal NPC intel ops</div>
                {(gs?.counter_intel_cooldown || 0) > 0 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Cooldown: {gs.counter_intel_cooldown} day(s)</button>
                ) : (gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                ) : (gs?.personal_wealth || 0) < 2 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $2B personal</button>
                ) : (
                  <button className="sc-op-deploy-btn" onClick={() => !loading && handleOp10c('opsCounterIntel')} disabled={loading}>
                    Sweep — $2B personal
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🛡️</span><span className="sc-op-label">Counter-Intel Sweep</span></div><div className="sc-op-lock-msg">Requires Intel Tier 2</div></div>
            )}

            {/* 10C Section 8: Coalition Intelligence Network — stub card */}
            {(() => {
              const agreements = gs?.intel_sharing_agreements || {}
              const l2Count = Object.values(agreements).filter(a => (a.level || 0) >= 2).length
              return (
                <div className="sc-op-card sc-op-locked" style={{ marginTop: '0.5rem', borderLeft: '3px solid rgba(200,168,75,0.3)' }}>
                  <div className="sc-op-header">
                    <span className="sc-op-icon">🌐</span>
                    <span className="sc-op-label">Coalition Intelligence Network</span>
                  </div>
                  <div className="sc-op-effect">
                    Available when: Intel Tier 4+ with Level 2+ sharing agreements with 3 or more partners
                  </div>
                  <div className="sc-op-effect" style={{ fontWeight: 600 }}>
                    Currently: {l2Count}/3 partners at Level 2+
                    {(gs?.intelligence_tier || 0) < 4 && ` (Intel Tier: ${gs?.intelligence_tier || 0}/4)`}
                  </div>
                  <div className="sc-op-lock-msg">COMING SOON — Coalition operations in development</div>
                </div>
              )
            })()}

            {/* 10C: DIPLOMATIC ACTIONS — gated by diplomatic_tier */}
            <div className="sc-drawer-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
              🤝 DIPLOMATIC ACTIONS
            </div>

            {/* Trade Mission — Diplomatic Tier 2+ */}
            {(gs?.diplomatic_tier || 0) >= 2 ? (
              <div className="sc-op-card">
                <div className="sc-op-header"><span className="sc-op-icon">🚢</span><span className="sc-op-label">Trade Mission</span><span className="sc-op-budget-type sc-budget-state">NATIONAL</span><span className="sc-op-cost">$1.5B</span></div>
                <div className="sc-op-effect">+10 relations with target NPC (3-day cooldown)</div>
                {(gs?.trade_mission_cooldown || 0) > 0 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Cooldown: {gs.trade_mission_cooldown} day(s)</button>
                ) : (gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                ) : (gs?.budget || 0) < 1.5 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $1.5B national</button>
                ) : (
                  <button className="sc-op-deploy-btn" onClick={() => !loading && handleOp10c('opsTradeMission', selectedTarget)} disabled={loading}>
                    Trade Mission to {selectedTarget.toUpperCase()} — $1.5B
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🚢</span><span className="sc-op-label">Trade Mission</span></div><div className="sc-op-lock-msg">Requires Diplomatic Tier 2</div></div>
            )}

            {/* Diplomatic Pressure — Diplomatic Tier 2+ */}
            {(gs?.diplomatic_tier || 0) >= 2 ? (
              <div className="sc-op-card">
                <div className="sc-op-header"><span className="sc-op-icon">🕵️</span><span className="sc-op-label">Diplomatic Pressure</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$1.5B</span></div>
                <div className="sc-op-effect">+5 relations with target NPC</div>
                {(gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                ) : (gs?.personal_wealth || 0) < 1.5 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $1.5B personal</button>
                ) : (
                  <button className="sc-op-deploy-btn" onClick={() => !loading && handleOp10c('opsDiploPressure', selectedTarget)} disabled={loading}>
                    Pressure {selectedTarget.toUpperCase()} — $1.5B personal
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🕵️</span><span className="sc-op-label">Diplomatic Pressure</span></div><div className="sc-op-lock-msg">Requires Diplomatic Tier 2</div></div>
            )}

            {/* Opposition Funding — Diplomatic Tier 3+ */}
            {(gs?.diplomatic_tier || 0) >= 3 ? (
              <div className="sc-op-card">
                <div className="sc-op-header"><span className="sc-op-icon">💰</span><span className="sc-op-label">Opposition Funding</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$3B</span></div>
                <div className="sc-op-effect">Destabilize target NPC domestically</div>
                <div className="sc-op-risk">⚠️ 35% detection — hostile act if caught</div>
                {(gs?.ops_legitimate_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Legitimate op used this turn</button>
                ) : (gs?.personal_wealth || 0) < 3 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $3B personal</button>
                ) : (
                  <button className="sc-op-deploy-btn" onClick={() => !loading && handleOp10c('opsOppositionFunding', selectedTarget)} disabled={loading}>
                    Fund Opposition in {selectedTarget.toUpperCase()} — $3B personal
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">💰</span><span className="sc-op-label">Opposition Funding</span></div><div className="sc-op-lock-msg">Requires Diplomatic Tier 3</div></div>
            )}

            {/* Session 6: Media Actions — gated by Media axis level */}
            {(axes.media || 0) >= 3 && (
              <>
                <div className="sc-drawer-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
                  📺 MEDIA ACTIONS
                </div>
                {/* L3: Suppress Scandal */}
                <div className="sc-op-card">
                  <div className="sc-op-header"><span className="sc-op-icon">🤫</span><span className="sc-op-label">Suppress Scandal</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$1B</span></div>
                  <div className="sc-op-effect">Immunity from next corruption scandal this turn</div>
                  {gs?.scandal_suppressed_this_turn ? (
                    <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Already suppressed this turn</button>
                  ) : (
                    <button className={`sc-op-deploy-btn ${personalWealth < 1 ? 'sc-axis-btn-disabled' : ''}`} onClick={() => personalWealth >= 1 && !loading && handleMediaAction('suppress_scandal')} disabled={personalWealth < 1 || loading}>
                      {personalWealth >= 1 ? 'Suppress — $1B personal' : 'Need $1B personal'}
                    </button>
                  )}
                </div>
                {/* L6: Narrative Campaign */}
                {(axes.media || 0) >= 6 ? (
                  <div className="sc-op-card">
                    <div className="sc-op-header"><span className="sc-op-icon">📣</span><span className="sc-op-label">Narrative Campaign</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$2B</span></div>
                    <div className="sc-op-effect">+8% approval, {selectedTarget.toUpperCase()} -5 relations</div>
                    <button className={`sc-op-deploy-btn ${personalWealth < 2 ? 'sc-axis-btn-disabled' : ''}`} onClick={() => personalWealth >= 2 && !loading && handleMediaAction('narrative_campaign')} disabled={personalWealth < 2 || loading}>
                      {personalWealth >= 2 ? `Campaign vs ${selectedTarget.toUpperCase()} — $2B personal` : 'Need $2B personal'}
                    </button>
                  </div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">📣</span><span className="sc-op-label">Narrative Campaign</span></div><div className="sc-op-lock-msg">Requires Media level 6</div></div>
                )}
                {/* L9: Information Blackout */}
                {(axes.media || 0) >= 9 ? (
                  <div className="sc-op-card">
                    <div className="sc-op-header"><span className="sc-op-icon">🔇</span><span className="sc-op-label">Information Blackout</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$4B</span></div>
                    <div className="sc-op-effect">World events affecting approval/stability muted 2 turns</div>
                    {(gs?.info_blackout_turns || 0) > 0 ? (
                      <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Active: {gs.info_blackout_turns} turn(s)</button>
                    ) : (
                      <button className={`sc-op-deploy-btn ${personalWealth < 4 ? 'sc-axis-btn-disabled' : ''}`} onClick={() => personalWealth >= 4 && !loading && handleMediaAction('info_blackout')} disabled={personalWealth < 4 || loading}>
                        {personalWealth >= 4 ? 'Blackout — $4B personal' : 'Need $4B personal'}
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🔇</span><span className="sc-op-label">Information Blackout</span></div><div className="sc-op-lock-msg">Requires Media level 9</div></div>
                )}
              </>
            )}

            {/* Session 6: Judicial Actions — gated by Judicial axis level */}
            {(axes.judicial || 0) >= 3 && (
              <>
                <div className="sc-drawer-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
                  ⚖️ JUDICIAL ACTIONS
                </div>
                {/* L3: Drop Investigation */}
                <div className="sc-op-card">
                  <div className="sc-op-header"><span className="sc-op-icon">📋</span><span className="sc-op-label">Drop Investigation</span><span className="sc-op-budget-type sc-budget-state">FREE</span></div>
                  <div className="sc-op-effect">Immunity from next corruption scandal this turn</div>
                  {gs?.drop_investigation_this_turn ? (
                    <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Already dropped this turn</button>
                  ) : (
                    <button className="sc-op-deploy-btn" onClick={() => !loading && handleJudicialAction('drop_investigation')} disabled={loading}>Drop Investigation (free, once/turn)</button>
                  )}
                </div>
                {/* L6: Lawfare */}
                {(axes.judicial || 0) >= 6 ? (
                  <div className="sc-op-card">
                    <div className="sc-op-header"><span className="sc-op-icon">⚖️</span><span className="sc-op-label">Lawfare</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$3B</span></div>
                    <div className="sc-op-effect">Suspend {selectedTarget.toUpperCase()} pressure events 2 turns</div>
                    {(gs?.lawfare_turns || 0) > 0 ? (
                      <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Active vs {(gs?.lawfare_target || '').toUpperCase()}: {gs.lawfare_turns} turn(s)</button>
                    ) : (
                      <button className={`sc-op-deploy-btn ${personalWealth < 3 ? 'sc-axis-btn-disabled' : ''}`} onClick={() => personalWealth >= 3 && !loading && handleJudicialAction('lawfare')} disabled={personalWealth < 3 || loading}>
                        {personalWealth >= 3 ? `Lawfare vs ${selectedTarget.toUpperCase()} — $3B personal` : 'Need $3B personal'}
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">⚖️</span><span className="sc-op-label">Lawfare</span></div><div className="sc-op-lock-msg">Requires Judicial level 6</div></div>
                )}
                {/* L9: Asset Seizure */}
                {(axes.judicial || 0) >= 9 ? (
                  <div className="sc-op-card">
                    <div className="sc-op-header"><span className="sc-op-icon">🏦</span><span className="sc-op-label">Asset Seizure</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$5B</span></div>
                    <div className="sc-op-effect">+$3B national, +5% stability, -8% approval</div>
                    <button className={`sc-op-deploy-btn ${personalWealth < 5 ? 'sc-axis-btn-disabled' : ''}`} onClick={() => personalWealth >= 5 && !loading && handleJudicialAction('asset_seizure')} disabled={personalWealth < 5 || loading}>
                      {personalWealth >= 5 ? 'Seize Assets — $5B personal' : 'Need $5B personal'}
                    </button>
                  </div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🏦</span><span className="sc-op-label">Asset Seizure</span></div><div className="sc-op-lock-msg">Requires Judicial level 9</div></div>
                )}
              </>
            )}

            {/* Session 6: Political Actions — gated by Political axis level */}
            {(axes.political || 0) >= 3 && (
              <>
                <div className="sc-drawer-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
                  🏛️ POLITICAL ACTIONS
                </div>
                {/* L3: Party Consolidation */}
                <div className="sc-op-card">
                  <div className="sc-op-header"><span className="sc-op-icon">🤝</span><span className="sc-op-label">Party Consolidation</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$1B</span></div>
                  <div className="sc-op-effect">Tax approval drain reduced 25% for 3 turns</div>
                  {(gs?.party_consolidation_turns || 0) > 0 ? (
                    <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Active: {gs.party_consolidation_turns} turn(s)</button>
                  ) : (
                    <button className={`sc-op-deploy-btn ${personalWealth < 1 ? 'sc-axis-btn-disabled' : ''}`} onClick={() => personalWealth >= 1 && !loading && handlePoliticalAction('party_consolidation')} disabled={personalWealth < 1 || loading}>
                      {personalWealth >= 1 ? 'Consolidate — $1B personal' : 'Need $1B personal'}
                    </button>
                  )}
                </div>
                {/* L6: Pack the Cabinet */}
                {(axes.political || 0) >= 6 ? (
                  <div className={`sc-op-card ${gs?.fourth_advisor_slot ? 'sc-op-locked' : ''}`}>
                    <div className="sc-op-header"><span className="sc-op-icon">👥</span><span className="sc-op-label">Pack the Cabinet</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$3B</span></div>
                    <div className="sc-op-effect">4th advisor slot permanently unlocked</div>
                    {gs?.fourth_advisor_slot ? (
                      <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Already unlocked</button>
                    ) : (
                      <button className={`sc-op-deploy-btn ${personalWealth < 3 ? 'sc-axis-btn-disabled' : ''}`} onClick={() => personalWealth >= 3 && !loading && handlePoliticalAction('pack_cabinet')} disabled={personalWealth < 3 || loading}>
                        {personalWealth >= 3 ? 'Pack Cabinet — $3B personal' : 'Need $3B personal'}
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">👥</span><span className="sc-op-label">Pack the Cabinet</span></div><div className="sc-op-lock-msg">Requires Political level 6</div></div>
                )}
                {/* L9: Constitutional Revision */}
                {(axes.political || 0) >= 9 ? (
                  <div className={`sc-op-card ${gs?.constitutional_revision_active ? 'sc-op-locked' : ''}`}>
                    <div className="sc-op-header"><span className="sc-op-icon">📜</span><span className="sc-op-label">Constitutional Revision</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$6B</span></div>
                    <div className="sc-op-effect">Remove electoral mechanics, regime hard right, EU -15</div>
                    <div className="sc-op-risk">⚠️ Reversible: Marsha may demand reversal as deal condition</div>
                    {gs?.constitutional_revision_active ? (
                      <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Already enacted</button>
                    ) : (
                      <button className={`sc-op-deploy-btn ${personalWealth < 6 ? 'sc-axis-btn-disabled' : ''}`} onClick={() => personalWealth >= 6 && !loading && handlePoliticalAction('constitutional_revision')} disabled={personalWealth < 6 || loading}>
                        {personalWealth >= 6 ? 'Revise Constitution — $6B personal' : 'Need $6B personal'}
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">📜</span><span className="sc-op-label">Constitutional Revision</span></div><div className="sc-op-lock-msg">Requires Political level 9</div></div>
                )}
              </>
            )}

            {/* Session 6: Extraction Actions — gated by Extraction axis level */}
            {(axes.extraction || 0) >= 6 && (
              <>
                <div className="sc-drawer-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
                  💰 EXTRACTION ACTIONS
                </div>
                {/* L6: Offshore Transfer */}
                <div className="sc-op-card">
                  <div className="sc-op-header"><span className="sc-op-icon">🏝️</span><span className="sc-op-label">Offshore Transfer</span><span className="sc-op-budget-type sc-budget-state">NATIONAL</span></div>
                  <div className="sc-op-effect">{"Move up to $10B national -> personal (no skim heat, EU -3)"}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', margin: '0.3rem 0' }}>
                    <span style={{ fontSize: '0.7rem' }}>Amount:</span>
                    <input type="range" min={1} max={Math.min(10, Math.floor(gs?.budget || 0))} step={1} value={offshoreAmount}
                      onChange={e => setOffshoreAmount(parseInt(e.target.value))} style={{ flex: 1 }} disabled={loading} />
                    <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>${offshoreAmount}B</span>
                  </div>
                  {gs?.offshore_transfer_this_turn ? (
                    <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Already transferred this turn</button>
                  ) : (gs?.budget || 0) < 1 ? (
                    <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need national budget</button>
                  ) : (
                    <button className="sc-op-deploy-btn" onClick={() => !loading && handleExtractionAction('offshore_transfer', offshoreAmount)} disabled={loading}>
                      Transfer ${offshoreAmount}B offshore
                    </button>
                  )}
                </div>
                {/* L7: Private Security Force */}
                {(axes.extraction || 0) >= 7 ? (
                  <div className={`sc-op-card ${gs?.private_security_force ? 'sc-op-locked' : ''}`}>
                    <div className="sc-op-header"><span className="sc-op-icon">🛡️</span><span className="sc-op-label">Private Security Force</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$5B</span></div>
                    <div className="sc-op-effect">15 militia strength, no decay, coup immunity</div>
                    <div className="sc-op-risk">⚠️ If detected (heat 80+): Bill/Marsha demand disbandment</div>
                    {gs?.private_security_force ? (
                      <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Active — strength: {gs?.private_security_strength || 15}</button>
                    ) : (
                      <button className={`sc-op-deploy-btn ${personalWealth < 5 ? 'sc-axis-btn-disabled' : ''}`} onClick={() => personalWealth >= 5 && !loading && handleExtractionAction('private_security_force')} disabled={personalWealth < 5 || loading}>
                        {personalWealth >= 5 ? 'Purchase — $5B personal (one-time)' : 'Need $5B personal'}
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🛡️</span><span className="sc-op-label">Private Security Force</span></div><div className="sc-op-lock-msg">Requires Extraction level 7</div></div>
                )}
                {/* L9: Sovereign Wealth Capture — passive */}
                {(axes.extraction || 0) >= 9 ? (
                  <div className="sc-op-card"><div className="sc-op-header"><span className="sc-op-icon">🏛️</span><span className="sc-op-label">Sovereign Wealth Capture</span><span className="sc-op-budget-type sc-budget-state">PASSIVE</span></div>
                    <div className="sc-op-effect">15% of GDP auto-diverts to personal wealth each turn — active</div></div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🏛️</span><span className="sc-op-label">Sovereign Wealth Capture</span></div><div className="sc-op-lock-msg">Requires Extraction level 9</div></div>
                )}
              </>
            )}

            {/* Session 6: Resource Development Actions — gated by Resource Dev axis level */}
            {(axes.resource_dev || 0) >= 3 && (
              <>
                <div className="sc-drawer-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
                  🏗️ RESOURCE DEVELOPMENT ACTIONS
                </div>
                {/* L3: Export Contract */}
                <div className={`sc-op-card ${gs?.export_contract_used ? 'sc-op-locked' : ''}`}>
                  <div className="sc-op-header"><span className="sc-op-icon">📄</span><span className="sc-op-label">Export Contract</span><span className="sc-op-budget-type sc-budget-state">FREE</span></div>
                  <div className="sc-op-effect">One-time +$8B national budget, no NPC penalties</div>
                  {gs?.export_contract_used ? (
                    <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Already used</button>
                  ) : (
                    <button className="sc-op-deploy-btn" onClick={() => !loading && handleResourceDevAction('export_contract')} disabled={loading}>Sign Export Contract (+$8B)</button>
                  )}
                </div>
                {/* L5: GDP Credibility — passive milestone */}
                {(axes.resource_dev || 0) >= 5 ? (
                  <div className="sc-op-card"><div className="sc-op-header"><span className="sc-op-icon">📈</span><span className="sc-op-label">GDP Credibility</span><span className="sc-op-budget-type sc-budget-state">PASSIVE</span></div>
                    <div className="sc-op-effect">NPC negotiation ceilings +20% permanently — active</div></div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">📈</span><span className="sc-op-label">GDP Credibility</span></div><div className="sc-op-lock-msg">Requires Resource Dev level 5</div></div>
                )}
                {/* L6: Sovereign Collateral Loan */}
                {(axes.resource_dev || 0) >= 6 ? (
                  <div className={`sc-op-card ${gs?.sovereign_collateral_used ? 'sc-op-locked' : ''}`}>
                    <div className="sc-op-header"><span className="sc-op-icon">🏦</span><span className="sc-op-label">Sovereign Collateral Loan</span><span className="sc-op-budget-type sc-budget-state">NATIONAL</span></div>
                    <div className="sc-op-effect">+$10B national, 15% interest (~$3.83B/turn x 3), zero NPC penalties</div>
                    {gs?.sovereign_collateral_used ? (
                      <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>
                        {(gs?.sovereign_collateral_turns || 0) > 0 ? `Repaying: ${gs.sovereign_collateral_turns} turn(s) left` : 'Already used this game'}
                      </button>
                    ) : (
                      <button className="sc-op-deploy-btn" onClick={() => !loading && handleResourceDevAction('sovereign_collateral_loan')} disabled={loading}>Issue Loan (+$10B, once per game)</button>
                    )}
                  </div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🏦</span><span className="sc-op-label">Sovereign Collateral Loan</span></div><div className="sc-op-lock-msg">Requires Resource Dev level 6</div></div>
                )}
                {/* L8: Strategic Resource Partner */}
                {(axes.resource_dev || 0) >= 8 ? (
                  <div className={`sc-op-card ${gs?.strategic_resource_partner ? 'sc-op-locked' : ''}`}>
                    <div className="sc-op-header"><span className="sc-op-icon">🤝</span><span className="sc-op-label">Strategic Resource Partner</span><span className="sc-op-budget-type sc-budget-state">FREE</span></div>
                    <div className="sc-op-effect">Choose one NPC: their ceiling +50% permanently, warmer tone</div>
                    {gs?.strategic_resource_partner ? (
                      <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Partnered with {gs.strategic_resource_partner.toUpperCase()}</button>
                    ) : (
                      <button className="sc-op-deploy-btn" onClick={() => !loading && handleResourceDevAction('strategic_resource_partner')} disabled={loading}>
                        Partner with {selectedTarget.toUpperCase()} (permanent)
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🤝</span><span className="sc-op-label">Strategic Resource Partner</span></div><div className="sc-op-lock-msg">Requires Resource Dev level 8</div></div>
                )}
                {/* L9: Resource Independence — passive milestone */}
                {(axes.resource_dev || 0) >= 9 ? (
                  <div className="sc-op-card"><div className="sc-op-header"><span className="sc-op-icon">⛽</span><span className="sc-op-label">Resource Independence</span><span className="sc-op-budget-type sc-budget-state">PASSIVE</span></div>
                    <div className="sc-op-effect">Oil imports eliminated permanently, saves $3-5B/turn — active</div></div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">⛽</span><span className="sc-op-label">Resource Independence</span></div><div className="sc-op-lock-msg">Requires Resource Dev level 9</div></div>
                )}
                {/* L10: Better Bond Terms — passive */}
                {(axes.resource_dev || 0) >= 10 ? (
                  <div className="sc-op-card"><div className="sc-op-header"><span className="sc-op-icon">📉</span><span className="sc-op-label">Better Bond Terms</span><span className="sc-op-budget-type sc-budget-state">PASSIVE</span></div>
                    <div className="sc-op-effect">Reduced bond interest rates — active</div></div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">📉</span><span className="sc-op-label">Better Bond Terms</span></div><div className="sc-op-lock-msg">Requires Resource Dev level 10</div></div>
                )}
              </>
            )}

            {/* 10C: SHADOW OPERATIONS — gated by various shadow axis tiers */}
            <div className="sc-drawer-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
              🖤 SHADOW OPERATIONS
            </div>

            {/* Political Sabotage — Surveillance Tier 3+ */}
            {(gs?.domestic_surveillance_tier || 0) >= 3 ? (
              <div className="sc-op-card sc-op-black">
                <div className="sc-op-header"><span className="sc-op-icon">🖤</span><span className="sc-op-label">Political Sabotage</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$3B</span></div>
                <div className="sc-op-effect">Suspend target pressure 1 turn, cross-NPC penalty -50%</div>
                <div className="sc-op-risk">⚠️ 25% detection — target -10 relations</div>
                {(gs?.ops_shadow_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Shadow op used this turn</button>
                ) : (gs?.personal_wealth || 0) < 3 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $3B personal</button>
                ) : (
                  <button className="sc-op-deploy-btn sc-op-deploy-black" onClick={() => !loading && handleOp10c('opsPoliticalSabotage', selectedTarget)} disabled={loading}>
                    Sabotage {selectedTarget.toUpperCase()} — $3B
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🖤</span><span className="sc-op-label">Political Sabotage</span></div><div className="sc-op-lock-msg">Requires Surveillance Tier 3</div></div>
            )}

            {/* Reputation Laundering — Extraction Tier 3+ */}
            {(gs?.extraction_tier || 0) >= 3 ? (
              <div className="sc-op-card sc-op-black">
                <div className="sc-op-header"><span className="sc-op-icon">🖤</span><span className="sc-op-label">Reputation Laundering</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$3B</span></div>
                <div className="sc-op-effect">Detection heat -15 (no detection risk)</div>
                {(gs?.ops_shadow_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Shadow op used this turn</button>
                ) : (gs?.personal_wealth || 0) < 3 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $3B personal</button>
                ) : (
                  <button className="sc-op-deploy-btn sc-op-deploy-black" onClick={() => !loading && handleOp10c('opsRepLaundering')} disabled={loading}>
                    Launder — $3B (heat: {gs?.detection_heat || 0}%)
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🖤</span><span className="sc-op-label">Reputation Laundering</span></div><div className="sc-op-lock-msg">Requires Extraction Tier 3</div></div>
            )}

            {/* Fabricate Crisis — Surveillance Tier 4+ */}
            {(gs?.domestic_surveillance_tier || 0) >= 4 ? (
              <div className="sc-op-card sc-op-black">
                <div className="sc-op-header"><span className="sc-op-icon">🖤</span><span className="sc-op-label">Fabricate Crisis</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$4B</span></div>
                <div className="sc-op-effect">Suspend target pressure 2 turns</div>
                <div className="sc-op-risk">⚠️ 35% detection — target -15 relations</div>
                {(gs?.ops_shadow_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Shadow op used this turn</button>
                ) : (gs?.personal_wealth || 0) < 4 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $4B personal</button>
                ) : (
                  <button className="sc-op-deploy-btn sc-op-deploy-black" onClick={() => !loading && handleOp10c('opsFabricateCrisis', selectedTarget)} disabled={loading}>
                    Fabricate vs {selectedTarget.toUpperCase()} — $4B
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🖤</span><span className="sc-op-label">Fabricate Crisis</span></div><div className="sc-op-lock-msg">Requires Surveillance Tier 4</div></div>
            )}

            {/* Blackmail Operation — Intel Tier 3+ */}
            {(gs?.intelligence_tier || 0) >= 3 ? (
              <div className="sc-op-card sc-op-black">
                <div className="sc-op-header"><span className="sc-op-icon">🖤</span><span className="sc-op-label">Blackmail Operation</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$5B</span></div>
                <div className="sc-op-effect">Extract one-time concession from target</div>
                <div className="sc-op-risk">⚠️ 40% detection — target -5 permanent</div>
                {(gs?.ops_shadow_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Shadow op used this turn</button>
                ) : (gs?.personal_wealth || 0) < 5 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $5B personal</button>
                ) : (
                  <button className="sc-op-deploy-btn sc-op-deploy-black" onClick={() => !loading && handleOp10c('opsBlackmail', selectedTarget)} disabled={loading}>
                    Blackmail {selectedTarget.toUpperCase()} — $5B
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🖤</span><span className="sc-op-label">Blackmail Operation</span></div><div className="sc-op-lock-msg">Requires Intel Tier 3</div></div>
            )}

            {/* False Flag — Surveillance Tier 5+ */}
            {(gs?.domestic_surveillance_tier || 0) >= 5 ? (
              <div className="sc-op-card sc-op-black">
                <div className="sc-op-header"><span className="sc-op-icon">🖤</span><span className="sc-op-label">False Flag</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$6B</span></div>
                <div className="sc-op-effect">Damage bilateral relations between two NPCs (-10)</div>
                <div className="sc-op-risk">⚠️ 50% detection — both NPCs -20 relations</div>
                {(gs?.ops_shadow_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Shadow op used this turn</button>
                ) : (gs?.personal_wealth || 0) < 6 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $6B personal</button>
                ) : (
                  <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                    {['usa', 'arabia', 'eu', 'dprg', 'russia', 'china'].filter(n => n !== selectedTarget).map(blameNpc => (
                      <button key={blameNpc} className="sc-op-deploy-btn sc-op-deploy-black" style={{ fontSize: '0.6rem', flex: '1 1 30%' }}
                        onClick={() => !loading && handleOp10c('opsFalseFlag', selectedTarget, blameNpc)} disabled={loading}>
                        {selectedTarget.toUpperCase()} blame {blameNpc.toUpperCase()}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🖤</span><span className="sc-op-label">False Flag</span></div><div className="sc-op-lock-msg">Requires Surveillance Tier 5</div></div>
            )}

            {/* Journalist Elimination — Media 7+ AND Judicial 5+ */}
            {(gs?.media_tier || 0) >= 7 && (gs?.judicial_tier || 0) >= 5 ? (
              <div className="sc-op-card sc-op-black">
                <div className="sc-op-header"><span className="sc-op-icon">☠️</span><span className="sc-op-label">Journalist Elimination</span><span className="sc-op-budget-type sc-budget-personal">PERSONAL</span><span className="sc-op-cost">$4B</span></div>
                <div className="sc-op-effect">One-time: slow stability/approval decay 3 days. Discovery inevitable.</div>
                <div className="sc-op-risk">⚠️ ALWAYS discovered (3-10 days) — EU cap at 40</div>
                {!gs?.journalist_elimination_available ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Already used this game</button>
                ) : (gs?.ops_shadow_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Shadow op used this turn</button>
                ) : (gs?.personal_wealth || 0) < 4 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Need $4B personal</button>
                ) : (
                  <button className="sc-op-deploy-btn sc-op-deploy-black" onClick={() => !loading && handleOp10c('opsJournalistElimination')} disabled={loading}>
                    Eliminate — $4B (IRREVERSIBLE)
                  </button>
                )}
              </div>
            ) : (
              <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">☠️</span><span className="sc-op-label">Journalist Elimination</span></div><div className="sc-op-lock-msg">Requires Media Tier 7 and Judicial Tier 5</div></div>
            )}

            {/* Asset Exfiltration — Intel 4+ (only shown when eligible) */}
            {(gs?.intelligence_tier || 0) >= 4 && ((gs?.in_exile || gs?.exile_active) || (gs?.personal_wealth || 0) < 5) && (
              <div className="sc-op-card sc-op-black">
                <div className="sc-op-header"><span className="sc-op-icon">💼</span><span className="sc-op-label">Asset Exfiltration</span><span className="sc-op-budget-type sc-budget-personal">FREE</span></div>
                <div className="sc-op-effect">Recover ${(2.0 + ((gs?.intelligence_tier || 4) - 4) * 0.75).toFixed(1)}B from frozen accounts</div>
                {(gs?.ops_shadow_this_turn || 0) >= 1 ? (
                  <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>Shadow op used this turn</button>
                ) : (
                  <button className="sc-op-deploy-btn sc-op-deploy-black" onClick={() => !loading && handleOp10c('opsAssetExfiltration')} disabled={loading}>
                    Exfiltrate Assets
                  </button>
                )}
              </div>
            )}

          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════
            DRAWER 3 — ADMINISTRATION
        ═══════════════════════════════════════════════════════════════════ */}
        {activeDrawer === 2 && (
          <AdministrationTab gs={gs} sessionId={sessionId} />
        )}


        {/* Extraction-only disclaimer — scoped to Infrastructure drawer */}
        {activeDrawer === 0 && (
          <div className="sc-footer">
            All transactions are off-book. No public record.
          </div>
        )}

        {/* Abandon session */}
        <div className="sc-abandon-section">
          {!confirmAbandon ? (
            <button
              className="sc-abandon-btn"
              onClick={() => setConfirmAbandon(true)}
            >
              Abandon &amp; Start New Game
            </button>
          ) : (
            <div className="sc-abandon-confirm">
              <div className="sc-abandon-warning">
                Are you sure? All progress will be lost.
              </div>
              <div className="sc-abandon-actions">
                <button
                  className="btn-ghost sc-abandon-cancel"
                  onClick={() => setConfirmAbandon(false)}
                >
                  Cancel
                </button>
                <button
                  className="sc-abandon-confirm-btn"
                  onClick={() => { onClose(); onRestart && onRestart() }}
                >
                  Confirm — End Tenure
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
