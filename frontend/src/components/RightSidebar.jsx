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

// NPC_ORDER matches dialogue array indices
const NPC_DIALOGUE_INDEX = { usa: 0, arabia: 1, eu: 2, dprg: 3, russia: 4, china: 5 }

// Parse daily communique text into cable text
function _extractCableFromDialogue(raw) {
  if (!raw) return null
  const lines = raw.split('\n').map(l => l.trim()).filter(Boolean)
  const textLines = lines.filter(l => !l.match(/^─+$/) && !l.match(/^[A-Z\s]+:$/))
  if (textLines.length === 0) return null
  return textLines.join(' ')
}

// Relation-based fallback cables in NPC voice — never show "No recent communications"
const FALLBACK_CABLES = {
  usa: {
    warm: "Washington views the current trajectory of our relations favorably. We remain committed to our partnership with Europa.",
    neutral: "The State Department is monitoring developments in Europa. We expect continued engagement on shared interests.",
    cool: "Washington has growing concerns about Europa's direction. We urge a return to constructive dialogue.",
  },
  arabia: {
    warm: "Our friendship with Europa brings prosperity to both our peoples. The oil flows freely between allies.",
    neutral: "Arabia observes Europa's path with interest. There are opportunities for those who choose wisely.",
    cool: "Europa's recent choices have not gone unnoticed in our councils. We hope for wiser decisions ahead.",
  },
  eu: {
    warm: "Brussels welcomes Europa's commitment to European values and continued integration efforts.",
    neutral: "The Commission is reviewing Europa's alignment with EU standards. Regular consultations continue.",
    cool: "There are significant concerns in Brussels about governance trends in Europa. Reforms are expected.",
  },
  dprg: {
    warm: "The People's Republic celebrates our fraternal bonds with Europa. Together we resist imperialism.",
    neutral: "The DPRG watches Europa's balancing act between East and West with professional interest.",
    cool: "Europa's alignment with Western powers has been noted by our leadership. We advise reconsideration.",
  },
  russia: {
    warm: "Moscow values its strategic partnership with Europa. Together we shape the multipolar world order.",
    neutral: "Russia monitors the situation in Europa. There are always possibilities for pragmatic cooperation.",
    cool: "Europa's choices concern Moscow. We suggest Europa consider where its true strategic interests lie.",
  },
  china: {
    warm: "Beijing sees Europa as a valued partner in the Belt and Road initiative. Our cooperation deepens.",
    neutral: "China follows developments in Europa with measured interest. We see potential for mutual benefit.",
    cool: "Beijing notes Europa's recent positioning with concern. We encourage a more balanced approach.",
  },
}

function getFallbackCable(npcKey, relation) {
  const templates = FALLBACK_CABLES[npcKey]
  if (!templates) return null
  if (relation > 60) return templates.warm
  if (relation >= 40) return templates.neutral
  return templates.cool
}

export default function RightSidebar({ gs, onContact, onContactRequest, contactLoading, contactResults, negotiatingNpc, contactsDisabled, onBackchannel, backchannelDisabled, onGetIntel, intelLoading, intelResults, dialogue, onRequestBriefing, briefingLoading }) {
  if (!gs) return null

  const rel = gs.relations || {}
  const apiCables = gs.diplomatic_cables || {}

  // Build cables: API cables > daily dialogue > relation-based fallback
  const cables = {}
  for (const npc of NPC_LIST) {
    const r = rel[npc.key] ?? 50
    if (apiCables[npc.key]) {
      cables[npc.key] = apiCables[npc.key]
    } else if (dialogue && dialogue[NPC_DIALOGUE_INDEX[npc.key]]) {
      cables[npc.key] = _extractCableFromDialogue(dialogue[NPC_DIALOGUE_INDEX[npc.key]])
    } else {
      // Always show something in NPC voice
      cables[npc.key] = getFallbackCable(npc.key, r)
    }
  }

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
