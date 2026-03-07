/**
 * DashboardLayout — Three-panel desktop shell + mobile card feed.
 * Desktop (≥1024px): LeftSidebar | Center content | RightSidebar
 * Mobile (<1024px): NPC strip + condensed stats + center content
 * Session 7A Step 1.
 */
import { useEffect } from 'react'
import LeftSidebar from './LeftSidebar'
import RightSidebar from './RightSidebar'

const MOBILE_NPCS = [
  { key: 'usa',    flag: '🇺🇸', label: 'USA' },
  { key: 'arabia', flag: '🛢️',  label: 'ARB' },
  { key: 'eu',     flag: '🇪🇺', label: 'EU' },
  { key: 'dprg',   flag: '⚡',  label: 'DPRG' },
]

export default function DashboardLayout({ gs, children, onShadowCabinet }) {
  useEffect(() => {
    console.log('[DASHBOARD] Three-panel layout mounted')
  }, [])

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

  return (
    <div className="dashboard-shell">

      {/* ── Left Sidebar (desktop only) ──────────────────────────────── */}
      <aside className="dashboard-left hidden lg:block">
        <LeftSidebar gs={gs} onShadowCabinet={onShadowCabinet} />
      </aside>

      {/* ── Center Panel ─────────────────────────────────────────────── */}
      <main className="dashboard-center">
        {/* Context label */}
        <div className="dashboard-context-label">
          TURN {gs.current_turn}/{gs.max_turns} — PRESIDENTIAL BRIEFING
        </div>

        {/* Mobile NPC strip (hidden on desktop) */}
        <div className="mobile-npc-strip block lg:hidden">
          {MOBILE_NPCS.map(npc => (
            <div key={npc.key} className="mobile-npc-item">
              <div className={`mobile-npc-circle ${npcHealth(npc.key)}`}>
                {npc.flag}
              </div>
              <div className="mobile-npc-name">
                {npc.label} {Math.round(rel[npc.key] ?? 50)}
              </div>
            </div>
          ))}
        </div>

        {/* Mobile condensed stats (hidden on desktop) */}
        <div className="mobile-stats-condensed block lg:hidden">
          <span>Budget <span className={`ms-val ${budgetClass}`}>${gs.budget.toFixed(1)}B</span></span>
          <span>Stab <span className={`ms-val ${stabilityClass}`}>{gs.stability ?? 0}%</span></span>
          <span>Appr <span className={`ms-val ${approvalClass}`}>{gs.public_approval ?? 0}%</span></span>
          <span>Oil <span className="ms-val">${gs.oil_price ?? 0}/bbl</span></span>
        </div>

        {/* Game content passed as children */}
        {children}
      </main>

      {/* ── Right Sidebar (desktop only) ─────────────────────────────── */}
      <aside className="dashboard-right hidden lg:block">
        <RightSidebar gs={gs} />
      </aside>

    </div>
  )
}
