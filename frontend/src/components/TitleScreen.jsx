/**
 * Title / splash screen shown before the game starts.
 *
 * Session persistence:
 *   hasResumable = null  → checking backend for saved session (loading state)
 *   hasResumable = false → no saved session — show normal "Begin Tenure"
 *   hasResumable = true  → active session found — show "Resume Game" + "New Game"
 */
export default function TitleScreen({ onStart, onResume, hasResumable, resumeData, loading }) {
  const gs = resumeData?.game_state

  return (
    <div className="title-screen">
      <div>
        <h1>The World Stage</h1>
        <p className="title-subtitle">A Geopolitical Simulation</p>
      </div>

      <p className="title-flavour">
        You are the newly installed leader of <strong>Europa</strong> —
        a small nation caught between superpowers. Manage your budget,
        keep the people appeased, and navigate the demands of four
        ruthless diplomatic actors. You have <strong>10 turns</strong>.
        Choose wisely.
      </p>

      <div style={{ fontFamily: 'var(--mono)', fontSize: '0.78rem', color: 'var(--muted)', lineHeight: 1.8 }}>
        <div>🇺🇸 Bill Hartwell — USA</div>
        <div>🛢️ Sadam — Arabia</div>
        <div>🇪🇺 Marsha — European Union</div>
        <div>💀 Ji-won Ryang — DPRG</div>
      </div>

      {/* ── Checking for saved session (hasResumable === null) ── */}
      {hasResumable === null && (
        <p style={{ fontSize: '0.82rem', color: 'var(--muted)', fontStyle: 'italic' }}>
          Checking for saved game...
        </p>
      )}

      {/* ── Resume block — only when a valid active session was found ── */}
      {hasResumable === true && gs && (
        <div className="resume-block">
          <div className="resume-summary">
            <span className="resume-label">Saved session found</span>
            <span className="resume-detail">
              Turn {gs.current_turn}/{gs.max_turns}
              &nbsp;·&nbsp;${gs.budget?.toFixed(1)}B budget
              &nbsp;·&nbsp;{gs.stability}% stability
            </span>
          </div>
          <div className="resume-actions">
            <button
              className="btn-primary"
              onClick={onResume}
              disabled={loading}
            >
              {loading ? 'Loading…' : 'Resume Game →'}
            </button>
            <button
              className="btn-ghost resume-new-btn"
              onClick={onStart}
              disabled={loading}
            >
              New Game
            </button>
          </div>
        </div>
      )}

      {/* ── Normal start — no saved session ── */}
      {hasResumable === false && (
        <button
          className="btn-primary"
          onClick={onStart}
          disabled={loading}
        >
          {loading ? 'Starting…' : 'Begin Tenure'}
        </button>
      )}

      <p style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
        Sessions last 24 hours
      </p>
    </div>
  )
}
