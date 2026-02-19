/**
 * Emergency injection panel (Option G sub-choice).
 * injectOptions: list of { choice, label, personal_cost, national_gain }
 * onInject: (choice: number) => void
 */
export default function InjectPanel({ injectOptions, onInject, disabled }) {
  if (!injectOptions || injectOptions.length === 0) return null

  return (
    <div className="panel">
      <div className="panel-header" style={{ color: 'var(--warning)' }}>
        ⚠️ Emergency Fund Injection
      </div>
      <p style={{ fontSize: '0.83rem', color: 'var(--muted)', marginBottom: '0.75rem', lineHeight: 1.5 }}>
        The national treasury is dangerously low. You may inject personal funds to prevent collapse.
      </p>
      {injectOptions.map((opt) => (
        <button
          key={opt.choice}
          className="sub-option-btn"
          onClick={() => onInject(opt.choice)}
          disabled={disabled}
        >
          {opt.choice === 0 ? '❌' : opt.choice === 3 ? '🏛️' : '💵'}&nbsp;
          {opt.label}
        </button>
      ))}
    </div>
  )
}
