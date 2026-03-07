/**
 * fixes_10 Fix 7: Debug panel for manual stat adjustment.
 * Activated by Ctrl+Shift+D. Hidden in production (import.meta.env.PROD).
 * Allows manual override of relations, budget, stability, approval, etc.
 */
import { useState } from 'react'
import { api } from '../api'

const FIELDS = [
  { key: 'usa',             label: 'USA Relations',      min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.relations?.usa ?? 50 },
  { key: 'arabia',          label: 'Arabia Relations',    min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.relations?.arabia ?? 50 },
  { key: 'eu',              label: 'EU Relations',        min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.relations?.eu ?? 50 },
  { key: 'dprg',            label: 'DPRG Relations',      min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.relations?.dprg ?? 50 },
  { key: 'budget',          label: 'Budget ($B)',         min: -20, max: 100, step: 0.5, type: 'number', gsPath: (gs) => gs?.budget ?? 20 },
  { key: 'personal_wealth', label: 'Personal Wealth ($B)', min: 0, max: 100, step: 0.5, type: 'number', gsPath: (gs) => gs?.personal_wealth ?? 0 },
  { key: 'stability',       label: 'Stability (%)',       min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.stability ?? 50 },
  { key: 'public_approval', label: 'Approval (%)',        min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.public_approval ?? 50 },
  { key: 'detection_heat',  label: 'Heat (%)',            min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.detection_heat ?? 0 },
  { key: 'military_strength', label: 'Military',          min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.military_strength ?? 20 },
  { key: 'tech_level',      label: 'Tech Level',          min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.tech_level ?? 0 },
]

export default function DebugPanel({ gs, sessionId, onClose, onGsUpdate }) {
  // Initialize local values from current game state
  const [values, setValues] = useState(() => {
    const init = {}
    for (const f of FIELDS) {
      init[f.key] = f.gsPath(gs)
    }
    return init
  })
  const [applying, setApplying] = useState(false)
  const [result, setResult] = useState(null)

  function handleChange(key, raw) {
    const field = FIELDS.find(f => f.key === key)
    const val = field?.step < 1 ? parseFloat(raw) : parseInt(raw, 10)
    if (isNaN(val)) return
    setValues(prev => ({ ...prev, [key]: val }))
  }

  async function handleApply() {
    setApplying(true)
    setResult(null)
    try {
      // Only send values that differ from current game state
      const overrides = {}
      for (const f of FIELDS) {
        const current = f.gsPath(gs)
        if (values[f.key] !== current) {
          overrides[f.key] = values[f.key]
        }
      }
      if (Object.keys(overrides).length === 0) {
        setResult('No changes to apply.')
        setApplying(false)
        return
      }
      const res = await api.debugSetState(sessionId, overrides)
      if (res.game_state) onGsUpdate(res.game_state)
      setResult(`Applied ${Object.keys(res.applied || {}).length} override(s).`)
      // Auto-close after brief delay
      setTimeout(() => onClose(), 600)
    } catch (e) {
      setResult(`Error: ${e.message}`)
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="debug-overlay">
      <div className="debug-panel">
        <div className="debug-header">
          <span className="debug-mode-label">DEBUG MODE</span>
          <button className="debug-close" onClick={onClose}>X</button>
        </div>

        <div className="debug-fields">
          {FIELDS.map(f => (
            <div key={f.key} className="debug-field-row">
              <label className="debug-field-label">{f.label}</label>
              {f.type === 'range' ? (
                <div className="debug-range-wrap">
                  <input
                    type="range"
                    min={f.min}
                    max={f.max}
                    step={f.step}
                    value={values[f.key]}
                    onChange={e => handleChange(f.key, e.target.value)}
                    className="debug-range"
                  />
                  <span className="debug-range-val">{values[f.key]}</span>
                </div>
              ) : (
                <input
                  type="number"
                  min={f.min}
                  max={f.max}
                  step={f.step}
                  value={values[f.key]}
                  onChange={e => handleChange(f.key, e.target.value)}
                  className="debug-number-input"
                />
              )}
            </div>
          ))}
        </div>

        {result && <div className="debug-result">{result}</div>}

        <div className="debug-actions">
          <button
            className="debug-apply-btn"
            onClick={handleApply}
            disabled={applying}
          >
            {applying ? 'Applying...' : 'Apply Overrides'}
          </button>
          <button className="debug-cancel-btn" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
