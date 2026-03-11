/**
 * DomesticTab — Budget Allocation sliders for five categories + Education spending.
 * Player adjusts percentages (must sum to 100), then Apply to save.
 * Domestic Affairs Tab — Session 7.
 * 8B: Education spending row (separate $B allocation, not part of 100% split).
 */
import { useState, useEffect } from 'react'
import { api } from '../api'

const EDUCATION_LEVEL_NAMES = ['Underdeveloped', 'Basic', 'Developed', 'Advanced']
const EDUCATION_LEVEL_COLORS = ['#666', '#4a9eff', '#50c878', '#ffd700']
const EDUCATION_MAINTENANCE = { 1: 1.5, 2: 3.0, 3: 5.0 }
const EDUCATION_GAIN_THRESHOLDS = { 0: 2.0, 1: 4.0, 2: 7.0 }

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

  // 8B: Education state
  const eduLevel = gs?.education_level ?? 0
  const eduProgress = gs?.education_gain_progress ?? 0
  const eduDecayClock = gs?.education_decay_clock ?? 0
  const savedEduAlloc = gs?.education_allocation ?? 0
  const [eduAlloc, setEduAlloc] = useState(savedEduAlloc)
  const [savingEdu, setSavingEdu] = useState(false)
  const [eduFlash, setEduFlash] = useState(null)

  // Sync from gs if it changes externally
  useEffect(() => {
    if (gs?.budget_allocation) {
      setAlloc({ ...gs.budget_allocation })
    }
  }, [gs?.budget_allocation])

  useEffect(() => {
    setEduAlloc(gs?.education_allocation ?? 0)
  }, [gs?.education_allocation])

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

  // 8B: Education allocation save
  async function handleEduApply() {
    if (savingEdu) return
    setSavingEdu(true)
    try {
      const res = await api.educationAllocation(sessionId, eduAlloc)
      if (res.game_state) {
        onGsUpdate(res.game_state)
      }
      console.log('[EDUCATION] Allocation saved:', eduAlloc)
      setEduFlash('Education spending saved')
      setTimeout(() => setEduFlash(null), 2000)
    } catch (e) {
      console.error('[EDUCATION] Save failed:', e)
      setEduFlash('Save failed: ' + e.message)
      setTimeout(() => setEduFlash(null), 3000)
    } finally {
      setSavingEdu(false)
    }
  }

  // 8B: Computed education warnings
  const eduMaintenance = EDUCATION_MAINTENANCE[eduLevel] || 0
  const eduGainThreshold = EDUCATION_GAIN_THRESHOLDS[eduLevel] ?? null
  const isDecaying = eduLevel > 0 && eduAlloc < eduMaintenance
  const isGaining = eduLevel < 3 && eduGainThreshold !== null && eduAlloc >= eduGainThreshold
  const eduIsDirty = Math.abs(eduAlloc - savedEduAlloc) > 0.05

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

      {/* ── 8B: Education Spending ── */}
      <div className="domestic-header" style={{ marginTop: '1rem' }}>
        <span className="domestic-title">🎓 EDUCATION</span>
        <span className="edu-level-badge" style={{ color: EDUCATION_LEVEL_COLORS[eduLevel] }}>
          L{eduLevel} — {EDUCATION_LEVEL_NAMES[eduLevel]}
        </span>
      </div>

      <div className="education-section">
        {/* Progress bar */}
        {eduLevel < 3 && (
          <div className="edu-progress-row">
            <span className="edu-progress-label">
              Progress to {EDUCATION_LEVEL_NAMES[eduLevel + 1]}
            </span>
            <div className="edu-progress-bar">
              <div
                className="edu-progress-fill"
                style={{
                  width: `${Math.min(100, eduProgress * 100)}%`,
                  backgroundColor: EDUCATION_LEVEL_COLORS[eduLevel + 1],
                }}
              />
            </div>
            <span className="edu-progress-pct">{(eduProgress * 100).toFixed(0)}%</span>
          </div>
        )}
        {eduLevel === 3 && (
          <div className="edu-maxed">✅ Maximum education level reached</div>
        )}

        {/* Slider */}
        <div className="edu-alloc-row">
          <span className="edu-alloc-label">Spending:</span>
          <input
            type="range"
            min={0}
            max={15}
            step={0.5}
            value={eduAlloc}
            onChange={e => setEduAlloc(parseFloat(e.target.value))}
            className={`domestic-range ${isGaining ? 'slider-high' : isDecaying ? 'slider-low' : 'slider-med'}`}
          />
          <span className="edu-alloc-amount">${eduAlloc.toFixed(1)}B/turn</span>
        </div>

        {/* Status indicators */}
        <div className="edu-status">
          {isDecaying && (
            <span className="edu-decay-warning">
              ⚠️ Below maintenance (${eduMaintenance.toFixed(1)}B) — decay in {Math.max(0, 5 - eduDecayClock)} days
            </span>
          )}
          {isGaining && (
            <span className="edu-gaining">
              📈 Progressing — threshold met (${eduGainThreshold.toFixed(1)}B)
            </span>
          )}
          {!isDecaying && !isGaining && eduLevel > 0 && (
            <span className="edu-maintaining">
              ✔️ Maintaining {EDUCATION_LEVEL_NAMES[eduLevel]} (min ${eduMaintenance.toFixed(1)}B)
            </span>
          )}
          {!isDecaying && !isGaining && eduLevel === 0 && eduAlloc < (EDUCATION_GAIN_THRESHOLDS[0] || 2) && eduAlloc > 0 && (
            <span className="edu-insufficient">
              ⚡ Below gain threshold (${(EDUCATION_GAIN_THRESHOLDS[0] || 2).toFixed(1)}B needed)
            </span>
          )}
          {eduLevel >= 2 && gs?.stability < 30 && (
            <span className="edu-brain-drain">
              🧠 Brain drain risk — stability too low
            </span>
          )}
        </div>

        {/* Apply button */}
        <div className="domestic-actions">
          {eduFlash && (
            <span className={`domestic-flash ${eduFlash.includes('failed') ? 'flash-error' : 'flash-ok'}`}>
              {eduFlash}
            </span>
          )}
          <button
            className="domestic-apply-btn"
            onClick={handleEduApply}
            disabled={savingEdu || !eduIsDirty}
          >
            {savingEdu ? 'Saving...' : 'Set Education Spending'}
          </button>
        </div>
      </div>
    </div>
  )
}
