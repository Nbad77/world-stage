/**
 * AdministrationTab — pure data-display panel for the Cabinet drawer.
 * Seven sections: Cabinet, Government, Regime, Commitments, Wealth, Era, History.
 * Zero Haiku calls.
 */

export default function AdministrationTab({ gs, sessionId }) {
  if (!gs) return null

  const statLabel = (val) => {
    if (val >= 80) return 'High'
    if (val >= 60) return 'Solid'
    if (val >= 40) return 'Moderate'
    return 'Concerning'
  }

  const regimeType = gs.state_identity?.regime_type || 'Managed Democracy'
  const powerBase = gs.state_identity?.power_base || 'Mass-Dependent'

  // ── SECTION 1: CABINET ──────────────────────────────────────────────────
  const advisors = gs.advisors || {}
  const advisorKeys = Object.keys(advisors)

  // ── SECTION 4: COMMITMENTS ──────────────────────────────────────────────
  const installments = gs.active_installments || []
  const promises = (gs.binding_promises || []).filter(p => !p.broken)
  const hasCommitments = installments.length > 0 || promises.length > 0

  // ── SECTION 5: WEALTH ───────────────────────────────────────────────────
  const pw = gs.personal_wealth || 0
  const skimRate = gs.skim_rate || 0

  // ── SECTION 7: HISTORY ──────────────────────────────────────────────────
  const history = gs.action_history || []
  const recentHistory = [...history].reverse().slice(0, 20)

  return (
    <div className="admin-tab">

      {/* SECTION 1 — CABINET */}
      <div className="admin-section">
        <div className="admin-section-header">Your Cabinet</div>
        {advisorKeys.length === 0 ? (
          <div className="admin-stat-note">No advisors retained.</div>
        ) : (
          advisorKeys.map(key => {
            const a = advisors[key]
            return (
              <div key={key} className="admin-cabinet-card">
                <div className="admin-cabinet-icon">{a.icon || '👤'}</div>
                <div className="admin-cabinet-meta">
                  <div className="admin-cabinet-name">{a.name}</div>
                  <div className="admin-cabinet-label">{a.label || a.archetype}</div>
                  <div className="admin-cabinet-stats">
                    Competence: {statLabel(a.competence || 0)} · Loyalty: {statLabel(a.loyalty || 0)} · Since Day {a.hire_day || '?'}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* SECTION 2 — GOVERNMENT AT A GLANCE */}
      <div className="admin-section">
        <div className="admin-section-header">Government</div>

        <StatRow
          label="Stability"
          value={`${gs.stability ?? 0}%`}
          note={stabilityNote(gs)}
        />
        <StatRow
          label="Approval"
          value={`${gs.public_approval ?? 0}%`}
          note={approvalNote(gs.public_approval ?? 0)}
        />
        <StatRow
          label="Military"
          value={gs.military_strength ?? 0}
          note={militaryNote(gs.military_strength ?? 0)}
        />
        <StatRow
          label="Reliability"
          value={Math.round(gs.reliability_score ?? 100)}
          note={reliabilityNote(gs.reliability_score ?? 100)}
        />
        <StatRow
          label="Soft Power"
          value={gs.soft_power ?? 0}
          note={softPowerNote(gs.soft_power ?? 0)}
        />
      </div>

      {/* SECTION 3 — REGIME & POWER BASE */}
      <div className="admin-section">
        <div className="admin-section-header">Regime</div>
        <StatRow label="Regime Type" value={regimeType} />
        <StatRow label="Power Base" value={powerBase} />
        <div className="admin-regime-hint">{regimeHint(regimeType)}</div>
      </div>

      {/* SECTION 4 — ACTIVE COMMITMENTS */}
      <div className="admin-section">
        <div className="admin-section-header">Commitments</div>
        {!hasCommitments ? (
          <div className="admin-stat-note">No active commitments.</div>
        ) : (
          <>
            {installments.map((inst, i) => (
              <div key={`inst-${i}`} className="admin-commitment-item">
                {inst.description || 'Payment'}: ${inst.amount}B × {inst.turns_remaining} turns remaining
                <div className="admin-commitment-meta">To: {(inst.npc || '').toUpperCase()}</div>
              </div>
            ))}
            {promises.map((p, i) => (
              <div key={`prom-${i}`} className="admin-commitment-item">
                Promised {(p.npc || '').toUpperCase()}: {(p.promise_text || '').slice(0, 60)}{(p.promise_text || '').length > 60 ? '...' : ''}
                <div className="admin-commitment-meta">Made Day {p.turn_made ?? '?'}</div>
              </div>
            ))}
          </>
        )}
        <StatRow
          label="Reliability"
          value={`${Math.round(gs.reliability_score ?? 100)}/100`}
          note={
            (gs.binding_promises || []).some(p => p.broken)
              ? 'Affected by broken commitments.'
              : null
          }
        />
      </div>

      {/* SECTION 5 — PERSONAL WEALTH */}
      <div className="admin-section">
        <div className="admin-section-header">Personal Account</div>
        <StatRow label="Personal Wealth" value={`$${(pw).toFixed(1)}B`} />
        <StatRow label="Skim Rate" value={`${(skimRate * 100).toFixed(0)}%`} />
        {pw === 0 && skimRate === 0 ? (
          <div className="admin-wealth-status admin-wealth-status--clean">
            No personal extraction active.
          </div>
        ) : (
          <div className={`admin-wealth-status ${wealthStatusClass(pw)}`}>
            {wealthStatusText(pw)}
          </div>
        )}
      </div>

      {/* SECTION 6 — ERA SUMMARY */}
      <div className="admin-section">
        <div className="admin-section-header">Era {gs.current_era || 1}</div>
        <StatRow
          label="Current Day"
          value={`Day ${gs.current_day || 1} of Era ${gs.current_era || 1}`}
        />
      </div>

      {/* SECTION 7 — HISTORY LOG */}
      <div className="admin-section">
        <div className="admin-section-header">History</div>
        {recentHistory.length === 0 ? (
          <div className="admin-stat-note">No recorded actions.</div>
        ) : (
          <>
            {recentHistory.map((entry, i) => (
              <div key={i} className="admin-history-item">
                <span className="admin-history-turn">Day {entry.turn ?? '?'}</span>
                {entry.type || 'action'}
                {entry.npc ? ` (${entry.npc.toUpperCase()})` : ''}
                {entry.action ? ` — ${entry.action}` : ''}
                {entry.amount ? ` $${entry.amount}B` : ''}
              </div>
            ))}
            <div className="admin-stat-note">Showing last {recentHistory.length} entries.</div>
          </>
        )}
      </div>

    </div>
  )
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function StatRow({ label, value, note }) {
  return (
    <div className="admin-stat-row">
      <div className="admin-stat-label">{label}</div>
      <div className="admin-stat-value">{value}</div>
      {note && <div className="admin-stat-note">{note}</div>}
    </div>
  )
}

function stabilityNote(gs) {
  const s = gs.stability ?? 0
  const leg = gs.legitimacy_stability
  const coe = gs.coercion_stability
  let base
  if (s >= 70) base = 'Stable. No immediate structural risk.'
  else if (s >= 50) base = 'Manageable but under pressure.'
  else if (s >= 30) base = 'Fragile. One crisis away from collapse.'
  else base = 'Critical. Immediate intervention required.'
  if (leg != null && coe != null) {
    base += ` (Legitimacy ${leg}, Coercion ${coe})`
  }
  return base
}

function approvalNote(v) {
  if (v >= 70) return 'Strong popular mandate.'
  if (v >= 50) return 'Adequate. Watch for erosion.'
  if (v >= 30) return 'Weak. Policy changes needed.'
  return 'Dangerous. Legitimacy at risk.'
}

function militaryNote(v) {
  if (v >= 70) return 'Strong deterrent capability.'
  if (v >= 50) return 'Functional but not dominant.'
  return 'Limited. Vulnerable to pressure.'
}

function reliabilityNote(v) {
  if (v >= 80) return 'Strong track record. NPCs extend trust.'
  if (v >= 60) return 'Acceptable. Room to improve.'
  return 'Damaged. Deal terms are suffering.'
}

function softPowerNote(v) {
  if (v >= 60) return 'Respected internationally.'
  if (v >= 40) return 'Moderate standing.'
  return 'Weak. Limited diplomatic leverage.'
}

function regimeHint(regime) {
  switch (regime) {
    case 'Managed Democracy':
      return 'Legitimacy requires popular support. Suppression carries electoral cost.'
    case 'Soft Authoritarianism':
      return 'The facade holds — for now. Watch the institutions.'
    case 'Patronage State':
      return 'Loyalty is purchased. Price rises over time.'
    case 'Kleptocracy':
      return 'The system serves the system. Exposure is the only real risk.'
    case 'Totalitarian Regime':
      return 'Total control. Total fragility.'
    default:
      return ''
  }
}

function wealthStatusClass(pw) {
  if (pw < 8) return 'admin-wealth-status--clean'
  if (pw < 20) return 'admin-wealth-status--flagged'
  return 'admin-wealth-status--exposed'
}

function wealthStatusText(pw) {
  if (pw < 8) return 'Below CIA monitoring threshold.'
  if (pw < 20) return 'CIA has flagged unusual transfers.'
  if (pw < 35) return 'Under active CIA scrutiny.'
  return 'Full CIA exposure. Leverage active.'
}
