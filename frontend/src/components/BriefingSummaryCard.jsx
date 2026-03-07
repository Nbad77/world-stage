/**
 * BriefingSummaryCard — Session 7B Step 4.
 * Compact summary card shown at the top of each day's briefing.
 * Shows item counts, budget trend, active escalations.
 * Dismissable per day (reappears next day).
 */
import { useState, useEffect, useRef } from 'react'

const NPC_NAMES = {
  usa: 'Bill Hartwell',
  arabia: 'Sadam',
  eu: 'Marsha',
  dprg: 'Ji-won Ryang',
}

export default function BriefingSummaryCard({ gs, currentEvent, intercepts }) {
  const [dismissed, setDismissed] = useState(false)
  const lastDayRef = useRef(null)

  const era = gs?.current_era ?? 1
  const day = gs?.current_day ?? gs?.current_turn ?? 1

  // Reset dismissed state when day changes
  useEffect(() => {
    if (lastDayRef.current !== null && lastDayRef.current !== day) {
      setDismissed(false)
    }
    lastDayRef.current = day
  }, [day])

  if (dismissed) {
    return (
      <button
        className="briefing-summary-collapsed"
        onClick={() => setDismissed(false)}
      >
        ERA {era} · DAY {day} BRIEFING — click to expand
      </button>
    )
  }

  // ── Count briefing items ────────────────────────────────────────────
  let urgentCount = 0
  let incomingCount = 0
  const escalations = []

  const ignoredComms = gs?.ignored_communiques || {}

  for (const npc of ['usa', 'arabia', 'eu', 'dprg']) {
    const rel = gs?.relations?.[npc] ?? 50
    const hasSanctions = npc === 'usa' && gs?.usa_sanctions_active
    const hasEmbargo = npc === 'arabia' && gs?.arabia_embargo_active
    if (hasSanctions || hasEmbargo || rel < 25) urgentCount++
    else incomingCount++

    // Check for escalations
    const esc = ignoredComms[npc]
    if (esc && esc.ignore_count >= 2) {
      escalations.push({
        npc,
        name: NPC_NAMES[npc] || npc.toUpperCase(),
        days: esc.ignore_count,
      })
    }
  }

  // Intelligence items
  const intelCount = (intercepts || []).length

  // Event
  if (currentEvent) {
    const fx = currentEvent.effects || {}
    const hasConsequence = fx.oil_price_delta || fx.stability_delta ||
      Object.values(fx.relations_delta || {}).some(v => v !== 0)
    if (hasConsequence) urgentCount++
    else incomingCount++
  }

  // ── Budget trend ────────────────────────────────────────────────────
  // Compare current budget to what it was at start of day (approximation using last EOT)
  const budget = gs?.budget ?? 0
  const prevBudget = gs?.budget_last_eot ?? budget
  const budgetDelta = budget - prevBudget
  const budgetTrend = budgetDelta > 0.5 ? 'up' : budgetDelta < -0.5 ? 'down' : 'flat'
  const budgetArrow = budgetTrend === 'up' ? '↑' : budgetTrend === 'down' ? '↓' : '→'
  const budgetClass = budgetTrend === 'up' ? 'trend-up' : budgetTrend === 'down' ? 'trend-down' : 'trend-flat'

  const totalItems = urgentCount + incomingCount + intelCount

  const summary = { era, day, urgentCount, incomingCount, intelCount, budgetTrend, escalations: escalations.length }
  console.log('[BRIEFING] Summary card rendered:', summary)

  return (
    <div className="briefing-summary-card">
      <div className="briefing-summary-header">
        <div className="briefing-summary-title">
          ERA {era} · DAY {day} BRIEFING
        </div>
        <button
          className="briefing-summary-dismiss"
          onClick={() => setDismissed(true)}
          title="Collapse briefing"
        >
          _
        </button>
      </div>

      <div className="briefing-summary-body">
        <div className="briefing-summary-counts">
          {urgentCount > 0 && (
            <span className="briefing-count-chip chip-urgent">{urgentCount} urgent</span>
          )}
          <span className="briefing-count-chip chip-incoming">{incomingCount} incoming</span>
          {intelCount > 0 && (
            <span className="briefing-count-chip chip-intel">{intelCount} intelligence</span>
          )}
        </div>

        <div className="briefing-summary-stats">
          <span className={`briefing-budget-trend ${budgetClass}`}>
            Budget: ${budget.toFixed(1)}B {budgetArrow}
          </span>
        </div>

        {escalations.length > 0 && (
          <div className="briefing-summary-escalations">
            {escalations.map(esc => (
              <div key={esc.npc} className="briefing-escalation-item">
                {esc.name}: {esc.days} day{esc.days !== 1 ? 's' : ''} without response
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
