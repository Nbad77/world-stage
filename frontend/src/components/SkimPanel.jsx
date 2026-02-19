/**
 * Skim panel — the end-of-turn corruption / stay-clean choice.
 * skimOptions: list of { choice, label, national_cost, personal_gain, ... }
 * onSkim: (choice: number) => void
 */
export default function SkimPanel({ skimOptions, onSkim, disabled }) {
  if (!skimOptions || skimOptions.length === 0) return null

  return (
    <div className="panel">
      <div className="panel-header">End of Turn — Personal Allocation</div>
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
