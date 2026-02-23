/**
 * End-of-turn effects panel — collapsible sections.
 * Session 2: replaces flat list with category sections.
 * Categories parsed from emoji prefixes in message strings.
 */
import { useState } from 'react'

function isFinance(msg) {
  return /^[💰🏛️⛽📉📈💸]/.test(msg) && !/^[🛢️🇺🇸🇪🇺]/.test(msg)
}
function isOil(msg) {
  return /^🛢️/.test(msg)
}
function isWarning(msg) {
  return /^(💔|⚠️|🇺🇸 USA SANCTION|🛢️ ARABIA EMBARGO|🇪🇺 EU TRADE)/.test(msg)
}
function isRegime(msg) {
  return /^(👁️|🔒|📊 Regime|Regime shifted|regime hardened|power base)/.test(msg) ||
    /shifted to|Power base/.test(msg)
}

function categorise(messages) {
  const finances = []
  const oil = []
  const warnings = []
  const regime = []
  const other = []

  for (const msg of messages) {
    if (isWarning(msg))      warnings.push(msg)
    else if (isOil(msg))     oil.push(msg)
    else if (isRegime(msg))  regime.push(msg)
    else if (isFinance(msg)) finances.push(msg)
    else                     other.push(msg)
  }

  return { finances, oil, warnings, regime, other }
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

  const { finances, oil, warnings, regime, other } = categorise(messages)

  // Net finance change — extract the last budget line for summary
  const financeAll = [...finances, ...other]
  const drainLine = financeAll.find(m => /Passive drain|Net drain/.test(m))
  const financeSummary = drainLine
    ? drainLine.replace(/^💰\s*/, '').replace(/Passive drain this turn:\s*/i, '').trim()
    : `${financeAll.length} item${financeAll.length !== 1 ? 's' : ''}`

  // Oil summary — grab price value
  const oilLine = oil.find(m => /\$\d+\/bbl/.test(m)) || oil[0] || ''
  const oilMatch = oilLine.match(/\$(\d+)\/bbl/)
  const oilSummary = oilMatch ? `$${oilMatch[1]}/bbl` : `${oil.length} item${oil.length !== 1 ? 's' : ''}`

  return (
    <div className="eot-panel">
      <div className="panel-header">End of Turn Effects</div>

      <Section
        icon="💰"
        title="FINANCES"
        summary={financeSummary}
        items={financeAll}
        defaultOpen={false}
      />
      <Section
        icon="🛢️"
        title="OIL"
        summary={oilSummary}
        items={oil}
        defaultOpen={false}
      />
      {warnings.length > 0 && (
        <Section
          icon="⚠️"
          title="WARNINGS"
          badge={warnings.length}
          summary={`${warnings.length} active`}
          items={warnings}
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
