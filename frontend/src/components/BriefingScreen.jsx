/**
 * BriefingScreen — Session 10B-1.
 * Replaces Foreign Affairs tab center content with a five-state
 * daily briefing hub: hub, event_active, event_summary, free_action, end_day.
 *
 * Mounts inside DashboardLayout's {children} when Foreign Affairs tab is active.
 * Does NOT own EOT logic — delegates to parent via onEndDay callback.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api'

// ── NPC display info for event communiqués ─────────────────────────────────
const NPC_DISPLAY = {
  usa:    { flag: '\u{1F1FA}\u{1F1F8}', name: 'Bill Hartwell',   color: '#1a3a5c' },
  arabia: { flag: '\u{1F1F8}\u{1F1E6}', name: 'Sadam',           color: '#2d5a1e' },
  eu:     { flag: '\u{1F1EA}\u{1F1FA}', name: 'Marsha',          color: '#1a3a6b' },
  dprg:   { flag: '\u{1F1F0}\u{1F1F5}', name: 'Ji-won Ryang',    color: '#5a1a1a' },
  russia: { flag: '\u{1F1F7}\u{1F1FA}', name: 'Nikolai Volkov',  color: '#3a1a4a' },
  china:  { flag: '\u{1F1E8}\u{1F1F3}', name: 'Wei Jianming',    color: '#8b4513' },
}

// ── Severity styling ────────────────────────────────────────────────────────
const SEVERITY_COLORS = {
  routine:  { bg: 'rgba(74,158,255,0.08)', border: '#4a9eff', text: '#4a9eff' },
  moderate: { bg: 'rgba(229,163,74,0.08)', border: '#e5a34a', text: '#e5a34a' },
  urgent:   { bg: 'rgba(229,74,74,0.08)',  border: '#e54a4a', text: '#e54a4a' },
  critical: { bg: 'rgba(229,74,74,0.15)',  border: '#e54a4a', text: '#ff6b6b' },
}

const CATEGORY_ICONS = {
  diplomatic: '\u{1F310}',  // globe
  economic:   '\u{1F4B0}',  // money bag
  military:   '\u2694\uFE0F', // swords
  domestic:   '\u{1F3DB}\uFE0F', // classical building
  crisis:     '\u26A0\uFE0F',  // warning
}

const INTEL_LEVEL_LABELS = {
  vague:      'LOW CONFIDENCE',
  partial:    'PARTIAL',
  specific:   'HIGH CONFIDENCE',
  actionable: 'FULL PICTURE',
}

// ── EventCard ───────────────────────────────────────────────────────────────
function EventCard({ event, onClick }) {
  const sev = SEVERITY_COLORS[event.severity] || SEVERITY_COLORS.moderate
  const icon = CATEGORY_ICONS[event.category] || ''
  const resolved = event.resolved

  return (
    <button
      className="briefing-event-card"
      onClick={onClick}
      disabled={resolved}
      style={{
        background: resolved ? 'var(--surface)' : sev.bg,
        borderColor: resolved ? 'var(--border)' : sev.border,
        opacity: resolved ? 0.6 : 1,
      }}
    >
      <div className="briefing-event-card-header">
        <span
          className="briefing-severity-badge"
          style={{ color: sev.text, borderColor: sev.border }}
        >
          {event.severity.toUpperCase()}
        </span>
        {event.required && !resolved && (
          <span className="briefing-required-tag">REQUIRED</span>
        )}
        {resolved && (
          <span className="briefing-resolved-tag">{'\u2713'} RESOLVED</span>
        )}
      </div>
      <div className="briefing-event-title">
        {icon} {event.title}
      </div>
      <div className="briefing-event-summary">
        {event.summary.length > 120 ? event.summary.slice(0, 120) + '...' : event.summary}
      </div>
      {event.applicable_npcs?.length > 0 && (
        <div className="briefing-event-npcs">
          {event.applicable_npcs.map(npc => (
            <span key={npc} className="briefing-npc-chip">{npc.toUpperCase()}</span>
          ))}
        </div>
      )}
    </button>
  )
}

// ── Default event choices by category (until GM generates custom ones) ──────
function _getDefaultChoices(event) {
  const cat = event.category || 'diplomatic'
  const sev = event.severity || 'moderate'

  if (cat === 'military') return [
    'Deploy forces to secure the border',
    'Seek diplomatic de-escalation',
    'Request international mediation',
    'Monitor but take no action',
  ]
  if (cat === 'economic') return [
    'Negotiate favorable trade terms',
    'Impose retaliatory tariffs',
    'Seek international economic partnership',
    'Accept short-term costs for stability',
  ]
  if (cat === 'crisis') return [
    'Declare a state of emergency',
    'Address the nation publicly',
    'Convene an emergency cabinet meeting',
    'Seek international assistance',
  ]
  if (cat === 'domestic') return [
    'Address citizens\' concerns directly',
    'Implement policy reforms',
    'Suppress dissent through security forces',
    'Defer to local authorities',
  ]
  // diplomatic default
  return [
    'Engage in direct negotiations',
    'Issue a formal diplomatic response',
    'Build a coalition of allies',
    'Maintain strategic ambiguity',
  ]
}

// ── Main BriefingScreen ─────────────────────────────────────────────────────
export default function BriefingScreen({
  gameState,
  sessionId,
  currentDay,
  currentEra,
  onEndDay,
  onEventResolved,
  onGsUpdate,
  // existing content to wrap in event_active state
  existingDiplomaticContent,
}) {
  const [briefingState, setBriefingState] = useState('hub')
  const [activeEvent, setActiveEvent] = useState(null)
  const [dailyEvents, setDailyEvents] = useState([])
  const [dayStatus, setDayStatus] = useState({
    events_resolved: 0,
    events_required: 3,
    can_end_day: false,
  })
  const [morningBriefing, setMorningBriefing] = useState(null)
  const [morningBriefingOpen, setMorningBriefingOpen] = useState(false)
  const [morningBriefingLoading, setMorningBriefingLoading] = useState(false)
  const [eventsLoading, setEventsLoading] = useState(false)
  const [resolving, setResolving] = useState(false)
  const lastDayRef = useRef(null)

  // 10B-2: Event screen state
  const [eventDialogues, setEventDialogues] = useState([])
  const [eventDialoguesLoading, setEventDialoguesLoading] = useState(false)
  const [advisorAnalyses, setAdvisorAnalyses] = useState([])
  const [advisorAnalysesLoading, setAdvisorAnalysesLoading] = useState(false)
  const [advisorDrawerOpen, setAdvisorDrawerOpen] = useState(false)
  const [advisorAnalysesReady, setAdvisorAnalysesReady] = useState(false)
  const [eventScreenTransition, setEventScreenTransition] = useState(false)

  // 10B-2: Resolution consequences
  const [resolutionConsequences, setResolutionConsequences] = useState(null)

  // 10B-2: Declarations
  const [declarationText, setDeclarationText] = useState('')
  const [declarationLoading, setDeclarationLoading] = useState(false)
  const [todaysDeclaration, setTodaysDeclaration] = useState('')
  const declarationsAvailable = (gameState?.declarations_available ?? 0) >= 1
  const declarationUsedToday = gameState?.declaration_used_today ?? false

  // Derive intel level label
  const intelTier = gameState?.intelligence_tier ?? 1
  const intelLevelLabel = (() => {
    if (intelTier >= 6) return INTEL_LEVEL_LABELS.actionable
    if (intelTier >= 4) return INTEL_LEVEL_LABELS.specific
    if (intelTier >= 2) return INTEL_LEVEL_LABELS.partial
    return INTEL_LEVEL_LABELS.vague
  })()

  // ── Load events on mount / day change ────────────────────────────────────
  const loadEvents = useCallback(async () => {
    if (!sessionId) return
    setEventsLoading(true)
    try {
      // First check if already generated
      const status = await api.briefingDayStatus(sessionId)
      if (status.day_events_generated && status.events?.length > 0) {
        setDailyEvents(status.events)
        setDayStatus({
          events_resolved: status.events_resolved,
          events_required: status.events_required,
          can_end_day: status.can_end_day,
        })
        if (status.morning_briefing_read) {
          setMorningBriefing('(already read)')
        }
      } else {
        // Generate new events
        const result = await api.briefingGenerateEvents(sessionId)
        setDailyEvents(result.events || [])
        if (result.game_state && onGsUpdate) {
          onGsUpdate(result.game_state)
        }
      }
    } catch (e) {
      console.error('[BRIEFING] Failed to load events:', e)
    } finally {
      setEventsLoading(false)
    }
  }, [sessionId, onGsUpdate])

  useEffect(() => {
    if (currentDay !== lastDayRef.current) {
      lastDayRef.current = currentDay
      setBriefingState('hub')
      setActiveEvent(null)
      setMorningBriefing(null)
      setMorningBriefingOpen(false)
      loadEvents()
    }
  }, [currentDay, loadEvents])

  // Also load on mount
  useEffect(() => {
    loadEvents()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Handlers ─────────────────────────────────────────────────────────────
  async function handleMorningBriefing() {
    if (morningBriefing && morningBriefing !== '(already read)') {
      setMorningBriefingOpen(!morningBriefingOpen)
      return
    }
    setMorningBriefingLoading(true)
    try {
      const result = await api.briefingMorning(sessionId)
      setMorningBriefing(result.briefing_text)
      setMorningBriefingOpen(true)
      if (result.game_state && onGsUpdate) {
        onGsUpdate(result.game_state)
      }
    } catch (e) {
      console.error('[BRIEFING] Morning briefing failed:', e)
      setMorningBriefing('Intelligence services were unable to compile a briefing at this time.')
      setMorningBriefingOpen(true)
    } finally {
      setMorningBriefingLoading(false)
    }
  }

  function handleOpenEvent(event) {
    if (event.resolved) return
    setActiveEvent(event)
    setEventDialogues([])
    setAdvisorAnalyses([])
    setAdvisorDrawerOpen(false)
    setAdvisorAnalysesReady(false)
    setEventScreenTransition(true)
    setBriefingState('event_active')

    // Fetch event-specific NPC dialogues (always — backend uses all NPCs if applicable_npcs empty)
    setEventDialoguesLoading(true)
    api.briefingEventDialogue(sessionId, event.id)
      .then(res => setEventDialogues(res.dialogues || []))
      .catch(e => console.error('[10B-2] Event dialogue fetch failed:', e))
      .finally(() => setEventDialoguesLoading(false))

    // Fetch advisor analyses in background
    setAdvisorAnalysesLoading(true)
    api.briefingAdvisorEventAnalysis(sessionId, event.id)
      .then(res => {
        setAdvisorAnalyses(res.analyses || [])
        if (res.analyses?.length > 0) setAdvisorAnalysesReady(true)
      })
      .catch(e => console.error('[10B-2] Advisor analysis fetch failed:', e))
      .finally(() => setAdvisorAnalysesLoading(false))

    // Trigger CSS transition
    setTimeout(() => setEventScreenTransition(false), 50)
  }

  async function handleResolveEvent(resolution) {
    if (!activeEvent || resolving) return
    setResolving(true)
    try {
      const result = await api.briefingResolveEvent(sessionId, activeEvent.id, resolution)
      // Update local state
      setDailyEvents(prev => prev.map(e =>
        e.id === activeEvent.id ? { ...e, resolved: true, resolution } : e
      ))
      setDayStatus({
        events_resolved: result.events_resolved,
        events_required: result.events_required,
        can_end_day: result.can_end_day,
      })
      setActiveEvent({ ...activeEvent, resolved: true, resolution })
      setResolutionConsequences(result.consequences || null)
      setBriefingState('event_summary')
      if (result.game_state && onGsUpdate) {
        onGsUpdate(result.game_state)
      }
      if (onEventResolved) {
        onEventResolved(activeEvent, resolution)
      }
    } catch (e) {
      console.error('[BRIEFING] Event resolution failed:', e)
    } finally {
      setResolving(false)
    }
  }

  async function handleDeclaration() {
    if (!declarationText.trim() || declarationLoading) return
    setDeclarationLoading(true)
    try {
      const result = await api.briefingDeclaration(sessionId, declarationText.trim())
      setTodaysDeclaration(declarationText.trim())
      setDeclarationText('')
      if (result.game_state && onGsUpdate) onGsUpdate(result.game_state)
    } catch (e) {
      console.error('[10B-2] Declaration failed:', e)
    } finally {
      setDeclarationLoading(false)
    }
  }

  function returnToBriefing() {
    setActiveEvent(null)
    setEventDialogues([])
    setAdvisorAnalyses([])
    setAdvisorDrawerOpen(false)
    const canEnd = dayStatus.events_resolved >= dayStatus.events_required
    setBriefingState(canEnd ? 'free_action' : 'hub')
  }

  function handleEndDay() {
    setBriefingState('end_day')
    if (onEndDay) onEndDay()
  }

  // ── Render: Loading ──────────────────────────────────────────────────────
  if (eventsLoading) {
    return (
      <div className="briefing-loading">
        <div className="briefing-loading-cards">
          {[1, 2, 3].map(i => (
            <div key={i} className="briefing-event-card briefing-skeleton" />
          ))}
        </div>
        <p className="briefing-loading-text">Preparing your briefing...</p>
      </div>
    )
  }

  // ── Render: Event Active (10B-2 redesign) ───────────────────────────────
  if (briefingState === 'event_active' && activeEvent) {
    const sev = SEVERITY_COLORS[activeEvent.severity] || SEVERITY_COLORS.moderate
    const catIcon = CATEGORY_ICONS[activeEvent.category] || ''

    // Build choice list: use event.choices if available, else generate from category
    const eventChoices = activeEvent.choices?.length > 0
      ? activeEvent.choices
      : _getDefaultChoices(activeEvent)

    return (
      <div className={`briefing-event-screen ${eventScreenTransition ? 'entering' : 'entered'}`}>
        {/* Header */}
        <div className="briefing-event-screen-header">
          <button className="briefing-back-btn" onClick={returnToBriefing}>
            {'\u2190'} BRIEFING
          </button>
          {/* Advisor drawer tab */}
          <button
            className={`briefing-advisor-drawer-tab ${advisorDrawerOpen ? 'open' : ''}`}
            onClick={() => setAdvisorDrawerOpen(!advisorDrawerOpen)}
          >
            ADVISORS {advisorDrawerOpen ? '\u25BC' : '\u25B2'}
            {advisorAnalysesReady && !advisorDrawerOpen && (
              <span className="advisor-ready-dot">{'\u25CF'}</span>
            )}
          </button>
        </div>

        {/* Event title block */}
        <div className="briefing-event-title-block">
          <div className="briefing-event-meta">
            <span
              className="briefing-severity-badge"
              style={{ color: sev.text, borderColor: sev.border }}
            >
              {activeEvent.severity.toUpperCase()}
            </span>
            <span className="briefing-event-category">{catIcon} {activeEvent.category?.toUpperCase()}</span>
          </div>
          <h2 className="briefing-event-active-title">{activeEvent.title}</h2>
          <p className="briefing-event-active-summary">{activeEvent.summary}</p>
        </div>

        <div className="briefing-event-divider" />

        {/* NPC Communiqués */}
        <div className="briefing-event-communiques">
          {eventDialoguesLoading && (
            <div className="briefing-communiques-loading">
              <div className="briefing-skeleton" style={{ height: '80px', marginBottom: '0.75rem' }} />
              <div className="briefing-skeleton" style={{ height: '80px' }} />
              <p className="briefing-loading-text">Receiving diplomatic communiqués...</p>
            </div>
          )}
          {!eventDialoguesLoading && eventDialogues.map(d => {
            const npcInfo = NPC_DISPLAY[d.npc_id] || { flag: '\u{1F310}', name: d.npc_name, color: '#333' }
            return (
              <div key={d.npc_id} className="briefing-event-npc-card">
                <div className="briefing-event-npc-header">
                  <span className="briefing-event-npc-flag" style={{ background: npcInfo.color }}>
                    {npcInfo.flag}
                  </span>
                  <span className="briefing-event-npc-name">{d.npc_name}</span>
                </div>
                <p className="briefing-event-npc-message">{d.message}</p>
              </div>
            )
          })}
          {!eventDialoguesLoading && eventDialogues.length === 0 && (
            <p style={{ color: 'var(--muted)', fontStyle: 'italic', fontSize: '0.85rem' }}>
              No diplomatic communiqués received for this event.
            </p>
          )}
        </div>

        <div className="briefing-event-divider" />

        {/* Your Move — real choices */}
        <div className="briefing-event-choices">
          <p className="briefing-choices-label">YOUR MOVE</p>
          {eventChoices.map((choice, i) => (
            <button
              key={i}
              className="briefing-choice-btn"
              onClick={() => handleResolveEvent(choice)}
              disabled={resolving}
            >
              <span className="briefing-choice-letter">{String.fromCharCode(65 + i)}</span>
              {choice}
            </button>
          ))}
        </div>

        {/* Optional events can go back without resolving */}
        {!activeEvent.required && (
          <button className="briefing-back-link" onClick={returnToBriefing}>
            {'\u2190'} Back to Briefing
          </button>
        )}

        {/* Advisor Drawer (slides up) */}
        {advisorDrawerOpen && (
          <div className="briefing-advisor-drawer">
            <div className="briefing-advisor-drawer-content">
              {advisorAnalysesLoading && (
                <p className="briefing-loading-text">Advisors analyzing situation...</p>
              )}
              {!advisorAnalysesLoading && advisorAnalyses.length === 0 && (
                <p style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>
                  No advisors assigned today. Assign advisors from the Domestic tab.
                </p>
              )}
              {advisorAnalyses.map((a, i) => (
                <div key={i} className="briefing-advisor-analysis-card">
                  <div className="briefing-advisor-analysis-name">{a.advisor_name}</div>
                  <div className="briefing-advisor-analysis-type">{a.advisor_type}</div>
                  <p className="briefing-advisor-analysis-text">{a.analysis_text}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  // ── Render: Event Summary ────────────────────────────────────────────────
  if (briefingState === 'event_summary' && activeEvent) {
    const csq = resolutionConsequences
    return (
      <div className="briefing-event-summary">
        <h3 className="briefing-summary-title">EVENT RESOLVED</h3>
        <div className="briefing-resolved-event-card">
          <div className="briefing-event-title">{activeEvent.title}</div>
          <p className="briefing-resolution-text">
            Response: {activeEvent.resolution}
          </p>
        </div>

        {/* Consequences */}
        {csq && (
          <div className="briefing-consequences">
            {csq.interpretation && (
              <p className="briefing-consequence-interpretation">{csq.interpretation}</p>
            )}

            {/* NPC Relation Deltas */}
            {csq.npc_reactions && Object.entries(csq.npc_reactions).some(([, d]) => d !== 0) && (
              <div className="briefing-consequence-section">
                <span className="briefing-consequence-label">RELATIONS</span>
                <div className="briefing-consequence-deltas">
                  {Object.entries(csq.npc_reactions).filter(([, d]) => d !== 0).map(([npc, delta]) => {
                    const info = NPC_DISPLAY[npc]
                    return (
                      <span key={npc} className={`briefing-delta ${delta > 0 ? 'positive' : 'negative'}`}>
                        {info?.flag || npc} {delta > 0 ? '+' : ''}{delta}
                      </span>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Stability Delta */}
            {csq.stability_delta !== 0 && csq.stability_delta != null && (
              <div className="briefing-consequence-section">
                <span className="briefing-consequence-label">STABILITY</span>
                <span className={`briefing-delta ${csq.stability_delta > 0 ? 'positive' : 'negative'}`}>
                  {csq.stability_delta > 0 ? '+' : ''}{csq.stability_delta}
                </span>
              </div>
            )}

            {/* Budget Delta */}
            {csq.budget_delta !== 0 && csq.budget_delta != null && (
              <div className="briefing-consequence-section">
                <span className="briefing-consequence-label">BUDGET</span>
                <span className={`briefing-delta ${csq.budget_delta > 0 ? 'positive' : 'negative'}`}>
                  {csq.budget_delta > 0 ? '+' : ''}{csq.budget_delta.toFixed(1)}B
                </span>
              </div>
            )}

            {/* Flags */}
            {csq.flags?.length > 0 && (
              <div className="briefing-consequence-section">
                <span className="briefing-consequence-label">FLAGS</span>
                {csq.flags.map((f, i) => (
                  <span key={i} className="briefing-flag">{f}</span>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="briefing-progress-inline">
          Progress: {dayStatus.events_resolved} / {dayStatus.events_required} required events
        </div>
        <button className="briefing-back-btn" onClick={returnToBriefing}>
          {'\u2190'} Return to Briefing
        </button>
      </div>
    )
  }

  // ── Render: Free Action / Hub ────────────────────────────────────────────
  const canEndDay = dayStatus.events_resolved >= dayStatus.events_required
  const unresolvedEvents = dailyEvents.filter(e => !e.resolved)

  return (
    <div className="briefing-hub">
      {/* Free action banner */}
      {canEndDay && briefingState !== 'end_day' && (
        <div className="briefing-free-action-header">
          <span className="briefing-phase-label">
            {'\u2713'} REQUIRED EVENTS COMPLETE
          </span>
          <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0.25rem 0' }}>
            You may continue working events, or end the day.
          </p>
        </div>
      )}

      {/* Morning briefing card */}
      <button
        className="briefing-morning-card"
        onClick={handleMorningBriefing}
        disabled={morningBriefingLoading}
      >
        <span className="briefing-morning-label">
          {'\u25CF'} MORNING BRIEFING
        </span>
        <span className="briefing-morning-subtitle">
          Intelligence summary — {intelLevelLabel}
        </span>
        {morningBriefing && morningBriefing !== '(already read)' && (
          <span className="briefing-morning-read">{'\u2713'} Read</span>
        )}
        {morningBriefingLoading && (
          <span className="briefing-morning-loading">Loading...</span>
        )}
      </button>

      {/* Morning briefing expanded text */}
      {morningBriefingOpen && morningBriefing && morningBriefing !== '(already read)' && (
        <div className="briefing-morning-text">
          {morningBriefing}
        </div>
      )}

      {/* 10B-2: Declaration panel */}
      {declarationsAvailable && !declarationUsedToday && (
        <div className="declaration-panel">
          <div className="declaration-header">
            <span className="declaration-label">ISSUE A DECLARATION</span>
            <span className="declaration-hint">
              Public statements carry diplomatic weight.
            </span>
          </div>
          <textarea
            className="declaration-input"
            placeholder="State your government's position..."
            value={declarationText}
            onChange={e => setDeclarationText(e.target.value)}
            maxLength={280}
            rows={3}
          />
          <button
            className="btn-declaration"
            onClick={handleDeclaration}
            disabled={!declarationText.trim() || declarationLoading}
          >
            {declarationLoading ? 'Issuing...' : 'Issue Declaration \u2192'}
          </button>
        </div>
      )}
      {declarationUsedToday && (
        <div className="declaration-used">
          <span>Declaration issued today</span>
          <span className="declaration-text-preview">
            {todaysDeclaration || gameState?.todays_declaration || ''}
          </span>
        </div>
      )}
      {!declarationsAvailable && (
        <div className="declaration-locked">
          Declarations unlock on Day 5
        </div>
      )}

      {/* Day progress indicator */}
      <div className="briefing-day-progress">
        <span>REQUIRED EVENTS: {dayStatus.events_resolved} / {dayStatus.events_required}</span>
        <div className="briefing-progress-pips">
          {[...Array(dayStatus.events_required)].map((_, i) => (
            <span
              key={i}
              className={`briefing-pip ${i < dayStatus.events_resolved ? 'pip-filled' : ''}`}
            >
              {'\u25C6'}
            </span>
          ))}
        </div>
      </div>

      {/* World events queue */}
      <div className="briefing-events-queue">
        {dailyEvents.map(event => (
          <EventCard
            key={event.id}
            event={event}
            onClick={() => handleOpenEvent(event)}
          />
        ))}
        {dailyEvents.length === 0 && !eventsLoading && (
          <div style={{ color: 'var(--muted)', textAlign: 'center', padding: '2rem' }}>
            No world events today.
          </div>
        )}
      </div>

      {/* End day button */}
      {canEndDay && (
        <button className="briefing-end-day-btn" onClick={handleEndDay}>
          End Day {currentDay} {'\u2192'}
        </button>
      )}
    </div>
  )
}
