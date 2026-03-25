/**
 * End-of-turn effects panel — structured treasury + state + relations + events.
 * Accepts both structured eotData (preferred) and legacy messages (fallback).
 * Session 10B-EOT: replaces regex-categorised string lists with structured data.
 */
import { useState } from 'react'

/* ── Formatting helpers ──────────────────────────────────────────────────── */
function fmt(n, prefix = '') {
  if (n == null || isNaN(n)) return ''
  const sign = n > 0 ? '+' : ''
  return `${prefix}${sign}${n.toFixed(1)}B`
}

function deltaColor(n) {
  if (n > 0) return '#6fbf73'
  if (n < 0) return '#e57373'
  return 'rgba(255,255,255,0.5)'
}

function deltaArrow(n) {
  if (n > 0) return '↑'
  if (n < 0) return '↓'
  return '—'
}

/* ── Nested accordion (used inside Treasury) ─────────────────────────────── */
function SubSection({ label, total, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="eot-sub">
      <button className="eot-sub-header" onClick={() => setOpen(o => !o)}>
        <span className="eot-sub-chevron">{open ? '▼' : '▶'}</span>
        <span className="eot-sub-label">{label}</span>
        <span className="eot-sub-total" style={{ color: deltaColor(total) }}>
          {fmt(total, '$')}
        </span>
      </button>
      {open && <div className="eot-sub-body">{children}</div>}
    </div>
  )
}

/* ── Top-level collapsible section ───────────────────────────────────────── */
function Section({ icon, title, summary, summaryColor, badge, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="eot-section">
      <button className="eot-section-header" onClick={() => setOpen(o => !o)}>
        <span className="eot-section-icon">{icon}</span>
        <span className="eot-section-title">{title}</span>
        {badge != null && badge > 0 && (
          <span className="eot-section-badge">{badge}</span>
        )}
        <span className="eot-section-summary" style={summaryColor ? { color: summaryColor } : undefined}>
          {summary}
        </span>
        <span className="eot-section-chevron">{open ? '▾' : '▸'}</span>
      </button>
      {open && <div className="eot-section-body eot-structured-body">{children}</div>}
    </div>
  )
}

/* ── Line item row ───────────────────────────────────────────────────────── */
function Row({ label, value, muted = false, indent = false }) {
  return (
    <div className={`eot-row${indent ? ' eot-row--indent' : ''}`}>
      <span className={`eot-row-label${muted ? ' eot-row--muted' : ''}`}>{label}</span>
      <span className="eot-row-value" style={{ color: typeof value === 'number' ? deltaColor(value) : 'rgba(255,255,255,0.7)' }}>
        {typeof value === 'number' ? fmt(value, '$') : value}
      </span>
    </div>
  )
}

/* ── TREASURY section ────────────────────────────────────────────────────── */
function TreasurySection({ treasury }) {
  const { income, costs, deals, pending } = treasury
  const taxBreak = income?.tax_breakdown || {}
  const costBreak = costs?.commitment_breakdown || {}

  return (
    <>
      <SubSection label="INCOME" total={income?.tax_revenue || 0}>
        <Row label="Income tax" value={taxBreak.income || 0} indent />
        <Row label="Corporate tax" value={taxBreak.corporate || 0} indent />
        <Row label="Resource tax" value={taxBreak.resource || 0} indent />
        {taxBreak.infra_bonus > 0 && (
          <Row label={`Infra bonus (${(taxBreak.infra_bonus * 100).toFixed(1)}%)`} value={null} indent muted />
        )}
        {income?.oil_modifier != null && income.oil_modifier !== 0 && (
          <Row label={income.oil_modifier_note || 'Oil price modifier'} value={income.oil_modifier} indent />
        )}
      </SubSection>

      <SubSection label="COSTS" total={(costs?.oil_imports || 0) + (costs?.government || 0) + (costs?.commitments || 0) + (costs?.negotiation || 0)}>
        <Row label="Oil imports" value={costs?.oil_imports || 0} indent />
        <Row label="Government" value={costs?.government || 0} indent />
        <Row label="Commitments" value={costs?.commitments || 0} indent />
        {Object.entries(costBreak).map(([k, v]) =>
          v > 0 ? <Row key={k} label={`  ${k}`} value={-v} indent muted /> : null
        )}
        {(costs?.negotiation || 0) !== 0 && (
          <Row label="Negotiation" value={costs?.negotiation || 0} indent />
        )}
      </SubSection>

      {deals && deals.length > 0 && (
        <SubSection label="DEALS" total={deals.reduce((s, d) => s + (d.gm_consequences?.budget_delta || 0), 0)}>
          {deals.map((d, i) => (
            <Row key={i} label={d.npc_name || d.npc_id || '?'} value={d.gm_consequences?.budget_delta || 0} indent />
          ))}
        </SubSection>
      )}

      {pending && pending.length > 0 && (
        <SubSection label="PENDING" total={pending.reduce((s, p) => s + (p.amount_per_turn || 0), 0)}>
          {pending.map((p, i) => (
            <Row key={i}
              label={`${p.npc_name} (${p.turns_remaining} turns left)`}
              value={p.amount_per_turn || 0} indent />
          ))}
        </SubSection>
      )}
    </>
  )
}

/* ── STATE section ───────────────────────────────────────────────────────── */
function StateSection({ state }) {
  const metrics = [
    { key: 'approval', label: 'Approval', suffix: '%' },
    { key: 'stability', label: 'Stability', suffix: '%' },
    { key: 'military', label: 'Military', suffix: '' },
    { key: 'tech', label: 'Tech', suffix: '' },
    { key: 'education', label: 'Education', suffix: '' },
    { key: 'soft_power', label: 'Soft Power', suffix: '' },
    { key: 'dip_capital', label: 'Dip. Capital', suffix: '' },
  ]

  return (
    <div className="eot-state-table">
      {metrics.map(({ key, label, suffix }) => {
        const m = state[key]
        if (!m) return null
        const showDelta = m.delta != null && m.delta !== 0
        return (
          <div key={key} className="eot-state-row">
            <span className="eot-state-label">{label}</span>
            <span className="eot-state-value">
              {typeof m.value === 'number' ? `${m.value}${suffix}` : m.value}
            </span>
            {showDelta && (
              <span className="eot-state-delta" style={{ color: deltaColor(m.delta) }}>
                {deltaArrow(m.delta)} {m.delta > 0 ? '+' : ''}{typeof m.delta === 'number' ? m.delta.toFixed(1) : m.delta}
              </span>
            )}
            {!showDelta && <span className="eot-state-delta" style={{ color: 'rgba(255,255,255,0.2)' }}>—</span>}
            {m.note && <span className="eot-state-note">{m.note}</span>}
          </div>
        )
      })}
    </div>
  )
}

/* ── RELATIONS section ───────────────────────────────────────────────────── */
function RelationsSection({ relations }) {
  if (!relations || relations.length === 0) return (
    <div className="eot-row eot-row--muted">No relation changes this turn</div>
  )
  return (
    <div className="eot-relations-list">
      {relations.map((r, i) => (
        <div key={i} className="eot-relations-row">
          <span className="eot-relations-arrow" style={{ color: deltaColor(r.delta) }}>
            {deltaArrow(r.delta)}
          </span>
          <span className="eot-relations-name">{r.npc_name}</span>
          <span className="eot-relations-value">{Math.round(r.value)}</span>
          <span className="eot-relations-delta" style={{ color: deltaColor(r.delta) }}>
            {r.delta > 0 ? '+' : ''}{r.delta.toFixed(1)}
          </span>
          {r.note && <span className="eot-relations-note">{r.note}</span>}
        </div>
      ))}
    </div>
  )
}

/* ── Legacy fallback (string-based) ──────────────────────────────────────── */
function isElectionLine(msg) { return /🗳️/.test(msg) }
function isWorldEvent(msg) {
  return /^(🇺🇸🇪🇺|🛢️⚡|🌍|⚡🇺🇸|🛢️💰|⚡🤝|🕵️|🖤|🪧|🏛️)/.test(msg) ||
    /WESTERN BLOC|SHADOW PACT|TOTAL DIPLOMATIC|PROVOCATION|ENERGY CRISIS|COOPERATION|INTELLIGENCE SHARING|protests|observer/.test(msg)
}
function isRegime(msg) {
  return /^(⚠️\s*Regime|✅\s*Regime|🔄\s*Power)/.test(msg) ||
    /Regime shift|regime shift|Power base/.test(msg)
}

function LegacyPanel({ messages }) {
  const worldEvents = []
  const regime = []
  const finances = []
  for (const msg of messages) {
    if (isElectionLine(msg)) continue
    else if (isRegime(msg)) regime.push(msg)
    else if (isWorldEvent(msg)) worldEvents.push(msg)
    else finances.push(msg)
  }

  let financeNet = 0
  for (const msg of finances) {
    const amounts = msg.match(/[+-]?\$[\d.]+B/g)
    if (amounts) {
      for (const amt of amounts) {
        const val = parseFloat(amt.replace('$', '').replace('B', ''))
        if (!isNaN(val)) financeNet += val
      }
    }
  }
  const financeSummary = financeNet !== 0
    ? `${financeNet >= 0 ? '+' : ''}$${financeNet.toFixed(1)}B net`
    : `${finances.length} item${finances.length !== 1 ? 's' : ''}`

  return (
    <>
      {finances.length > 0 && (
        <Section icon="💰" title="FINANCES" summary={financeSummary}
          summaryColor={deltaColor(financeNet)}>
          <ul className="msg-list">{finances.map((m, i) => <li key={i}>{m}</li>)}</ul>
        </Section>
      )}
      {worldEvents.length > 0 && (
        <Section icon="🌍" title="WORLD EVENTS"
          badge={worldEvents.length}
          summary={`${worldEvents.length} event${worldEvents.length !== 1 ? 's' : ''}`}
          defaultOpen>
          <ul className="msg-list">{worldEvents.map((m, i) => <li key={i}>{m}</li>)}</ul>
        </Section>
      )}
      {regime.length > 0 && (
        <Section icon="📊" title="REGIME" summary="shift this turn" defaultOpen>
          <ul className="msg-list">{regime.map((m, i) => <li key={i}>{m}</li>)}</ul>
        </Section>
      )}
    </>
  )
}

/* ── Main component ──────────────────────────────────────────────────────── */
export default function EotPanel({ messages, eotData }) {
  if ((!messages || messages.length === 0) && !eotData) return null

  // Use structured data if available, legacy fallback otherwise
  if (!eotData) {
    return (
      <div className="eot-panel">
        <div className="panel-header">End of Day Summary</div>
        <LegacyPanel messages={messages || []} />
      </div>
    )
  }

  const { treasury, state, relations, world_events } = eotData
  const netBudget = treasury?.net || 0
  const stateDeltas = state ? Object.values(state).filter(m => m && m.delta !== 0).length : 0
  const relCount = relations?.length || 0
  const eventCount = world_events?.length || 0

  return (
    <div className="eot-panel">
      <div className="panel-header">End of Day Summary</div>

      {/* TREASURY */}
      <Section
        icon="💰"
        title="FINANCES"
        summary={fmt(netBudget, '$') + ' net'}
        summaryColor={deltaColor(netBudget)}
      >
        <TreasurySection treasury={treasury} />
      </Section>

      {/* STATE */}
      {state && stateDeltas > 0 && (
        <Section
          icon="📊"
          title="STATE"
          summary={`${stateDeltas} changed`}
        >
          <StateSection state={state} />
        </Section>
      )}

      {/* RELATIONS */}
      {relCount > 0 && (
        <Section
          icon="🤝"
          title="RELATIONS"
          badge={relCount}
          summary={`${relCount} changed`}
        >
          <RelationsSection relations={relations} />
        </Section>
      )}

      {/* WORLD EVENTS */}
      {eventCount > 0 && (
        <Section
          icon="🌍"
          title="WORLD EVENTS"
          badge={eventCount}
          summary={`${eventCount} event${eventCount !== 1 ? 's' : ''}`}
          defaultOpen
        >
          <div className="eot-events-list">
            {world_events.map((evt, i) => (
              <div key={i} className="eot-event-row">
                <span className="eot-event-text">{evt.text}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Legacy fallback only renders when eotData is null — see early return above */}
    </div>
  )
}
