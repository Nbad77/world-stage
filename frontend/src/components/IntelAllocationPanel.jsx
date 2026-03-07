/**
 * IntelAllocationPanel — Shown before skim screen each turn (Session 4D).
 * Player allocates national budget to intelligence apparatus.
 * Options: none ($0), maintenance ($0.5B), active ($1.0B), expansion ($2.0B)
 */
import { useState } from 'react'

const INTEL_OPTIONS = [
  { key: 'none',        label: 'No Funding',         cost: 0,   desc: 'Apparatus degrades after 2 consecutive unfunded turns' },
  { key: 'maintenance', label: 'Maintenance',         cost: 0.5, desc: 'Keep apparatus at current level' },
  { key: 'active',      label: 'Active Operations',   cost: 1.0, desc: 'Full operational capability this turn' },
  { key: 'expansion',   label: 'Expansion',            cost: 2.0, desc: 'Maximum investment — apparatus grows' },
]

export default function IntelAllocationPanel({ gs, onAllocate, disabled }) {
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)

  if (!gs) return null

  const budget = gs.budget ?? 0
  const unfundedStreak = gs.intel_turns_unfunded ?? 0
  const currentAllocation = gs.intel_budget_allocation ?? 'maintenance'

  async function handleConfirm() {
    if (!selected || loading) return
    setLoading(true)
    try {
      await onAllocate(selected)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">Intelligence Budget Allocation</div>
      <p style={{ fontSize: '0.85rem', color: 'var(--muted)', margin: '0.5rem 0' }}>
        Allocate national budget to intelligence apparatus before personal allocation.
        {unfundedStreak > 0 && (
          <span style={{ color: 'var(--danger)', fontWeight: 600 }}>
            {' '}Unfunded {unfundedStreak}/2 turns — apparatus will degrade!
          </span>
        )}
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', margin: '0.5rem 0' }}>
        {INTEL_OPTIONS.map(opt => {
          const canAfford = budget >= opt.cost
          const isSelected = selected === opt.key
          const isCurrent = currentAllocation === opt.key

          return (
            <button
              key={opt.key}
              onClick={() => !disabled && canAfford && setSelected(opt.key)}
              disabled={disabled || !canAfford}
              style={{
                padding: '0.6rem 0.8rem',
                background: isSelected ? 'var(--accent)' : 'var(--bg-panel)',
                color: isSelected ? '#000' : canAfford ? 'var(--fg)' : 'var(--muted)',
                border: isSelected ? '2px solid var(--accent)' : '1px solid var(--border)',
                borderRadius: '6px',
                cursor: canAfford && !disabled ? 'pointer' : 'not-allowed',
                textAlign: 'left',
                opacity: canAfford ? 1 : 0.5,
                fontFamily: 'var(--mono)',
                fontSize: '0.85rem',
              }}
            >
              <div style={{ fontWeight: 600 }}>
                {opt.label} {opt.cost > 0 ? `— $${opt.cost.toFixed(1)}B` : '— $0'}
                {isCurrent && <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: 'var(--muted)' }}>(current)</span>}
              </div>
              <div style={{ fontSize: '0.78rem', color: isSelected ? '#333' : 'var(--muted)', marginTop: '0.2rem' }}>
                {opt.desc}
              </div>
            </button>
          )
        })}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
          National budget: ${budget.toFixed(1)}B
        </span>
        <button
          className="btn-primary"
          onClick={handleConfirm}
          disabled={!selected || loading || disabled}
          style={{ minWidth: '120px' }}
        >
          {loading ? 'Allocating...' : 'Confirm'}
        </button>
      </div>
    </div>
  )
}
