/**
 * EndingPanel — Displayed when an alternate ending triggers (Session 4D).
 * Four possible endings: retirement, democratic, capture, martyrdom.
 * Shows ending flavor text + historian summary + final stats, then allows restart.
 *
 * Session 6 Phase 7: Added distinct border accents, historian summary section,
 * and console.logs per ending type.
 */
export default function EndingPanel({ ending, gs, onRestart, onExportLog }) {
  if (!ending) return null
  console.log(`[ENDING] Alternate ending rendered: ${ending}`, { gs })

  const ENDING_STYLES = {
    retirement: {
      icon: '🏖️',
      title: 'Voluntary Retirement',
      flavor: 'You left on your own terms — rarer than it sounds.',
      gradeMin: 'B',
      color: 'var(--accent)',
    },
    democratic: {
      icon: '🏛️',
      title: 'Democratic Transition',
      flavor: 'Europa democratized under your watch — history will be kind.',
      gradeMin: 'A',
      color: '#4fc3f7',
    },
    capture: {
      icon: '👑',
      title: 'State Capture Complete',
      flavor: "You didn't lose power. You became the state.",
      gradeMin: null,
      color: '#ab47bc',
    },
    martyrdom: {
      icon: '⚔️',
      title: 'Martyrdom',
      flavor: 'The people loved you. That\'s why they had to remove you.',
      gradeMin: null,
      color: '#ef5350',
    },
  }

  const style = ENDING_STYLES[ending] || ENDING_STYLES.retirement
  const rels = gs?.relations || {}
  const r = (v) => typeof v === 'number' ? Math.round(v) : (v ?? '—')

  return (
    <div className="ending-screen">
      <div
        className="ending-grade-box"
        style={{ borderColor: style.color, background: 'var(--bg-panel)' }}
      >
        <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>{style.icon}</div>
        <div
          className="ending-grade"
          style={{ color: style.color, fontSize: '1.5rem' }}
        >
          {style.title}
        </div>
        {style.gradeMin && (
          <div className="ending-grade-label">Minimum Grade: {style.gradeMin}</div>
        )}
        <div
          className="ending-desc"
          style={{ marginTop: '0.5rem', fontStyle: 'italic', color: 'var(--muted)' }}
        >
          {style.flavor}
        </div>
      </div>

      {/* Historian summary — same display as EndingScreen */}
      {gs?.historian_summary && (
        <div className="panel" style={{ borderLeft: `3px solid ${style.color}`, background: 'rgba(255,255,255,0.03)' }}>
          <div className="panel-header">The Historian's Verdict</div>
          <p style={{
            fontSize: '0.9rem',
            lineHeight: 1.7,
            color: 'var(--text)',
            fontStyle: 'italic',
            padding: '0.5rem 0',
          }}>
            {gs.historian_summary}
          </p>
        </div>
      )}

      {/* Final stats */}
      <div className="panel">
        <div className="panel-header">Final Statistics</div>
        <div className="ending-stats">
          <div>Turn: {gs?.current_turn ?? '—'} / 10</div>
          <div>Budget: ${typeof gs?.budget === 'number' ? gs.budget.toFixed(1) : '—'}B</div>
          <div>Stability: {gs?.stability ?? '—'}%</div>
          <div>Approval: {gs?.public_approval ?? '—'}%</div>
          {gs?.personal_wealth > 0 && (
            <div>Personal wealth: ${gs.personal_wealth.toFixed(1)}B</div>
          )}
          {gs?.tech_level > 0 && (
            <div>Tech Level: {gs.tech_level}</div>
          )}
          <div style={{ marginTop: '0.5rem' }}>
            USA: {r(rels.usa)} | Arabia: {r(rels.arabia)} | EU: {r(rels.eu)} | DPRG: {r(rels.dprg)}
          </div>
        </div>
      </div>

      <button className="btn-primary" onClick={onRestart}>
        Start New Game
      </button>

      {onExportLog && (
        <div className="dev-export-footer" style={{ display: 'block', textAlign: 'center' }}>
          <button
            className="dev-export-btn"
            onClick={onExportLog}
            title="Export full session log as .txt"
          >
            Export Session Log
          </button>
        </div>
      )}
    </div>
  )
}
