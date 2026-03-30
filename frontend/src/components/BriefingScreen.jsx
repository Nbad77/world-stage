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

// ── Advisor stat helpers ─────────────────────────────────────────────────────
function statLabel(value) {
  if (value >= 80) return 'High'
  if (value >= 60) return 'Solid'
  if (value >= 40) return 'Moderate'
  return 'Concerning'
}

// ── Advisor role colors ──────────────────────────────────────────────────────
const ROLE_COLORS = {
  finance_minister: '#5a8a5a',
  security_chief: '#8a5a5a',
  diplomat: '#7a6a9a',
  technocrat: '#5a7a8a',
  propagandist: '#8a7a5a',
  oligarch: '#7a5a3a',
  general: '#6a6a5a',
  fixer: '#5a5a6a',
  spy_chief: '#4a6a8a',
  militia_commander: '#7a4a4a',
}

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
  dealsRefreshing,
  onSwitchToAdvisors,
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
    deals_today: [],
  })
  const [advisorBriefings, setAdvisorBriefings] = useState(null)
  const [chiefOfStaff, setChiefOfStaff] = useState(null)
  const [councilOpen, setCouncilOpen] = useState(true)

  // Advisor profile expand state
  const [expandedAdvisor, setExpandedAdvisor] = useState(null)
  const [advisorProfile, setAdvisorProfile] = useState(null)
  const [profileLoading, setProfileLoading] = useState(false)

  // Advisor pool (available to hire) state
  const [availableAdvisors, setAvailableAdvisors] = useState([])
  const [poolProfileCache, setPoolProfileCache] = useState({})
  const [poolProfileLoading, setPoolProfileLoading] = useState(false)
  const [expandedPoolAdvisor, setExpandedPoolAdvisor] = useState(null)
  const [hiring, setHiring] = useState(false)

  // 10B-3: When gameState.deals_today changes, immediately show deals
  // then background-refresh from server for authoritative data
  useEffect(() => {
    if (!sessionId) return
    const gsDeals = gameState?.deals_today || []
    const dsDeals = dayStatus.deals_today || []
    if (gsDeals.length > dsDeals.length) {
      // Immediately show optimistic deals from gameState prop
      setDayStatus(prev => ({
        ...prev,
        deals_today: gsDeals,
      }))
      // Then refresh from server for authoritative data (non-blocking)
      api.briefingDayStatus(sessionId).then(status => {
        if (status?.deals_today?.length > 0) {
          setDayStatus(prev => ({
            ...prev,
            deals_today: status.deals_today,
          }))
        }
      }).catch(() => {})
    }
  }, [gameState?.deals_today?.length])
  const [morningBriefingLoading, setMorningBriefingLoading] = useState(false)
  const [eventsLoading, setEventsLoading] = useState(false)
  const [resolving, setResolving] = useState(false)
  const [expandedDealId, setExpandedDealId] = useState(null)
  const lastDayRef = useRef(null)
  const eventsLoadingRef = useRef(false)

  // 10B-2: Event screen state
  const [eventDialogues, setEventDialogues] = useState([])
  const [eventDialoguesLoading, setEventDialoguesLoading] = useState(false)
  const [advisorAnalyses, setAdvisorAnalyses] = useState([])
  const [advisorAnalysesLoading, setAdvisorAnalysesLoading] = useState(false)
  const [advisorDrawerOpen, setAdvisorDrawerOpen] = useState(false)
  const [advisorAnalysesReady, setAdvisorAnalysesReady] = useState(false)
  const [eventScreenTransition, setEventScreenTransition] = useState(false)

  // E3b: NPC event drawer state
  const [eventNpcDrawerOpen, setEventNpcDrawerOpen] = useState(false)
  const [selectedEventNpc, setSelectedEventNpc] = useState(null)
  // { npc_id, display_name, flag }
  const [eventNpcMessage, setEventNpcMessage] = useState(null)
  // null = not fetched, '' = loading, string = message

  // E5: Mike confirmation + resolution beat
  const [confirmModalOpen, setConfirmModalOpen] = useState(false)
  const [pendingResolution, setPendingResolution] = useState(null)
  // { resolutionValue, choiceText }
  const [mikeConfirmRead, setMikeConfirmRead] = useState(null)
  // null=not fetched, ''=loading, string=read
  const [resolutionBeat, setResolutionBeat] = useState(null)
  // null=not shown, { mike_beat, budget_delta, stability_delta }

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
    if (eventsLoadingRef.current) {
      console.log('[EVENTS] loadEvents() skipped — already in flight')
      return
    }
    eventsLoadingRef.current = true
    setEventsLoading(true)
    try {
      // First check if already generated
      const status = await api.briefingDayStatus(sessionId)
      if (status.day_events_generated && status.events?.length > 0) {
        setDailyEvents(status.events)
        setDayStatus(prev => ({
          events_resolved: status.events_resolved,
          events_required: status.events_required,
          can_end_day: status.can_end_day,
          deals_today: (status.deals_today?.length > 0)
            ? status.deals_today
            : prev.deals_today || [],
        }))
        // morning_briefing_read check removed — advisory council handles its own state
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
      eventsLoadingRef.current = false
    }
  }, [sessionId, onGsUpdate])

  useEffect(() => {
    if (currentDay !== lastDayRef.current) {
      lastDayRef.current = currentDay
      setBriefingState('hub')
      setActiveEvent(null)
      setAdvisorBriefings(null)
      setChiefOfStaff(null)
      setCouncilOpen(true)
      loadEvents()
    }
  }, [currentDay, loadEvents])

  // Also load on mount
  useEffect(() => {
    loadEvents()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Advisory Council: auto-fetch morning briefings on mount / day change
  useEffect(() => {
    if (!sessionId || advisorBriefings || morningBriefingLoading) return
    setMorningBriefingLoading(true)
    api.briefingMorning(sessionId)
      .then(result => {
        setChiefOfStaff(result.chief_of_staff)
        setAdvisorBriefings(result.advisor_briefings || [])
        setCouncilOpen(!result.intro_done ? true : true)
        if (result.game_state && onGsUpdate) onGsUpdate(result.game_state)
      })
      .catch(e => {
        console.error('[BRIEFING] Advisor morning briefing failed:', e)
        setChiefOfStaff({
          name: "Mikhail 'Mike' Sorel",
          role: "chief_of_staff",
          label: "Chief of Staff",
          icon: "\uD83E\uDDED",
          text: "Intelligence services unavailable."
        })
        setAdvisorBriefings([])
      })
      .finally(() => setMorningBriefingLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, currentDay])

  // Cables are now on-demand via REQUEST BRIEFING button — no auto-fetch
  // Incoming communiqués are populated by EOT in gs.pending_npc_contacts
  useEffect(() => {
    // No-op: kept for future use if needed
    void 0
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, currentDay])

  // ── Handlers ─────────────────────────────────────────────────────────────

  async function handleAdvisorClick(advisor) {
    if (expandedAdvisor?.role === advisor.role) {
      setExpandedAdvisor(null)
      setAdvisorProfile(null)
      return
    }
    setExpandedAdvisor(advisor)
    setAdvisorProfile(null)
    setProfileLoading(true)
    try {
      const result = await api.advisorProfileRead(sessionId, advisor.role)
      setAdvisorProfile(result)
    } catch (e) {
      console.error('[ADVISOR] profile read failed', e)
      setAdvisorProfile({
        profile_text: 'Assessment unavailable.',
        dismiss_consequence: '',
        eliminate_consequence: ''
      })
    } finally {
      setProfileLoading(false)
    }
  }

  async function handleAdvisorDismiss(archetype) {
    try {
      const result = await api.dismissAdvisor(sessionId, archetype)
      if (result.game_state && onGsUpdate) onGsUpdate(result.game_state)
      setExpandedAdvisor(null)
      setAdvisorProfile(null)
      setAdvisorBriefings(prev => prev.filter(a => a.role !== archetype))
      // Refresh pool after dismiss (advisor returns to pool)
      api.getAdvisorPool(sessionId)
        .then(r => setAvailableAdvisors(r.pool || []))
        .catch(() => {})
    } catch (e) {
      console.error('[ADVISOR] dismiss failed', e)
    }
  }

  async function handleAdvisorEliminate(archetype) {
    try {
      const result = await api.eliminateAdvisor(sessionId, archetype)
      if (result.game_state && onGsUpdate) onGsUpdate(result.game_state)
      setExpandedAdvisor(null)
      setAdvisorProfile(null)
      setAdvisorBriefings(prev => prev.filter(a => a.role !== archetype))
      // Refresh pool after eliminate (advisor is removed permanently)
      api.getAdvisorPool(sessionId)
        .then(r => setAvailableAdvisors(r.pool || []))
        .catch(() => {})
    } catch (e) {
      console.error('[ADVISOR] eliminate failed', e)
    }
  }

  // Fetch available advisor pool on mount / day change
  useEffect(() => {
    if (!sessionId) return
    api.getAdvisorPool(sessionId)
      .then(result => {
        setAvailableAdvisors(result.pool || [])
      })
      .catch(e => console.error('[ADVISOR] pool fetch failed', e))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, currentDay])

  async function handlePoolAdvisorClick(advisor) {
    if (expandedPoolAdvisor?.archetype === advisor.archetype) {
      setExpandedPoolAdvisor(null)
      return
    }
    setExpandedPoolAdvisor(advisor)
    // Return cached result if available
    if (poolProfileCache[advisor.archetype]) {
      return
    }
    setPoolProfileLoading(true)
    try {
      const result = await api.advisorPoolRead(sessionId, advisor.archetype)
      setPoolProfileCache(prev => ({
        ...prev,
        [advisor.archetype]: result
      }))
    } catch (e) {
      console.error('[ADVISOR] pool read failed', e)
      setPoolProfileCache(prev => ({
        ...prev,
        [advisor.archetype]: {
          profile_text: 'Assessment unavailable.',
          hire_recommendation: ''
        }
      }))
    } finally {
      setPoolProfileLoading(false)
    }
  }

  async function handleHire(advisor) {
    setHiring(true)
    try {
      const result = await api.hireAdvisor(sessionId, advisor.id)
      if (result.game_state && onGsUpdate) onGsUpdate(result.game_state)
      setExpandedPoolAdvisor(null)
      setPoolProfileCache(prev => {
        const next = {...prev}
        delete next[advisor.archetype]
        return next
      })
      // Refresh pool
      const pool = await api.getAdvisorPool(sessionId)
      setAvailableAdvisors(pool.pool || [])
      // Refresh morning briefings to show new hire
      const morning = await api.briefingMorning(sessionId)
      setChiefOfStaff(morning.chief_of_staff)
      setAdvisorBriefings(morning.advisor_briefings || [])
    } catch (e) {
      console.error('[ADVISOR] hire failed', e)
    } finally {
      setHiring(false)
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

  // E3b: NPC event drawer handler + fetch
  const handleEventNpcDrawer = (npc_id, display_name, flag) => {
    console.log('[EVENT_NPC_DRAWER] opened npc=', npc_id,
      'event=', activeEvent?.id)
    setSelectedEventNpc({ npc_id, display_name, flag })
    setEventNpcMessage('')  // '' = loading state
    setEventNpcDrawerOpen(true)
    fetchEventNpcDialogue(npc_id)
  }

  const fetchEventNpcDialogue = async (npc_id) => {
    try {
      console.log('[EVENT_NPC_DIALOGUE] requesting npc=',
        npc_id, 'event=', activeEvent?.id)
      const res = await api.getEventNPCDialogue(
        sessionId,
        npc_id,
        activeEvent.id,
        { title: activeEvent.title, summary: activeEvent.summary }
      )
      setEventNpcMessage(res.message)
    } catch (err) {
      console.log('[EVENT_NPC_DIALOGUE] failed:', err.message)
      setEventNpcMessage('Channel unavailable \u2014 try again shortly.')
    }
  }

  // E5: Intercept — open confirmation modal instead of firing API directly
  const handleResolveEvent = (resolutionValue, choiceText) => {
    setPendingResolution({ resolutionValue, choiceText })
    setMikeConfirmRead('')
    setConfirmModalOpen(true)
    fetchMikeConfirmRead(resolutionValue, choiceText)
  }

  const fetchMikeConfirmRead = async (resolutionValue, choiceText) => {
    try {
      const res = await api.getMikeConfirmRead(
        sessionId,
        activeEvent.id,
        activeEvent.title,
        choiceText
      )
      setMikeConfirmRead(res.read)
    } catch (err) {
      console.log('[MIKE_CONFIRM] fetch failed:', err.message)
      setMikeConfirmRead(
        'This decision will have consequences. Proceed carefully.'
      )
    }
  }

  const handleConfirmResolution = async () => {
    if (!pendingResolution || resolving) return
    setResolving(true)
    try {
      const result = await api.briefingResolveEvent(
        sessionId,
        activeEvent.id,
        pendingResolution.resolutionValue
      )
      setConfirmModalOpen(false)
      setPendingResolution(null)
      setMikeConfirmRead(null)

      // Update local state
      setDailyEvents(prev => prev.map(e =>
        e.id === activeEvent.id ? { ...e, resolved: true, resolution: pendingResolution.resolutionValue } : e
      ))
      setDayStatus(prev => ({
        events_resolved: result.events_resolved,
        events_required: result.events_required,
        can_end_day: result.can_end_day,
        deals_today: (result.deals_today?.length > 0)
          ? result.deals_today
          : prev.deals_today || [],
      }))
      setActiveEvent({ ...activeEvent, resolved: true, resolution: pendingResolution.resolutionValue })
      console.log('[10B-2] Resolution consequences:', result.consequences)
      setResolutionConsequences(result.consequences || null)

      if (result.game_state && onGsUpdate) {
        onGsUpdate(result.game_state)
      }

      // Show resolution beat if mike_beat present
      if (result.mike_beat) {
        setResolutionBeat({
          mike_beat: result.mike_beat,
          budget_delta: result.consequences?.budget_delta || 0,
          stability_delta: result.consequences?.stability_delta || 0,
        })
      } else {
        // No beat — transition to event_summary directly
        setBriefingState('event_summary')
        if (onEventResolved) onEventResolved(activeEvent, pendingResolution.resolutionValue)
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

  const [endingDay, setEndingDay] = useState(false)

  async function handleEndDay() {
    setEndingDay(true)
    setBriefingState('end_day')
    try {
      if (onEndDay) await onEndDay()
    } finally {
      setEndingDay(false)
    }
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

  // ── Render: Resolution Beat (E5) ─────────────────────────────────────────
  if (resolutionBeat && activeEvent) {
    return (
      <div className="briefing-resolution-beat">
        <div className="briefing-beat-header">
          <span className="briefing-severity-badge briefing-severity-resolved">RESOLVED</span>
          <span className="briefing-beat-title">{activeEvent.title}</span>
        </div>

        {resolutionBeat.mike_beat && (
          <div className="briefing-beat-mike">
            <span className="briefing-modal-mike-label">MIKE SOREL</span>
            <p>{resolutionBeat.mike_beat}</p>
          </div>
        )}

        <div className="briefing-beat-consequences">
          {resolutionBeat.budget_delta !== 0 && (
            <span className={resolutionBeat.budget_delta > 0
              ? 'briefing-delta-positive' : 'briefing-delta-negative'}>
              Budget {resolutionBeat.budget_delta > 0 ? '+' : ''}{resolutionBeat.budget_delta}B
            </span>
          )}
          {resolutionBeat.stability_delta !== 0 && (
            <span className={resolutionBeat.stability_delta > 0
              ? 'briefing-delta-positive' : 'briefing-delta-negative'}>
              Stability {resolutionBeat.stability_delta > 0 ? '+' : ''}{resolutionBeat.stability_delta}%
            </span>
          )}
        </div>

        <button
          className="briefing-modal-confirm"
          onClick={() => {
            setResolutionBeat(null)
            setBriefingState('hub')
            if (onEventResolved) onEventResolved(activeEvent, activeEvent.resolution)
          }}>
          CLOSE
        </button>
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
              <div key={d.npc_id} className="briefing-event-npc-card"
                style={{ cursor: 'pointer' }}
                onClick={() => handleEventNpcDrawer(d.npc_id, npcInfo.name, npcInfo.flag)}>
                <div className="briefing-event-npc-header">
                  <span className="briefing-event-npc-flag" style={{ background: npcInfo.color }}>
                    {npcInfo.flag}
                  </span>
                  <span className="briefing-event-npc-name">{d.npc_name}</span>
                </div>
                <p className="briefing-event-npc-message">{d.message}</p>
                <span className="briefing-npc-open-hint">{'\u2193'} open channel</span>
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

        {/* E3b: NPC event drawer */}
        {eventNpcDrawerOpen && selectedEventNpc && (
          <div className="briefing-advisor-drawer briefing-event-npc-drawer">
            <div className="briefing-npc-drawer-header">
              <span>{selectedEventNpc.flag} {selectedEventNpc.display_name}</span>
              <button
                className="briefing-drawer-close"
                onClick={() => {
                  setEventNpcDrawerOpen(false)
                  setSelectedEventNpc(null)
                  setEventNpcMessage(null)
                }}>
                {'\u2715'}
              </button>
            </div>
            <div className="briefing-npc-drawer-body">
              {eventNpcMessage === ''
                ? <span className="briefing-npc-loading">...</span>
                : <p>{eventNpcMessage}</p>
              }
            </div>
          </div>
        )}

        {/* Your Move — real choices */}
        <div className="briefing-event-choices">
          <p className="briefing-choices-label">YOUR MOVE</p>
          {eventChoices.map((choice, i) => {
            // Handle both formats: Haiku objects {label,text,hint}
            // and legacy strings from _getDefaultChoices()
            const isObject = typeof choice === 'object' && choice !== null
            const choiceText = isObject ? choice.text : choice
            const choiceHint = isObject ? choice.hint : null
            const resolutionValue = isObject
              ? `${choice.label}: ${choice.text}`
              : choice
            console.log('[CHOICE_RENDER] source=',
              typeof choice === 'object' ? 'haiku' : 'legacy',
              'text=', choiceText?.slice(0, 40))

            return (
              <button key={i} className="briefing-choice-btn"
                onClick={() => handleResolveEvent(resolutionValue, choiceText)}
                disabled={resolving}>
                <span className="briefing-choice-letter">
                  {String.fromCharCode(65 + i)}
                </span>
                <span className="briefing-choice-text">{choiceText}</span>
                {choiceHint && (
                  <span className="briefing-choice-hint">{choiceHint}</span>
                )}
              </button>
            )
          })}
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

        {/* E5: Mike confirmation modal */}
        {confirmModalOpen && (
          <div className="briefing-modal-overlay">
            <div className="briefing-modal">

              <div className="briefing-modal-event-title">
                {activeEvent?.title}
              </div>

              <div className="briefing-modal-choice">
                <span className="briefing-modal-choice-label">YOUR MOVE</span>
                <span>{pendingResolution?.choiceText}</span>
              </div>

              <div className="briefing-modal-mike">
                <span className="briefing-modal-mike-label">
                  MIKE SOREL {'\u2014'} CHIEF OF STAFF
                </span>
                <div className="briefing-modal-mike-body">
                  {mikeConfirmRead === ''
                    ? <span className="briefing-npc-loading">...</span>
                    : <p>{mikeConfirmRead}</p>
                  }
                </div>
              </div>

              <div className="briefing-modal-actions">
                <button
                  className="briefing-modal-confirm"
                  onClick={handleConfirmResolution}
                  disabled={mikeConfirmRead === '' || resolving}>
                  CONFIRM
                </button>
                <button
                  className="briefing-modal-back"
                  onClick={() => {
                    setConfirmModalOpen(false)
                    setPendingResolution(null)
                    setMikeConfirmRead(null)
                  }}>
                  GO BACK
                </button>
              </div>

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
          Events reviewed: {dayStatus.events_resolved} / 3
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
            {'\u2713'} BRIEFING COMPLETE
          </span>
          <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0.25rem 0' }}>
            You may continue working events, or end the day.
          </p>
        </div>
      )}

      {/* Advisory Council Panel */}
      <div className="advisory-council-panel">
        <div className="advisory-council-header" onClick={() => setCouncilOpen(!councilOpen)}>
          <span className="advisory-council-title">ADVISORY COUNCIL</span>
          <span className="advisory-council-toggle">{councilOpen ? '\u2212' : '+'}</span>
        </div>
        {councilOpen && (
          <div className="advisory-council-body">
            {morningBriefingLoading && (
              <div className="advisory-council-loading">Assembling briefings...</div>
            )}
            {/* Chief of Staff — always shown */}
            {chiefOfStaff && (
              <div className="advisor-briefing-card advisor-briefing-card--chief"
                   onClick={() => {
                     if (expandedAdvisor?.role === 'chief_of_staff') {
                       setExpandedAdvisor(null)
                       return
                     }
                     setExpandedAdvisor({ role: 'chief_of_staff' })
                   }}
                   style={{ cursor: 'pointer' }}>
                <div className="advisor-briefing-header">
                  <span className="advisor-briefing-icon">{chiefOfStaff.icon}</span>
                  <div className="advisor-briefing-meta">
                    <span className="advisor-briefing-name">{chiefOfStaff.name}</span>
                    <span className="advisor-briefing-label">{chiefOfStaff.label}</span>
                  </div>
                </div>
                <div className="advisor-briefing-text">{chiefOfStaff.text}</div>
                {expandedAdvisor?.role === 'chief_of_staff' && (
                  <div className="advisor-profile-expand">
                    <div className="advisor-profile-divider"/>
                    <div className="advisor-profile-text">
                      Mikhail Sorel cannot be dismissed. He serves Europa regardless of who leads it.
                    </div>
                  </div>
                )}
              </div>
            )}
            {/* Hired advisor cards */}
            {(advisorBriefings || []).map(advisor => {
              return (
                <div key={advisor.id}
                     className="advisor-briefing-card"
                     onClick={() => handleAdvisorClick(advisor)}
                     style={{
                       borderLeftColor: ROLE_COLORS[advisor.role] || 'rgba(255,255,255,0.15)',
                       cursor: 'pointer'
                     }}>
                  <div className="advisor-briefing-header">
                    <span className="advisor-briefing-icon">{advisor.icon}</span>
                    <div className="advisor-briefing-meta">
                      <span className="advisor-briefing-name">{advisor.name}</span>
                      <span className="advisor-briefing-label">{advisor.label}</span>
                    </div>
                  </div>
                  <div className="advisor-briefing-text">{advisor.text}</div>
                  {expandedAdvisor?.role === advisor.role && (
                    <div className="advisor-profile-expand">
                      {profileLoading && (
                        <div className="advisor-profile-loading">
                          Consulting Mike...
                        </div>
                      )}
                      {advisorProfile && !profileLoading && (
                        <>
                          <div className="advisor-profile-divider"/>
                          <div className="advisor-profile-stats">
                            <span>Capability: {statLabel(advisorProfile.competence)}</span>
                            <span>Loyalty: {statLabel(advisorProfile.loyalty)}</span>
                            <span>Trust: {statLabel(advisorProfile.trust)}</span>
                            <span>Since Day {advisorProfile.hire_day}</span>
                          </div>
                          <div className="advisor-profile-text">
                            {advisorProfile.profile_text}
                          </div>
                          <div className="advisor-profile-actions">
                            <div className="advisor-action-row">
                              <button
                                className="advisor-action-btn advisor-action-btn--dismiss"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleAdvisorDismiss(advisor.role)
                                }}>
                                Dismiss
                              </button>
                              <span className="advisor-consequence advisor-consequence--dismiss">
                                {advisorProfile.dismiss_consequence}
                              </span>
                            </div>
                            <div className="advisor-action-row">
                              <button
                                className="advisor-action-btn advisor-action-btn--eliminate"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleAdvisorEliminate(advisor.role)
                                }}>
                                Eliminate
                              </button>
                              <span className="advisor-consequence advisor-consequence--eliminate">
                                {advisorProfile.eliminate_consequence}
                              </span>
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
            {/* Available advisor pool cards */}
            {availableAdvisors.map(advisor => {
              // Skip already hired archetypes
              const hiredArchetypes = (advisorBriefings || []).map(a => a.role)
              if (hiredArchetypes.includes(advisor.archetype)) return null
              return (
                <div key={advisor.archetype}
                     className="advisor-briefing-card advisor-briefing-card--available"
                     style={{
                       borderLeftColor: ROLE_COLORS[advisor.archetype] || 'rgba(255,255,255,0.15)',
                       cursor: 'pointer',
                       opacity: 0.6
                     }}
                     onClick={() => handlePoolAdvisorClick(advisor)}>
                  <div className="advisor-briefing-header">
                    <span className="advisor-briefing-icon">{advisor.icon}</span>
                    <div className="advisor-briefing-meta">
                      <span className="advisor-briefing-name">{advisor.name}</span>
                      <span className="advisor-briefing-label">{advisor.label} — Available</span>
                    </div>
                    <span className="advisor-hire-cost">${advisor.hire_cost || '0.5'}B</span>
                  </div>
                  {expandedPoolAdvisor?.archetype === advisor.archetype && (
                    <div className="advisor-profile-expand">
                      {poolProfileLoading && (
                        <div className="advisor-profile-loading">
                          Consulting Mike...
                        </div>
                      )}
                      {poolProfileCache[advisor.archetype] && !poolProfileLoading && (
                        <>
                          <div className="advisor-profile-divider"/>
                          <div className="advisor-profile-stats">
                            <span>Capability: {statLabel(poolProfileCache[advisor.archetype].competence)}</span>
                            <span>Loyalty: {statLabel(poolProfileCache[advisor.archetype].loyalty)}</span>
                          </div>
                          <div className="advisor-profile-text">
                            {poolProfileCache[advisor.archetype].profile_text}
                          </div>
                          <div className="advisor-hire-recommendation">
                            {poolProfileCache[advisor.archetype].hire_recommendation}
                          </div>
                          <button
                            className="advisor-action-btn advisor-action-btn--hire"
                            disabled={hiring}
                            onClick={(e) => {
                              e.stopPropagation()
                              handleHire(advisor)
                            }}>
                            {hiring ? 'Hiring...' : `Hire — $${advisor.hire_cost || '0.5'}B`}
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

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
        <span>EVENTS REVIEWED: {dayStatus.events_resolved} / 3</span>
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

      {/* 10B-3: Today's Decisions — always visible */}
      {(() => {
        // Use whichever source has more deals — gameState (optimistic/immediate) or dayStatus (server)
        const gsDeals = gameState?.deals_today || []
        const dsDeals = dayStatus?.deals_today || []
        const visibleDeals = gsDeals.length >= dsDeals.length ? gsDeals : dsDeals
        return (
      <div className="todays-deals">
        <h4 className="deals-header">TODAY'S DECISIONS</h4>
        {dealsRefreshing && (
          <div className="deals-loading"><span>Updating day record...</span></div>
        )}
        {visibleDeals.length === 0 && !dealsRefreshing && (
          <div className="decisions-empty">
            <span>No decisions recorded yet today.</span>
          </div>
        )}
        {visibleDeals.length > 0 && (<>

          {visibleDeals.map(deal => {
            const flagMap = { usa: '🇺🇸', arabia: '🇸🇦', eu: '🇪🇺', dprg: '🇰🇵', russia: '🇷🇺', china: '🇨🇳' }
            const flag = flagMap[deal.npc_id] || '🏳️'
            const delta = deal.relation_delta
            const isExpanded = expandedDealId === deal.id
            const gm = deal.gm_consequences
            return (
              <div key={deal.id} className={`deal-entry ${isExpanded ? 'expanded' : ''}`}>
                <div
                  className="deal-item deal-item-clickable"
                  onClick={() => setExpandedDealId(isExpanded ? null : deal.id)}
                >
                  <span className="deal-npc">{flag} {deal.npc_name}</span>
                  <span className="deal-summary">{deal.briefing_summary}</span>
                  <span className="deal-meta">
                    <span className="deal-source">
                      {deal.is_backchannel ? '🔒 Covert'
                        : deal.source === 'world_event' ? '🌐 Event'
                        : '📋 Direct'}
                    </span>
                    {delta != null && delta !== 0 && (
                      <span className={`deal-delta ${delta > 0 ? 'positive' : 'negative'}`}>
                        {delta > 0 ? '+' : ''}{delta}
                      </span>
                    )}
                    <span className="deal-expand-icon">{isExpanded ? '▲' : '▼'}</span>
                  </span>
                </div>
                {isExpanded && gm && (
                  <div className="deal-consequences-panel">
                    <div className="deal-full-text">{deal.deal_text}</div>
                    <h5 className="deal-impact-header">DIPLOMATIC IMPACT</h5>
                    {(gm.affected_relations || Object.entries(gm.relations_delta || {})).length > 0 && (
                      <div className="deal-affected-list">
                        {/* If affected_relations exists (qualitative), use it */}
                        {gm.affected_relations ? gm.affected_relations.map((ar, i) => (
                          <div key={i} className="deal-affected-item">
                            <span className={`deal-direction-icon ${ar.direction}`}>
                              {ar.direction === 'positive' ? '▲' : ar.direction === 'negative' ? '▼' : '—'}
                            </span>
                            <span className="deal-affected-npc">{flagMap[ar.npc] || ''} {(ar.npc || '').toUpperCase()}</span>
                            <span className="deal-affected-reason">{ar.reason}</span>
                          </div>
                        )) : Object.entries(gm.relations_delta || {}).map(([npc, d]) => {
                          const dir = d > 0 ? 'positive' : d < 0 ? 'negative' : 'neutral'
                          const reason = d > 3 ? 'alignment strengthened'
                            : d > 0 ? 'relations improve modestly'
                            : d < -3 ? 'significant diplomatic strain'
                            : d < 0 ? 'relations cool slightly'
                            : 'monitoring situation'
                          return (
                            <div key={npc} className="deal-affected-item">
                              <span className={`deal-direction-icon ${dir}`}>
                                {d > 0 ? '▲' : d < 0 ? '▼' : '—'}
                              </span>
                              <span className="deal-affected-npc">{flagMap[npc] || ''} {npc.toUpperCase()}</span>
                              <span className="deal-affected-reason">{reason}</span>
                            </div>
                          )
                        })}
                      </div>
                    )}
                    {gm.historian_note && (
                      <div className="deal-historian-note">{gm.historian_note}</div>
                    )}
                    {/* Advisor reactions */}
                    {deal.advisor_reactions?.length > 0 && (
                      <div className="advisor-reactions-section">
                        <h5 className="deal-impact-header">ADVISOR REACTIONS</h5>
                        {deal.advisor_reactions.map((ar, i) => {
                          const icon = ar.stance === 'approve' ? '👍' : ar.stance === 'oppose' ? '👎' : '👋'
                          const stanceClass = ar.stance === 'approve' ? 'stance-approve' : ar.stance === 'oppose' ? 'stance-oppose' : 'stance-neutral'
                          return (
                            <div key={i} className={`advisor-reaction-item ${stanceClass}`}>
                              <span className="advisor-reaction-icon">{icon}</span>
                              <span className="advisor-reaction-name">{ar.advisor_name}</span>
                              <span className="advisor-reaction-type">({ar.advisor_type?.replace('_', ' ')})</span>
                              <span className="advisor-reaction-text">{ar.reasoning}</span>
                            </div>
                          )
                        })}
                      </div>
                    )}
                    {/* Dismiss deal button */}
                    {deal.id && (
                      <div className="deal-dismiss-row">
                        <button
                          className="advisor-action-btn advisor-action-btn--dismiss"
                          onClick={async (e) => {
                            e.stopPropagation()
                            try {
                              const res = await api.dismissDeal(sessionId, deal.id)
                              console.log('[DISMISS_UI] success dealId=', deal.id)
                              if (res.game_state && onGsUpdate) onGsUpdate(res.game_state)
                            } catch (err) {
                              console.error('[DISMISS_UI] failed:', err)
                            }
                          }}
                        >
                          DISMISS DEAL
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}

          {/* FIX 5: Advisor notes on today's decisions */}
          {gameState?.advisors_assigned_today?.length > 0 && (
            <div className="advisor-notes-section">
              <h5 className="advisor-notes-header">ADVISOR NOTES</h5>
              {gameState.advisors_assigned_today.map(adv => {
                const name = adv.name || adv.advisor_name || adv.type || 'Advisor'
                const analysis = adv.cached_analysis || adv.latest_analysis || null
                if (!analysis) return null
                return (
                  <div key={name} className="advisor-note-item">
                    <span className="advisor-note-name">{name}:</span>
                    <span className="advisor-note-text">{analysis}</span>
                  </div>
                )
              })}
            </div>
          )}
        </>)}
      </div>
        )
      })()}

      {/* End day button */}
      {canEndDay && (
        <button
          className="briefing-end-day-btn"
          onClick={handleEndDay}
          disabled={endingDay}
        >
          {endingDay ? 'Processing...' : `End Day ${currentDay} \u2192`}
        </button>
      )}
    </div>
  )
}
