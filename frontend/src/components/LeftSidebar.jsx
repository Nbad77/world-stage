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

export default function LeftSidebar({ gs, onShadowCabinet, mode, onHistorian, historianLoading, onBiography }) {
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
  const techGain = gs.tech_gain_last_turn ?? 0
  const techTier = gs.tech_tier ?? 0
  const techTierName = gs.tech_tier_name ?? 'Pre-Industrial'
  const techClass = tech === 0 ? '' : techTier >= 3 ? 'good' : 'warn'
  console.log('[TECH] Display updated:', tech, techGain, `tier=${techTier} (${techTierName})`)

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
        {/* fixes_21 Fix J: Election countdown — amber indicator */}
        {gs.election_warning_shown && !gs.election_fired &&
         gs.current_turn < (gs.election_turn ?? 4) && (
          <span className="ls-election-warning">
            🗳️ ELECTION T-{(gs.election_turn ?? 4) - gs.current_turn}
          </span>
        )}
      </div>

      {/* Cabinet button — prominent, gold border, above era/day */}
      {onShadowCabinet && (
        <button className="ls-cabinet-btn-prominent" onClick={onShadowCabinet}>
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

      {/* ── Era & Day ─────────────────────────────────────────────────── */}
      <div className="ls-era-day">
        <span>ERA {gs.current_era ?? 1}</span>
        <span>DAY {gs.current_day ?? gs.current_turn ?? 1}</span>
      </div>

      {/* ── Financial ────────────────────────────────────────────────── */}
      <div className="ls-section-label">Financial</div>

      <div className="ls-stat-row">
        <span className="ls-stat-label">Treasury</span>
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
            className={`ls-bar-fill ${stabilityClass}${mode === 'event' ? ' bar-pulse' : ''}`}
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
            className={`ls-bar-fill ${approvalClass}${mode === 'event' ? ' bar-pulse' : ''}`}
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

      {/* fixes_21 Fix L: Tech Level always visible — show "0" muted when zero */}
      <div className="ls-stat-row">
        <span className="ls-stat-label">Tech Level</span>
        <span
          className={`ls-stat-value ${techClass}`}
          style={tech === 0 ? { opacity: 0.4 } : {}}
          title="Higher tech unlocks EU ceiling, boosts GDP, reduces detection risk"
        >{tech === 0 ? '0' : tech.toFixed(1)}</span>
      </div>
      <div className="ls-tech-tier" style={tech === 0 ? { opacity: 0.4 } : {}}>
        {techTierName}
      </div>
      {techGain > 0 && (
        <div className="ls-tech-gain">+{techGain.toFixed(1)}/turn</div>
      )}

      {/* 8B: Education indicator */}
      {(() => {
        const eduLevel = gs.education_level ?? 0
        const eduNames = ['Underdeveloped', 'Basic', 'Developed', 'Advanced']
        const eduColors = ['', 'warn', 'good', 'good']  // muted/amber/green/green
        const eduProgress = gs.education_gain_progress ?? 0
        const eduAlloc = gs.education_allocation ?? 0
        const eduDecay = gs.education_decay_clock ?? 0
        const eduMaint = { 1: 1.5, 2: 3.0, 3: 5.0 }[eduLevel] || 0
        const isDecaying = eduLevel > 0 && eduAlloc < eduMaint
        return (
          <>
            <div className="ls-stat-row">
              <span className="ls-stat-label">Education</span>
              <span
                className={`ls-stat-value ${eduColors[eduLevel]}`}
                style={eduLevel === 0 ? { opacity: 0.4 } : {}}
                title={`$${eduAlloc.toFixed(1)}B/turn allocated`}
              >🎓 L{eduLevel}</span>
            </div>
            <div className="ls-tech-tier" style={eduLevel === 0 ? { opacity: 0.4 } : {}}>
              {eduNames[eduLevel]}
              {isDecaying && <span style={{ color: 'var(--danger)', marginLeft: '0.3rem' }}>⚠ decay</span>}
            </div>
            {eduLevel < 3 && eduProgress > 0 && (
              <div className="ls-edu-progress-mini">
                <div className="ls-edu-progress-track">
                  <div
                    className="ls-edu-progress-fill"
                    style={{ width: `${Math.min(100, eduProgress * 100)}%` }}
                  />
                </div>
              </div>
            )}
          </>
        )
      })()}

      {/* ── Budget Allocation Summary ──────────────────────────────── */}
      {gs.budget_allocation && (() => {
        const ba = gs.budget_allocation
        const intelPct = ba.intelligence ?? 20
        const intelTier = intelPct > 25 ? 'Expand' : intelPct >= 20 ? 'Active' : intelPct >= 15 ? 'Maint' : 'Low'
        const milLevel = (ba.military ?? 20) > 30 ? 'High' : (ba.military ?? 20) >= 20 ? 'Med' : 'Low'
        const svcLevel = (ba.public_services ?? 20) > 30 ? 'High' : (ba.public_services ?? 20) >= 20 ? 'Med' : 'Low'
        return (
          <div className="ls-budget-summary">
            Intel {intelTier} · Mil {milLevel} · Svc {svcLevel}
          </div>
        )
      })()}

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

      {/* ── Influence & Summit Credibility ─────────────────────────────── */}
      {(gs.soft_power > 0 || gs.diplomatic_capital > 0 || (gs.summit_credibility ?? 100) < 100 || (gs.active_summit_commitments || []).length > 0) && (
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

      {/* ── Session 7E Step 3: Summit Credibility ──────────────────────── */}
      {(() => {
        const cred = gs.summit_credibility ?? 100
        const commitments = gs.active_summit_commitments || []
        const activeCount = commitments.filter(c => !c.broken).length
        const brokenCount = commitments.filter(c => c.broken).length
        // Only show when there's summit activity
        if (cred >= 100 && activeCount === 0 && brokenCount === 0) return null
        const credClass = cred >= 80 ? 'good' : cred >= 50 ? 'warn' : 'bad'
        return (
          <>
            <div className="ls-section-label">UN Standing</div>
            <div className="ls-stat-row">
              <span className="ls-stat-label">Credibility</span>
              <span className={`ls-stat-value ${credClass}`}>🌐 {Math.round(cred)}</span>
            </div>
            <div className="ls-bar-container">
              <div className="ls-bar-track">
                <div
                  className={`ls-bar-fill ${credClass}`}
                  style={{ width: `${Math.max(0, Math.min(100, cred))}%` }}
                />
              </div>
            </div>
            {(activeCount > 0 || brokenCount > 0) && (
              <div className="ls-summit-commitments-summary">
                {activeCount > 0 && (
                  <span className="ls-commitment-active">📋 {activeCount} active</span>
                )}
                {brokenCount > 0 && (
                  <span className="ls-commitment-broken">❌ {brokenCount} broken</span>
                )}
              </div>
            )}
          </>
        )
      })()}

      {/* ── Historian button (Session 7A Step 5: functional) ─────────── */}
      <button
        className={`ls-historian-btn ${onHistorian ? 'ls-historian-active' : ''}`}
        disabled={!onHistorian || historianLoading}
        onClick={onHistorian}
      >
        {historianLoading ? '📜 Consulting…' : '📜 Historian\'s Assessment'}
      </button>

      {/* ── 9B: Political Biography button ─────────────────────────────── */}
      {onBiography && (
        <button
          className="ls-historian-btn ls-historian-active"
          onClick={onBiography}
          style={{ marginTop: '0.3rem' }}
        >
          📖 Political Biography
        </button>
      )}

      {/* ── Emergency tokens (placeholder) ───────────────────────────── */}
      <div className="ls-emergency-tokens">
        <div className="ls-token">⏸</div>
        <div className="ls-token">⏸</div>
        <div className="ls-token">⏸</div>
      </div>

      {/* fixes_21 Fix N: Old bottom cabinet button removed — moved to prominent position above era/day */}
    </div>
  )
}
