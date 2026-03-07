/**
 * RightSidebar — Desktop right panel showing NPC relationship cards.
 * Four active NPCs + two passive observer cards (Russia, China).
 * Session 7A Step 1.  Session 7C Step 4: Russia/China functional.
 * Session 7D Step 2: Backchannel button props.
 */
import NpcCard from './NpcCard'

const NPC_LIST = [
  { key: 'usa',    label: 'Bill Hartwell',  flag: '🇺🇸', subtitle: 'United States',    color: 'var(--usa)' },
  { key: 'arabia', label: 'Sadam',          flag: '🛢️',  subtitle: 'Arabia',            color: 'var(--arabia)' },
  { key: 'eu',     label: 'Marsha',         flag: '🇪🇺', subtitle: 'EU Commission',     color: 'var(--eu)' },
  { key: 'dprg',   label: 'Ji-won Ryang',   flag: '⚡',  subtitle: 'DPRG',              color: 'var(--dprg)' },
]

const PASSIVE_NPCS = [
  { key: 'russia', label: 'Russia',  flag: '🇷🇺', subtitle: 'Observer — No Direct Channel', color: '#7b1fa2', gsField: 'russia_relations' },
  { key: 'china',  label: 'China',   flag: '🇨🇳', subtitle: 'Observer — No Direct Channel', color: '#c62828', gsField: 'china_relations' },
]

export default function RightSidebar({ gs, onContact, negotiatingNpc, contactsDisabled, onBackchannel, backchannelDisabled }) {
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
          onContact={onContact}
          contactDisabled={contactsDisabled || negotiatingNpc === npc.key}
          onBackchannel={onBackchannel}
          backchannelDisabled={backchannelDisabled}
          gs={gs}
        />
      ))}

      {/* Session 7C Step 4: Russia & China — passive observer cards */}
      {PASSIVE_NPCS.map(npc => (
        <NpcCard
          key={npc.key}
          npcKey={npc.key}
          label={npc.label}
          flag={npc.flag}
          subtitle={npc.subtitle}
          relation={gs[npc.gsField] ?? 35}
          isPlaceholder={false}
          isPassive={true}
          color={npc.color}
        />
      ))}
    </div>
  )
}
