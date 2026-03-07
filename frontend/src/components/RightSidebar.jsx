/**
 * RightSidebar — Desktop right panel showing NPC relationship cards.
 * Four active NPCs + two placeholder cards (Russia, China).
 * Session 7A Step 1.
 */
import NpcCard from './NpcCard'

const NPC_LIST = [
  { key: 'usa',    label: 'Bill Hartwell',  flag: '🇺🇸', subtitle: 'United States',    color: 'var(--usa)' },
  { key: 'arabia', label: 'Sadam',          flag: '🛢️',  subtitle: 'Arabia',            color: 'var(--arabia)' },
  { key: 'eu',     label: 'Marsha',         flag: '🇪🇺', subtitle: 'EU Commission',     color: 'var(--eu)' },
  { key: 'dprg',   label: 'Ji-won Ryang',   flag: '⚡',  subtitle: 'DPRG',              color: 'var(--dprg)' },
]

const PLACEHOLDER_NPCS = [
  { key: 'russia', label: 'Russia',  flag: '🇷🇺', color: '#555' },
  { key: 'china',  label: 'China',   flag: '🇨🇳', color: '#555' },
]

export default function RightSidebar({ gs }) {
  if (!gs) return null

  const rel = gs.relations || {}

  return (
    <div className="right-sidebar">
      {/* Intelligence intercept badge (placeholder) */}
      <div className="rs-intel-badge">
        🔍 Intelligence Intercepts
        <span style={{ marginLeft: 'auto', opacity: 0.5 }}>—</span>
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
          relation={rel[npc.key] ?? 50}
          hasWarning={
            (npc.key === 'usa' && gs.usa_sanctions_active) ||
            (npc.key === 'arabia' && gs.arabia_embargo_active)
          }
          isPlaceholder={false}
          color={npc.color}
        />
      ))}

      {/* Placeholder cards — Russia & China */}
      {PLACEHOLDER_NPCS.map(npc => (
        <NpcCard
          key={npc.key}
          npcKey={npc.key}
          label={npc.label}
          flag={npc.flag}
          relation={0}
          isPlaceholder={true}
          color={npc.color}
        />
      ))}
    </div>
  )
}
