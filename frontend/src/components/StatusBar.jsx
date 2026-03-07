/**
 * Sticky top status bar — mirrors game_state.get_status_display()
 * Stage 5: shows state identity (regime_type | power_base) below main stats.
 * Session 2: onShadowCabinet prop opens the Shadow Cabinet drawer.
 * Addition 2: compact relations mini-row always visible below regime identity.
 */
import { useEffect } from 'react'

export default function StatusBar({ gs, onShadowCabinet }) {
  const approval = gs?.public_approval
  const stability = gs?.stability

  // fixes_8 Fix 1 + fixes_19 Fix B: useEffect must be called unconditionally (before early return)
  useEffect(() => {
    if (approval != null && stability != null) {
      console.log("HEADER VALUES — approval:", approval, "stability:", stability)
    }
  }, [approval, stability])

  if (!gs) return null

  const budgetClass = gs.budget < 5 ? 'bad' : gs.budget < 15 ? 'warn' : 'good'
  const stabilityClass = stability < 20 ? 'bad' : stability < 40 ? 'warn' : 'good'
  const approvalClass = approval < 20 ? 'bad' : approval < 40 ? 'warn' : 'good'

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
      {/* ITEM 3: Military Strength */}
      <div className="stat">
        <span className="stat-label">Military</span>
        <span className={`stat-value mono ${(gs.military_strength ?? 20) < 10 ? 'bad' : (gs.military_strength ?? 20) < 30 ? 'warn' : 'good'}`}>⚔️ {gs.military_strength ?? 20}</span>
      </div>

      {/* fixes_8 Fix 4: Tech Level always visible — greyed at 0 */}
      <div className="stat">
        <span className="stat-label">Tech</span>
        <span className={`stat-value mono ${(gs.tech_level ?? 0) === 0 ? '' : gs.tech_level >= 41 ? 'good' : 'warn'}`}
          style={(gs.tech_level ?? 0) === 0 ? { opacity: 0.4 } : {}}
          title="Higher tech unlocks EU ceiling, boosts GDP, reduces detection risk"
        >{typeof gs.tech_level === 'number' ? gs.tech_level.toFixed(1) : (gs.tech_level ?? 0)}</span>
      </div>

      {/* Session 5: Latent stats — Soft Power + Diplomatic Capital */}
      {(gs.soft_power > 0 || gs.diplomatic_capital > 0) && (
        <>
          <div className="stat">
            <span className="stat-label">Soft Pwr</span>
            <span className={`stat-value mono ${gs.soft_power >= 50 ? 'good' : gs.soft_power >= 25 ? 'warn' : ''}`}
              style={gs.soft_power === 0 ? { opacity: 0.4 } : {}}
              title={`Soft Power: ${gs.soft_power}/100 — derived from relations, tech, approval`}
            >{gs.soft_power}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Dip Cap</span>
            <span className={`stat-value mono ${gs.diplomatic_capital >= 50 ? 'good' : gs.diplomatic_capital >= 25 ? 'warn' : ''}`}
              style={gs.diplomatic_capital === 0 ? { opacity: 0.4 } : {}}
              title={`Diplomatic Capital: ${gs.diplomatic_capital}/100 — derived from deals, leverage, alliances`}
            >{gs.diplomatic_capital}</span>
          </div>
        </>
      )}

      {/* Stage 5: state identity — full width row below the stats */}
      <div className="state-identity-row">
        <span className={`state-identity-regime ${regimeColorClass}`}>{regimeType}</span>
        <span className="state-identity-sep">·</span>
        <span className="state-identity-power">{powerBase}</span>
        {/* fixes_10 Fix 3: Election warning — flag set one turn earlier by backend */}
        {gs.election_warning_shown && !gs.election_fired &&
         gs.current_turn < (gs.election_turn ?? 4) && (
          <span style={{ marginLeft: '0.5rem', color: '#ffb74d', fontWeight: 600, fontSize: '0.72rem' }}>
            | 🗳️ Election Next Turn
          </span>
        )}
        {/* Session 5: NPC-Initiated Contact indicator */}
        {gs.pending_npc_contacts && gs.pending_npc_contacts.length > 0 && (
          <span style={{ marginLeft: '0.5rem', color: '#ff5252', fontWeight: 600, fontSize: '0.72rem', animation: 'pulse 1.5s infinite' }}>
            | ⚡ {gs.pending_npc_contacts.length} INCOMING
          </span>
        )}
      </div>

      {/* Addition 2: Compact relations mini-row — always visible in the sticky bar */}
      <div className="sb-relations-row">
        {relItems.map(({ key, label, val, warn }, i) => (
          <span key={key} className={`sb-rel-item sb-rel-${key}${val < 25 ? ' sb-rel-critical' : val < 45 ? ' sb-rel-low' : ''}`}>
            {i > 0 && <span className="sb-rel-sep">|</span>}
            <span className="sb-rel-label">{label}</span>
            <span className="sb-rel-val">{typeof val === 'number' ? Math.round(val) : (val ?? '—')}</span>
            {warn && <span className="sb-rel-alert">⚠️</span>}
          </span>
        ))}
      </div>

      {/* fixes_11 Fix 10: Renamed to CABINET, always accessible at all game phases */}
      {onShadowCabinet && (
        <button
          className="shadow-cabinet-row-btn"
          onClick={onShadowCabinet}
        >
          <span className="sc-row-icon">🗄️</span>
          <span className="sc-row-label">CABINET</span>
          {gs.personal_wealth > 0 && (
            <span className="sc-row-funds">${gs.personal_wealth.toFixed(1)}B available</span>
          )}
          <span className="sc-row-arrow">›</span>
        </button>
      )}
    </div>
  )
}
