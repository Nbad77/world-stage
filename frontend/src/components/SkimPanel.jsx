/**
 * Skim panel — the end-of-turn corruption / stay-clean choice.
 * skimOptions:     list of { choice, label, national_cost, personal_gain, ... }
 * onSkim:          (choice: number) => void
 * drainProjection: { projected_drain, budget_after_drain } | null  (Addition 2)
 */
export default function SkimPanel({ skimOptions, onSkim, disabled, drainProjection }) {
  if (!skimOptions || skimOptions.length === 0) return null

  return (
    <div className="panel">
      <div className="panel-header">End of Turn — Personal Allocation</div>

      {/* Addition 2: Pre-skim EOT drain projection */}
      {drainProjection && (
        <div className="skim-drain-projection">
          <span className="skim-drain-label">Projected drain this turn:</span>
          <span className="skim-drain-amount">-${drainProjection.projected_drain.toFixed(1)}B</span>
          <span className="skim-drain-sep">·</span>
          <span className="skim-drain-label">Budget after drain (before skim):</span>
          <span className={`skim-drain-budget ${drainProjection.budget_after_drain < 5 ? 'skim-drain-bad' : drainProjection.budget_after_drain < 15 ? 'skim-drain-warn' : ''}`}>
            ${drainProjection.budget_after_drain.toFixed(1)}B
          </span>
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
