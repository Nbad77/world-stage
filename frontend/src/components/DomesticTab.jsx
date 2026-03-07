/**
 * DomesticTab — Budget Allocation sliders for five categories.
 * Player adjusts percentages (must sum to 100), then Apply to save.
 * Domestic Affairs Tab — Session 7.
 */
import { useState, useEffect } from 'react'
import { api } from '../api'

const CATEGORIES = [
  {
    key: 'military',
    label: 'Military',
    icon: '⚔️',
    effectHigh: 'Gaining +2/turn',
    effectMed: 'Decay halved',
    effectLow: 'Normal decay',
  },
  {
    key: 'intelligence',
    label: 'Intelligence',
    icon: '🕵️',
    effectHigh: 'Expanding',
    effectMed: 'Active',
    effectMedLow: 'Maintenance',
    effectLow: 'Degrading',
  },
  {
    key: 'public_services',
    label: 'Public Services',
    icon: '🏥',
    effectHigh: '+2 approval/turn, +1 stability',
    effectMed: 'Neutral',
    effectLow: '-1 approval/turn, -1 stability',
  },
  {
    key: 'infrastructure',
    label: 'Infrastructure',
    icon: '🏗️',
    effectHigh: '+0.5% GDP bonus',
    effectMed: 'Neutral',
    effectLow: 'Neutral',
  },
  {
    key: 'diplomacy',
    label: 'Diplomacy',
    icon: '🤝',
    effectHigh: 'Relations drift moderated',
    effectMed: 'Neutral',
    effectLow: 'Neutral',
  },
]

function getEffect(cat, pct) {
  if (cat.key === 'intelligence') {
    if (pct > 25) return { text: cat.effectHigh, cls: 'effect-good' }
    if (pct >= 20) return { text: cat.effectMed, cls: 'effect-ok' }
    if (pct >= 15) return { text: cat.effectMedLow, cls: 'effect-warn' }
    return { text: cat.effectLow, cls: 'effect-bad' }
  }
  if (pct > 30) return { text: cat.effectHigh, cls: 'effect-good' }
  if (pct >= 20) return { text: cat.effectMed, cls: 'effect-ok' }
  return { text: cat.effectLow, cls: 'effect-bad' }
}

function getSliderClass(pct) {
  if (pct > 30) return 'slider-high'
  if (pct >= 20) return 'slider-med'
  return 'slider-low'
}

export default function DomesticTab({ gs, sessionId, onGsUpdate }) {
  const saved = gs?.budget_allocation || {
    military: 20, intelligence: 20, public_services: 20,
    infrastructure: 20, diplomacy: 20,
  }

  const [alloc, setAlloc] = useState({ ...saved })
  const [saving, setSaving] = useState(false)
  const [flash, setFlash] = useState(null)

  // Sync from gs if it changes externally
  useEffect(() => {
    if (gs?.budget_allocation) {
      setAlloc({ ...gs.budget_allocation })
    }
  }, [gs?.budget_allocation])

  const total = Object.values(alloc).reduce((s, v) => s + v, 0)
  const isDirty = CATEGORIES.some(c => alloc[c.key] !== saved[c.key])

  function handleSlider(key, newVal) {
    const oldVal = alloc[key]
    if (newVal === oldVal) return

    const others = CATEGORIES.filter(c => c.key !== key)
    const othersTotal = others.reduce((s, c) => s + alloc[c.key], 0)

    // Clamp: can't take more than others have
    newVal = Math.max(0, Math.min(oldVal + othersTotal, newVal))

    const updated = { [key]: newVal }
    const newOthersTotal = 100 - newVal

    if (othersTotal === 0) {
      // All others at 0 — split evenly
      const share = Math.floor(newOthersTotal / others.length)
      let leftover = newOthersTotal - share * others.length
      others.forEach(c => {
        updated[c.key] = share + (leftover > 0 ? 1 : 0)
        if (leftover > 0) leftover--
      })
    } else {
      // Proportional: each other keeps its share of the remaining pool
      let assigned = 0
      for (let i = 0; i < others.length; i++) {
        const c = others[i]
        if (i === others.length - 1) {
          // Last one gets remainder to guarantee exact 100
          updated[c.key] = Math.max(0, newOthersTotal - assigned)
        } else {
          const share = Math.max(0, Math.round((alloc[c.key] / othersTotal) * newOthersTotal))
          updated[c.key] = share
          assigned += share
        }
      }
    }

    setAlloc(updated)
  }

  async function handleApply() {
    if (saving) return
    // Ensure sum is 100
    const t = Object.values(alloc).reduce((s, v) => s + v, 0)
    if (t !== 100) return

    setSaving(true)
    try {
      const res = await api.budgetAllocation(sessionId, alloc)
      if (res.game_state) {
        onGsUpdate(res.game_state)
      }
      console.log('[BUDGET] Allocation saved:', alloc)
      setFlash('Allocation saved')
      setTimeout(() => setFlash(null), 2000)
    } catch (e) {
      console.error('[BUDGET] Save failed:', e)
      setFlash('Save failed: ' + e.message)
      setTimeout(() => setFlash(null), 3000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="domestic-tab">
      <div className="domestic-header">
        <span className="domestic-title">BUDGET ALLOCATION</span>
        <span className={`domestic-total ${total !== 100 ? 'total-error' : ''}`}>
          Total: {total}%
        </span>
      </div>

      <div className="domestic-sliders">
        {CATEGORIES.map(cat => {
          const pct = alloc[cat.key]
          const effect = getEffect(cat, pct)
          const sliderCls = getSliderClass(pct)

          return (
            <div key={cat.key} className="domestic-slider-row">
              <div className="domestic-slider-header">
                <span className="domestic-cat-label">
                  {cat.icon} {cat.label}
                </span>
                <span className={`domestic-cat-pct ${sliderCls}`}>{pct}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={pct}
                onChange={e => handleSlider(cat.key, parseInt(e.target.value))}
                className={`domestic-range ${sliderCls}`}
              />
              <div className={`domestic-effect ${effect.cls}`}>
                {effect.text}
              </div>
            </div>
          )
        })}
      </div>

      <div className="domestic-actions">
        {flash && (
          <span className={`domestic-flash ${flash.includes('failed') ? 'flash-error' : 'flash-ok'}`}>
            {flash}
          </span>
        )}
        <button
          className="domestic-apply-btn"
          onClick={handleApply}
          disabled={saving || total !== 100 || !isDirty}
        >
          {saving ? 'Saving...' : 'Apply'}
        </button>
      </div>
    </div>
  )
}
