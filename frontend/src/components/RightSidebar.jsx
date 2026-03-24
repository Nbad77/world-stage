/**
 * RightSidebar — Desktop right panel showing NPC relationship cards.
 * Six active NPCs including Russia (Nikolai Volkov) and China (Wei Jianming).
 * Session 7A Step 1.  Session 8A: Russia/China promoted to full NPCs.
 * Session 7D Step 2: Backchannel button props.
 * Session 10B-2: Wider panel, urgent badges, expandable cables, GET INTEL.
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

export default function RightSidebar({ gs, onContact, onContactRequest, contactLoading, contactResults, negotiatingNpc, contactsDisabled, onBackchannel, backchannelDisabled, onGetIntel, intelLoading, intelResults, onRequestBriefing, briefingLoading }) {
  if (!gs) return null

  const rel = gs.relations || {}
  const apiCables = gs.diplomatic_cables || {}

  // Cables come only from gs.diplomatic_cables — no fallbacks
  const cables = apiCables

  return (
    <div className="right-sidebar">
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
          onContactRequest={onContactRequest}
          contactDisabled={contactsDisabled || negotiatingNpc === npc.key}
          contactLoading={contactLoading?.[npc.key] || false}
          contactResult={contactResults?.[npc.key] || null}
          onBackchannel={onBackchannel}
          backchannelDisabled={backchannelDisabled}
          onGetIntel={onGetIntel}
          intelLoading={intelLoading?.[npc.key] || false}
          intelResult={intelResults?.[npc.key] || null}
          cable={cables[npc.key] || null}
          gs={gs}
          onRequestBriefing={onRequestBriefing}
          briefingLoading={briefingLoading?.[npc.key] || false}
        />
      ))}
    </div>
  )
}
