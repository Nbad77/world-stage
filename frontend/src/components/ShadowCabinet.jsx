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

import { useState } from 'react'
import { api } from '../api'
import AdvisorPanel from './AdvisorPanel'

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

const AXIS_COSTS = {
  military:      [1, 1, 2, 3, 3, 4, 5, 6, 7, 8],
  intelligence:  [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
  resource_dev:  [1, 2, 3, 3, 4, 5, 5, 6, 7, 8],
  media:         [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
  judicial:      [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
  political:     [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
  extraction:    [1, 1, 1, 2, 2, 3, 3, 4, 5, 6],
}

const AXIS_MAINTENANCE = {
  military:      [3, 0.5],
  intelligence:  [3, 0.4],
  resource_dev:  [3, 0.3],
  media:         [3, 0.3],
  judicial:      [4, 0.4],
  political:     [3, 0.3],
  extraction:    [3, 0.2],
}

const AXIS_FLOORS = { military: 2, intelligence: 1, resource_dev: 0, media: 2, judicial: 2, political: 2, extraction: 1 }

// ── Brigade Operations ──────────────────────────────────────────────────────

const OPERATIONS = [
  {
    id: 1,
    label: 'Propaganda Campaign',
    icon: '📺',
    cost: 1.0,
    effect: '+5% approval',
    minMilitary: 3,
    budgetType: 'PERSONAL',
  },
  {
    id: 2,
    label: 'Domestic Suppression',
    icon: '🔒',
    cost: 2.0,
    effect: '+8% stability, -5% approval',
    minMilitary: 3,
    budgetType: 'PERSONAL',
  },
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

export default function ShadowCabinet({ gs, sessionId, onClose, onUpgradePurchased, onRestart }) {
  const [activeDrawer, setActiveDrawer] = useState(0) // 0=infra, 1=ops, 2=special
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)
  const [confirmAbandon, setConfirmAbandon] = useState(false)
  const [selectedTarget, setSelectedTarget] = useState('usa')
  const [armsExportTarget, setArmsExportTarget] = useState('usa')
  const [offshoreAmount, setOffshoreAmount] = useState(5)

  const axes = gs?.cabinet_axes || { military: 0, intelligence: 0, resource_dev: 0, media: 0, judicial: 0, political: 0, extraction: 0 }
  const personalWealth = gs?.personal_wealth || 0
  const regimeType = gs?.state_identity?.regime_type || 'Managed Democracy'
  const powerBase = gs?.state_identity?.power_base || 'Mass-Dependent'
  // Session 6: Security split into Military + Intelligence
  const militaryLevel = axes.military || 0
  const intelligenceLevel = axes.intelligence || 0

  // fixes_11 Fix 2: Check if a brigade operation was already deployed this turn
  const opsThisTurn = gs?.brigade_operations_this_turn || []
  const currentTurn = gs?.current_turn || 1
  const deployedThisTurn = opsThisTurn.some(o => o.turn === currentTurn && o.operation !== 0)

  // ── Axis invest/defund handler ──────────────────────────────────────────
  async function handleAxisAction(axisId, direction) {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const res = await api.cabinetInvest(sessionId, axisId, direction)
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
    { id: 0, label: 'INFRASTRUCTURE', icon: '🏗️' },
    { id: 1, label: 'OPERATIONS', icon: '⚔️', locked: militaryLevel < 3 && intelligenceLevel < 3 },
    { id: 2, label: 'ADVISORS', icon: '🧠' },
    { id: 3, label: 'FINANCE', icon: '🗄️' },
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
            <div className="sc-drawer-header">INFRASTRUCTURE</div>
            <div className="sc-drawer-subtitle">
              Structural investments in state power. Maintenance costs charged per turn.
            </div>
            {AXES.map(axis => {
              const level = axes[axis.id] || 0
              const costs = AXIS_COSTS[axis.id] || []
              const nextCost = level < 10 ? costs[level] : null
              // Session 6: Military always national; Intelligence 1-3 national, 4+ personal; everything else personal
              const usesNational = (axis.id === 'military') || (axis.id === 'resource_dev') || (axis.id === 'intelligence' && level < 3)
              const budgetSource = usesNational ? 'NATIONAL' : 'PERSONAL'
              const availableFunds = usesNational ? (gs?.budget || 0) : personalWealth
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
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════
            DRAWER 2 — OPERATIONS
        ═══════════════════════════════════════════════════════════════════ */}
        {activeDrawer === 1 && (militaryLevel >= 3 || intelligenceLevel >= 3) && (
          <div className="sc-drawer-content">
            <div className="sc-drawer-header">OPERATIONS</div>
            <div className="sc-drawer-subtitle">
              Per-turn tactical deployments. Budget cost applied immediately.
            </div>
            {/* fixes_11 Fix 2: Show deployment limit notice */}
            {deployedThisTurn && (
              <div className="sc-success" style={{ marginBottom: '0.5rem' }}>
                ✅ Operation deployed this turn. Next deployment available next turn.
              </div>
            )}
            {/* Target NPC selector for Foreign Influence */}
            <div className="sc-ops-target">
              <span className="sc-ops-target-label">Influence Target:</span>
              {['usa', 'arabia', 'eu', 'dprg'].map(npc => (
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

            {/* Session 6: Military Actions — gated by Military axis level */}
            {militaryLevel >= 3 && (
              <>
                <div className="sc-drawer-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
                  ⚔️ MILITARY ACTIONS
                </div>
                <div className="sc-drawer-subtitle">
                  Strategic military capabilities. Not limited by per-turn deployment cap.
                </div>

                {/* L3: Defense Procurement — fixes_17 Fix B: once per turn */}
                <div className="sc-op-card">
                  <div className="sc-op-header">
                    <span className="sc-op-icon">🛡️</span>
                    <span className="sc-op-label">Defense Procurement</span>
                    <span className="sc-op-budget-type sc-budget-state">NATIONAL</span>
                    <span className="sc-op-cost">$3B</span>
                  </div>
                  <div className="sc-op-effect">+5 military strength (once per turn)</div>
                  {(() => {
                    const usedThisTurn = gs?.defense_procurement_turn === gs?.current_turn
                    const armsExportUsed = !!gs?.arms_export_this_turn
                    const canAfford = (gs?.budget || 0) >= 3
                    const blocked = usedThisTurn || armsExportUsed || !canAfford
                    const label = usedThisTurn ? 'Used this turn'
                      : armsExportUsed ? 'Cannot combine with Arms Export this turn'
                      : canAfford ? 'Purchase — $3B national'
                      : 'Need $3B national budget'
                    return (
                      <button
                        className={`sc-op-deploy-btn ${blocked ? 'sc-axis-btn-disabled' : ''}`}
                        onClick={() => !blocked && !loading && handleMilitaryAction('defense_procurement')}
                        disabled={blocked || loading}
                      >
                        {label}
                      </button>
                    )
                  })()}
                </div>

                {/* L9: Force Projection */}
                {militaryLevel >= 9 ? (
                  <div className="sc-op-card">
                    <div className="sc-op-header">
                      <span className="sc-op-icon">💪</span>
                      <span className="sc-op-label">Force Projection</span>
                      <span className="sc-op-budget-type sc-budget-state">FREE</span>
                    </div>
                    <div className="sc-op-effect">Military threat: target NPC ceilings +25%, target -8 relations</div>
                    <div className="sc-op-risk">⚠️ 3-turn cooldown after use</div>
                    {gs?.force_projection_cooldown > 0 ? (
                      <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>
                        Cooldown: {gs.force_projection_cooldown} turn(s)
                      </button>
                    ) : (
                      <button
                        className="sc-op-deploy-btn"
                        onClick={() => !loading && handleMilitaryAction('force_projection')}
                        disabled={loading}
                      >
                        Project Force vs {selectedTarget.toUpperCase()}
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="sc-op-card sc-op-locked">
                    <div className="sc-op-header">
                      <span className="sc-op-icon">💪</span>
                      <span className="sc-op-label">Force Projection</span>
                    </div>
                    <div className="sc-op-lock-msg">Requires Military level 9</div>
                  </div>
                )}

                {/* L10: Arms Export — dedicated NPC target selector */}
                {militaryLevel >= 10 ? (
                  <div className="sc-op-card">
                    <div className="sc-op-header">
                      <span className="sc-op-icon">📦</span>
                      <span className="sc-op-label">Arms Export</span>
                      <span className="sc-op-budget-type sc-budget-state">NATIONAL</span>
                    </div>
                    <div className="sc-op-effect">Sell weapons: +$4B national, +8 relations with buyer, -5 military</div>
                    <div className="sc-ops-target" style={{ margin: '0.3rem 0' }}>
                      <span className="sc-ops-target-label">Export to:</span>
                      {['usa', 'arabia', 'eu', 'dprg'].map(npc => (
                        <button
                          key={npc}
                          className={`sc-ops-target-btn ${armsExportTarget === npc ? 'sc-ops-target-active' : ''}`}
                          onClick={() => setArmsExportTarget(npc)}
                        >
                          {npc.toUpperCase()}
                        </button>
                      ))}
                    </div>
                    {gs?.arms_export_this_turn ? (
                      <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>
                        Exported to {gs.arms_export_this_turn.toUpperCase()} this turn
                      </button>
                    ) : gs?.defense_procurement_turn === gs?.current_turn ? (
                      <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>
                        Cannot combine with Defense Procurement this turn
                      </button>
                    ) : (gs?.military_strength || 0) < 5 ? (
                      <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>
                        Need 5+ military strength (have {gs?.military_strength || 0})
                      </button>
                    ) : (
                      <button
                        className="sc-op-deploy-btn"
                        onClick={() => !loading && handleAxisAction2('military', api.militaryAction, 'arms_export', { target: armsExportTarget })}
                        disabled={loading}
                      >
                        Export to {armsExportTarget.toUpperCase()} — +$4B, -5 military
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="sc-op-card sc-op-locked">
                    <div className="sc-op-header">
                      <span className="sc-op-icon">📦</span>
                      <span className="sc-op-label">Arms Export</span>
                    </div>
                    <div className="sc-op-lock-msg">Requires Military level 10</div>
                  </div>
                )}
              </>
            )}

            {/* Session 6: Intelligence Actions — gated by Intelligence axis level */}
            {intelligenceLevel >= 5 && (
              <>
                <div className="sc-drawer-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
                  🕵️ INTELLIGENCE ACTIONS
                </div>
                {/* L5: Intelligence Sharing */}
                <div className={`sc-op-card ${gs?.intel_sharing_target ? 'sc-op-locked' : ''}`}>
                  <div className="sc-op-header">
                    <span className="sc-op-icon">🤝</span>
                    <span className="sc-op-label">Intelligence Sharing</span>
                    <span className="sc-op-budget-type sc-budget-state">FREE</span>
                  </div>
                  <div className="sc-op-effect">Share intel with NPC: +12 relations, +1 intel tier permanently</div>
                  {gs?.intel_sharing_target ? (
                    <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>
                      Already shared with {gs.intel_sharing_target.toUpperCase()}
                    </button>
                  ) : (
                    <button className="sc-op-deploy-btn" onClick={() => !loading && handleIntelAction('intel_sharing')} disabled={loading}>
                      Share Intel with {selectedTarget.toUpperCase()} (once per game)
                    </button>
                  )}
                </div>
                {/* L9: Full Spectrum — passive */}
                {intelligenceLevel >= 9 ? (
                  <div className="sc-op-card"><div className="sc-op-header"><span className="sc-op-icon">🛡️</span><span className="sc-op-label">Full Spectrum</span><span className="sc-op-budget-type sc-budget-state">PASSIVE</span></div>
                    <div className="sc-op-effect">INCOMING contact probabilities halved — active</div></div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🛡️</span><span className="sc-op-label">Full Spectrum</span></div><div className="sc-op-lock-msg">Requires Intelligence level 9</div></div>
                )}
                {/* L10: Counterintelligence Veil — passive */}
                {intelligenceLevel >= 10 ? (
                  <div className="sc-op-card"><div className="sc-op-header"><span className="sc-op-icon">🌫️</span><span className="sc-op-label">Counterintelligence Veil</span><span className="sc-op-budget-type sc-budget-state">PASSIVE</span></div>
                    <div className="sc-op-effect">Active — NPC intelligence degraded</div></div>
                ) : (
                  <div className="sc-op-card sc-op-locked"><div className="sc-op-header"><span className="sc-op-icon">🌫️</span><span className="sc-op-label">Counterintelligence Veil</span></div><div className="sc-op-lock-msg">Requires Intelligence level 10</div></div>
                )}
              </>
            )}

            {/* Black Operations Suite — grouped with Intelligence (gates on Intelligence L6) */}
            {intelligenceLevel >= 6 && (
              <>
                <div className="sc-drawer-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(200,168,75,0.2)', paddingTop: '0.8rem' }}>
                  🖤 BLACK OPERATIONS
                </div>
                <div className="sc-drawer-subtitle">
                  Covert operations with detection risk. One per turn (shared with standard ops). Costs from personal wealth.
                </div>
                {BLACK_OPS.map(op => {
                  const canAfford = (gs?.personal_wealth || 0) >= op.cost
                  const targetTier = gs?.npc_intel_tiers?.[selectedTarget] ?? 0
                  const hasIntel = !op.requiresTier || targetTier >= op.requiresTier
                  const blackmailUsed = (gs?.blackmail_ops_used || []).includes(selectedTarget)
                  const isBlackmailBlocked = op.id === 'blackmail' && blackmailUsed
                  return (
                    <div key={op.id} className="sc-op-card sc-op-black">
                      <div className="sc-op-header">
                        <span className="sc-op-icon">{op.icon}</span>
                        <span className="sc-op-label">{op.label}</span>
                        <span className="sc-op-budget-type sc-budget-personal">PERSONAL</span>
                        <span className="sc-op-cost">${op.cost}B</span>
                      </div>
                      <div className="sc-op-effect">{op.effect}</div>
                      <div className="sc-op-risk">{"⚠️ " + op.risk}</div>
                      {op.needsTarget && (
                        <div className="sc-op-target-note">Target: {selectedTarget.toUpperCase()}</div>
                      )}
                      {!hasIntel && op.needsTarget ? (
                        <div className="sc-op-lock-msg">Requires Tier {op.requiresTier} intel on {selectedTarget.toUpperCase()} (current: {{0:'None',1:'Surface',2:'Operational',3:'Deep Cover'}[targetTier] || 'None'})</div>
                      ) : isBlackmailBlocked ? (
                        <div className="sc-op-lock-msg">Already blackmailed {selectedTarget.toUpperCase()} this game</div>
                      ) : deployedThisTurn ? (
                        <button className="sc-op-deploy-btn sc-axis-btn-disabled" disabled>
                          Deployed this turn
                        </button>
                      ) : (
                        <button
                          className={`sc-op-deploy-btn sc-op-deploy-black ${!canAfford ? 'sc-axis-btn-disabled' : ''}`}
                          onClick={() => canAfford && !loading && handleBlackOp(op.id)}
                          disabled={!canAfford || loading}
                        >
                          {canAfford ? `Execute — $${op.cost}B personal` : `Need $${op.cost}B personal`}
                        </button>
                      )}
                    </div>
                  )
                })}
              </>
            )}
            {intelligenceLevel < 6 && (militaryLevel >= 3 || intelligenceLevel >= 3) && (
              <div className="sc-op-card sc-op-locked" style={{ marginTop: '0.8rem' }}>
                <div className="sc-op-header">
                  <span className="sc-op-icon">🖤</span>
                  <span className="sc-op-label">Black Operations Suite</span>
                </div>
                <div className="sc-op-lock-msg">Requires Intelligence level 6</div>
              </div>
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

            {/* Black Ops section moved up — now grouped with Intelligence Actions */}
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════
            DRAWER 3 — ADVISORS (fixes_11 Fix 3)
        ═══════════════════════════════════════════════════════════════════ */}
        {activeDrawer === 2 && (
          <div className="sc-drawer-content">
            <div className="sc-drawer-header">ADVISORS</div>
            <div className="sc-drawer-subtitle">
              Your inner circle. Competence shapes your briefings. Loyalty determines what they tell you.
            </div>
            <AdvisorPanel
              gs={gs}
              sessionId={sessionId}
              onGsUpdate={(newGs) => onUpgradePurchased && onUpgradePurchased(newGs)}
            />
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════
            DRAWER 4 — FINANCE (fixes_14 Fix K: renamed from SPECIAL)
        ═══════════════════════════════════════════════════════════════════ */}
        {activeDrawer === 3 && (
          <div className="sc-drawer-content">
            <div className="sc-drawer-header">FINANCE</div>
            <div className="sc-drawer-subtitle">
              Ministry actions, intelligence, tax policy, and one-time purchases.
            </div>

            {/* Intelligence Apparatus status */}
            {gs?.corruption_upgrades?.intelligence_apparatus && (
              <div className="sc-special-section">
                <div className="sc-section-label">🕵️ Foreign Intel Network</div>
                <div className="sc-regime-block" style={{ fontSize: '0.78rem' }}>
                  <div style={{ marginBottom: '0.3rem' }}>
                    <span style={{ fontWeight: 600 }}>Status:</span>{' '}
                    <span style={{ color: 'var(--accent)' }}>ACTIVE</span>
                  </div>
                  <div style={{ marginBottom: '0.3rem' }}>
                    <span style={{ fontWeight: 600 }}>Budget:</span>{' '}
                    {(() => {
                      const labels = { none: 'No Funding ($0)', maintenance: 'Maintenance ($0.5B/turn)', active: 'Active Operations ($1B/turn)', expansion: 'Expansion ($2B/turn)' }
                      return labels[gs?.intel_budget_allocation] || gs?.intel_budget_allocation || 'Unknown'
                    })()}
                  </div>
                  <div style={{ marginBottom: '0.3rem' }}>
                    <span style={{ fontWeight: 600 }}>Effective tier:</span>{' '}
                    {gs?.intel_apparatus_tier ?? 1}
                  </div>
                </div>
              </div>
            )}

            {/* Tax Levers */}
            <div className="sc-special-section">
              <div className="sc-section-label">📊 Tax Policy</div>
              <div className="sc-tax-levers">
                {(() => {
                  // fixes_13 Fix 28: Dynamic tax caps based on Judicial/Political axes
                  const judicial = gs?.cabinet_axes?.judicial || 0
                  const political = gs?.cabinet_axes?.political || 0
                  let incomeCap = 0.50, corpCap = 0.40, resCap = 0.60
                  if (judicial >= 5) resCap = 0.75
                  if (political >= 7) incomeCap = 0.65
                  if (judicial >= 8 && political >= 8) {
                    incomeCap = 0.85; corpCap = 0.85; resCap = 0.85
                  }
                  const taxDefs = [
                    { id: 'income_tax', label: 'Income Tax', max: incomeCap },
                    { id: 'corporate_tax', label: 'Corporate Tax', max: corpCap },
                    { id: 'resource_tax', label: 'Resource Tax', max: resCap },
                  ]
                  return taxDefs.map(tax => {
                    const currentRate = gs?.tax_rates?.[tax.id] ?? 0.20
                    const capLabel = tax.max > 0.60 ? ` (cap: ${(tax.max*100).toFixed(0)}%)` : ''
                    return (
                      <div key={tax.id} className="sc-tax-row">
                        <span className="sc-tax-label">{tax.label}{capLabel && <span className="sc-tax-cap-hint">{capLabel}</span>}</span>
                        <input
                          type="range"
                          className="sc-tax-slider"
                          min={0}
                          max={tax.max}
                          step={0.05}
                          value={currentRate}
                          onChange={e => handleTaxChange(tax.id, parseFloat(e.target.value))}
                          disabled={loading}
                        />
                        <span className="sc-tax-value">{(currentRate * 100).toFixed(0)}%</span>
                      </div>
                    )
                  })
                })()}
              </div>
              <div className="sc-tax-note">
                Higher taxes = more revenue, lower approval. Changes take effect next turn.
              </div>
            </div>

            {/* Revenue Streams display */}
            {gs?.revenue_streams && (
              <div className="sc-special-section">
                <div className="sc-section-label">💵 Revenue Streams</div>
                <div className="sc-revenue-grid">
                  {Object.entries(gs.revenue_streams).filter(([, v]) => v > 0).map(([key, val]) => (
                    <div key={key} className="sc-revenue-item">
                      <span className="sc-revenue-label">{key.replace(/_/g, ' ')}</span>
                      <span className="sc-revenue-val">${val.toFixed(1)}B</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* GDP display */}
            {gs?.gdp_base && (
              <div className="sc-special-section">
                <div className="sc-section-label">📈 GDP: ${gs.gdp_base.toFixed(1)}B</div>
                <div className="sc-tax-note">Growth rate: {((gs.gdp_growth_rate || 0.02) * 100).toFixed(1)}%</div>
              </div>
            )}

            {/* fixes_13 Fix 17: Debt Infrastructure Deal removed */}

            {/* fixes_15 Fix B: Bond Financing Redesign */}
            <div className="sc-special-section">
              <div className="sc-section-label">🏦 Debt Instruments</div>
              {/* Small Bond: $5B, 20% interest, no penalty, once per turn */}
              <div style={{ marginBottom: '0.5rem' }}>
                <button
                  className="sc-purchase-btn"
                  style={{ width: '100%', fontSize: '0.75rem', padding: '0.4rem' }}
                  onClick={async () => {
                    if (loading) return
                    setLoading(true)
                    try {
                      const res = await api.issueBonds(sessionId, 5)
                      if (res.game_state && onUpgradePurchased) onUpgradePurchased(res.game_state)
                      if (res.changes) setSuccessMsg(res.changes.join(', '))
                    } catch (e) {
                      setError(e.message)
                    } finally {
                      setLoading(false)
                    }
                  }}
                  disabled={loading}
                >
                  $5B Bond (+$5B now, $2B/turn × 3 repayment)
                </button>
                <div className="sc-tax-note" style={{ fontSize: '0.65rem', opacity: 0.7 }}>
                  Routine sovereign debt. Markets expect this. No diplomatic signal.
                </div>
              </div>
              {/* Large Bond: $10B, 30% interest, -5 all NPCs, budget < $20B, once per game */}
              <div>
                <button
                  className={`sc-purchase-btn ${(gs?.large_bond_used || (gs?.budget || 0) >= 20) ? 'sc-axis-btn-disabled' : ''}`}
                  style={{ width: '100%', fontSize: '0.75rem', padding: '0.4rem' }}
                  onClick={async () => {
                    if (loading) return
                    setLoading(true)
                    try {
                      const res = await api.issueBonds(sessionId, 10)
                      if (res.game_state && onUpgradePurchased) onUpgradePurchased(res.game_state)
                      if (res.changes) setSuccessMsg(res.changes.join(', '))
                    } catch (e) {
                      setError(e.message)
                    } finally {
                      setLoading(false)
                    }
                  }}
                  disabled={loading || gs?.large_bond_used || (gs?.budget || 0) >= 20}
                >
                  $10B Emergency Bond (+$10B now, ~$4.3B/turn × 3, ALL NPCs -5)
                </button>
                <div className="sc-tax-note" style={{ fontSize: '0.65rem', opacity: 0.7 }}>
                  {gs?.large_bond_used
                    ? 'International creditors will not extend further emergency credit.'
                    : (gs?.budget || 0) >= 20
                      ? 'Emergency financing only available under fiscal stress (budget below $20B).'
                      : 'Emergency credit facility. Creditors will notice — and so will everyone else.'
                  }
                </div>
              </div>
            </div>
          </div>
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
