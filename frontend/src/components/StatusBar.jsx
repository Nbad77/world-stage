/**
 * Sticky top status bar — mirrors game_state.get_status_display()
 */
export default function StatusBar({ gs }) {
  if (!gs) return null

  const budgetClass = gs.budget < 5 ? 'bad' : gs.budget < 15 ? 'warn' : 'good'
  const stabilityClass = gs.stability < 20 ? 'bad' : gs.stability < 40 ? 'warn' : 'good'
  const approvalClass = gs.public_approval < 20 ? 'bad' : gs.public_approval < 40 ? 'warn' : 'good'

  const approvalEmoji =
    gs.public_approval >= 70 ? '🟢' :
    gs.public_approval >= 50 ? '🟡' :
    gs.public_approval >= 30 ? '🔴' : '💀'

  return (
    <div className="status-bar">
      <div className="stat">
        <span className="stat-label">Turn</span>
        <span className="stat-value mono">{gs.current_turn}/{gs.max_turns}</span>
      </div>
      <div className="stat">
        <span className="stat-label">Budget</span>
        <span className={`stat-value mono ${budgetClass}`}>${gs.budget.toFixed(1)}B</span>
      </div>
      {gs.personal_wealth > 0 && (
        <div className="stat">
          <span className="stat-label">Personal</span>
          <span className="stat-value mono warn">🏦 ${gs.personal_wealth.toFixed(1)}B</span>
        </div>
      )}
      <div className="stat">
        <span className="stat-label">Stability</span>
        <span className={`stat-value mono ${stabilityClass}`}>{gs.stability}%</span>
      </div>
      <div className="stat">
        <span className="stat-label">Approval</span>
        <span className={`stat-value mono ${approvalClass}`}>{approvalEmoji} {gs.public_approval}%</span>
      </div>
      <div className="stat">
        <span className="stat-label">Oil</span>
        <span className="stat-value mono">${gs.oil_price}/bbl</span>
      </div>
    </div>
  )
}
