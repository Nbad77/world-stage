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
  { key: 'russia',          label: 'Russia Relations',    min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.relations?.russia ?? 35 },
  { key: 'china',           label: 'China Relations',     min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.relations?.china ?? 35 },
  { key: 'budget',          label: 'Budget ($B)',         min: -20, max: 100, step: 0.5, type: 'number', gsPath: (gs) => gs?.budget ?? 20 },
  { key: 'personal_wealth', label: 'Personal Wealth ($B)', min: 0, max: 100, step: 0.5, type: 'number', gsPath: (gs) => gs?.personal_wealth ?? 0 },
  { key: 'stability',       label: 'Stability (%)',       min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.stability ?? 50 },
  { key: 'public_approval', label: 'Approval (%)',        min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.public_approval ?? 50 },
  { key: 'detection_heat',  label: 'Heat (%)',            min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.detection_heat ?? 0 },
  { key: 'military_strength', label: 'Military',          min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.military_strength ?? 20 },
  { key: 'tech_level',      label: 'Tech Level',          min: 0, max: 100, step: 1,   type: 'range',  gsPath: (gs) => gs?.tech_level ?? 0 },
  // 8B: Education fields
  { key: 'education_level',         label: 'Education Level',    min: 0, max: 3,   step: 1,   type: 'range',  gsPath: (gs) => gs?.education_level ?? 0 },
  { key: 'education_allocation',    label: 'Edu Alloc ($B)',     min: 0, max: 15,  step: 0.5, type: 'number', gsPath: (gs) => gs?.education_allocation ?? 0 },
  { key: 'education_gain_progress', label: 'Edu Progress',       min: 0, max: 1,   step: 0.05,type: 'number', gsPath: (gs) => gs?.education_gain_progress ?? 0 },
  // 8C: Exile fields
  { key: 'in_exile',                label: 'In Exile (0/1)',     min: 0, max: 1,   step: 1,   type: 'range',  gsPath: (gs) => gs?.in_exile ? 1 : 0 },
  { key: 'exile_day',               label: 'Exile Day',          min: 0, max: 100, step: 1,   type: 'number', gsPath: (gs) => gs?.exile_day ?? 0 },
  // 9A: Comeback fields
  { key: 'return_progress',         label: 'Return Progress',    min: 0, max: 200, step: 1,   type: 'number', gsPath: (gs) => gs?.return_progress ?? 0 },
  { key: 'return_threshold',        label: 'Return Threshold',   min: 20, max: 150, step: 1,  type: 'number', gsPath: (gs) => gs?.return_threshold ?? 100 },
  // 9C: Additional fields for ending testing
  { key: 'return_attempts',        label: 'Return Attempts',    min: 0, max: 10,  step: 1,  type: 'number', gsPath: (gs) => gs?.return_attempts ?? 0 },
  { key: 'restoration_active',     label: 'Restoration (0/1)',  min: 0, max: 1,   step: 1,  type: 'range',  gsPath: (gs) => gs?.restoration_active ? 1 : 0 },
  // 10C: Axis tier controls
  { key: '_sep_axes',              label: 'AXIS TIERS',         type: 'separator' },
  { key: 'military_tier',         label: 'Military Tier',       min: 0, max: 10, step: 1, type: 'range', gsPath: (gs) => gs?.military_tier ?? 0 },
  { key: 'intelligence_tier',     label: 'Intelligence Tier',   min: 0, max: 10, step: 1, type: 'range', gsPath: (gs) => gs?.intelligence_tier ?? 0 },
  { key: 'diplomatic_tier',       label: 'Diplomatic Tier',     min: 0, max: 10, step: 1, type: 'range', gsPath: (gs) => gs?.diplomatic_tier ?? 0 },
  { key: 'domestic_surveillance_tier', label: 'Surveillance Tier', min: 0, max: 10, step: 1, type: 'range', gsPath: (gs) => gs?.domestic_surveillance_tier ?? 0 },
  { key: 'media_tier',            label: 'Media Tier',          min: 0, max: 10, step: 1, type: 'range', gsPath: (gs) => gs?.media_tier ?? 0 },
  { key: 'judicial_tier',         label: 'Judicial Tier',       min: 0, max: 10, step: 1, type: 'range', gsPath: (gs) => gs?.judicial_tier ?? 0 },
  { key: 'extraction_tier',       label: 'Extraction Tier',     min: 0, max: 10, step: 1, type: 'range', gsPath: (gs) => gs?.extraction_tier ?? 0 },
  { key: 'militia_tier',          label: 'Militia Tier',        min: 0, max: 10, step: 1, type: 'range', gsPath: (gs) => gs?.militia_tier ?? 0 },
  // Cabinet axes (gate checks for advisor pool)
  { key: '_sep_cabinet_axes',    label: 'CABINET AXES (GATES)', type: 'separator' },
  { key: 'cabinet_axes_military',     label: 'Cab.Axes: Military',     min: 0, max: 10, step: 1, type: 'range', gsPath: (gs) => gs?.cabinet_axes?.military ?? 0 },
  { key: 'cabinet_axes_intelligence', label: 'Cab.Axes: Intelligence', min: 0, max: 10, step: 1, type: 'range', gsPath: (gs) => gs?.cabinet_axes?.intelligence ?? 0 },
  { key: 'cabinet_axes_political',    label: 'Cab.Axes: Political',    min: 0, max: 10, step: 1, type: 'range', gsPath: (gs) => gs?.cabinet_axes?.political ?? 0 },
  // 9.5A: Ending trigger fields
  { key: '_sep_ending',            label: 'ENDING TRIGGERS',    type: 'separator' },
  { key: 'current_turn',          label: 'Current Turn',        min: 1, max: 20,  step: 1,  type: 'number', gsPath: (gs) => gs?.current_turn ?? 1 },
  { key: 'constitutional_revision_active', label: 'Constitutional Revision', min: 0, max: 1, step: 1, type: 'range', gsPath: (gs) => gs?.constitutional_revision_active ? 1 : 0 },
  { key: 'action_press_suppressed',       label: 'Press Suppressed',        min: 0, max: 1, step: 1, type: 'range', gsPath: (gs) => gs?.action_press_suppressed ? 1 : 0 },
  { key: 'action_judiciary_captured',     label: 'Judiciary Captured',      min: 0, max: 1, step: 1, type: 'range', gsPath: (gs) => gs?.action_judiciary_captured ? 1 : 0 },
]

export default function DebugPanel({ gs, sessionId, onClose, onGsUpdate }) {
  // Initialize local values from current game state
  const [values, setValues] = useState(() => {
    const init = {}
    for (const f of FIELDS) {
      if (f.type === 'separator') continue
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
        if (f.type === 'separator') continue
        const current = f.gsPath(gs)
        if (values[f.key] !== current) {
          // 8C/9C: Convert boolean fields from 0/1 to true/false
          if (f.key === 'in_exile' || f.key === 'restoration_active' ||
              f.key === 'constitutional_revision_active' ||
              f.key === 'action_press_suppressed' ||
              f.key === 'action_judiciary_captured') {
            overrides[f.key] = values[f.key] === 1
          } else {
            overrides[f.key] = values[f.key]
          }
        }
      }
      if (Object.keys(overrides).length === 0) {
        setResult('No changes to apply.')
        setApplying(false)
        return
      }
      const res = await api.debugSetState(sessionId, overrides)
      // Fix F: Force full game state re-fetch to ensure all computed fields update
      const freshData = await api.getGame(sessionId)
      if (freshData.game_state) {
        onGsUpdate(freshData.game_state)
        console.log('[debug] Fix F: full game state re-fetched after debug/set_state')
      } else if (res.game_state) {
        onGsUpdate(res.game_state)
      }
      // FIX 2: Log return_progress changes
      if (overrides.return_progress !== undefined) {
        console.log(`[FIX] cheat panel return_progress set to ${overrides.return_progress}`)
      }
      if (overrides.return_threshold !== undefined) {
        console.log(`[FIX] cheat panel return_threshold set to ${overrides.return_threshold}`)
      }
      setResult(`Applied ${Object.keys(res.applied || {}).length} override(s).`)
      // Reload to refresh advisor pool and other state derived from gs fields
      setTimeout(() => window.location.reload(), 500)
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
          {FIELDS.map(f => f.type === 'separator' ? (
            <div key={f.key} style={{
              borderTop: '1px solid var(--border, #333)',
              margin: '0.75rem 0 0.25rem',
              paddingTop: '0.5rem',
              fontSize: '0.65rem',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: 'var(--muted, #888)',
            }}>{f.label}</div>
          ) : (
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

        {/* FIX 4: Budget bankruptcy warning */}
        {values.budget < 5 && (
          <div style={{
            background: 'rgba(255, 180, 0, 0.15)',
            border: '1px solid rgba(255, 180, 0, 0.4)',
            borderRadius: '4px',
            padding: '0.5rem 0.75rem',
            margin: '0.5rem 0',
            fontSize: '0.7rem',
            color: '#ffb400',
          }}>
            ⚠️ Budget below $5B will trigger bankruptcy exile on next EOT
          </div>
        )}

        {/* FIX 1: Ending Triggered display */}
        <div style={{
          borderTop: '1px solid var(--border, #333)',
          margin: '0.75rem 0',
          paddingTop: '0.5rem',
        }}>
          <div style={{
            fontSize: '0.65rem', letterSpacing: '0.1em',
            textTransform: 'uppercase', color: 'var(--muted, #888)',
            marginBottom: '0.25rem',
          }}>
            Ending Triggered
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{
              fontFamily: 'monospace', fontSize: '0.8rem',
              color: gs?.ending_triggered ? '#ff6b6b' : 'var(--muted, #666)',
            }}>
              {gs?.ending_triggered || 'None'}
            </span>
            {gs?.ending_triggered && (
              <button
                className="debug-cancel-btn"
                style={{ fontSize: '0.65rem', padding: '0.2rem 0.5rem' }}
                onClick={async () => {
                  try {
                    await api.debugSetState(sessionId, { ending_triggered: null })
                    const freshData = await api.getGame(sessionId)
                    if (freshData.game_state) onGsUpdate(freshData.game_state)
                    setResult('Cleared ending_triggered.')
                  } catch (e) {
                    setResult(`Error: ${e.message}`)
                  }
                }}
              >
                Clear Ending
              </button>
            )}
          </div>
        </div>

        {/* 9C: Quick-set buttons for testing new endings */}
        <div style={{
          borderTop: '1px solid var(--border, #333)',
          margin: '0.75rem 0',
          paddingTop: '0.75rem',
        }}>
          <div style={{
            fontSize: '0.65rem', letterSpacing: '0.1em',
            textTransform: 'uppercase', color: 'var(--muted, #888)',
            marginBottom: '0.5rem',
          }}>
            TEST PRESETS
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button
              className="debug-cancel-btn"
              style={{ fontSize: '0.7rem', padding: '0.3rem 0.6rem' }}
              onClick={() => {
                setValues(prev => ({
                  ...prev,
                  personal_wealth: 5,
                  stability: 60,
                  public_approval: 50,
                  exile_day: 15,
                  return_attempts: 1,
                  restoration_active: 0,
                }))
                console.log('[9C] Restoration Legacy preset applied', {restoration_active: 0, exile_day: 15, return_attempts: 1, exile_trigger: 'revolution'})
              }}
            >
              Set: Restoration Legacy
            </button>
            <button
              className="debug-cancel-btn"
              style={{ fontSize: '0.7rem', padding: '0.3rem 0.6rem' }}
              onClick={() => setValues(prev => ({
                ...prev,
                in_exile: 1,
                return_attempts: 3,
                return_progress: 25,
              }))}
            >
              Set: Permanent Exile
            </button>
          </div>
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
