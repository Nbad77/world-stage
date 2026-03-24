/**
 * DashboardLayout — Three-panel desktop shell + mobile card feed.
 * Desktop (≥1024px): LeftSidebar | Center content | RightSidebar
 * Mobile (<1024px): NPC strip + condensed stats + center content
 * Session 7A Step 1.  Step 3: Ambient vs Event Mode.
 */
import { useEffect, useRef } from 'react'
import LeftSidebar from './LeftSidebar'
import RightSidebar from './RightSidebar'

const MOBILE_NPCS = [
  { key: 'usa',    flag: '🇺🇸', label: 'USA' },
  { key: 'arabia', flag: '🛢️',  label: 'ARB' },
  { key: 'eu',     flag: '🇪🇺', label: 'EU' },
  { key: 'dprg',   flag: '⚡',  label: 'DPRG' },
  { key: 'russia', flag: '🇷🇺', label: 'RUS' },
  { key: 'china',  flag: '🇨🇳', label: 'CHN' },
]

const NPC_LABELS = {
  usa:    'BILL HARTWELL',
  arabia: 'SADAM',
  eu:     'MARSHA',
  dprg:   'JI-WON RYANG',
  russia: 'NIKOLAI VOLKOV',
  china:  'WEI JIANMING',
}

export default function DashboardLayout({ gs, children, onShadowCabinet, negotiatingNpc, onHistorian, historianLoading, onContact, onContactRequest, contactLoading, contactResults, contactsDisabled, activeTab, onTabChange, domesticContent, onBackchannel, backchannelDisabled, onBiography, onGetIntel, intelLoading, intelResults, onRequestBriefing, briefingLoading }) {
  // ── Ambient vs Event mode ────────────────────────────────────────────
  const mode = negotiatingNpc ? 'event' : 'ambient'
  const prevModeRef = useRef(mode)

  useEffect(() => {
    console.log('[DASHBOARD] Three-panel layout mounted')
  }, [])

  useEffect(() => {
    if (prevModeRef.current !== mode) {
      console.log('[MODE] Switched to:', mode)
      prevModeRef.current = mode
    }
  }, [mode])

  if (!gs) return <>{children}</>

  const rel = gs.relations || {}

  // ── Mobile stat helpers ──────────────────────────────────────────────
  const budgetClass = gs.budget < 5 ? 'bad' : gs.budget < 15 ? 'warn' : 'good'
  const stabilityClass = (gs.stability ?? 0) < 20 ? 'bad' : (gs.stability ?? 0) < 40 ? 'warn' : 'good'
  const approvalClass = (gs.public_approval ?? 0) < 20 ? 'bad' : (gs.public_approval ?? 0) < 40 ? 'warn' : 'good'

  // NPC circle health class
  function npcHealth(key) {
    const v = rel[key] ?? 50
    return v >= 60 ? 'health-good' : v >= 30 ? 'health-warn' : 'health-bad'
  }

  // ── Context label content ────────────────────────────────────────────
  const npcLabel = negotiatingNpc ? (NPC_LABELS[negotiatingNpc] || negotiatingNpc.toUpperCase()) : ''
  const contextText = mode === 'event'
    ? `ACTIVE NEGOTIATION — ${npcLabel}`
    : `ERA ${gs.current_era ?? 1} · DAY ${gs.current_day ?? gs.current_turn ?? 1} — PRESIDENTIAL BRIEFING`

  return (
    <div className={`dashboard-shell ${mode === 'event' ? 'mode-event' : 'mode-ambient'}`}>

      {/* ── Left Sidebar (desktop only) ──────────────────────────────── */}
      <aside className="dashboard-left hidden lg:block">
        <LeftSidebar gs={gs} onShadowCabinet={onShadowCabinet} mode={mode} onHistorian={onHistorian} historianLoading={historianLoading} onBiography={onBiography} />
      </aside>

      {/* ── Center Panel ─────────────────────────────────────────────── */}
      <main className="dashboard-center">
        {/* Context label */}
        <div className={`dashboard-context-label ${mode === 'event' ? 'context-event' : ''}`}>
          <span className="context-mode-indicator">
            {mode === 'event' ? '⚡ EVENT IN PROGRESS' : '● AMBIENT'}
          </span>
          {contextText}
        </div>

        {/* ── Tab bar ─────────────────────────────────────────────── */}
        {onTabChange && (
          <div className="dashboard-tab-bar">
            <button
              className={`dashboard-tab ${(activeTab || 'foreign') === 'foreign' ? 'tab-active' : ''}`}
              onClick={() => onTabChange('foreign')}
            >
              FOREIGN AFFAIRS
            </button>
            <button
              className={`dashboard-tab ${activeTab === 'domestic' ? 'tab-active' : ''}`}
              onClick={() => onTabChange('domestic')}
            >
              DOMESTIC
            </button>
          </div>
        )}

        {/* Mobile NPC strip (hidden on desktop) — Session 7D: wired to backchannel */}
        <div className="mobile-npc-strip block lg:hidden">
          {MOBILE_NPCS.map(npc => {
            const canBackchannel = onBackchannel && !backchannelDisabled
            return (
              <div key={npc.key} className="mobile-npc-item">
                <button
                  className={`mobile-npc-circle npc-${npc.key} ${npcHealth(npc.key)} ${canBackchannel ? 'mobile-npc-tappable' : ''}`}
                  disabled={!canBackchannel}
                  onClick={() => {
                    if (canBackchannel) {
                      console.log('[BACKCHANNEL] Mobile backchannel initiated:', npc.key)
                      onBackchannel(npc.key)
                    }
                  }}
                >
                  {npc.flag}
                </button>
                <div className="mobile-npc-name">
                  {npc.label} {Math.round(rel[npc.key] ?? 50)}
                </div>
              </div>
            )
          })}
        </div>

        {/* Mobile condensed stats (hidden on desktop) */}
        <div className="mobile-stats-condensed block lg:hidden">
          <span>Budget <span className={`ms-val ${budgetClass}`}>${gs.budget.toFixed(1)}B</span></span>
          <span>Stab <span className={`ms-val ${stabilityClass}`}>{gs.stability ?? 0}%</span></span>
          <span>Appr <span className={`ms-val ${approvalClass}`}>{gs.public_approval ?? 0}%</span></span>
          <span>Oil <span className="ms-val">${gs.oil_price ?? 0}/bbl</span></span>
        </div>

        {/* Center content: Foreign Affairs (children) or Domestic tab */}
        {activeTab === 'domestic' && domesticContent ? domesticContent : children}
      </main>

      {/* ── Right Sidebar (desktop only) ─────────────────────────────── */}
      <aside className="dashboard-right hidden lg:block">
        <RightSidebar gs={gs} onContact={onContact} onContactRequest={onContactRequest} contactLoading={contactLoading} contactResults={contactResults} negotiatingNpc={negotiatingNpc} contactsDisabled={contactsDisabled} onBackchannel={onBackchannel} backchannelDisabled={backchannelDisabled} onGetIntel={onGetIntel} intelLoading={intelLoading} intelResults={intelResults} onRequestBriefing={onRequestBriefing} briefingLoading={briefingLoading} />
      </aside>

    </div>
  )
}
