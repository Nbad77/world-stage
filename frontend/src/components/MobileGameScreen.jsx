/**
 * MobileGameScreen — 5-tab bottom-nav layout for narrow viewports (<768px).
 * Mounted by GameScreen when useIsMobile() returns true.
 * Self-fetches morning briefing / advisor pool / daily events via api.*
 * since BriefingScreen never mounts on mobile.
 *
 * Sovereignty: this component receives gs + handlers from GameScreen and
 * does not modify any backend or desktop state shape.
 */
import { useState, useEffect, useRef } from 'react'
import { api } from '../api'
import MobileNpcDrawer from './MobileNpcDrawer'
import MobileEotScreen from './MobileEotScreen'

/* ── NPC metadata (same character/relations key mapping as desktop) ─────── */
const NPC_INFO_MOBILE = {
  bill:   { name: 'Bill Hartwell',  country: 'United States', avatar: 'BH', avatarBg: '#1a2030', avatarText: '#6090c8', relKey: 'usa' },
  eu:     { name: 'Marsha',         country: 'European Union', avatar: 'M', avatarBg: '#101828', avatarText: '#5080c0', relKey: 'eu' },
  wei:    { name: 'Wei Jianming',   country: 'China',          avatar: 'WJ', avatarBg: '#200c0c', avatarText: '#c85050', relKey: 'china' },
  volkov: { name: 'Nikolai Volkov', country: 'Russia',         avatar: 'NV', avatarBg: '#1a0c1e', avatarText: '#9060a8', relKey: 'russia' },
  sadam:  { name: 'Sadam',          country: 'Arabia',         avatar: 'S',  avatarBg: '#28200e', avatarText: '#c09840', relKey: 'arabia' },
  dprg:   { name: 'Ji-won Ryang',   country: 'DPRO',           avatar: 'JR', avatarBg: '#200c0c', avatarText: '#b84040', relKey: 'dprg' },
}
const NPC_ORDER = ['bill', 'eu', 'wei', 'volkov', 'sadam', 'dprg']

const TECH_TIER_NAMES = ['Pre-Industrial', 'Emerging', 'Functional', 'Strategic', 'Advanced', 'Frontier']
function techTier(t) {
  const v = t || 0
  if (v >= 100) return 5
  if (v >= 75) return 4
  if (v >= 50) return 3
  if (v >= 25) return 2
  if (v >= 10) return 1
  return 0
}

const EDU_TIER_NAMES = ['Basic', 'Modern', 'Advanced', 'Excellent']
function eduLabel(level) {
  const i = Math.max(0, Math.min(3, Math.round(level || 0)))
  return EDU_TIER_NAMES[i]
}

const ROLE_AVATAR_CLASS = {
  diplomat:   'av-diplomat',
  technocrat: 'av-tech',
  finance:    'av-finance',
  general:    'av-general',
  military:   'av-general',
  spy_chief:  'av-spy',
  spy:        'av-spy',
}
function avatarClass(role) { return ROLE_AVATAR_CLASS[role] || 'av-default' }

/* Standing label/color (mirrors desktop NpcCard.standingLabel) */
function standingFor(npcId, gs) {
  if (gs?.ambassador_recalled?.[npcId]) return { label: 'RECALLED', color: '#de5858', bold: true }
  const s = gs?.diplomatic_standing?.[npcId] ?? 50
  if (s >= 75) return { label: 'RESPECTED',   color: '#7ed458' }
  if (s >= 50) return { label: 'ESTABLISHED', color: '#6aaade' }
  if (s >= 25) return { label: 'STRAINED',    color: '#e0b83a' }
  if (s >= 10) return { label: 'DAMAGED',     color: '#ff8a65' }
  return                  { label: 'CRITICAL',    color: '#de5858' }
}

function eventBadgeClass(urgency) {
  const u = (urgency || '').toLowerCase()
  if (u === 'urgent' || u === 'high') return 'urgent'
  if (u === 'positive' || u === 'good') return 'positive'
  return 'moderate'
}

function eventInitials(text) {
  if (!text) return ''
  return text.slice(0, 120) + (text.length > 120 ? '…' : '')
}

/* ── Header ─────────────────────────────────────────────────────────────── */
function MobileHeader({ gs, onEndDay, endDayDisabled }) {
  const regime = gs?.state_identity?.regime_type || 'Managed Democracy'
  const era = gs?.current_era ?? 1
  const day = gs?.current_day ?? gs?.current_turn ?? 1
  const treasury = gs?.budget ?? 0
  return (
    <header className="mobile-header">
      <div className="mobile-header-meta">
        <div className="mobile-header-regime">{regime}</div>
        <div className="mobile-header-day">ERA {era} · DAY {day}</div>
      </div>
      <span className="mobile-treasury-chip">${treasury.toFixed(1)}B</span>
      <button
        className="mobile-end-day-btn"
        onClick={onEndDay}
        disabled={endDayDisabled}
        title={endDayDisabled ? 'Resolve required events first' : 'End the current day'}
      >
        END DAY
      </button>
    </header>
  )
}

/* ── Stats strip ────────────────────────────────────────────────────────── */
function MobileStatsStrip({ gs }) {
  const stab = Math.round(gs?.stability ?? 0)
  const appr = Math.round(gs?.public_approval ?? 0)
  const mil  = gs?.military_tier ?? 1
  const oil  = Math.round(gs?.oil_price ?? 0)
  const tt   = techTier(gs?.tech_level)
  const edu  = eduLabel(gs?.education_level)
  const eduRaw = gs?.education_level ?? 0
  const eduRed = eduRaw < 2.0
  return (
    <div className="mobile-stats-strip">
      <span className="mobile-stat-pill"><span className="mobile-stat-label">STAB</span><span className="mobile-stat-value">{stab}%</span></span>
      <span className="mobile-stat-pill"><span className="mobile-stat-label">APPR</span><span className="mobile-stat-value">{appr}%</span></span>
      <span className="mobile-stat-pill"><span className="mobile-stat-label">MIL</span><span className="mobile-stat-value" style={{ color: '#6aaade' }}>×{mil}</span></span>
      <span className="mobile-stat-pill"><span className="mobile-stat-label">OIL</span><span className="mobile-stat-value">${oil}</span></span>
      <span className="mobile-stat-pill"><span className="mobile-stat-label">TECH</span><span className="mobile-stat-value">{TECH_TIER_NAMES[tt]}</span></span>
      <span className="mobile-stat-pill"><span className="mobile-stat-label">EDUC</span><span className="mobile-stat-value" style={{ color: eduRed ? '#de5858' : undefined }}>{edu}</span></span>
    </div>
  )
}

/* ── Bottom nav ─────────────────────────────────────────────────────────── */
const NAV_TABS = [
  { id: 'brief',   icon: '⬡', label: 'Brief' },
  { id: 'events',  icon: '◈', label: 'Events' },
  { id: 'diplo',   icon: '◎', label: 'Diplo' },
  { id: 'state',   icon: '▦', label: 'State' },
  { id: 'cabinet', icon: '≡', label: 'Cabinet' },
]
function MobileBottomNav({ active, onChange }) {
  return (
    <nav className="mobile-nav">
      {NAV_TABS.map(t => (
        <button
          key={t.id}
          className={`mobile-nav-tab ${active === t.id ? 'active' : ''}`}
          onClick={() => onChange(t.id)}
        >
          <span className="mobile-nav-icon">{t.icon}</span>
          <span className="mobile-nav-label">{t.label}</span>
        </button>
      ))}
    </nav>
  )
}

/* ── Brief tab ──────────────────────────────────────────────────────────── */
function BriefTab({ chiefOfStaff, advisorBriefings, advisorPool, expandedId, setExpandedId, onDismiss, gs }) {
  const hiredArchetypes = new Set((advisorBriefings || []).map(a => a.role))
  const poolFiltered = (advisorPool || []).filter(p => !hiredArchetypes.has(p.archetype))

  return (
    <>
      {/* Mike Sorel card */}
      <div className="mobile-card chief">
        <div className="mobile-card-row">
          <div className="mobile-avatar av-chief">MS</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="mobile-card-name purple">Mikhail &lsquo;Mike&rsquo; Sorel</div>
            <div className="mobile-card-role">Chief of Staff · Always Present</div>
          </div>
        </div>
        <div className="mobile-card-body italic">
          {chiefOfStaff?.briefing_text || 'Preparing morning briefing…'}
        </div>
      </div>

      <div className="mobile-section-header">Advisory Council</div>
      {(advisorBriefings || []).length === 0 && (
        <div className="mobile-empty">No advisors assigned yet.</div>
      )}
      {(advisorBriefings || []).map(a => {
        const isExpanded = expandedId === a.role
        const advData = (gs?.advisors || {})[a.role]
        const isAssigned = !!advData
        return (
          <div
            key={a.role}
            className="mobile-card advisor"
            onClick={() => setExpandedId(isExpanded ? null : a.role)}
          >
            <div className="mobile-card-row">
              <div className={`mobile-avatar ${avatarClass(a.role)}`}>{(a.name || '?').split(' ').map(s => s[0]).join('').slice(0, 2).toUpperCase()}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="mobile-card-name">{a.name}</div>
                <div className="mobile-card-role">{a.label}</div>
              </div>
              {isAssigned && <span className="mobile-badge-assigned">ASSIGNED</span>}
              <span className="mobile-card-chevron">{isExpanded ? '▾' : '›'}</span>
            </div>
            {isExpanded && (
              <>
                <div className="mobile-card-body">{a.text}</div>
                <button
                  className="mobile-btn-dismiss"
                  onClick={(e) => { e.stopPropagation(); onDismiss(a.role) }}
                >DISMISS</button>
              </>
            )}
          </div>
        )
      })}

      <div className="mobile-section-header">Available to Hire</div>
      {poolFiltered.length === 0 && (
        <div className="mobile-empty">No advisors available in pool.</div>
      )}
      {poolFiltered.map(p => (
        <div key={p.archetype} className="mobile-card advisor pool">
          <div className="mobile-card-row">
            <div className={`mobile-avatar ${avatarClass(p.archetype)}`}>{(p.name || '?').split(' ').map(s => s[0]).join('').slice(0, 2).toUpperCase()}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="mobile-card-name">{p.name}</div>
              <div className="mobile-card-role">{p.label || p.archetype}</div>
            </div>
            {p.locked && <span className="mobile-badge-locked">LOCKED</span>}
          </div>
        </div>
      ))}
    </>
  )
}

/* ── Events tab ─────────────────────────────────────────────────────────── */
function EventsTab({ dailyEvents, dayStatus, currentDay, expandedId, setExpandedId, onResolve }) {
  const required = dayStatus?.events_required ?? 3
  const resolved = dayStatus?.events_resolved ?? 0
  return (
    <>
      <div className="mobile-events-counter">
        Events Reviewed&nbsp;&nbsp;<strong>{resolved} / {required}</strong>&nbsp;required
      </div>
      {currentDay < 5 && (
        <div className="mobile-declaration-note">Declarations unlock on Day 5</div>
      )}
      {(!dailyEvents || dailyEvents.length === 0) && (
        <div className="mobile-empty">No events generated yet.</div>
      )}
      {(dailyEvents || []).map(evt => {
        const isExpanded = expandedId === evt.id
        const isResolved = !!evt.resolved
        const choices = evt.choices || evt.options || []
        return (
          <div
            key={evt.id}
            className="mobile-card mobile-event-card"
            onClick={() => setExpandedId(isExpanded ? null : evt.id)}
          >
            <div className="mobile-card-row" style={{ justifyContent: 'space-between' }}>
              <span className={`mobile-event-badge ${eventBadgeClass(evt.urgency)}`}>
                {(evt.urgency || 'MODERATE').toUpperCase()}
              </span>
              {evt.npc_id && (
                <span className="mobile-event-npc-tag">{evt.npc_id}</span>
              )}
            </div>
            <div className="mobile-event-title">{evt.title || evt.headline || 'Event'}</div>
            <div className="mobile-event-preview">
              {isExpanded ? (evt.text || evt.body || '') : eventInitials(evt.text || evt.body || '')}
            </div>
            {isExpanded && (
              <div className="mobile-event-choices" onClick={e => e.stopPropagation()}>
                {choices.length === 0 && !isResolved && (
                  <div className="mobile-empty">No choices available.</div>
                )}
                {choices.map((c, i) => {
                  const text = typeof c === 'string' ? c : (c?.text || c?.label || `Option ${String.fromCharCode(65 + i)}`)
                  const chosen = isResolved && evt.chosen_index === i
                  const cls = isResolved
                    ? `mobile-event-choice ${chosen ? 'chosen' : 'chosen'}`
                    : `mobile-event-choice ${i === 0 ? 'first' : ''}`
                  return (
                    <button
                      key={i}
                      className={cls}
                      disabled={isResolved}
                      onClick={() => !isResolved && onResolve(evt.id, i)}
                    >
                      {String.fromCharCode(65 + i)}. {text}
                      {chosen && ' ✓'}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </>
  )
}

/* ── Diplo tab ──────────────────────────────────────────────────────────── */
function DiploTab({ gs, onOpenDrawer }) {
  return (
    <>
      <div className="mobile-section-header">NPC Contacts</div>
      {NPC_ORDER.map(npcId => {
        const meta = NPC_INFO_MOBILE[npcId]
        const rel = Math.round((gs?.relations || {})[meta.relKey] ?? 50)
        const standing = standingFor(npcId, gs)
        const recalled = !!(gs?.ambassador_recalled || {})[npcId]
        return (
          <div
            key={npcId}
            className="mobile-card mobile-npc-card"
            onClick={() => onOpenDrawer(npcId)}
          >
            <div className="mobile-card-row">
              <div
                className="mobile-avatar"
                style={{ background: meta.avatarBg, color: meta.avatarText }}
              >{meta.avatar}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="mobile-npc-name">{meta.name}</div>
                <div className="mobile-npc-country">{meta.country}</div>
              </div>
              <div className="mobile-npc-relation">
                <div>{rel}</div>
                <div className="mobile-npc-standing" style={{ color: standing.color, fontWeight: standing.bold ? 800 : 700 }}>
                  {standing.label}
                </div>
              </div>
            </div>
            {recalled && (
              <div className="mobile-npc-recalled-banner">AMBASSADOR RECALLED</div>
            )}
          </div>
        )
      })}
    </>
  )
}

/* ── State tab ──────────────────────────────────────────────────────────── */
function PowerBaseSlider({ value }) {
  // value in {Mass, Mixed, Elite}-ish — derive from gs.state_identity.power_base
  const v = (value || '').toLowerCase()
  let pct = 50
  if (v.includes('mass')) pct = 15
  else if (v.includes('elite')) pct = 85
  else if (v.includes('mixed')) pct = 50
  return (
    <div className="mobile-power-base">
      <div className="mobile-power-track">
        <div className="mobile-power-knob" style={{ left: `${pct}%` }} />
      </div>
      <div className="mobile-power-labels">
        <span>Mass</span><span>Mixed</span><span>Elite</span>
      </div>
    </div>
  )
}

function Bar({ label, value, max = 100, fillClass, indent }) {
  const pct = Math.max(0, Math.min(100, ((value || 0) / max) * 100))
  return (
    <div className="mobile-bar-row">
      <div className={`mobile-bar-label ${indent ? 'indent' : ''}`}>
        <span>{label}</span>
        <span className="mobile-bar-value">{Math.round(value || 0)}{max === 100 ? '%' : ''}</span>
      </div>
      <div className="mobile-bar-track">
        <div className={`mobile-bar-fill ${fillClass || ''}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function StateTab({ gs, subTab, setSubTab, onShadowCabinet, onHistorian, historianLoading, onBiography }) {
  return (
    <>
      <div className="mobile-subtabs">
        {[['national', 'National'], ['domestic', 'Domestic'], ['history', 'History']].map(([id, label]) => (
          <button
            key={id}
            className={`mobile-subtab ${subTab === id ? 'active' : ''}`}
            onClick={() => setSubTab(id)}
          >{label}</button>
        ))}
      </div>

      {subTab === 'national' && (
        <>
          <div className="mobile-section-header">Financial</div>
          <div className="mobile-card">
            <div className="mobile-kv-row"><span className="mobile-kv-label">Treasury</span><span className="mobile-kv-value">${(gs?.budget ?? 0).toFixed(1)}B</span></div>
            <div className="mobile-kv-row"><span className="mobile-kv-label">Oil Price</span><span className="mobile-kv-value">${Math.round(gs?.oil_price ?? 0)}/bbl</span></div>
          </div>

          <div className="mobile-section-header">Capability</div>
          <div className="mobile-card">
            <div className="mobile-kv-row">
              <span className="mobile-kv-label">Military</span>
              <span className="mobile-kv-value">×{gs?.military_tier ?? 1} · Tier {gs?.military_tier ?? 1}</span>
            </div>
            <div className="mobile-kv-row">
              <span className="mobile-kv-label">Tech Level</span>
              <span className="mobile-kv-value">{TECH_TIER_NAMES[techTier(gs?.tech_level)]}</span>
            </div>
            <div className="mobile-kv-row">
              <span className="mobile-kv-label">Education</span>
              <span className="mobile-kv-value">Tier {gs?.education_level ?? 0} · {eduLabel(gs?.education_level)}</span>
            </div>
            <div className="mobile-kv-row">
              <span className="mobile-kv-label">Intel</span>
              <span className="mobile-kv-value">Tier {gs?.intelligence_tier ?? 0}</span>
            </div>
          </div>

          <div className="mobile-section-header">Power Base</div>
          <div className="mobile-card">
            <PowerBaseSlider value={gs?.state_identity?.power_base} />
          </div>

          <button className="mobile-action-btn" onClick={onHistorian} disabled={historianLoading}>
            {historianLoading ? "Consulting historian…" : "Historian's Assessment"}
          </button>
          <button className="mobile-action-btn" onClick={onBiography}>
            Political Biography
          </button>
          {onShadowCabinet && (
            <button className="mobile-action-btn" onClick={onShadowCabinet}>
              Open Shadow Cabinet
            </button>
          )}
        </>
      )}

      {subTab === 'domestic' && (
        <>
          <div className="mobile-section-header">Stability</div>
          <div className="mobile-card">
            <Bar label="Overall" value={gs?.stability ?? 0} />
            <Bar label="Legitimacy" value={gs?.legitimacy_stability ?? 0} fillClass="legitimacy" indent />
            <Bar label="Coercion" value={gs?.coercion_stability ?? 0} fillClass="coercion" indent />
          </div>

          <div className="mobile-section-header">Approval</div>
          <div className="mobile-card">
            <Bar label="Public approval" value={gs?.public_approval ?? 0} fillClass="approval" />
          </div>

          <div className="mobile-section-header">Budget Allocation</div>
          <div className="mobile-card">
            {Object.entries(gs?.cabinet_axes || {}).map(([axis, val]) => (
              <div key={axis} className="mobile-bar-row">
                <div className="mobile-bar-label">
                  <span>{axis.replace(/_/g, ' ')}</span>
                  <span className="mobile-bar-value">Tier {val}</span>
                </div>
                <div className="mobile-bar-track">
                  <div className="mobile-bar-fill" style={{ width: `${(val || 0) * 10}%` }} />
                </div>
              </div>
            ))}
          </div>

          {gs?.state_identity?.regime_type && (
            <div className="mobile-regime-hint">
              {gs.state_identity.regime_type} · {gs.state_identity.power_base}
            </div>
          )}
        </>
      )}

      {subTab === 'history' && (
        <>
          {(!gs?.action_history || gs.action_history.length === 0) ? (
            <div className="mobile-empty">No actions recorded yet.</div>
          ) : (
            <div className="mobile-card">
              {[...(gs.action_history || [])].reverse().slice(0, 20).map((entry, i) => {
                const day = entry.day || entry.turn || ''
                const text = entry.description || entry.text || entry.summary || JSON.stringify(entry)
                return (
                  <div key={i} className="mobile-history-row">
                    {day !== '' && <span className="mobile-history-day">D{day}</span>}
                    <span>{text}</span>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}
    </>
  )
}

/* ── Cabinet tab ────────────────────────────────────────────────────────── */
function CabinetTab({ gs, advisorBriefings, subTab, setSubTab, currentDay }) {
  const advisors = gs?.advisors || {}
  const installments = gs?.active_installments || []

  return (
    <>
      <div className="mobile-subtabs">
        {[['roster', 'Roster'], ['axes', 'Axes'], ['actions', 'Actions']].map(([id, label]) => (
          <button
            key={id}
            className={`mobile-subtab ${subTab === id ? 'active' : ''}`}
            onClick={() => setSubTab(id)}
          >{label}</button>
        ))}
      </div>

      {subTab === 'roster' && (
        <>
          <div className="mobile-section-header">Cabinet</div>
          <div className="mobile-card">
            <div className="mobile-card-row">
              <div className="mobile-avatar av-chief">MS</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="mobile-card-name purple">Mikhail Sorel</div>
                <div className="mobile-card-role">Chief of Staff</div>
              </div>
            </div>
          </div>
          {Object.entries(advisors).map(([role, data]) => (
            <div key={role} className="mobile-card">
              <div className="mobile-card-row">
                <div className={`mobile-avatar ${avatarClass(role)}`}>
                  {(data?.name || role || '?').split(' ').map(s => s[0]).join('').slice(0, 2).toUpperCase()}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="mobile-card-name">{data?.name || role}</div>
                  <div className="mobile-card-role">
                    {role.replace(/_/g, ' ')}
                    {data?.hire_day != null && ` · Hired Day ${data.hire_day}`}
                  </div>
                </div>
              </div>
            </div>
          ))}

          <div className="mobile-section-header">Government</div>
          <div className="mobile-card">
            <div className="mobile-kv-row"><span className="mobile-kv-label">Regime</span><span className="mobile-kv-value">{gs?.state_identity?.regime_type || '—'}</span></div>
            <div className="mobile-kv-row"><span className="mobile-kv-label">Power Base</span><span className="mobile-kv-value">{gs?.state_identity?.power_base || '—'}</span></div>
            <div className="mobile-kv-row"><span className="mobile-kv-label">Reliability</span><span className="mobile-kv-value">{Math.round(gs?.reliability_score ?? 100)}</span></div>
            <div className="mobile-kv-row"><span className="mobile-kv-label">Soft Power</span><span className="mobile-kv-value">{gs?.soft_power ?? 0}</span></div>
          </div>

          <div className="mobile-section-header">Personal Account</div>
          <div className="mobile-card">
            <div className="mobile-kv-row"><span className="mobile-kv-label">Personal Wealth</span><span className="mobile-kv-value">${(gs?.personal_wealth ?? 0).toFixed(2)}B</span></div>
            <div className="mobile-kv-row"><span className="mobile-kv-label">Skim Rate</span><span className="mobile-kv-value">{Math.round((gs?.skim_rate ?? 0) * 100)}%</span></div>
          </div>

          <div className="mobile-section-header">Active Commitments</div>
          {installments.length === 0 ? (
            <div className="mobile-empty">No active deals or installments.</div>
          ) : (
            <div className="mobile-card">
              {installments.map((it, i) => (
                <div key={i} className="mobile-kv-row">
                  <span className="mobile-kv-label">
                    {it.npc || it.npc_id || '?'} · {it.description || ''}
                  </span>
                  <span className="mobile-kv-value">
                    ${(it.amount ?? it.amount_per_turn ?? 0).toFixed(1)}B
                    {it.turns_remaining != null && ` · ${it.turns_remaining}t`}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {subTab === 'axes' && (
        <>
          {Object.entries(gs?.cabinet_axes || {}).map(([axis, tier]) => {
            const locked = (tier || 0) === 0
            return (
              <div key={axis} className={`mobile-card mobile-axis-row ${locked ? 'locked' : ''}`}>
                <div className="mobile-axis-head">
                  <span className="mobile-axis-name">{axis.replace(/_/g, ' ')}</span>
                  <span className="mobile-axis-tier">Tier {tier} / 10</span>
                </div>
                <div className="mobile-bar-track">
                  <div className="mobile-bar-fill" style={{ width: `${(tier || 0) * 10}%` }} />
                </div>
              </div>
            )
          })}
          {Object.keys(gs?.cabinet_axes || {}).length === 0 && (
            <div className="mobile-empty">No cabinet axes configured.</div>
          )}
        </>
      )}

      {subTab === 'actions' && (
        <>
          {currentDay < 5 ? (
            <div className="mobile-declaration-note">Declarations unlock on Day 5.</div>
          ) : (
            <div className="mobile-card">
              <div className="mobile-card-body">
                Declaration compose (placeholder for future session).
              </div>
            </div>
          )}
        </>
      )}
    </>
  )
}

/* ── Main component ─────────────────────────────────────────────────────── */
export default function MobileGameScreen(props) {
  const {
    gs, sessionId, setGs, phase, ending,
    onEndDay, onContinue,
    onContact, onContactRequest, onBackchannel, onGetIntel, onRequestBriefing,
    contactLoading, contactResults, intelLoading, intelResults, briefingLoading,
    backchannelDisabled, contactsDisabled,
    onShadowCabinet, onHistorian, historianLoading, onBiography,
    eotData, eotMessages,
  } = props

  const [activeTab, setActiveTab] = useState('brief')
  const [stateSubTab, setStateSubTab] = useState('national')
  const [cabinetSubTab, setCabinetSubTab] = useState('roster')
  const [expandedAdvisorId, setExpandedAdvisorId] = useState(null)
  const [expandedEventId, setExpandedEventId] = useState(null)
  const [activeNpcDrawer, setActiveNpcDrawer] = useState(null)

  const [chiefOfStaff, setChiefOfStaff] = useState(null)
  const [advisorBriefings, setAdvisorBriefings] = useState([])
  const [advisorPool, setAdvisorPool] = useState([])
  const [dailyEvents, setDailyEvents] = useState([])
  const [dayStatus, setDayStatus] = useState({ events_resolved: 0, events_required: 3 })

  const lastFetchedDay = useRef(-1)
  const currentDay = gs?.current_day ?? gs?.current_turn ?? 1

  // Fetch morning briefing + daily events + advisor pool on day change while in dialogue phase
  useEffect(() => {
    if (!sessionId) return
    if (phase !== 'dialogue') return
    if (lastFetchedDay.current === currentDay) return
    lastFetchedDay.current = currentDay

    let cancelled = false
    ;(async () => {
      try {
        const morning = await api.briefingMorning(sessionId)
        if (!cancelled && morning) {
          setChiefOfStaff(morning.chief_of_staff || null)
          setAdvisorBriefings(morning.advisor_briefings || [])
        }
      } catch (e) { console.error('[MOBILE] briefingMorning failed:', e) }

      try {
        const status = await api.briefingDayStatus(sessionId)
        if (!cancelled && status) {
          setDayStatus({
            events_resolved: status.events_resolved ?? 0,
            events_required: status.events_required ?? 3,
          })
        }
        const gen = await api.briefingGenerateEvents(sessionId)
        if (!cancelled && gen?.events) setDailyEvents(gen.events)
      } catch (e) { console.error('[MOBILE] events fetch failed:', e) }

      try {
        const pool = await api.getAdvisorPool(sessionId)
        if (!cancelled && pool) setAdvisorPool(pool.pool || pool.advisors || [])
      } catch (e) { console.error('[MOBILE] advisor pool failed:', e) }
    })()

    return () => { cancelled = true }
  }, [sessionId, phase, currentDay])

  async function handleResolveEvent(eventId, choiceIndex) {
    try {
      await api.briefingResolveEvent(sessionId, eventId, choiceIndex)
      setDailyEvents(evts => evts.map(e => e.id === eventId
        ? { ...e, resolved: true, chosen_index: choiceIndex }
        : e))
      setDayStatus(d => ({ ...d, events_resolved: (d.events_resolved || 0) + 1 }))
      const fresh = await api.getGame(sessionId)
      if (fresh?.game_state) setGs(fresh.game_state)
    } catch (err) {
      console.error('[MOBILE] resolve event failed:', err)
    }
  }

  async function handleDismissAdvisor(advisorKey) {
    try {
      await api.dismissAdvisor(sessionId, advisorKey)
      setAdvisorBriefings(list => list.filter(a => a.role !== advisorKey))
      const fresh = await api.getGame(sessionId)
      if (fresh?.game_state) setGs(fresh.game_state)
      lastFetchedDay.current = -1
    } catch (err) {
      console.error('[MOBILE] dismiss advisor failed:', err)
    }
  }

  function openNpcDrawer(npcId) {
    console.log('[MOBILE_DRAWER] open=', true, 'npc=', npcId)
    setActiveNpcDrawer(npcId)
  }
  function closeNpcDrawer() {
    console.log('[MOBILE_DRAWER] open=', false, 'npc=', activeNpcDrawer)
    setActiveNpcDrawer(null)
  }

  const showEot = phase === 'eot'
  const endDayDisabled = (dayStatus.events_resolved ?? 0) < (dayStatus.events_required ?? 3)
  const drawerNpc = activeNpcDrawer
  const drawerMeta = drawerNpc ? NPC_INFO_MOBILE[drawerNpc] : null

  return (
    <div className="mobile-root">
      <MobileHeader gs={gs} onEndDay={onEndDay} endDayDisabled={endDayDisabled} />
      <MobileStatsStrip gs={gs} />

      <main className="mobile-content">
        {activeTab === 'brief' && (
          <BriefTab
            chiefOfStaff={chiefOfStaff}
            advisorBriefings={advisorBriefings}
            advisorPool={advisorPool}
            expandedId={expandedAdvisorId}
            setExpandedId={setExpandedAdvisorId}
            onDismiss={handleDismissAdvisor}
            gs={gs}
          />
        )}
        {activeTab === 'events' && (
          <EventsTab
            dailyEvents={dailyEvents}
            dayStatus={dayStatus}
            currentDay={currentDay}
            expandedId={expandedEventId}
            setExpandedId={setExpandedEventId}
            onResolve={handleResolveEvent}
          />
        )}
        {activeTab === 'diplo' && (
          <DiploTab gs={gs} onOpenDrawer={openNpcDrawer} />
        )}
        {activeTab === 'state' && (
          <StateTab
            gs={gs}
            subTab={stateSubTab}
            setSubTab={setStateSubTab}
            onShadowCabinet={onShadowCabinet}
            onHistorian={onHistorian}
            historianLoading={historianLoading}
            onBiography={onBiography}
          />
        )}
        {activeTab === 'cabinet' && (
          <CabinetTab
            gs={gs}
            advisorBriefings={advisorBriefings}
            subTab={cabinetSubTab}
            setSubTab={setCabinetSubTab}
            currentDay={currentDay}
          />
        )}
      </main>

      <MobileBottomNav active={activeTab} onChange={setActiveTab} />

      {/* Overlays */}
      {showEot && (
        <MobileEotScreen
          gs={gs}
          eotData={eotData}
          eotMessages={eotMessages}
          onContinue={onContinue}
          ending={ending}
        />
      )}
      {drawerNpc && drawerMeta && (
        <MobileNpcDrawer
          npcId={drawerNpc}
          meta={drawerMeta}
          gs={gs}
          onClose={closeNpcDrawer}
          onContact={onContact}
          onContactRequest={onContactRequest}
          onBackchannel={onBackchannel}
          onGetIntel={onGetIntel}
          onRequestBriefing={onRequestBriefing}
          contactLoading={contactLoading}
          contactResult={contactResults?.[drawerMeta.relKey]}
          intelLoading={intelLoading}
          intelResult={intelResults?.[drawerMeta.relKey]}
          briefingLoading={briefingLoading}
          contactsDisabled={contactsDisabled}
          backchannelDisabled={backchannelDisabled}
        />
      )}
    </div>
  )
}
