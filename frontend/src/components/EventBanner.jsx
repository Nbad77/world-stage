/**
 * EventBanner — breaking news ticker style banner for world events.
 * Shown at the top of the DIALOGUE phase when current_event is set.
 *
 * event shape:
 *   { title, description, effects: { oil_price_delta, stability_delta, relations_delta }, affected_npc }
 */

const NPC_FLAGS = {
  usa:    '🇺🇸',
  arabia: '🛢️',
  eu:     '🇪🇺',
  dprg:   '⚡',
  russia: '🇷🇺',
  china:  '🇨🇳',
}

function formatEffect(key, val) {
  if (val === 0 || val === undefined) return null
  const sign = val > 0 ? '+' : ''
  switch (key) {
    case 'oil_price_delta':    return `Oil ${sign}$${val}/bbl`
    case 'stability_delta':    return `Stability ${sign}${val}%`
    default: return null
  }
}

function formatRelDelta(npc, val) {
  if (!val) return null
  const sign = val > 0 ? '+' : ''
  const flag = NPC_FLAGS[npc] || npc.toUpperCase()
  return `${flag} ${sign}${val}`
}

export default function EventBanner({ event }) {
  if (!event) return null

  const { title, description, effects = {}, affected_npc } = event
  const { oil_price_delta, stability_delta, relations_delta = {} } = effects

  // Build effect chips
  const chips = []
  const oilFx = formatEffect('oil_price_delta', oil_price_delta)
  const stabFx = formatEffect('stability_delta', stability_delta)
  if (oilFx) chips.push({ label: oilFx, positive: oil_price_delta < 0 }) // cheaper oil = good
  if (stabFx) chips.push({ label: stabFx, positive: stability_delta > 0 })
  for (const [npc, val] of Object.entries(relations_delta)) {
    const label = formatRelDelta(npc, val)
    if (label) chips.push({ label, positive: val > 0 })
  }

  // Session 7B: Determine if event has immediate consequences → URGENT, else DEVELOPING
  const hasImmediateConsequence = oil_price_delta || stability_delta ||
    Object.values(relations_delta).some(v => v !== 0)
  const eventTier = hasImmediateConsequence ? 'urgent' : 'developing'

  return (
    <div className="event-banner">
      <div className="event-banner-header">
        <span className={`briefing-tag briefing-tag-${eventTier}`}>
          {eventTier === 'urgent' ? 'URGENT' : 'DEVELOPING'}
        </span>
        <span className="event-ticker">⚠ BREAKING</span>
        <span className="event-title">{title}</span>
        {affected_npc && affected_npc !== 'none' && (
          <span className="event-npc-flag">{NPC_FLAGS[affected_npc] || ''}</span>
        )}
      </div>
      <div className="event-description">{description}</div>
      {chips.length > 0 && (
        <div className="event-effects">
          {chips.map((chip, i) => (
            <span
              key={i}
              className={`event-chip ${chip.positive ? 'chip-good' : 'chip-bad'}`}
            >
              {chip.label}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
