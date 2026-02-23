/**
 * Skim panel — the end-of-turn corruption / stay-clean choice.
 * skimOptions:     list of { choice, label, national_cost, personal_gain, ... }
 * onSkim:          (choice: number) => void
 * drainProjection: { projected_drain, budget_after_drain, base_cost, oil_cost,
 *                    installment_net, installment_streams } | null  (Addition 2)
 * Session 2 Item 7: show per-stream installment lines in projection.
 */
export default function SkimPanel({ skimOptions, onSkim, disabled, drainProjection }) {
  if (!skimOptions || skimOptions.length === 0) return null

  const hasStreams = drainProjection?.installment_streams?.length > 0
  const showExpanded = drainProjection && hasStreams

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
              <span className="skim-drain-label">Projected drain this turn:</span>
              <span className="skim-drain-amount">-${drainProjection.projected_drain.toFixed(1)}B</span>
              <span className="skim-drain-sep">·</span>
              <span className="skim-drain-label">Budget after drain (before skim):</span>
              <span className={`skim-drain-budget ${drainProjection.budget_after_drain < 5 ? 'skim-drain-bad' : drainProjection.budget_after_drain < 15 ? 'skim-drain-warn' : ''}`}>
                ${drainProjection.budget_after_drain.toFixed(1)}B
              </span>
            </>
          )}
        </div>
      )}

      <p style={{ fontSize: '0.83rem', color: 'var(--muted)', marginBottom: '0.75rem', lineHeight: 1.5 }}>
        Before closing the books, decide whether to redirect any national funds to your personal account.
      </p>
      {skimOptions.map((opt) => (
        <button
          key={opt.choice}
          className="sub-option-btn"
          onClick={() => onSkim(opt.choice)}
          disabled={disabled}
        >
          {opt.choice === 1 ? '✅' : opt.choice === 2 ? '💰' : opt.choice === 3 ? '💰💰' : '💰💰💰'}&nbsp;
          {opt.label}
        </button>
      ))}
    </div>
  )
}
