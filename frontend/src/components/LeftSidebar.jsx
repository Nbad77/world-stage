/**
 * LeftSidebar — Desktop left panel showing vital signs.
 * Reads same gs fields as StatusBar. Does not modify StatusBar.
 * Session 7A Step 1.
 */

const REGIME_ORDER = [
  'Managed Democracy',
  'Soft Authoritarianism',
  'Patronage State',
  'Kleptocracy',
  'Totalitarian Regime',
]

const POWER_BASE_POSITIONS = {
  'Mass-Dependent': 10,
  'Mixed':          50,
  'Elite-Captured': 90,
}

export default function LeftSidebar({ gs, onShadowCabinet }) {
  if (!gs) return null

  // ── Regime identity ──────────────────────────────────────────────────
  const regimeType = gs.state_identity?.regime_type || 'Managed Democracy'
  const powerBase  = gs.state_identity?.power_base  || 'Mass-Dependent'
  const regimeIdx  = REGIME_ORDER.indexOf(regimeType)
  const regimeColorClass = regimeIdx <= 1 ? 'regime-democratic'
    : regimeIdx === 2 ? 'regime-mid'
    : 'regime-authoritarian'

  // ── Budget ───────────────────────────────────────────────────────────
  const budgetClass = gs.budget < 5 ? 'bad' : gs.budget < 15 ? 'warn' : 'good'

  // ── Stability ────────────────────────────────────────────────────────
  const stability = gs.stability ?? 0
  const stabilityClass = stability < 20 ? 'bad' : stability < 40 ? 'warn' : 'good'

  // ── Approval ─────────────────────────────────────────────────────────
  const approval = gs.public_approval ?? 0
  const approvalClass = approval < 20 ? 'bad' : approval < 40 ? 'warn' : 'good'
  const approvalEmoji = approval >= 70 ? '🟢' : approval >= 50 ? '🟡' : approval >= 30 ? '🔴' : '💀'

  // ── Oil price ────────────────────────────────────────────────────────
  const oilPrice = gs.oil_price ?? 0

  // ── Military & Tech ──────────────────────────────────────────────────
  const military = gs.military_strength ?? 20
  const militaryClass = military < 10 ? 'bad' : military < 30 ? 'warn' : 'good'
  const tech = gs.tech_level ?? 0
  const techClass = tech === 0 ? '' : tech >= 41 ? 'good' : 'warn'

  // ── Power base slider position ───────────────────────────────────────
  const sliderPos = POWER_BASE_POSITIONS[powerBase] ?? 50

  return (
    <div className="left-sidebar">

      {/* ── State Identity — Most prominent ──────────────────────────── */}
      <div className="ls-state-identity">
        <span className={`ls-regime-label ${regimeColorClass}`}>
          {regimeType}
        </span>
        <span className="ls-power-base">{powerBase}</span>
      </div>

      {/* ── Era & Day (placeholder) ──────────────────────────────────── */}
      <div className="ls-era-day">
        <span>ERA 1</span>
        <span>DAY 1</span>
      </div>

      {/* ── Financial ────────────────────────────────────────────────── */}
      <div className="ls-section-label">Financial</div>

      <div className="ls-stat-row">
        <span className="ls-stat-label">Budget</span>
        <span className={`ls-stat-value ${budgetClass}`}>${gs.budget.toFixed(1)}B</span>
      </div>

      {gs.personal_wealth > 0 && (
        <div className="ls-stat-row">
          <span className="ls-stat-label">Personal</span>
          <span className="ls-stat-value warn">🏦 ${gs.personal_wealth.toFixed(1)}B</span>
        </div>
      )}

      <div className="ls-stat-row">
        <span className="ls-stat-label">Oil Price</span>
        <span className="ls-stat-value">
          ${oilPrice}/bbl
          {gs.arabia_embargo_active && (
            <span className="ls-embargo-badge">EMBARGO T{gs.arabia_embargo_tier ?? 1}</span>
          )}
          {gs.usa_sanctions_active && (
            <span className="ls-sanctions-badge">SANCTIONS T{gs.usa_sanctions_tier ?? 1}</span>
          )}
        </span>
      </div>

      {/* ── Domestic ─────────────────────────────────────────────────── */}
      <div className="ls-section-label">Domestic</div>

      <div className="ls-stat-row">
        <span className="ls-stat-label">Stability</span>
        <span className={`ls-stat-value ${stabilityClass}`}>{stability}%</span>
      </div>
      <div className="ls-bar-container">
        <div className="ls-bar-track">
          <div
            className={`ls-bar-fill ${stabilityClass}`}
            style={{ width: `${Math.max(0, Math.min(100, stability))}%` }}
          />
        </div>
      </div>

      <div className="ls-stat-row">
        <span className="ls-stat-label">Approval</span>
        <span className={`ls-stat-value ${approvalClass}`}>{approvalEmoji} {approval}%</span>
      </div>
      <div className="ls-bar-container">
        <div className="ls-bar-track">
          <div
            className={`ls-bar-fill ${approvalClass}`}
            style={{ width: `${Math.max(0, Math.min(100, approval))}%` }}
          />
        </div>
      </div>

      {/* ── Military & Tech ──────────────────────────────────────────── */}
      <div className="ls-section-label">Capability</div>

      <div className="ls-stat-row">
        <span className="ls-stat-label">Military</span>
        <span className={`ls-stat-value ${militaryClass}`}>⚔️ {military}</span>
      </div>

      <div className="ls-stat-row">
        <span className="ls-stat-label">Tech Level</span>
        <span
          className={`ls-stat-value ${techClass}`}
          style={tech === 0 ? { opacity: 0.4 } : {}}
        >{tech}</span>
      </div>

      {/* ── Power Base slider (read-only) ────────────────────────────── */}
      <div className="ls-section-label">Power Base</div>
      <div className="ls-slider-track">
        <div className="ls-slider-thumb" style={{ left: `${sliderPos}%` }} />
      </div>
      <div className="ls-slider-labels">
        <span>Mass</span>
        <span>Mixed</span>
        <span>Elite</span>
      </div>

      {/* ── Soft Power / Diplomatic Capital (if > 0) ─────────────────── */}
      {(gs.soft_power > 0 || gs.diplomatic_capital > 0) && (
        <>
          <div className="ls-section-label">Influence</div>
          {gs.soft_power > 0 && (
            <div className="ls-stat-row">
              <span className="ls-stat-label">Soft Power</span>
              <span className={`ls-stat-value ${gs.soft_power >= 50 ? 'good' : gs.soft_power >= 25 ? 'warn' : ''}`}>
                {gs.soft_power}
              </span>
            </div>
          )}
          {gs.diplomatic_capital > 0 && (
            <div className="ls-stat-row">
              <span className="ls-stat-label">Dip. Capital</span>
              <span className={`ls-stat-value ${gs.diplomatic_capital >= 50 ? 'good' : gs.diplomatic_capital >= 25 ? 'warn' : ''}`}>
                {gs.diplomatic_capital}
              </span>
            </div>
          )}
        </>
      )}

      {/* ── Historian button (placeholder) ───────────────────────────── */}
      <button className="ls-historian-btn" disabled>
        📜 Historian's Assessment
      </button>

      {/* ── Emergency tokens (placeholder) ───────────────────────────── */}
      <div className="ls-emergency-tokens">
        <div className="ls-token">⏸</div>
        <div className="ls-token">⏸</div>
        <div className="ls-token">⏸</div>
      </div>

      {/* ── Cabinet button ───────────────────────────────────────────── */}
      {onShadowCabinet && (
        <button className="ls-cabinet-btn" onClick={onShadowCabinet}>
          <span>🗄️</span>
          <span>CABINET</span>
          {gs.personal_wealth > 0 && (
            <span style={{ fontSize: '0.65rem', color: 'var(--muted)' }}>
              ${gs.personal_wealth.toFixed(1)}B
            </span>
          )}
          <span className="ls-cabinet-arrow">›</span>
        </button>
      )}
    </div>
  )
}
