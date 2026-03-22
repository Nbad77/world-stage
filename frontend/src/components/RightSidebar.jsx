/**
 * RightSidebar — Desktop right panel showing NPC relationship cards.
 * Six active NPCs including Russia (Nikolai Volkov) and China (Wei Jianming).
 * Session 7A Step 1.  Session 8A: Russia/China promoted to full NPCs.
 * Session 7D Step 2: Backchannel button props.
 */
import NpcCard from './NpcCard'

const NPC_LIST = [
  { key: 'usa',    label: 'Bill Hartwell',    flag: '🇺🇸', subtitle: 'United States',      color: 'var(--usa)' },
  { key: 'arabia', label: 'Sadam',            flag: '🛢️',  subtitle: 'Arabia',              color: 'var(--arabia)' },
  { key: 'eu',     label: 'Marsha',           flag: '🇪🇺', subtitle: 'EU Commission',       color: 'var(--eu)' },
  { key: 'dprg',   label: 'Ji-won Ryang',     flag: '⚡',  subtitle: 'DPRG',                color: 'var(--dprg)' },
  { key: 'russia', label: 'Nikolai Volkov',   flag: '🇷🇺', subtitle: 'Russian Federation',  color: 'var(--russia)' },
  { key: 'china',  label: 'Wei Jianming',     flag: '🇨🇳', subtitle: 'China',               color: 'var(--china)' },
]

// Parse daily communiqué text into a short cable teaser
function _extractCableFromDialogue(raw) {
  if (!raw) return null
  const lines = raw.split('\n').map(l => l.trim()).filter(Boolean)
  // Skip separator lines and headers, get first substantive line
  const textLines = lines.filter(l => !l.match(/^─+$/) && !l.match(/^[A-Z\s]+:$/))
  if (textLines.length === 0) return null
  // Take first 2 sentences max, truncate to ~120 chars
  const text = textLines.join(' ')
  if (text.length <= 120) return text
  return text.slice(0, 117) + '...'
}

// NPC_ORDER matches dialogue array indices
const NPC_DIALOGUE_INDEX = { usa: 0, arabia: 1, eu: 2, dprg: 3, russia: 4, china: 5 }

export default function RightSidebar({ gs, onContact, negotiatingNpc, contactsDisabled, onBackchannel, backchannelDisabled, onGetIntel, intelLoading, dialogue }) {
  if (!gs) return null

  const rel = gs.relations || {}
  const apiCables = gs.diplomatic_cables || {}

  // FIX 6: Build cables from diplomatic_cables or fallback to daily dialogue
  const cables = {}
  for (const npc of NPC_LIST) {
    if (apiCables[npc.key]) {
      cables[npc.key] = apiCables[npc.key]
    } else if (dialogue && dialogue[NPC_DIALOGUE_INDEX[npc.key]]) {
      cables[npc.key] = _extractCableFromDialogue(dialogue[NPC_DIALOGUE_INDEX[npc.key]])
    }
  }

  return (
    <div className="right-sidebar">
      {/* Intelligence intercept badge */}
      <div className="rs-intel-badge">
        🔍 Intelligence Intercepts
        <span style={{ marginLeft: 'auto', opacity: 0.5 }}>
          {(gs.intelligence_tier ?? 0) >= 1 ? `Tier ${gs.intelligence_tier}` : '—'}
        </span>
      </div>

      <div className="rs-header">Diplomatic Relations</div>

      {/* Active NPC cards */}
      {NPC_LIST.map(npc => (
        <NpcCard
          key={npc.key}
          npcKey={npc.key}
          label={npc.label}
          flag={npc.flag}
          subtitle={npc.subtitle}
          relation={rel[npc.key] ?? (npc.key === 'russia' || npc.key === 'china' ? 35 : 50)}
          hasWarning={
            (npc.key === 'usa' && gs.usa_sanctions_active) ||
            (npc.key === 'arabia' && gs.arabia_embargo_active)
          }
          isPlaceholder={false}
          color={npc.color}
          onContact={onContact}
          contactDisabled={contactsDisabled || negotiatingNpc === npc.key}
          onBackchannel={onBackchannel}
          backchannelDisabled={backchannelDisabled}
          onGetIntel={onGetIntel}
          intelLoading={intelLoading?.[npc.key] || false}
          cable={cables[npc.key] || null}
          gs={gs}
        />
      ))}
    </div>
  )
}
