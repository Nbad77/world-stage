/**
 * DomesticTab — 9.5A: Commitment Model + Budget Overview.
 * Replaces old allocation sliders with tier-based spending commitments.
 * Keeps: Budget breakdown, Tax policy, Revenue streams, GDP, Debt, Education.
 * National commitments, budget breakdown, tax policy, revenue, GDP, debt, education.
 */
import { useState } from 'react'
import { api } from '../api'


// 9.5A: Commitment axes — matches backend TIER_COSTS keys
const COMMITMENT_AXES = [
  {
    key: 'military', label: 'Military', icon: '\u2694\uFE0F',
    names: {0:'Minimal',1:'Basic Defense',2:'Regional Force',3:'Serious Military',4:'Advanced Force'},
  },
  {
    key: 'intelligence', label: 'Intelligence', icon: '\uD83D\uDD75\uFE0F',
    names: {0:'None',1:'Basic Signals',2:'Active Collection',3:'Full Apparatus'},
  },
  {
    key: 'diplomatic', label: 'Diplomatic', icon: '\uD83E\uDD1D',
    names: {0:'Minimal',1:'Basic Corps',2:'Professional',3:'Full Corps',4:'Elite Corps'},
  },
  {
    key: 'social', label: 'Social Services', icon: '\uD83C\uDFE5',
    names: {0:'Neglected',1:'Basic Services',2:'Functional',3:'Strong Services'},
  },
  {
    key: 'resource', label: 'Resource Dev.', icon: '\u26CF\uFE0F',
    names: {0:'Untapped',1:'Early Dev.',2:'Active Extraction',3:'Mature Sector',4:'Strategic Resource'},
  },
  {
    key: 'political', label: 'Political', icon: '\uD83C\uDFDB\uFE0F',
    names: {0:'None',1:'Basic',2:'Established',3:'Strong',4:'Deep Control'},
  },
  {
    key: 'education', label: 'Education', icon: '\uD83C\uDF93',
    names: {0:'Underdeveloped',1:'Basic',2:'Developed',3:'Advanced',4:'Strong Schools',
            5:'Research Culture',6:'Innovation Economy',7:'Knowledge Society',
            8:'Advanced Research',9:'World-Class',10:'Global Standard'},
  },
]

// Frontend copies of TIER_COSTS for display (must match backend)
const TIER_COSTS_FE = {
  military:     {0:0,1:0.5,2:0.9,3:1.4,4:2.0,5:2.7,6:3.5,7:4.4,8:5.5,9:7.0,10:9.0},
  intelligence: {0:0,1:0.3,2:0.6,3:1.0,4:1.5,5:2.1,6:2.8,7:3.6,8:4.5,9:5.5,10:7.0},
  diplomatic:   {0:0,1:0.3,2:0.6,3:1.0,4:1.5,5:2.0,6:2.6,7:3.3,8:4.1,9:5.0,10:6.5},
  social:       {0:0,1:0.4,2:0.8,3:1.4,4:2.0,5:2.7,6:3.5,7:4.4,8:5.5,9:6.5,10:8.0},
  education:    {0:0,1:0.3,2:0.7,3:1.2,4:1.8,5:2.5,6:3.2,7:4.0,8:5.0,9:6.0,10:7.5},
  resource:     {0:0,1:0.5,2:0.9,3:1.4,4:2.0,5:2.7,6:3.5,7:4.3,8:5.2,9:6.2,10:7.5},
  political:    {0:0,1:0.2,2:0.4,3:0.7,4:1.1,5:1.6,6:2.2,7:2.9,8:3.7,9:4.6,10:6.0},
}

function getTierName(axis, tier) {
  return axis.names[tier] || `Tier ${tier}`
}

export default function DomesticTab({ gs, sessionId, onGsUpdate }) {
  // Commitment action state
  const [upgrading, setUpgrading] = useState(null)
  const [downgrading, setDowngrading] = useState(null)
  const [commitFlash, setCommitFlash] = useState(null)


  // Finance section state
  const [taxLoading, setTaxLoading] = useState(false)
  const [taxFlash, setTaxFlash] = useState(null)
  const [previewRates, setPreviewRates] = useState({
    income_tax: gs?.tax_rates?.income_tax ?? 0.20,
    corporate_tax: gs?.tax_rates?.corporate_tax ?? 0.15,
    resource_tax: gs?.tax_rates?.resource_tax ?? 0.25,
  })
  const [bondLoading, setBondLoading] = useState(false)
  const [bondFlash, setBondFlash] = useState(null)


  // ── Commitment handlers ──
  async function handleUpgrade(tierKey) {
    if (upgrading) return
    setUpgrading(tierKey)
    setCommitFlash(null)
    try {
      const res = await api.commitmentUpgrade(sessionId, tierKey)
      if (res.success) {
        if (res.game_state) onGsUpdate(res.game_state)
        setCommitFlash(res.message || `${tierKey} upgraded`)
        if (tierKey === 'education') console.log('[FIX3] education tier upgrade:', {old_tier: res.old_tier, new_tier: res.new_tier})
        console.log(`[9.5A] Upgrade: ${tierKey} -> tier ${res.new_tier}`)
      } else {
        setCommitFlash(res.error || 'Upgrade failed')
      }
      setTimeout(() => setCommitFlash(null), 3000)
    } catch (e) {
      setCommitFlash('Failed: ' + e.message)
      setTimeout(() => setCommitFlash(null), 3000)
    } finally {
      setUpgrading(null)
    }
  }

  async function handleDowngrade(tierKey) {
    if (downgrading) return
    setDowngrading(tierKey)
    setCommitFlash(null)
    try {
      const res = await api.commitmentDowngrade(sessionId, tierKey)
      if (res.success) {
        if (res.game_state) onGsUpdate(res.game_state)
        setCommitFlash(res.message || `${tierKey} downgraded`)
        console.log(`[9.5A] Downgrade: ${tierKey} -> tier ${res.new_tier}`)
      } else {
        setCommitFlash(res.error || 'Downgrade failed')
      }
      setTimeout(() => setCommitFlash(null), 3000)
    } catch (e) {
      setCommitFlash('Failed: ' + e.message)
      setTimeout(() => setCommitFlash(null), 3000)
    } finally {
      setDowngrading(null)
    }
  }


  // Finance handlers
  async function handleTaxChange(taxType, newValue) {
    setTaxLoading(true)
    setTaxFlash(null)
    try {
      const res = await api.setTaxRates(sessionId, { [taxType]: newValue })
      if (res.game_state) onGsUpdate(res.game_state)
      setTaxFlash(res.changes?.join(', ') || 'Tax rate updated')
      setTimeout(() => setTaxFlash(null), 2000)
    } catch (e) {
      setTaxFlash('Failed: ' + e.message)
      setTimeout(() => setTaxFlash(null), 3000)
    } finally {
      setTaxLoading(false)
    }
  }

  async function handleBond(amount) {
    setBondLoading(true)
    setBondFlash(null)
    try {
      const res = await api.issueBonds(sessionId, amount)
      if (res.game_state) onGsUpdate(res.game_state)
      setBondFlash(res.changes?.join(', ') || `$${amount}B bond issued`)
      setTimeout(() => setBondFlash(null), 3000)
    } catch (e) {
      setBondFlash('Failed: ' + e.message)
      setTimeout(() => setBondFlash(null), 3000)
    } finally {
      setBondLoading(false)
    }
  }

  // ── Computed values ──
  const budget = gs?.budget || 0
  const personalWealth = gs?.personal_wealth || 0
  const totalSkimmed = gs?.total_skimmed || 0
  const totalCommitment = gs?.total_daily_commitment || 0
  const currentDay = gs?.current_day || gs?.current_turn || 1
  const cooldowns = gs?.tier_upgrade_cooldowns || {}
  const violations = gs?.prerequisite_violations || {}

  // Per-axis tier values
  const getTier = (key) => gs?.[`${key}_tier`] ?? 0
  const getDailyCost = (key) => {
    // For axes with stored daily cost fields
    const costMap = {
      military: 'daily_military_cost',
      intelligence: 'daily_intel_cost',
      diplomatic: 'daily_diplomatic_cost',
      social: 'daily_social_cost',
      education: 'daily_education_cost',
      resource: 'daily_resource_cost',
    }
    if (costMap[key]) return gs?.[costMap[key]] ?? 0
    // For political, use frontend cost table
    return TIER_COSTS_FE[key]?.[getTier(key)] ?? 0
  }


  // Budget breakdown items
  const govCost = 3.0
  const resourceIndep = gs?.resource_independence_active || false
  const oilImportCost = resourceIndep ? 0 : Math.round((gs?.oil_price || 75) / 15.0 * 10) / 10
  const installments = gs?.active_installments || []
  const installTotal = installments.reduce((s, inst) => s + (inst.amount || 0), 0)
  const sanctionsCostTable = {0: 0, 1: 2, 2: 4, 3: 7, 4: 10}
  const embargoCostTable = {0: 0, 1: 0, 2: 0, 3: 3, 4: 5}
  const sanctionsDrain = gs?.usa_sanctions_active ? (sanctionsCostTable[gs.usa_sanctions_tier || 1] || 2) : 0
  const embargoDrain = gs?.arabia_embargo_active ? (embargoCostTable[gs.arabia_embargo_tier || 1] || 0) : 0
  const fixedExpenses = Math.round((govCost + oilImportCost + installTotal + sanctionsDrain + embargoDrain) * 10) / 10
  const totalExpenses = Math.round((fixedExpenses + totalCommitment) * 10) / 10

  // Revenue for budget summary
  const dailyRevenue = gs?.last_gross_revenue || 5.5
  const dailySurplus = Math.round((dailyRevenue - totalCommitment - fixedExpenses) * 10) / 10
  const totalDailyCosts = Math.round((totalCommitment + fixedExpenses) * 10) / 10
  console.log('[FIX2] budget summary:', {commitments: gs?.total_daily_commitment, net_revenue: gs?.last_net_revenue, budget: gs?.budget})

  // Tax preview calculations
  const savedIncome = gs?.income_tax_rate || gs?.tax_rates?.income_tax || 0.20
  const savedCorp = gs?.corporate_tax_rate || gs?.tax_rates?.corporate_tax || 0.15
  const savedResource = gs?.resource_tax_rate || gs?.tax_rates?.resource_tax || 0.25
  const isPreview = Math.abs(previewRates.income_tax - savedIncome) > 0.001 ||
    Math.abs(previewRates.corporate_tax - savedCorp) > 0.001 ||
    Math.abs(previewRates.resource_tax - savedResource) > 0.001

  const previewRevenue = (() => {
    const gdp = gs?.gdp_base || 100
    const laffer = (rate) => {
      if (rate <= 0.25) return 1.0
      if (rate <= 0.45) return 1.0 - (rate - 0.25) * 1.5
      if (rate <= 0.60) return 0.70 - (rate - 0.45) * 2.5
      return Math.max(0.10, 0.33 - (rate - 0.60) * 2.0)
    }
    // Scale: revenue is ~5.5% of GDP/turn at default rates
    const scale = 0.055
    const income = gdp * scale * previewRates.income_tax * laffer(previewRates.income_tax) / 0.20
    const corp = gdp * scale * 0.6 * previewRates.corporate_tax * laffer(previewRates.corporate_tax) / 0.15
    const resourceBase = (gs?.resource_tier || 0) * 8.0
    const resource = resourceBase * previewRates.resource_tax
    const total = Math.max(0, income + corp + resource)
    if (isPreview) console.log('[FIX] tax preview:', {previewRates, savedIncome, savedCorp, savedResource, preview: total.toFixed(1), isPreview})
    return total
  })()


  // Cooldown helper
  function getCooldownDays(key) {
    const until = cooldowns[key] || 0
    return Math.max(0, until - currentDay)
  }

  // Render a single commitment axis row
  // Render a single commitment axis row
  function renderAxis(axis) {
    const tier = getTier(axis.key)
    const cost = getDailyCost(axis.key)
    const tierName = getTierName(axis, tier)
    const cooldownDays = getCooldownDays(axis.key)
    const hasViolation = violations[axis.key]

    return (
      <div key={axis.key} className="commit-row">
        <div className="commit-header">
          <span className="commit-label">
            {axis.icon} {axis.label}
          </span>
          <span className="commit-tier-badge">
            T{tier} — {tierName}
          </span>
        </div>
        <div className="commit-details">
          <span className="commit-cost">
            ${cost.toFixed(1)}B/day
          </span>
          {cooldownDays > 0 && (
            <span className="commit-cooldown">{cooldownDays}d cooldown</span>
          )}
          {hasViolation && (
            <span className="commit-violation">prereq not met</span>
          )}
        </div>
        <div className="commit-actions">
          <button
            className="commit-btn commit-btn-down"
            onClick={() => handleDowngrade(axis.key)}
            disabled={tier <= 0 || downgrading === axis.key}
          >
            {downgrading === axis.key ? '...' : '\u25BC'}
          </button>
          <div className="commit-tier-bar">
            <div
              className="commit-tier-fill"
              style={{ width: `${Math.min(100, tier * 10)}%` }}
            />
            <span className="commit-tier-num">{tier}/10</span>
          </div>
          <button
            className="commit-btn commit-btn-up"
            onClick={() => handleUpgrade(axis.key)}
            disabled={tier >= 10 || cooldownDays > 0 || upgrading === axis.key}
            title={cooldownDays > 0 ? `Cooldown: ${cooldownDays} days` : tier >= 10 ? 'Maximum' : 'Upgrade'}
          >
            {upgrading === axis.key ? '...' : '\u25B2'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="domestic-tab">
      {/* \u2550\u2550 COMMITMENTS \u2550\u2550 */}
      <div className="domestic-header">
        <span className="domestic-title">COMMITMENTS</span>
        <span className="domestic-total">${totalCommitment.toFixed(1)}B/day</span>
      </div>

      <div className="commit-panel">
        {COMMITMENT_AXES.map(axis => renderAxis(axis))}

        {commitFlash && (
          <div className={`domestic-flash ${commitFlash.includes('Failed') || commitFlash.includes('failed') || commitFlash.includes('Insufficient') || commitFlash.includes('cooldown') || commitFlash.includes('blocked') || commitFlash.includes('Invalid') || commitFlash.includes('already') ? 'flash-error' : 'flash-ok'}`}>
            {commitFlash}
          </div>
        )}
      </div>

      {/* \u2550\u2550 BUDGET SUMMARY \u2550\u2550 */}
      <div className="domestic-header" style={{ marginTop: '1rem' }}>
        <span className="domestic-title">BUDGET SUMMARY</span>
        <span className="domestic-budget-total">${budget.toFixed(1)}B</span>
      </div>
      <div className="domestic-finance-section">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', fontSize: '0.85rem' }}>
          <div style={{ marginBottom: '0.2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                {'\uD83D\uDCB5'} GDP: ${(gs?.gdp_base || 0).toFixed(0)}B
                <span style={{ color: '#666' }}>{' \u2192 '}</span>
                {isPreview
                  ? <span style={{ color: '#ffa500' }}>Est. revenue: ${previewRevenue.toFixed(1)}B/day <span style={{ fontSize: '0.65rem' }}>(preview)</span></span>
                  : <>Tax revenue: ${(gs?.last_net_revenue || dailyRevenue).toFixed(1)}B/day</>}
                {dailyRevenue > 0 && (gs?.gdp_base || 0) > 0 && (
                  <span style={{ fontSize: '0.7rem', color: '#888' }}>
                    ({(gs.gdp_base > 0 ? (dailyRevenue / gs.gdp_base * 100).toFixed(1) : '0')}% eff.)
                  </span>
                )}
              </span>
              <span style={{ color: '#50c878' }}>+${dailyRevenue.toFixed(1)}B</span>
            </div>
            {/* GDP growth drivers */}
            <div className="gdp-drivers" style={{ fontSize: '0.65rem', color: '#777', marginTop: '0.15rem' }}>
              <span style={{ color: (gs?.public_approval ?? 50) >= 50 ? '#50c878' : (gs?.public_approval ?? 50) >= 30 ? '#ffa500' : '#ff6b6b', cursor: 'help' }} title="Approval above 50% boosts GDP; below shrinks it">
                {(gs?.public_approval ?? 50) >= 50 ? '\u2191' : (gs?.public_approval ?? 50) >= 30 ? '\u2192' : '\u2193'} Approval {gs?.public_approval ?? 50}%
              </span>
              <span style={{ color: '#555' }}> \u00B7 </span>
              <span style={{ cursor: 'help' }} title="Education tier: higher = more efficient economy">Edu T{gs?.education_tier ?? 0}</span>
              <span style={{ color: '#555' }}> \u00B7 </span>
              <span style={{ cursor: 'help' }} title="Social services modifier">Social T{gs?.social_tier ?? 0}</span>
              <span style={{ color: '#555' }}> \u00B7 </span>
              <span style={{ cursor: 'help' }} title="Technology level efficiency bonus">Tech {(gs?.tech_level ?? 0).toFixed(1)}</span>
              {(gs?.skim_rate ?? 0) > 0.05 && (
                <>
                  <span style={{ color: '#555' }}> \u00B7 </span>
                  <span style={{ cursor: 'help', color: '#ffa500' }} title="Skim above 5% generates detection heat">
                    Skim {((gs?.skim_rate ?? 0) * 100).toFixed(0)}% {'\u26A0\uFE0F'}
                  </span>
                </>
              )}
            </div>
          </div>
          <div style={{ fontSize: '0.75rem', color: '#999', marginTop: '0.1rem', marginBottom: '0.1rem' }}>DAILY COSTS</div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>{'\uD83D\uDCCA'} Commitments</span>
            <span style={{ color: '#ff6b6b' }}>-${totalCommitment.toFixed(1)}B</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>{'\uD83C\uDFDB\uFE0F'} Fixed expenses</span>
            <span style={{ color: '#ff6b6b' }}>-${fixedExpenses.toFixed(1)}B</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#bbb' }}>
            <span>Total costs</span>
            <span style={{ color: '#ff6b6b' }}>-${totalDailyCosts.toFixed(1)}B/day</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '0.3rem', fontWeight: 'bold' }}>
            <span>{dailySurplus >= 0 ? '\u2705' : '\u26A0\uFE0F'} Daily surplus/deficit</span>
            <span style={{ color: dailySurplus > 0 ? '#50c878' : dailySurplus > -2 ? '#ffa500' : '#ff6b6b' }}>
              {dailySurplus >= 0 ? '+' : ''}{dailySurplus.toFixed(1)}B/day
            </span>
          </div>
        </div>
        {personalWealth > 0 && (
          <div className="budget-personal-note" style={{ marginTop: '0.5rem' }}>
            {'\uD83C\uDFE6'} Personal wealth: ${personalWealth.toFixed(1)}B
            {totalSkimmed > 0 && ` | total skimmed: $${totalSkimmed.toFixed(1)}B`}
          </div>
        )}
      </div>

      {/* \u2550\u2550 TAX POLICY \u2550\u2550 */}
      <div className="domestic-header" style={{ marginTop: '1rem' }}>
        <span className="domestic-title">TAX POLICY</span>
      </div>
      <div className="domestic-finance-section">
        {(() => {
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
              <div key={tax.id} className="domestic-tax-row">
                <span className="domestic-tax-label">
                  {tax.label}
                  {capLabel && <span className="domestic-tax-cap">{capLabel}</span>}
                </span>
                <input
                  type="range"
                  className="domestic-range"
                  min={0}
                  max={tax.max}
                  step={0.05}
                  value={previewRates[tax.id] ?? currentRate}
                  onChange={e => setPreviewRates(prev => ({...prev, [tax.id]: parseFloat(e.target.value)}))}
                  disabled={taxLoading}
                />
                <span className="domestic-tax-value" style={previewRates[tax.id] !== currentRate ? {color: '#ffa500'} : {}}>
                  {((previewRates[tax.id] ?? currentRate) * 100).toFixed(0)}%
                </span>
              </div>
            )
          })
        })()}
        <div className="domestic-tax-note">
          Higher taxes = more revenue, lower approval. Changes take effect next turn.
        </div>
        {isPreview && (
          <button
            className="domestic-apply-btn"
            style={{ marginTop: '0.3rem' }}
            onClick={async () => {
              const savedMap = {income_tax: savedIncome, corporate_tax: savedCorp, resource_tax: savedResource}
              for (const [id, rate] of Object.entries(previewRates)) {
                if (Math.abs(rate - (savedMap[id] || 0)) > 0.001) {
                  await handleTaxChange(id, rate)
                }
              }
            }}
            disabled={taxLoading}
          >
            {taxLoading ? 'Saving...' : 'Apply Tax Changes'}
          </button>
        )}
        {taxFlash && (
          <span className={`domestic-flash ${taxFlash.includes('Failed') ? 'flash-error' : 'flash-ok'}`}>
            {taxFlash}
          </span>
        )}
      </div>

      {/* \u2550\u2550 GDP \u2550\u2550 */}
      {gs?.gdp_base && (
        <div className="domestic-finance-section" style={{ marginTop: '0.5rem' }}>
          <div className="domestic-gdp-row">
            <span>{'\uD83D\uDCC8'} GDP: ${gs.gdp_base.toFixed(1)}B</span>
            <span className="domestic-gdp-growth">Growth: {((gs.gdp_growth_rate || 0.02) * 100).toFixed(1)}%</span>
          </div>
        </div>
      )}

      {/* \u2550\u2550 DEBT INSTRUMENTS \u2550\u2550 */}
      <div className="domestic-header" style={{ marginTop: '0.75rem' }}>
        <span className="domestic-title">DEBT INSTRUMENTS</span>
      </div>
      <div className="domestic-finance-section">
        <div style={{ marginBottom: '0.5rem' }}>
          <button
            className="domestic-bond-btn"
            onClick={() => handleBond(5)}
            disabled={bondLoading}
          >
            $5B Bond (+$5B now, $2B/turn × 3 repayment)
          </button>
          <div className="domestic-tax-note" style={{ fontSize: '0.65rem' }}>
            Routine sovereign debt. No diplomatic signal.
          </div>
        </div>
        <div>
          <button
            className={`domestic-bond-btn ${(gs?.large_bond_used || budget >= 20) ? 'domestic-bond-disabled' : ''}`}
            onClick={() => handleBond(10)}
            disabled={bondLoading || gs?.large_bond_used || budget >= 20}
          >
            $10B Emergency Bond (+$10B now, ~$4.3B/turn × 3, ALL NPCs -5)
          </button>
          <div className="domestic-tax-note" style={{ fontSize: '0.65rem' }}>
            {gs?.large_bond_used
              ? 'International creditors will not extend further emergency credit.'
              : budget >= 20
                ? 'Emergency financing only available under fiscal stress (budget below $20B).'
                : 'Emergency credit facility. Creditors will notice.'}
          </div>
        </div>
        {bondFlash && (
          <span className={`domestic-flash ${bondFlash.includes('Failed') ? 'flash-error' : 'flash-ok'}`} style={{ marginTop: '0.3rem', display: 'block' }}>
            {bondFlash}
          </span>
        )}
      </div>
    </div>
  )
}

