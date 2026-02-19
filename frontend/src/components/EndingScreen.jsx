/**
 * Ending / legacy screen — shown when game ends (won, lost, or escaped).
 */
export default function EndingScreen({ ending, gs, onRestart }) {
  if (!ending) return null

  const isWon = ending.cause === 'victory'
  const isEscaped = ending.cause === 'escaped'
  const isLost = !isWon && !isEscaped

  const screenClass = isWon ? 'won' : isEscaped ? 'escaped' : 'lost'

  // Grade display (victory only)
  const gradeStr = ending.grade || (isEscaped ? '?' : 'F')
  const gradeLabel = ending.grade_label || (isEscaped ? 'FLIGHT SUCCESSFUL' : 'GAME OVER')

  // Cause label
  const causeMap = {
    bankruptcy: '💸 National Bankruptcy',
    collapse: '🔥 State Collapse',
    revolt: '✊ Popular Revolt',
    victory: '🏛️ 10-Turn Tenure Complete',
    escaped: '🛫 Escaped with Ji-won',
  }
  const causeLabel = causeMap[ending.cause] || ending.cause

  const rels = ending.final_relations || {}

  return (
    <div className="ending-screen">
      {/* Grade box */}
      <div className={`ending-grade-box ${screenClass}`}>
        <div className={`ending-grade ${screenClass}`}>{gradeStr}</div>
        <div className="ending-grade-label">{gradeLabel}</div>
        <div className="ending-title">
          {ending.grade_title || ending.personal_title || 'Unknown Fate'}
        </div>
        <div className="ending-desc">
          {ending.grade_description || ending.personal_description || ''}
        </div>
      </div>

      {/* Cause */}
      <div className="panel">
        <div className="panel-header">How It Ended</div>
        <p style={{ fontFamily: 'var(--mono)', fontSize: '0.85rem' }}>{causeLabel}</p>
      </div>

      {/* Personal legacy — non-victory only (grade box above covers won endings) */}
      {!isWon && ending.personal_title && (
        <div className="ending-personal-box">
          <div className="panel-header">Personal Legacy</div>
          <p style={{ fontWeight: 600, marginBottom: '0.3rem' }}>{ending.personal_title}</p>
          <p style={{ fontSize: '0.88rem', color: 'var(--muted)', lineHeight: 1.6 }}>
            {ending.personal_description}
          </p>
        </div>
      )}

      {/* Final stats */}
      <div className="panel">
        <div className="panel-header">Final Statistics</div>
        <div className="ending-stats">
          <div>Budget: ${typeof ending.final_budget === 'number' ? ending.final_budget.toFixed(1) : '—'}B</div>
          <div>Stability: {ending.final_stability ?? '—'}%</div>
          <div>Approval: {ending.final_approval ?? '—'}%</div>
          {ending.personal_wealth > 0 && (
            <div>Personal wealth: ${ending.personal_wealth.toFixed(1)}B</div>
          )}
          <div style={{ marginTop: '0.5rem' }}>
            USA: {rels.usa ?? '—'} | Arabia: {rels.arabia ?? '—'} | EU: {rels.eu ?? '—'} | DPRG: {rels.dprg ?? '—'}
          </div>
          {ending.usa_sanctions_active && (
            <div style={{ color: 'var(--danger)' }}>⚠️ USA Sanctions were active</div>
          )}
          {ending.arabia_embargo_active && (
            <div style={{ color: 'var(--danger)' }}>⚠️ Arabia Embargo was active</div>
          )}
        </div>
      </div>

      <button className="btn-primary" onClick={onRestart}>
        Play Again
      </button>
    </div>
  )
}
