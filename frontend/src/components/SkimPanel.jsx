/**
 * Skim panel — the end-of-turn corruption / stay-clean choice.
 * skimOptions:     list of { choice, label, national_cost, personal_gain, ... }
 * onSkim:          (choice: number) => void
 * drainProjection: { projected_drain, budget_after_drain, base_cost, oil_cost,
 *                    installment_net, installment_streams } | null  (Addition 2)
 * detectionHeat:   number (0-95) — current detection risk level (Priority 3)
 * Session 2 Item 7: show per-stream installment lines in projection.
 */
export default function SkimPanel({ skimOptions, onSkim, disabled, drainProjection, detectionHeat = 0 }) {
  if (!skimOptions || skimOptions.length === 0) return null

  const hasStreams = drainProjection?.installment_streams?.length > 0
  const showExpanded = drainProjection && hasStreams

  // Detection risk colour thresholds
  const heatColor = detectionHeat >= 60 ? 'var(--danger)' :
                    detectionHeat >= 30 ? '#e0a040' :
                    detectionHeat > 0  ? 'var(--muted)' : null

  const heatLabel = detectionHeat >= 60 ? 'HIGH RISK' :
                    detectionHeat >= 30 ? 'ELEVATED' :
                    detectionHeat > 0  ? 'LOW' : 'CLEAR'

  return (
    <div className="panel">
      <div className="panel-header">End of Turn — Personal Allocation</div>

      {/* Addition 2 / Session 2 Item 7: Pre-skim EOT drain projection */}
      {drainProjection && (
        <div className="skim-drain-projection">
          {showExpanded ? (
            /* Detailed line-item view when installments are active */
            <div className="skim-drain-lines">
              <div className="skim-drain-line">
                <span className="skim-drain-label">Government costs:</span>
                <span className="skim-drain-amount">-${(drainProjection.base_cost ?? 3).toFixed(1)}B</span>
              </div>
              <div className="skim-drain-line">
                <span className="skim-drain-label">Oil imports:</span>
                <span className="skim-drain-amount">-${(drainProjection.oil_cost ?? 0).toFixed(1)}B</span>
              </div>
              {(drainProjection.installment_streams || []).map((stream, i) => {
                const amt = stream.amount
                const turns = stream.turns_remaining
                const isPositive = amt >= 0
                return (
                  <div key={i} className="skim-drain-line">
                    <span className="skim-drain-label">
                      {stream.description} (turn {turns} remaining):
                    </span>
                    <span className={isPositive ? 'skim-drain-positive' : 'skim-drain-amount'}>
                      {isPositive ? `+$${amt.toFixed(1)}B` : `-$${Math.abs(amt).toFixed(1)}B`}
                    </span>
                  </div>
                )
              })}
              <div className="skim-drain-line skim-drain-separator">
                <span className="skim-drain-label">Net change:</span>
                <span className={drainProjection.projected_drain <= 0 ? 'skim-drain-positive' : 'skim-drain-amount'}>
                  {drainProjection.projected_drain >= 0
                    ? `-$${drainProjection.projected_drain.toFixed(1)}B`
                    : `+$${Math.abs(drainProjection.projected_drain).toFixed(1)}B`}
                </span>
              </div>
              <div className="skim-drain-line">
                <span className="skim-drain-label">Budget after effects:</span>
                <span className={`skim-drain-budget ${drainProjection.budget_after_drain < 5 ? 'skim-drain-bad' : drainProjection.budget_after_drain < 15 ? 'skim-drain-warn' : ''}`}>
                  ${drainProjection.budget_after_drain.toFixed(1)}B
                </span>
              </div>
            </div>
          ) : (
            /* Compact single-line view (no active installments) */
            <>
              <span className="skim-drain-label">Projected EOT costs:</span>
              <span className="skim-drain-amount">-${drainProjection.projected_drain.toFixed(1)}B</span>
              <span className="skim-drain-sep">·</span>
              <span className="skim-drain-label">Budget after all EOT effects:</span>
              <span className={`skim-drain-budget ${drainProjection.budget_after_drain < 5 ? 'skim-drain-bad' : drainProjection.budget_after_drain < 15 ? 'skim-drain-warn' : ''}`}>
                ${drainProjection.budget_after_drain.toFixed(1)}B
              </span>
            </>
          )}
        </div>
      )}

      {/* Priority 3: Detection risk indicator */}
      {detectionHeat > 0 && (
        <div className="detection-risk-bar">
          <span className="detection-risk-label" style={{ color: heatColor }}>
            🔍 Detection Risk: {heatLabel} ({detectionHeat}%)
          </span>
          <div className="detection-risk-track">
            <div
              className="detection-risk-fill"
              style={{
                width: `${Math.min(100, detectionHeat)}%`,
                backgroundColor: heatColor,
              }}
            />
          </div>
        </div>
      )}

      <p style={{ fontSize: '0.83rem', color: 'var(--muted)', marginBottom: '0.75rem', lineHeight: 1.5 }}>
        Before closing the books, decide whether to redirect any national funds to your personal account.
      </p>
      {skimOptions.map((opt) => {
        {/* fixes_11 Fix 8: Show projected budget after skim + all EOT costs */}
        const budgetAfterAll = drainProjection
          ? (drainProjection.budget_after_drain - (opt.national_cost || 0)).toFixed(1)
          : null
        const willGoBankrupt = budgetAfterAll !== null && parseFloat(budgetAfterAll) < 0
        return (
          <button
            key={opt.choice}
            className="sub-option-btn"
            onClick={() => onSkim(opt.choice)}
            disabled={disabled}
          >
            <span>
              {opt.choice === 1 ? '✅' : opt.choice === 2 ? '💰' : opt.choice === 3 ? '💰💰' : '💰💰💰'}&nbsp;
              {opt.label}
            </span>
            {budgetAfterAll !== null && opt.national_cost > 0 && (
              <span className={`skim-projection-inline ${willGoBankrupt ? 'skim-drain-bad' : ''}`}>
                {willGoBankrupt
                  ? ` ⚠️ BANKRUPTCY RISK → $${budgetAfterAll}B`
                  : ` → $${budgetAfterAll}B after all costs`}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
