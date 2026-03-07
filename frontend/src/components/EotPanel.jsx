/**
 * End-of-turn effects panel — collapsible sections.
 * Session 2: replaces flat list with category sections.
 * Session 4C: split into FINANCES (collapsed) + WORLD EVENTS (expanded).
 * Election warning line shown as standalone highlight above sections.
 */
import { useState } from 'react'

function isElectionLine(msg) {
  // fixes_8 Fix 5: Election warning lines filtered out of EOT (shown as banner at turn start)
  return /🗳️/.test(msg)
}
function isWorldEvent(msg) {
  // Pressure events, world events, protests, democracy lock, isolation
  return /^(🇺🇸🇪🇺|🛢️⚡|🌍|⚡🇺🇸|🛢️💰|⚡🤝|🕵️|🖤|🪧|🏛️)/.test(msg) ||
    /WESTERN BLOC|SHADOW PACT|TOTAL DIPLOMATIC|PROVOCATION|ENERGY CRISIS|COOPERATION|INTELLIGENCE SHARING|protests|observer/.test(msg)
}
function isRegime(msg) {
  return /^(⚠️\s*Regime|✅\s*Regime|🔄\s*Power)/.test(msg) ||
    /Regime shift|regime shift|Power base/.test(msg)
}

function categorise(messages) {
  const electionLines = []
  const worldEvents = []
  const regime = []
  const finances = []

  for (const msg of messages) {
    if (isElectionLine(msg))       electionLines.push(msg)
    else if (isRegime(msg))        regime.push(msg)
    else if (isWorldEvent(msg))    worldEvents.push(msg)
    else                           finances.push(msg)
  }

  return { electionLines, worldEvents, regime, finances }
}

function Section({ icon, title, badge, summary, items, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  if (!items || items.length === 0) return null

  return (
    <div className="eot-section">
      <button className="eot-section-header" onClick={() => setOpen(o => !o)}>
        <span className="eot-section-icon">{icon}</span>
        <span className="eot-section-title">{title}</span>
        {badge != null && badge > 0 && (
          <span className="eot-section-badge">{badge}</span>
        )}
        <span className="eot-section-summary">{summary}</span>
        <span className="eot-section-chevron">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <ul className="msg-list eot-section-body">
          {items.map((msg, i) => <li key={i}>{msg}</li>)}
        </ul>
      )}
    </div>
  )
}

export default function EotPanel({ messages }) {
  if (!messages || messages.length === 0) return null

  const { electionLines, worldEvents, regime, finances } = categorise(messages)

  // fixes_13 Fix 15: FINANCES header shows true net budget change, not just passive drain
  // Parse all finance lines for $ amounts to compute net
  let financeNet = 0
  for (const msg of finances) {
    // Match patterns like "+$4.2B", "-$1.5B", "$3.0B" in context
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
    <div className="eot-panel">
      <div className="panel-header">End of Turn Effects</div>

      {/* fixes_8 Fix 5: Election warning lines removed from EOT — shown as banner at turn start instead */}

      <Section
        icon="💰"
        title="FINANCES"
        summary={financeSummary}
        items={finances}
        defaultOpen={false}
      />
      {worldEvents.length > 0 && (
        <Section
          icon="🌍"
          title="WORLD EVENTS"
          badge={worldEvents.length}
          summary={`${worldEvents.length} event${worldEvents.length !== 1 ? 's' : ''}`}
          items={worldEvents}
          defaultOpen={true}
        />
      )}
      {regime.length > 0 && (
        <Section
          icon="📊"
          title="REGIME"
          summary="shift this turn"
          items={regime}
          defaultOpen={true}
        />
      )}
    </div>
  )
}
