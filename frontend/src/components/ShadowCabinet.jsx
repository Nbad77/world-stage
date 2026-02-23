/**
 * ShadowCabinet — slide-in side drawer for corruption upgrades + regime identity.
 * Triggered by the briefcase icon in the StatusBar / header.
 * Replaces the inline upgrades panel in GameScreen.
 *
 * Props:
 *   gs               : game_state object
 *   sessionId        : string
 *   onClose          : () => void
 *   onUpgradePurchased : (newGs) => void — called after successful purchase
 */

import { useState } from 'react'
import { api } from '../api'

const UPGRADES = [
  {
    id: 'intelligence_apparatus',
    label: 'Intelligence Apparatus',
    cost: 3,
    icon: '🕵️',
    effect: 'Unlocks dynamic intel dossiers on each NPC — tier-gated by relation score.',
    activeEffect: 'Active — NPC dossiers visible in diplomatic communiqués',
  },
  {
    id: 'sovereign_wealth_diversion',
    label: 'Sovereign Wealth Diversion',
    cost: 5,
    icon: '💼',
    effect: 'Large skim stability penalty reduced: -6% → -3% per turn.',
    activeEffect: 'Active — large skim penalty halved',
  },
  {
    id: 'loyalty_brigades',
    label: 'Loyalty Brigades',
    cost: 8,
    icon: '⚔️',
    effect: 'Unlocks brigade deployment after each diplomatic choice. Costs $2B, -5% approval, +10% stability, all relations -3.',
    activeEffect: 'Active — brigade deployment prompt shown after each choice',
  },
  {
    id: 'debt_infrastructure_deal',
    label: 'Debt Infrastructure Deal',
    cost: 10,
    icon: '🏗️',
    effect: 'One-time: +$20B national budget. Consequences: USA -15, EU -15 (permanent backlash).',
    activeEffect: 'Completed — funds disbursed',
  },
]

const REGIME_DESCRIPTIONS = {
  'Managed Democracy':      'Elections are held. Results are managed.',
  'Soft Authoritarianism':  'Opposition exists. It does not threaten.',
  'Patronage State':        'Loyalty is purchased. Disloyalty is expensive.',
  'Kleptocracy':            'The treasury and the personal account blur.',
  'Totalitarian Regime':    'The state is you. You are the state.',
}

const POWER_DESCRIPTIONS = {
  'Mass-Dependent': 'Survival requires popular legitimacy.',
  'Mixed':          'Some constituencies, some elites.',
  'Elite-Captured': 'Oligarchs keep you in power. You keep them profitable.',
}

export default function ShadowCabinet({ gs, sessionId, onClose, onUpgradePurchased, onRestart }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)
  const [confirmAbandon, setConfirmAbandon] = useState(false)

  const upgrades = gs?.corruption_upgrades || {}
  const personalWealth = gs?.personal_wealth || 0
  const regimeType = gs?.state_identity?.regime_type || 'Managed Democracy'
  const powerBase  = gs?.state_identity?.power_base  || 'Mass-Dependent'

  async function handlePurchase(upgradeId) {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const res = await api.purchaseUpgrade(sessionId, upgradeId)
      setSuccessMsg(res.messages?.[0] || 'Upgrade purchased')
      onUpgradePurchased && onUpgradePurchased(res.game_state)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="shadow-cabinet-overlay" onClick={onClose}>
      <div
        className="shadow-cabinet-drawer"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sc-header">
          <span className="sc-title">🗄️ SHADOW CABINET</span>
          <button className="sc-close-btn" onClick={onClose}>✕</button>
        </div>

        {/* Regime identity section */}
        <div className="sc-section">
          <div className="sc-section-label">State Classification</div>
          <div className="sc-regime-block">
            <div className="sc-regime-name">{regimeType}</div>
            <div className="sc-regime-desc">{REGIME_DESCRIPTIONS[regimeType] || ''}</div>
            <div className="sc-power-name">Power Base: {powerBase}</div>
            <div className="sc-power-desc">{POWER_DESCRIPTIONS[powerBase] || ''}</div>
          </div>
        </div>

        {/* Personal wealth */}
        <div className="sc-section">
          <div className="sc-section-label">Personal Funds Available</div>
          <div className="sc-wealth">${personalWealth.toFixed(1)}B</div>
        </div>

        {/* Feedback messages */}
        {successMsg && (
          <div className="sc-success">{successMsg}</div>
        )}
        {error && (
          <div className="sc-error">{error}</div>
        )}

        {/* Upgrades list */}
        <div className="sc-section">
          <div className="sc-section-label">Corruption Infrastructure</div>
          {UPGRADES.map(u => {
            const owned = upgrades[u.id]
            const canAfford = personalWealth >= u.cost
            return (
              <div key={u.id} className={`sc-upgrade ${owned ? 'sc-upgrade-owned' : ''}`}>
                <div className="sc-upgrade-header">
                  <span className="sc-upgrade-icon">{u.icon}</span>
                  <span className="sc-upgrade-name">{u.label}</span>
                  {owned
                    ? <span className="sc-active-badge">ACTIVE</span>
                    : <span className="sc-upgrade-cost">${u.cost}B</span>
                  }
                </div>
                <div className="sc-upgrade-effect">
                  {owned ? u.activeEffect : u.effect}
                </div>
                {!owned && (
                  <button
                    className={`sc-purchase-btn ${canAfford ? '' : 'sc-purchase-btn-disabled'}`}
                    onClick={() => canAfford && !loading && handlePurchase(u.id)}
                    disabled={!canAfford || loading}
                    title={canAfford ? `Cost: $${u.cost}B personal` : `Need $${u.cost}B (have $${personalWealth.toFixed(1)}B)`}
                  >
                    {canAfford ? `Purchase — $${u.cost}B` : `Requires $${u.cost}B`}
                  </button>
                )}
              </div>
            )
          })}
        </div>

        <div className="sc-footer">
          All transactions are off-book. No public record.
        </div>

        {/* Abandon session — tucked at the very bottom, behind a confirmation */}
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
