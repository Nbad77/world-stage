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
    setBriefingState('event_active')
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

  function returnToBriefing() {
    setActiveEvent(null)
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

  // ── Render: Event Active ─────────────────────────────────────────────────
  if (briefingState === 'event_active' && activeEvent) {
    const sev = SEVERITY_COLORS[activeEvent.severity] || SEVERITY_COLORS.moderate
    return (
      <div className="briefing-event-active">
        <div className="briefing-event-active-header">
          <button className="briefing-back-btn" onClick={returnToBriefing}>
            {'\u2190'} Briefing
          </button>
          <div className="briefing-event-title-block">
            <span
              className="briefing-severity-badge"
              style={{ color: sev.text, borderColor: sev.border }}
            >
              {activeEvent.severity.toUpperCase()}
            </span>
            <h2 className="briefing-event-active-title">{activeEvent.title}</h2>
            <p className="briefing-event-active-summary">{activeEvent.summary}</p>
          </div>
        </div>

        {/* Quick resolution options */}
        <div className="briefing-event-choices">
          <p style={{ color: 'var(--muted)', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
            How do you respond?
          </p>
          <button
            className="briefing-choice-btn"
            onClick={() => handleResolveEvent('Engage diplomatically')}
            disabled={resolving}
          >
            Engage diplomatically
          </button>
          <button
            className="briefing-choice-btn"
            onClick={() => handleResolveEvent('Take a firm stance')}
            disabled={resolving}
          >
            Take a firm stance
          </button>
          <button
            className="briefing-choice-btn"
            onClick={() => handleResolveEvent('Defer to advisors')}
            disabled={resolving}
          >
            Defer to advisors
          </button>
          <button
            className="briefing-choice-btn briefing-choice-ignore"
            onClick={() => handleResolveEvent('Ignore')}
            disabled={resolving}
          >
            Ignore this event
          </button>
        </div>

        {/* Show existing diplomatic content below */}
        {existingDiplomaticContent}
      </div>
    )
  }

  // ── Render: Event Summary ────────────────────────────────────────────────
  if (briefingState === 'event_summary' && activeEvent) {
    return (
      <div className="briefing-event-summary">
        <h3 className="briefing-summary-title">EVENT RESOLVED</h3>
        <div className="briefing-resolved-event-card">
          <div className="briefing-event-title">{activeEvent.title}</div>
          <p className="briefing-resolution-text">
            Response: {activeEvent.resolution}
          </p>
        </div>
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
