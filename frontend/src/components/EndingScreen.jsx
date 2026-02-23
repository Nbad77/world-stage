/**
 * Ending / legacy screen — shown when game ends (won, lost, or escaped).
 */
export default function EndingScreen({ ending, gs, onRestart, onExportLog }) {
  if (!ending) return null

  const isWon = ending.cause === 'victory'
  const isEscaped = ending.cause === 'escaped'
  const isLost = !isWon && !isEscaped

  const screenClass = isWon ? 'won' : isEscaped ? 'escaped' : 'lost'

  // Grade display (victory only)
  const gradeStr = ending.grade || (isEscaped ? '?' : 'F')
  const gradeLabel = ending.grade_label || (isEscaped ? 'FLIGHT SUCCESSFUL' : 'GAME OVER')

  // Cause label
  // Exile destination label — reflects which NPC arranged the escape
  const exileNpcLabels = {
    usa: '🇺🇸 Escaped — Langley Arranged the Plane',
    arabia: '🛢️ Escaped — Sadam\'s People at the Airstrip',
    eu: '🇪🇺 Escaped — Brussels Offered Asylum',
    dprg: '⚡ Escaped — Ji-won Arranged the Plane',
  }
  const causeMap = {
    bankruptcy: '💸 National Bankruptcy',
    collapse: '🔥 State Collapse',
    revolt: '✊ Popular Revolt',
    victory: '🏛️ 10-Turn Tenure Complete',
    escaped: exileNpcLabels[ending.exile_npc] || '🛫 Escaped',
  }
  const causeLabel = causeMap[ending.cause] || ending.cause

  const rels = ending.final_relations || {}

  return (
    <div className="ending-screen">
      {/* Grade box */}
      <div className={`ending-grade-box ${screenClass}`}>
        <div className={`ending-grade ${screenClass}`}>{gradeStr}</div>
        <div className="ending-grade-label">{gradeLabel}</div>
        {/* BUG 3: Only show title/desc from grade_title (victory) — never fall back to
            personal_title here, since Personal Legacy section below handles that for
            non-victory endings. Avoids the duplicate text. */}
        {ending.grade_title && (
          <div className="ending-title">{ending.grade_title}</div>
        )}
        {ending.grade_description && (
          <div className="ending-desc">{ending.grade_description}</div>
        )}
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
            {(() => {
              const r = (v) => typeof v === 'number' ? Math.round(v) : (v ?? '—')
              return `USA: ${r(rels.usa)} | Arabia: ${r(rels.arabia)} | EU: ${r(rels.eu)} | DPRG: ${r(rels.dprg)}`
            })()}
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
        Start New Game
      </button>

      {/* Export Debug Log — same dev feature as in-game footer */}
      {onExportLog && (
        <div className="dev-export-footer" style={{ display: 'block', textAlign: 'center' }}>
          <button
            className="dev-export-btn"
            onClick={onExportLog}
            title="Export full session log as .txt"
          >
            ⬇ Export Session Log
          </button>
        </div>
      )}
    </div>
  )
}
