/**
 * Sticky top status bar — mirrors game_state.get_status_display()
 * Stage 5: shows state identity (regime_type | power_base) below main stats.
 * Session 2: onShadowCabinet prop opens the Shadow Cabinet drawer.
 * Addition 2: compact relations mini-row always visible below regime identity.
 */
export default function StatusBar({ gs, onShadowCabinet }) {
  if (!gs) return null

  const budgetClass = gs.budget < 5 ? 'bad' : gs.budget < 15 ? 'warn' : 'good'
  const stabilityClass = gs.stability < 20 ? 'bad' : gs.stability < 40 ? 'warn' : 'good'
  const approvalClass = gs.public_approval < 20 ? 'bad' : gs.public_approval < 40 ? 'warn' : 'good'

  const approvalEmoji =
    gs.public_approval >= 70 ? '🟢' :
    gs.public_approval >= 50 ? '🟡' :
    gs.public_approval >= 30 ? '🔴' : '💀'

  // Stage 5: state identity
  const regimeType = gs.state_identity?.regime_type || 'Managed Democracy'
  const powerBase  = gs.state_identity?.power_base  || 'Mass-Dependent'

  // Color-code regime severity (left = democratic, right = authoritarian)
  const REGIME_ORDER = ['Managed Democracy', 'Soft Authoritarianism', 'Patronage State', 'Kleptocracy', 'Totalitarian Regime']
  const regimeIdx = REGIME_ORDER.indexOf(regimeType)
  const regimeColorClass = regimeIdx <= 1 ? 'regime-democratic' : regimeIdx === 2 ? 'regime-mid' : 'regime-authoritarian'

  // Addition 2: relations mini-row data
  const rel = gs.relations || {}
  const relItems = [
    { key: 'usa',    label: 'USA',    val: rel.usa,    warn: gs.usa_sanctions_active },
    { key: 'arabia', label: 'ARABIA', val: rel.arabia, warn: gs.arabia_embargo_active },
    { key: 'eu',     label: 'EU',     val: rel.eu,     warn: false },
    { key: 'dprg',   label: 'DPRG',   val: rel.dprg,   warn: false },
  ]

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

      {/* Stage 5: state identity — full width row below the stats */}
      <div className="state-identity-row">
        <span className={`state-identity-regime ${regimeColorClass}`}>{regimeType}</span>
        <span className="state-identity-sep">·</span>
        <span className="state-identity-power">{powerBase}</span>
      </div>

      {/* Addition 2: Compact relations mini-row — always visible in the sticky bar */}
      <div className="sb-relations-row">
        {relItems.map(({ key, label, val, warn }, i) => (
          <span key={key} className={`sb-rel-item sb-rel-${key}${val < 25 ? ' sb-rel-critical' : val < 45 ? ' sb-rel-low' : ''}`}>
            {i > 0 && <span className="sb-rel-sep">|</span>}
            <span className="sb-rel-label">{label}</span>
            <span className="sb-rel-val">{val ?? '—'}</span>
            {warn && <span className="sb-rel-alert">⚠️</span>}
          </span>
        ))}
      </div>

      {/* Shadow Cabinet row — full width, only shown when personal wealth > 0 */}
      {onShadowCabinet && gs.personal_wealth > 0 && (
        <button
          className="shadow-cabinet-row-btn"
          onClick={onShadowCabinet}
        >
          <span className="sc-row-icon">🗄️</span>
          <span className="sc-row-label">SHADOW CABINET</span>
          <span className="sc-row-funds">${gs.personal_wealth.toFixed(1)}B available</span>
          <span className="sc-row-arrow">›</span>
        </button>
      )}
    </div>
  )
}
