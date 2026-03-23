import { useState, useRef, useEffect, useMemo } from 'react'
import { api } from '../api'
import StatusBar from './StatusBar'
import RelationBadges from './RelationBadges'
import DialoguePanel from './DialoguePanel'
import OffersPanel from './OffersPanel'
import ConsequencesPanel from './ConsequencesPanel'
import SkimPanel from './SkimPanel'
import InjectPanel from './InjectPanel'
import InterceptPanel from './InterceptPanel'
import EotPanel from './EotPanel'
import EndingScreen from './EndingScreen'
import EventBanner from './EventBanner'
import NegotiationPanel from './NegotiationPanel'
import ShadowCabinet from './ShadowCabinet'
import ElectionPanel from './ElectionPanel'
import EndingPanel from './EndingPanel'
import IntelAllocationPanel from './IntelAllocationPanel'
import AdvisorPanel from './AdvisorPanel'
import BackchannelModal from './BackchannelModal'
import PromiseTracker from './PromiseTracker'
import SummitModal from './SummitModal'
import SummitCommitmentTracker from './SummitCommitmentTracker'
import DebugPanel from './DebugPanel'
import TestPanel from './TestPanel'
import DashboardLayout from './DashboardLayout'
import DomesticTab from './DomesticTab'
import BriefingSummaryCard from './BriefingSummaryCard'
import BriefingScreen from './BriefingScreen'
import ExileDashboard from './ExileDashboard'
import LeakCrisisModal from './LeakCrisisModal'
import BiographyModal from './BiographyModal'

/**
 * GameScreen manages the full turn lifecycle:
 *
 * PHASE 0 — dialogue      : show NPC messages + offers panel
 * PHASE 1 — consequences  : show choice result + skim panel
 *                           (or inject panel if Option G)
 *                         : FEATURE 2 — brigade secondary prompt (if available)
 * PHASE 2 — eot           : show skim/inject result + EOT effects + intercepts
 *                           → then auto-advance to next turn (PHASE 0)
 *                         : FEATURE 3 — brigade aftermath banner (if flag set)
 */

const PHASE = {
  DIALOGUE: 'dialogue',
  CONSEQUENCES: 'consequences',
  BRIGADE_PROMPT: 'brigade_prompt',   // FEATURE 2: secondary brigade prompt
  INJECT_PROMPT: 'inject_prompt',
  EOT: 'eot',
  ENDED: 'ended',
}

const NPC_INFO = {
  usa:    { label: 'Bill Hartwell',    flag: '🇺🇸', letter: 'A' },
  arabia: { label: 'Sadam',            flag: '🛢️',  letter: 'B' },
  eu:     { label: 'Marsha',           flag: '🇪🇺', letter: 'C' },
  dprg:   { label: 'Ji-won Ryang',     flag: '⚡',  letter: 'D' },
  russia: { label: 'Nikolai Volkov',   flag: '🇷🇺', letter: 'R' },
  china:  { label: 'Wei Jianming',     flag: '🇨🇳', letter: 'W' },
}

export default function GameScreen({ sessionId, initialData, onGameEnd, onRestart, onSnapshotLoad }) {
  const [gs, setGs] = useState(initialData.game_state)
  const [dialogue, setDialogue] = useState(initialData.dialogue)
  const [offers, setOffers] = useState(initialData.offers)
  const [skimOptions, setSkimOptions] = useState(initialData.skim_options || [])
  const [blackmailActive, setBlackmailActive] = useState(initialData.blackmail_active || false)
  const [phase, setPhase] = useState(PHASE.DIALOGUE)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // FEATURE 1: Shadow Cabinet state
  const [shadowCabinetOpen, setShadowCabinetOpen] = useState(false)

  // FEATURE 2: Brigade secondary prompt
  const [brigadeAvailable, setBrigadeAvailable] = useState(false)
  const [brigadeLoading, setBrigadeLoading] = useState(false)
  const [brigadeResult, setBrigadeResult] = useState(null)

  // Addition 2: Pre-skim EOT drain projection
  const [drainProjection, setDrainProjection] = useState(null)

  // FEATURE 3: Brigade aftermath
  const [aftermathLoading, setAftermathLoading] = useState(false)
  const [aftermathResult, setAftermathResult] = useState(null)

  // Phase 1 data
  const [consequences, setConsequences] = useState([])
  const [blackmailResult, setBlackmailResult] = useState(null)

  // Phase 2 data
  const [skimMessages, setSkimMessages] = useState([])
  const [corruptionAlert, setCorruptionAlert] = useState(null)
  const [patriotMessage, setPatriotMessage] = useState(null)
  const [intercepts, setIntercepts] = useState([])
  const [eotMessages, setEotMessages] = useState([])

  // 8D: The Leak crisis modal
  const [showLeakCrisis, setShowLeakCrisis] = useState(false)

  // Inject sub-choice
  const [injectOptions, setInjectOptions] = useState([])

  // Ending
  const [ending, setEnding] = useState(null)

  // Session 4D: Intel allocation (done before skim each turn)
  const [intelAllocated, setIntelAllocated] = useState(false)

  // Session 2 Item 6: Diplomatic crisis modal — broken deal messages
  const [dipCrisisMessages, setDipCrisisMessages] = useState([])

  // Election → diplomatic choice: stash election results while player picks a deal
  const [electionConseqStash, setElectionConseqStash] = useState(null)

  // fixes_10 Fix 7: Debug panel — dev only, Ctrl+Shift+D
  const [debugOpen, setDebugOpen] = useState(false)

  // Domestic Affairs Tab
  const [activeTab, setActiveTab] = useState('foreign')

  // FEATURE 1: Confirmation dialog — intercepts choice + skim before committing
  // { type: 'choice'|'skim', value: letter|choiceNum, text: string } | null
  const [pendingConfirm, setPendingConfirm] = useState(null)

  // Stage 4: World events
  const [currentEvent, setCurrentEvent] = useState(initialData.current_event || null)

  // 10B-2: Intel loading state per NPC and results
  const [intelLoading, setIntelLoading] = useState({})
  const [intelResults, setIntelResults] = useState({})

  // Session 7A Step 5: Era transition + Historian
  const [eraTransitionSuggestion, setEraTransitionSuggestion] = useState(null)
  const [historianModal, setHistorianModal] = useState(null) // { era, summary, isOnDemand }
  const [historianLoading, setHistorianLoading] = useState(false)
  const [showBiography, setShowBiography] = useState(false)

  // Stage 4: Negotiation
  const [negotiatingNpc, setNegotiatingNpc] = useState(null)   // 'usa'|'arabia'|'eu'|'dprg'|null
  // counterOffers: { [letter]: counterOffer } — displayed in OffersPanel
  const [counterOffers, setCounterOffers] = useState({})
  // per-NPC chat history, keyed by npcKey — survives panel close/reopen within same turn
  // shape: { [npcKey]: { messages: [], pendingOffers: [] } }
  const [chatHistories, setChatHistories] = useState({})

  // Session 7D: Backchannel modal state
  const [backchannelNpc, setBackchannelNpc] = useState(null)  // npcKey or null

  // Session 7E: UN Summit modal state
  const [summitOpen, setSummitOpen] = useState(false)

  // 8C: Exile state
  const [exileMessages, setExileMessages] = useState([])
  const [exileDialogue, setExileDialogue] = useState(null) // Fix E: AI-generated NPC dialogue from reach-out

  // FIX C: Track in_exile transitions for post-return game load
  const prevInExileRef = useRef(gs?.in_exile)

  const scrollRef = useRef(null)

  // Session log ref — accumulates rich per-turn data for export log auditing.
  // Each entry: { turn, choiceText, npcSided, consequences, brigadeOp, skimLabel,
  //               skimNational, skimPersonal, eotEffects, budgetStart, budgetEnd,
  //               personalStart, personalEnd, stabilityStart, stabilityEnd,
  //               approvalStart, approvalEnd, epitaph }
  // FIX 4: Persist to localStorage so turns survive browser refresh.
  const _logKey = `session_log_${sessionId}`
  const _savedLog = useMemo(() => {
    try { return JSON.parse(localStorage.getItem(_logKey) || '[]') }
    catch { return [] }
  }, [_logKey])
  const sessionLogRef = useRef(_savedLog)
  const _persistLog = () => {
    try { localStorage.setItem(_logKey, JSON.stringify(sessionLogRef.current)) }
    catch { /* quota exceeded — non-fatal */ }
  }
  // Track start-of-turn snapshot for delta calculation
  const turnStartRef = useRef({
    budget: initialData.game_state?.budget ?? 0,
    personal: initialData.game_state?.personal_wealth ?? 0,
    stability: initialData.game_state?.stability ?? 0,
    approval: initialData.game_state?.public_approval ?? 0,
  })
  // Accumulator for current turn being built
  const currentTurnEntryRef = useRef({})

  // Scroll to top of game area whenever phase changes
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0
  }, [phase])

  // FIX C: Detect exile → active transition and fetch fresh turn data
  useEffect(() => {
    const wasInExile = prevInExileRef.current
    const isInExile = gs?.in_exile
    prevInExileRef.current = isInExile

    if (wasInExile && !isInExile) {
      console.log(`[FIXC] post-return state in_exile=${isInExile} restoration_active=${gs?.restoration_active} turn_button_enabled=${!!_nextTurnRef.current}`)
      console.log('[FIXC] exile→active transition detected, fetching fresh turn data')
      setLoading(true)
      api.getGame(sessionId).then(data => {
        setGs(data.game_state)
        setDialogue(data.dialogue)
        setOffers(data.offers)
        setSkimOptions(data.skim_options || [])
        setBlackmailActive(data.blackmail_active || false)
        setConsequences([])
        setSkimMessages([])
        setEotMessages([])
        setIntercepts([])
        setExileMessages([])
        setExileDialogue(null)
        setBrigadeAvailable(false)
        setBrigadeResult(null)
        setAftermathResult(null)
        setDrainProjection(null)
        setIntelAllocated(false)
        setElectionConseqStash(null)
        setEraTransitionSuggestion(null)
        setCurrentEvent(data.current_event || null)
        setNegotiatingNpc(null)
        setCounterOffers({})
        setChatHistories({})
        setPhase(PHASE.DIALOGUE)
        // FIXC2: Populate _nextTurnRef so handleContinue has valid data after restoration
        _nextTurnRef.current = {
          dialogue: data.dialogue || data.next_dialogue,
          offers: data.offers || data.next_offers,
          skimOptions: data.skim_options || data.next_skim_options,
          blackmailActive: data.blackmail_active || data.next_blackmail,
          status: data.status,
          ending: data.ending || null,
          event: data.next_event || null,
        }
        console.log(`[FIXC2] _nextTurnRef populated after restoration status=${data.status} dialogue_lines=${data.dialogue?.length || 0}`)
        console.log('[FIXC] fresh turn data loaded, phase=DIALOGUE, day:', data.game_state?.current_day ?? data.game_state?.current_turn)
      }).catch(err => {
        console.error('[FIXC] Failed to fetch post-return game data:', err)
        setError('Failed to load post-return game data. Please refresh.')
      }).finally(() => {
        setLoading(false)
      })
    }
  }, [gs?.in_exile, sessionId])

  // Domestic Affairs: Intel allocation gate removed
  useEffect(() => {
    console.log('[BUDGET] Intel allocation gate removed — using persistent domestic allocation')
  }, [])

  // fixes_10 Fix 7: Debug/Cheat panel — now locked behind test account check.
  // Ctrl+Shift+D removed. Cheat panel opened via TestPanel "Open Cheat Panel" button only.

  const clearError = () => setError(null)

  // ── FEATURE 1: Confirmation dialog helpers ────────────────────────────────
  function requestConfirmChoice(letter) {
    const allOffers = offers || []
    const counter = counterOffers[letter]
    const base = allOffers.find(o => o.letter === letter)
    const text = counter
      ? `[NEGOTIATED] ${counter.text}`
      : base?.text || `Option ${letter}`
    // fixes_21: Pass deal conflicts from offer so confirm modal can warn
    const dealConflicts = base?.deal_conflicts || []
    setPendingConfirm({ type: 'choice', value: letter, text, dealConflicts })
  }

  function requestConfirmSkim(choice) {
    const opt = (skimOptions || []).find(o => o.choice === choice)
    const text = opt?.label || `Option ${choice}`
    setPendingConfirm({ type: 'skim', value: choice, text })
  }

  async function handleConfirmExecute() {
    if (!pendingConfirm) return
    const { type, value } = pendingConfirm
    setPendingConfirm(null)
    if (type === 'choice') await _executeChoice(value)
    else if (type === 'skim') await _executeSkim(value)
  }

  function handleConfirmCancel() {
    setPendingConfirm(null)
  }

  // ── PHASE 0 → 1: player picks A-G ───────────────────────────────────────
  async function handleChoice(letter) {
    requestConfirmChoice(letter)
  }

  async function _executeChoice(letter) {
    clearError()
    setLoading(true)
    try {
      // Snapshot start-of-turn values for export log delta calculations
      if (gs) {
        turnStartRef.current = {
          budget:    gs.budget ?? 0,
          personal:  gs.personal_wealth ?? 0,
          stability: gs.stability ?? 0,
          approval:  gs.public_approval ?? 0,
        }
      }

      const res = await api.postAction(sessionId, letter)

      // Option F — escape
      if (res.action === 'escape') {
        setGs(res.game_state)
        setEnding(res.ending)
        setPhase(PHASE.ENDED)
        onGameEnd && onGameEnd(res.ending)
        return
      }

      // Option G — inject sub-prompt
      if (res.action === 'inject_prompt') {
        setGs(res.game_state)
        setInjectOptions(res.inject_options || [])
        setPhase(PHASE.INJECT_PROMPT)
        return
      }

      // Normal A-E choice — capture choice text for session log
      const allOffers = offers || []
      const counter = counterOffers[letter]
      const base = allOffers.find(o => o.letter === letter)
      const choiceText = counter
        ? `[NEGOTIATED] ${counter.text}`
        : base?.text || `Option ${letter}`
      const npcSided = counter?.npc || base?.npc || null

      // fixes_16: Preserve election data if election already recorded this turn
      const _prevEntry = currentTurnEntryRef.current
      currentTurnEntryRef.current = {
        ...(_prevEntry.electionChoice ? {
          electionChoice: _prevEntry.electionChoice,
          electionConsequences: _prevEntry.electionConsequences,
        } : {}),
        turn: gs?.current_turn ?? '?',
        choiceText,
        npcSided,
        consequences: res.consequences || [],
        brigadeOp: null,
        skimLabel: null, skimNational: 0, skimPersonal: 0,
        eotEffects: [],
        budgetStart:    turnStartRef.current.budget,
        budgetEnd:      null,
        personalStart:  turnStartRef.current.personal,
        personalEnd:    null,
        stabilityStart: turnStartRef.current.stability,
        stabilityEnd:   null,
        approvalStart:  turnStartRef.current.approval,
        approvalEnd:    null,
        epitaph: null,
      }

      setGs(res.game_state)
      // Merge stashed election consequences with deal consequences
      const dealConseqs = res.consequences || []
      if (electionConseqStash) {
        setConsequences([...(electionConseqStash.consequences || []), '—', ...dealConseqs])
        setElectionConseqStash(null)
      } else {
        setConsequences(dealConseqs)
      }
      setBlackmailResult(res.blackmail_result)
      setSkimOptions(res.skim_options || [])
      setBlackmailActive(false)
      setBrigadeAvailable(res.brigade_available || false)
      setBrigadeResult(null)
      setDrainProjection(res.drain_projection || null)

      // 9.5A-Shadow: Always auto-skip skim prompt — skim rate is set via
      // persistent slider in Shadow Cabinet POWER BASE drawer, not per-turn.
      // Legacy per-turn skim prompt removed. Auto-submit choice 1 to trigger EOT.
      if (!(res.brigade_available)) {
        console.log('[9.5A-Shadow] Auto-skipping skim prompt (persistent skim slider in Cabinet)')
        await _executeSkim(1)
        return
      }

      setPhase(PHASE.CONSEQUENCES)

    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── FEATURE 2: Brigade secondary prompt ───────────────────────────────────
  const [brigadeTargetNpc, setBrigadeTargetNpc] = useState('usa')   // for op 3

  async function handleBrigadeDeploy(operation, targetNpc = '') {
    clearError()
    setBrigadeLoading(true)
    try {
      const res = await api.deployBrigades(sessionId, operation > 0, operation, targetNpc)
      setGs(res.game_state)
      const opNames = { 0: 'Stand Down', 1: 'Propaganda Campaign', 2: 'Domestic Suppression', 3: 'Foreign Influence Ops', 4: 'Covert Security Apparatus', 5: 'Black Operation', 6: 'State Media Takeover' }
      const opLabel = opNames[operation] || `Op ${operation}`
      const brigadeLabel = operation > 0
        ? `${opLabel}${targetNpc ? ` (target: ${targetNpc.toUpperCase()})` : ''}`
        : 'Stand Down — not deployed'
      // PRE-SESSION 4 FIX (BUG F): Include full brigade outcome in export log
      const brigadeOutcome = res.messages || []
      currentTurnEntryRef.current.brigadeOp = brigadeLabel
      currentTurnEntryRef.current.brigadeOutcome = brigadeOutcome
      setBrigadeResult(res.messages?.join(' · ') || (operation > 0 ? 'Brigades deployed.' : 'Brigades stood down.'))
    } catch (e) {
      setError(e.message)
    } finally {
      setBrigadeLoading(false)
      // After brigade decision (either way), hide the prompt
      setBrigadeAvailable(false)
    }
  }

  // ── Session 4D: Intel allocation handler ───────────────────────────────────
  async function handleIntelAllocate(allocation) {
    clearError()
    try {
      const res = await api.intelAllocation(sessionId, allocation)
      // FIX B: Defer game state update for successful returns — modal must show result first
      if (res.game_state) {
        if (action === '9a_attempt_return' && res.success) {
          console.log('[FIXB] deferring setGs — successful return, modal will apply on close')
        } else {
          setGs(res.game_state)
        }
      }
      setIntelAllocated(true)
    } catch (e) {
      setError(e.message)
    }
  }

  // ── PHASE 1 → 2: player picks skim option ────────────────────────────────
  async function handleSkim(choice) {
    requestConfirmSkim(choice)
  }

  async function _executeSkim(choice) {
    clearError()
    setLoading(true)
    try {
      const res = await api.postSkim(sessionId, choice)

      setGs(res.game_state)
      setSkimMessages(res.skim_messages || [])
      setCorruptionAlert(res.corruption_alert || null)
      setIntercepts(res.intercepts || [])
      const rawEotMsgs = res.eot_effects || []
      // 8D: Separate crisis objects from string messages
      const eotMsgs = rawEotMsgs.filter(m => typeof m === 'string')
      const crisisItems = rawEotMsgs.filter(m => typeof m === 'object' && m?.tag === 'CRISIS')
      if (crisisItems.some(c => c.type === 'the_leak')) {
        console.log('[leak] Crisis card detected in EOT effects')
      }
      setEotMessages(eotMsgs)
      // fixes_18 Fix C: Pipe approval trace logs to browser console
      eotMsgs.filter(m => m.startsWith('[APPROVAL]')).forEach(m => console.log(m))
      // Session 2 Item 6: surface broken deal messages as diplomatic crisis modal
      const brokenDeals = eotMsgs.filter(m => m.startsWith('💔'))
      if (brokenDeals.length > 0) setDipCrisisMessages(brokenDeals)
      setPatriotMessage(null)
      setAftermathResult(null)

      // Session log: capture skim + EOT data and finalize turn entry
      const skimOpt = skimOptions.find(o => o.choice === choice)
      const entry = currentTurnEntryRef.current
      entry.skimLabel   = skimOpt?.label || `Skim option ${choice}`
      entry.skimNational = skimOpt?.national_cost ?? 0
      entry.skimPersonal = skimOpt?.personal_gain ?? 0
      entry.eotEffects  = eotMsgs
      entry.budgetEnd    = res.game_state?.budget ?? null
      entry.personalEnd  = res.game_state?.personal_wealth ?? null
      entry.stabilityEnd = res.game_state?.stability ?? null
      entry.approvalEnd  = res.game_state?.public_approval ?? null
      entry.epitaph      = res.game_state?.current_epitaph ?? null
      if (entry.turn) {
        sessionLogRef.current.push({ ...entry })
        _persistLog()
        currentTurnEntryRef.current = {}  // prevent duplicate push on double-click / re-trigger
      }

      if (res.status !== 'active') {
        setEnding(res.ending)
        setPhase(PHASE.EOT)
        return
      }

      // Session 7A Step 5: Capture era transition suggestion
      setEraTransitionSuggestion(res.era_transition_suggestion || null)

      setPhase(PHASE.EOT)

      _nextTurnRef.current = {
        dialogue: res.next_dialogue,
        offers: res.next_offers,
        skimOptions: res.next_skim_options,
        blackmailActive: res.next_blackmail,
        status: res.status,
        ending: res.ending,
        event: res.next_event || null,
      }

    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── PHASE inject → 2: player picks inject option ──────────────────────────
  async function handleInject(choice) {
    clearError()
    setLoading(true)
    try {
      const res = await api.postInject(sessionId, choice)

      setGs(res.game_state)
      setSkimMessages(res.inject_messages || [])
      setCorruptionAlert(null)
      setIntercepts([])
      const rawEotInject = res.eot_effects || []
      // 8D: Filter crisis objects from string messages
      const eotMsgsInject = rawEotInject.filter(m => typeof m === 'string')
      setEotMessages(eotMsgsInject)
      // fixes_18 Fix C: Pipe approval trace logs to browser console
      eotMsgsInject.filter(m => m.startsWith('[APPROVAL]')).forEach(m => console.log(m))
      const brokenDealsInject = eotMsgsInject.filter(m => m.startsWith('💔'))
      if (brokenDealsInject.length > 0) setDipCrisisMessages(brokenDealsInject)
      setPatriotMessage(res.patriot_message || null)
      setAftermathResult(null)

      // Session log: finalize inject turn entry
      const entry = currentTurnEntryRef.current
      entry.skimLabel   = `Emergency Inject (option ${choice})`
      entry.eotEffects  = eotMsgsInject
      entry.budgetEnd    = res.game_state?.budget ?? null
      entry.personalEnd  = res.game_state?.personal_wealth ?? null
      entry.stabilityEnd = res.game_state?.stability ?? null
      entry.approvalEnd  = res.game_state?.public_approval ?? null
      entry.epitaph      = res.game_state?.current_epitaph ?? null
      if (entry.turn) {
        sessionLogRef.current.push({ ...entry })
        _persistLog()
        currentTurnEntryRef.current = {}  // prevent duplicate push on double-click / re-trigger
      }

      if (res.status !== 'active') {
        setEnding(res.ending)
        setPhase(PHASE.EOT)
        return
      }

      // Session 7A Step 5: Capture era transition suggestion
      setEraTransitionSuggestion(res.era_transition_suggestion || null)

      setPhase(PHASE.EOT)

      _nextTurnRef.current = {
        dialogue: res.next_dialogue,
        offers: res.next_offers,
        skimOptions: res.next_skim_options,
        blackmailActive: res.next_blackmail,
        status: res.status,
        ending: res.ending,
        event: res.next_event || null,
      }

    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── FEATURE 3: Brigade aftermath handler ──────────────────────────────────
  async function handleAftermath(choice) {
    clearError()
    setAftermathLoading(true)
    try {
      const res = await api.brigadeAftermath(sessionId, choice)
      setGs(res.game_state)
      setAftermathResult(res.messages?.[0] || 'Crisis managed.')
    } catch (e) {
      setError(e.message)
    } finally {
      setAftermathLoading(false)
    }
  }

  // Stash next-turn data between phases
  const _nextTurnRef = useRef(null)

  // ── PHASE 2 → 0 (or ENDED): player hits "Next Day" ──────────────────────
  function handleContinue() {
    console.log('[DEBUG handleContinue]',
      'ref=', JSON.stringify(_nextTurnRef.current),
      'loading=', loading,
      'phase=', phase,
      'gs_status=', gs?.status,
      'in_exile=', gs?.in_exile)
    const next = _nextTurnRef.current

    if (ending) {
      setPhase(PHASE.ENDED)
      onGameEnd && onGameEnd(ending)
      return
    }

    if (!next || next.status !== 'active') {
      if (next?.ending) {
        setEnding(next.ending)
        setPhase(PHASE.ENDED)
        onGameEnd && onGameEnd(next.ending)
      }
      return
    }

    // Advance to next day
    console.log('[DAY] Day advanced to:', next.game_state?.current_day ?? gs?.current_turn)
    setDialogue(next.dialogue)
    setOffers(next.offers)
    setSkimOptions(next.skimOptions || [])
    setBlackmailActive(next.blackmailActive || false)
    setConsequences([])
    setBlackmailResult(null)
    setSkimMessages([])
    setCorruptionAlert(null)
    setPatriotMessage(null)
    setIntercepts([])
    setEotMessages([])
    setBrigadeAvailable(false)
    setBrigadeResult(null)
    setAftermathResult(null)
    setDrainProjection(null)
    setIntelAllocated(false)
    setElectionConseqStash(null)
    setEraTransitionSuggestion(null)
    // Stage 4
    setCurrentEvent(next.event || null)
    setNegotiatingNpc(null)
    setCounterOffers({})
    setChatHistories({})
    setPhase(PHASE.DIALOGUE)
    _nextTurnRef.current = null
  }

  // ── Session 7A Step 5: Era close + Historian handlers ───────────────────────
  async function handleCloseEra() {
    clearError()
    setHistorianLoading(true)
    try {
      const res = await api.closeEra(sessionId)
      console.log('[ERA] Era closed:', res.closed_era, '→', res.new_era, 'trigger:', res.trigger)
      setGs(res.game_state)
      setEraTransitionSuggestion(null)
      // Show historian verdict modal
      setHistorianModal({
        era: res.closed_era,
        summary: res.historian_summary,
        isOnDemand: false,
      })
    } catch (e) {
      setError(e.message)
    } finally {
      setHistorianLoading(false)
    }
  }

  function handleDismissEraCard() {
    setEraTransitionSuggestion(null)
  }

  async function handleHistorianAssessment() {
    clearError()
    setHistorianLoading(true)
    try {
      console.log('[ERA] Historian assessment requested')
      const res = await api.historianSummary(sessionId)
      setHistorianModal({
        era: res.era,
        summary: res.historian_summary,
        isOnDemand: true,
      })
    } catch (e) {
      setError(e.message)
    } finally {
      setHistorianLoading(false)
    }
  }

  // ── Session 4B: Election done handler ─────────────────────────────────────
  function handleElectionDone(resultData) {
    // Update game state from election result
    if (resultData.game_state) setGs(resultData.game_state)

    // Snapshot for session log
    if (gs) {
      turnStartRef.current = {
        budget:    gs.budget ?? 0,
        personal:  gs.personal_wealth ?? 0,
        stability: gs.stability ?? 0,
        approval:  gs.public_approval ?? 0,
      }
    }

    // fixes_16: Store election as a separate entry type so it is not
    // overwritten if a negotiated deal is also accepted on the same turn.
    const _prev = currentTurnEntryRef.current
    currentTurnEntryRef.current = {
      ...(_prev.turn ? _prev : {}),          // preserve existing deal data if any
      turn: gs?.current_turn ?? '?',
      electionChoice: `[ELECTION] ${resultData.result_key}`,
      electionConsequences: resultData.consequences || [],
      // Only set these defaults when no deal entry has claimed them yet
      ...(!_prev.choiceText ? {
        choiceText: null,
        npcSided: null,
        consequences: resultData.consequences || [],
      } : {}),
      brigadeOp: _prev.brigadeOp ?? null,
      skimLabel: _prev.skimLabel ?? null,
      skimNational: _prev.skimNational ?? 0,
      skimPersonal: _prev.skimPersonal ?? 0,
      eotEffects: _prev.eotEffects ?? [],
      budgetStart:    turnStartRef.current.budget,
      budgetEnd:      _prev.budgetEnd ?? null,
      personalStart:  turnStartRef.current.personal,
      personalEnd:    _prev.personalEnd ?? null,
      stabilityStart: turnStartRef.current.stability,
      stabilityEnd:   _prev.stabilityEnd ?? null,
      approvalStart:  turnStartRef.current.approval,
      approvalEnd:    _prev.approvalEnd ?? null,
      epitaph: _prev.epitaph ?? null,
    }

    // Stash election consequences — player now picks a diplomatic deal;
    // these will be prepended to the deal consequences in CONSEQUENCES phase.
    setElectionConseqStash({
      result_key: resultData.result_key,
      consequences: resultData.consequences || [],
      npc_reactions: resultData.npc_reactions || {},
    })
    // Stay in DIALOGUE phase — the ternary will now show OffersPanel
    // since election_fired is true in the updated game state.
  }

  // ── Stage 4: counter-offer handler ────────────────────────────────────────
  // fixes_13 Fix 24: Accept covert flag for Ji-won transactions
  async function handleCounterOffer(letter, counterOffer, covert = false) {
    setCounterOffers(prev => ({ ...prev, [letter]: counterOffer }))
    try {
      await api.acceptCounter(sessionId, letter, counterOffer, covert)
      if (covert) console.log(`[GameScreen] Fix 24: Covert deal accepted with ${counterOffer?.npc}`)

      // 10B-3: Sidebar deals get GM consequence resolution
      const npcId = (counterOffer?.npc || '').toLowerCase()
      const dealText = counterOffer?.text || 'Diplomatic deal'
      if (npcId && activeTab === 'foreign') {
        try {
          const conseqResult = await api.dealConsequences(sessionId, npcId, dealText, !!covert)
          console.log('[10B-3] Deal consequences applied:', conseqResult)
          // Refresh game state and day status
          await getGame()
        } catch (ce) {
          console.warn('[10B-3] deal-consequences failed (non-blocking):', ce.message)
        }
      }
    } catch (e) {
      console.warn('acceptCounter failed:', e.message)
    }
  }

  function handleHistoryChange(npcKey, newMessages, newPendingOffers, newHeldOffer) {
    setChatHistories(prev => ({
      ...prev,
      [npcKey]: {
        messages: newMessages,
        pendingOffers: newPendingOffers || [],
        heldOffer: newHeldOffer ?? (prev[npcKey]?.heldOffer ?? null),
      },
    }))
  }

  // ── 10B-2: GET INTEL handler ────────────────────────────────────────────
  async function handleGetIntel(npcKey) {
    setIntelLoading(prev => ({ ...prev, [npcKey]: true }))
    try {
      const result = await api.intelGetNpc(sessionId, npcKey)
      console.log('[10B-2] Intel result for', npcKey, ':', result)
      // Store intel result for inline display
      setIntelResults(prev => ({
        ...prev,
        [npcKey]: {
          text: result.intel_text || 'No actionable intelligence obtained.',
          detected: result.detected || false,
        }
      }))
      // Refresh gs to get updated budget and relations
      const data = await api.getGame(sessionId)
      setGs(data.game_state)
      if (result.detected) {
        console.log(`[10B-2] Intel detected by ${npcKey}`)
      }
    } catch (e) {
      console.error('[10B-2] Intel failed:', e)
      setError('Intel operation failed: ' + (e.message || e))
    } finally {
      setIntelLoading(prev => ({ ...prev, [npcKey]: false }))
    }
  }

  // ── Negotiation opener: inject communiqué as NPC's first message ─────────
  function handleStartNegotiation(npcKey, communiqueText) {
    if (npcKey === null) {
      setNegotiatingNpc(null)
      return
    }
    setNegotiatingNpc(npcKey)
    // If no prior chat history for this NPC, inject communiqué as opening message
    const existing = chatHistories[npcKey]
    if (!existing?.messages?.length && communiqueText && communiqueText !== '…') {
      setChatHistories(prev => ({
        ...prev,
        [npcKey]: {
          messages: [{ role: 'npc', content: communiqueText }],
          pendingOffers: prev[npcKey]?.pendingOffers || [],
          heldOffer: prev[npcKey]?.heldOffer ?? null,
        },
      }))
    }
  }

  // Session 7B Step 3: Player-initiated contact from RightSidebar
  async function handlePlayerContact(npcKey) {
    if (!npcKey || negotiatingNpc || loading) return
    console.log('[BRIEFING] Player-initiated contact:', npcKey)

    // If chat history already exists for this NPC, just open the panel
    const existing = chatHistories[npcKey]
    if (existing?.messages?.length) {
      setNegotiatingNpc(npcKey)
      return
    }

    // FIX 3: Do NOT open the panel yet — fetch the NPC's opening message first,
    // then open the panel with the message already in chatHistories.
    // Previously setNegotiatingNpc was called before the API call, causing
    // NegotiationPanel to mount with empty initialMessages (useState only
    // captures initial value on mount, ignoring subsequent prop changes).
    setLoading(true)

    try {
      const res = await api.negotiate(sessionId, npcKey, '[CONTACT]', [], null, true)
      // Populate chat history FIRST
      setChatHistories(prev => ({
        ...prev,
        [npcKey]: {
          messages: [{ role: 'npc', content: res.response }],
          pendingOffers: [],
          heldOffer: null,
        },
      }))
      if (res.game_state) setGs(res.game_state)
      console.log('[contact] Auto-opening message fetched for', npcKey)
      // NOW open the panel — initialMessages will include the NPC's opening
      setNegotiatingNpc(npcKey)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // Model C: Contact request for low-relations NPCs (< 40)
  const [contactLoading, setContactLoading] = useState({})
  const [contactResults, setContactResults] = useState({})

  async function handleContactRequest(npcKey) {
    if (!npcKey || contactLoading[npcKey]) return
    setContactLoading(prev => ({ ...prev, [npcKey]: true }))
    try {
      const res = await api.contactRequest(sessionId, npcKey)
      setContactResults(prev => ({
        ...prev,
        [npcKey]: {
          text: res.acknowledgment,
          gate_message: res.gate_message || null,
          type: 'request',
        },
      }))
      // Refresh gs to get contact_requested updated
      const fresh = await api.getGame(sessionId)
      if (fresh?.game_state) setGs(fresh.game_state)
    } catch (e) {
      setError(e.message)
    } finally {
      setContactLoading(prev => ({ ...prev, [npcKey]: false }))
    }
  }

  // Model C: Direct contact — opens NegotiationPanel (existing conversation modal)
  // The negotiate endpoint already has relationship-gated tone framing (Session 7B Step 3).
  // For relations >= 40 or crisis: opens full conversation modal via handlePlayerContact.
  // For relations < 40: NpcCard routes to handleContactRequest instead (terse ack, no modal).
  //
  // SIDE DEAL SEPARATION: Sidebar contacts go through /negotiate only — they do NOT
  // call /briefing/resolve-event and do NOT increment events_resolved_today.
  // World event resolution is handled separately by BriefingScreen's choice buttons.
  // This means sidebar diplomacy is independent of the daily event queue.
  function handleDirectContact(npcKey) {
    if (!npcKey) return
    // handlePlayerContact opens the NegotiationPanel — the existing multi-turn modal
    handlePlayerContact(npcKey)
  }

  // Session 7D Step 2: Open backchannel modal
  function handleOpenBackchannel(npcKey) {
    if (!npcKey) return
    console.log('[BACKCHANNEL] Opening covert channel:', npcKey)
    setBackchannelNpc(npcKey)
  }

  // ── 8C: Exile action handler ────────────────────────────────────────────
  async function handleExileAction(action, targetNpc = null, opType = null) {
    setLoading(true)
    setError(null)
    try {
      let res
      // 9A: Route to new exile endpoints
      if (action === '9a_wealth_action') {
        const data = targetNpc // { action_key, target, offer }
        res = await api.exileWealthAction(sessionId, data.action_key, data.target, data.offer)
        // 9A: Add detection messages to exile feed
        if (res.detected && res.detection_message) {
          setExileMessages(prev => [`🔍 ${res.detection_message}`, ...prev].slice(0, 50))
        }
        if (res.successor_reaction) {
          setExileMessages(prev => [`⚠️ ${res.successor_reaction}`, ...prev].slice(0, 50))
        }
      } else if (action === '9a_npc_backing') {
        const data = targetNpc // { npc_id, tier }
        res = await api.exileNpcBacking(sessionId, data.npc_id, data.tier)
      } else if (action === '9a_attempt_return') {
        res = await api.exileAttemptReturn(sessionId)
      } else {
        res = await api.exileAction(sessionId, action, targetNpc, opType)
      }
      if (res.game_state) setGs(res.game_state)
      // Append any messages from the response to the exile feed
      const newMsgs = res.messages || []
      if (newMsgs.length > 0) {
        setExileMessages(prev => [...newMsgs, ...prev].slice(0, 50))
      }
      // Fix E: Capture AI-generated NPC dialogue from reach-out
      if (res.npc_dialogue) {
        setExileDialogue({ npc: typeof targetNpc === 'string' ? targetNpc : null, text: res.npc_dialogue })
      } else if (!['9a_wealth_action', '9a_npc_backing', '9a_attempt_return'].includes(action)) {
        setExileDialogue(null)
      }
      console.log('[EXILE] Action completed:', action, targetNpc, opType)
      return res // 9A: Return response for component-level handling
    } catch (e) {
      setError(e.message)
      setExileMessages(prev => [`⚠ ${e.message}`, ...prev].slice(0, 50))
      throw e // 9A: Re-throw for component error handling
    } finally {
      setLoading(false)
    }
  }

  // ── FEATURE 1: Shadow Cabinet upgrade purchased → sync gs ────────────────
  // PRE-SESSION 4 FIX (BUG C): Shadow Cabinet purchases must always be logged.
  // If a turn entry is active, attach to it. Otherwise, attach to the most
  // recent completed turn or buffer for the next turn.
  function handleUpgradePurchased(newGs, purchaseInfo) {
    setGs(newGs)
    if (purchaseInfo) {
      const entry = currentTurnEntryRef.current
      // Check if a turn entry is active (has a 'turn' field)
      if (entry && entry.turn) {
        if (!entry.upgradePurchases) entry.upgradePurchases = []
        entry.upgradePurchases.push(purchaseInfo)
      } else {
        // No active turn entry — attach to most recent completed turn in session log
        const log = sessionLogRef.current
        if (log.length > 0) {
          const lastEntry = log[log.length - 1]
          if (!lastEntry.upgradePurchases) lastEntry.upgradePurchases = []
          lastEntry.upgradePurchases.push(purchaseInfo)
          _persistLog()
        } else {
          // Very first action before any turn — buffer in currentTurnEntryRef
          if (!entry.upgradePurchases) entry.upgradePurchases = []
          entry.upgradePurchases.push(purchaseInfo)
        }
      }
    }
  }

  // # DEV FEATURE — remove before public launch
  // ── Addition 1: Export Debug Log ─────────────────────────────────────────
  function handleExportDebugLog() {
    if (!gs) return
    const now = new Date()
    const ts = now.toISOString().replace('T', ' ').slice(0, 19)
    const tsFile = now.toISOString().replace(/[:.]/g, '-').slice(0, 19)
    const rr = (v) => typeof v === 'number' ? Math.round(v) : (v ?? '—')
    const fm = (v) => typeof v === 'number' ? `$${v.toFixed(1)}B` : '—'
    const sep = '─────────────────────────────────'

    const lines = []
    lines.push('=== WORLD STAGE — SESSION EXPORT ===')
    lines.push(`Generated: ${ts}`)
    lines.push('')

    // ── CURRENT STATE ─────────────────────────────────────────────────────
    lines.push('CURRENT STATE')
    lines.push(sep)
    lines.push(`Turn:          ${gs.current_turn}/${gs.max_turns}`)
    lines.push(`Budget:        ${fm(gs.budget)}`)
    lines.push(`Personal:      ${fm(gs.personal_wealth)}`)
    lines.push(`Stability:     ${gs.stability}%`)
    lines.push(`Approval:      ${gs.public_approval}%`)
    lines.push(`Oil:           $${gs.oil_price}/bbl`)
    const regime = gs.state_identity
    lines.push(`Regime:        ${regime?.regime_type || '—'} · ${regime?.power_base || '—'}`)
    const rel = gs.relations || {}
    lines.push(`Relations:     USA ${rr(rel.usa)} | Arabia ${rr(rel.arabia)} | EU ${rr(rel.eu)} | DPRG ${rr(rel.dprg)}`)

    const upgrades = gs.corruption_upgrades || {}
    const activeUpgrades = Object.entries(upgrades).filter(([, v]) => v).map(([k]) => k.replace(/_/g, ' '))
    lines.push(`Upgrades:      ${activeUpgrades.length > 0 ? activeUpgrades.join(', ') : 'none'}`)

    const penalties = []
    if (gs.usa_sanctions_active) penalties.push(`USA Sanctions (tier ${gs.usa_sanctions_tier})`)
    if (gs.arabia_embargo_active) penalties.push(`Arabia Embargo (tier ${gs.arabia_embargo_tier})`)
    lines.push(`Penalties:     ${penalties.length > 0 ? penalties.join(', ') : 'none'}`)

    const activeDeals = (gs.deal_history || []).filter(
      d => !d.broken && (d.expires_turn ?? 0) >= gs.current_turn
    )
    if (activeDeals.length > 0) {
      lines.push('Active Deals:')
      activeDeals.forEach(d => lines.push(`  · [${d.npc?.toUpperCase()}] ${d.summary} (expires turn ${d.expires_turn})`))
    } else {
      lines.push('Active Deals:  none')
    }
    lines.push('')

    // ── TURN HISTORY (rich, from sessionLogRef) ───────────────────────────
    lines.push('TURN HISTORY')
    lines.push(sep)
    const richLog = sessionLogRef.current
    if (richLog.length === 0) {
      lines.push('(no completed turns recorded this session)')
    } else {
      richLog.forEach(entry => {
        const npcName = entry.npcSided ? (NPC_INFO[entry.npcSided]?.label || entry.npcSided) : 'none'
        lines.push(`Turn ${entry.turn}:`)
        // fixes_16: Show election and deal as independent entries
        if (entry.electionChoice) {
          lines.push(`  Election:      ${entry.electionChoice}`)
          if (entry.electionConsequences?.length > 0) {
            lines.push('  Election consequences:')
            entry.electionConsequences.forEach(c => lines.push(`    · ${c}`))
          }
        }
        lines.push(`  Choice:        ${entry.choiceText || '—'}`)
        lines.push(`  NPC sided:     ${npcName}`)
        if (entry.consequences?.length > 0) {
          lines.push('  Consequences:')
          entry.consequences.forEach(c => lines.push(`    · ${c}`))
        }
        if (entry.upgradePurchases?.length > 0) {
          lines.push('  Upgrades:')
          entry.upgradePurchases.forEach(u => u.messages?.forEach(m => lines.push(`    · ${m}`)))
        }
        lines.push(`  Brigade:       ${entry.brigadeOp || 'not deployed / n/a'}`)
        if (entry.brigadeOutcome?.length > 0) {
          entry.brigadeOutcome.forEach(m => lines.push(`    · ${m}`))
        }
        if (entry.skimLabel) {
          lines.push(`  Skim:          ${entry.skimLabel}`)
          if (entry.skimNational) lines.push(`    National cost:   -${fm(entry.skimNational)}`)
          if (entry.skimPersonal) lines.push(`    Personal gain:   +${fm(entry.skimPersonal)}`)
        }
        if (entry.eotEffects?.length > 0) {
          lines.push('  EOT Effects:')
          entry.eotEffects.forEach(e => lines.push(`    · ${e}`))
        }
        const bS = entry.budgetStart, bE = entry.budgetEnd
        const pS = entry.personalStart, pE = entry.personalEnd
        const sS = entry.stabilityStart, sE = entry.stabilityEnd
        const aS = entry.approvalStart, aE = entry.approvalEnd
        if (bS != null && bE != null) lines.push(`  Budget:        ${fm(bS)} → ${fm(bE)}`)
        if (pS != null && pE != null) lines.push(`  Personal:      ${fm(pS)} → ${fm(pE)}`)
        if (sS != null && sE != null) lines.push(`  Stability:     ${sS}% → ${sE}%`)
        if (aS != null && aE != null) lines.push(`  Approval:      ${aS}% → ${aE}%`)
        if (entry.epitaph) lines.push(`  Epitaph:       "${entry.epitaph}"`)
        lines.push('')
      })
    }

    // ── NEGOTIATION LOG ───────────────────────────────────────────────────
    lines.push('NEGOTIATION LOG')
    lines.push(sep)
    const negLog = gs.negotiation_log || []
    if (negLog.length === 0) {
      lines.push('(no negotiations recorded)')
    } else {
      negLog.forEach((entry, i) => {
        const npcLabel = NPC_INFO[entry.npc]?.label || entry.npc
        lines.push(`[${i + 1}] Turn ${entry.turn} — ${npcLabel}:`)
        if (entry.player_message) lines.push(`  Player:        "${entry.player_message}"`)
        if (entry.npc_response)   lines.push(`  NPC:           "${entry.npc_response}"`)
        if (entry.counter_offer) {
          const co = entry.counter_offer
          lines.push(`  Counter-offer: ${co.text || JSON.stringify(co)}`)
          if (co.consequences) {
            const c = co.consequences
            const parts = []
            if (c.budget)  parts.push(`budget ${c.budget > 0 ? '+' : ''}${fm(c.budget)}`)
            if (c.oil_price) parts.push(`oil $${c.oil_price}/bbl`)
            if (c.usa)  parts.push(`USA ${c.usa > 0 ? '+' : ''}${c.usa}`)
            if (c.arabia) parts.push(`Arabia ${c.arabia > 0 ? '+' : ''}${c.arabia}`)
            if (c.eu)   parts.push(`EU ${c.eu > 0 ? '+' : ''}${c.eu}`)
            if (c.dprg) parts.push(`DPRG ${c.dprg > 0 ? '+' : ''}${c.dprg}`)
            if (parts.length > 0) lines.push(`    Mechanics:   ${parts.join(' · ')}`)
          }
        } else {
          lines.push('  Counter-offer: none')
        }
        lines.push(`  Outcome:       ${entry.outcome || '—'}`)
        lines.push('')
      })
    }

    // ── DEAL HISTORY ──────────────────────────────────────────────────────
    lines.push('DEAL HISTORY')
    lines.push(sep)
    const allDeals = gs.deal_history || []
    if (allDeals.length === 0) {
      lines.push('(no deals recorded)')
    } else {
      allDeals.forEach(d => {
        const npcLabel = NPC_INFO[d.npc]?.label || d.npc
        const status = d.broken
          ? 'BROKEN'
          : (d.expires_turn ?? 0) >= gs.current_turn
            ? 'ACTIVE'
            : 'EXPIRED'
        lines.push(`Turn ${d.turn_accepted} — ${npcLabel} [${status}]:`)
        lines.push(`  Terms:         ${d.summary}`)   // no truncation
        if (d.expires_turn) lines.push(`  Expires:       turn ${d.expires_turn}`)
        lines.push('')
      })
    }

    // ── BACKCHANNEL LOG — Session 7D Step 4 ────────────────────────────
    lines.push('BACKCHANNEL LOG (CLASSIFIED)')
    lines.push(sep)
    const bcHistory = gs.backchannel_history || []
    if (bcHistory.length === 0) {
      lines.push('(no backchannel exchanges recorded)')
    } else {
      bcHistory.forEach((entry, i) => {
        const npcLabel = NPC_INFO[entry.npc_id]?.label || entry.npc_id
        const detected = entry.detected_by ? `DETECTED by ${entry.detected_by}` : 'undetected'
        lines.push(`[${i + 1}] Turn ${entry.turn || '?'} — ${npcLabel} [${detected}]:`)
        if (entry.player_message) lines.push(`  Player:        "${entry.player_message}"`)
        if (entry.response_text)  lines.push(`  NPC:           "${entry.response_text}"`)
        if (entry.promise_made)   lines.push(`  Promise:       ${entry.promise_text || '(unspecified)'}`)
        lines.push('')
      })
    }

    // ── ACTIVE COVERT PROMISES ──────────────────────────────────────────
    const bcPromises = gs.active_backchannel_promises || []
    if (bcPromises.length > 0) {
      lines.push('ACTIVE COVERT PROMISES')
      lines.push(sep)
      bcPromises.forEach((p, i) => {
        const npcLabel = NPC_INFO[p.npc_id]?.label || p.npc_id
        const status = p.resolved ? 'RESOLVED' : p.detected_by ? `COMPROMISED (${p.detected_by})` : 'ACTIVE'
        lines.push(`[${i + 1}] ${npcLabel} [${status}]:`)
        lines.push(`  Promise:       ${p.promise_text || '(unspecified)'}`)
        lines.push(`  Made:          Turn ${p.turn || '?'}`)
        lines.push('')
      })
    }

    // ── SUMMIT HISTORY — Session 7E ─────────────────────────────────────
    lines.push('SUMMIT HISTORY')
    lines.push(sep)
    lines.push(`Summit Credibility: ${gs.summit_credibility ?? 100}`)
    lines.push(`Summit Due:         ${gs.summit_due ? 'YES' : 'No'}`)
    const summitHist = gs.summit_history || []
    if (summitHist.length === 0) {
      lines.push('(no summits held)')
    } else {
      summitHist.forEach((s, i) => {
        lines.push(`[${i + 1}] Day ${s.day}:`)
        lines.push(`  Declaration:   "${s.player_declaration}"`)
        if (s.npc_reactions) {
          s.npc_reactions.forEach(r => {
            lines.push(`  ${r.npc_name || r.npc_id}: [${r.reaction_type}] ${r.reaction_text || '(silence)'}`)
          })
        }
        if (s.commitments_made?.length > 0) lines.push(`  Commitments:   ${s.commitments_made.join('; ')}`)
        lines.push('')
      })
    }
    const summitCommits = gs.active_summit_commitments || []
    if (summitCommits.length > 0) {
      lines.push('ACTIVE SUMMIT COMMITMENTS')
      lines.push(sep)
      summitCommits.forEach((c, i) => {
        const status = c.broken ? 'BROKEN' : 'ACTIVE'
        lines.push(`[${i + 1}] [${status}] ${c.commitment_text || c.text || '(unknown)'}`)
      })
      lines.push('')
    }

    lines.push('=== END OF EXPORT ===')

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `worldstage-turn${gs.current_turn}-${tsFile}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  // ── Render: EXILE ─────────────────────────────────────────────────────────
  if (gs?.in_exile) {
    return (
      <div className="app-container exile-mode">
        <ExileDashboard
          gs={gs}
          sessionId={sessionId}
          onExileAction={handleExileAction}
          onGsUpdate={setGs}
          loading={loading}
          messages={exileMessages}
          exileDialogue={exileDialogue}
          onDismissDialogue={() => setExileDialogue(null)}
        />

        {/* Debug panel remains accessible during exile */}
        {debugOpen && (
          <DebugPanel
            gs={gs}
            sessionId={sessionId}
            onClose={() => setDebugOpen(false)}
            onGsUpdate={setGs}
          />
        )}
        <button
          className="dev-cheat-toggle"
          onClick={() => setDebugOpen(prev => !prev)}
          title="Toggle cheat panel"
        >
          DEV
        </button>
        <TestPanel
          sessionId={sessionId}
          gs={gs}
          onGsUpdate={setGs}
          onOpenCheatPanel={() => setDebugOpen(true)}
          onSnapshotLoad={onSnapshotLoad}
        />
      </div>
    )
  }

  // ── Render: ENDED ────────────────────────────────────────────────────────
  if (phase === PHASE.ENDED) {
    // Session 4D: Alternate ending takes precedence if triggered
    const altEnding = gs?.ending_triggered
    return (
      <div className="app-container">
        <div className="block lg:hidden">
          <StatusBar gs={gs} />
        </div>
        <DashboardLayout gs={gs}>
          {altEnding ? (
            <EndingPanel
              ending={altEnding}
              gs={gs}
              onRestart={onRestart}
              onExportLog={handleExportDebugLog}
            />
          ) : (
            <EndingScreen ending={ending} gs={gs} onRestart={onRestart} onExportLog={handleExportDebugLog} />
          )}
          {/* 9B: View Political Biography button */}
          <div style={{ textAlign: 'center', margin: '1rem 0' }}>
            <button
              className="btn-secondary"
              onClick={() => { console.log('[9B] opening biography from ending screen'); setShowBiography(true) }}
              style={{ fontSize: '0.82rem', padding: '0.6rem 1.5rem' }}
            >
              VIEW POLITICAL BIOGRAPHY
            </button>
          </div>
          <div className="dev-export-footer">
            <button
              className="dev-export-btn"
              onClick={handleExportDebugLog}
              title="Export full game state as .txt debug log"
            >
              Export Debug Log
            </button>
          </div>
        </DashboardLayout>

        {/* 9B: Biography Modal on ending screen */}
        <BiographyModal
          isOpen={showBiography}
          onClose={() => setShowBiography(false)}
          onPlayAgain={onRestart}
          sessionId={sessionId}
          isDraft={false}
        />
      </div>
    )
  }

  // ── Render: GAME ─────────────────────────────────────────────────────────
  return (
    <div className="app-container">
      {/* Mobile only: StatusBar visible below lg breakpoint */}
      <div className="block lg:hidden">
        <StatusBar
          gs={gs}
          onShadowCabinet={() => setShadowCabinetOpen(true)}
        />
      </div>

      <DashboardLayout gs={gs} onShadowCabinet={() => setShadowCabinetOpen(true)} negotiatingNpc={negotiatingNpc} onHistorian={handleHistorianAssessment} historianLoading={historianLoading} onBiography={() => { console.log('[9B] opening draft biography from sidebar'); setShowBiography(true) }} onContact={!loading && (phase === PHASE.DIALOGUE || activeTab === 'foreign') ? handleDirectContact : null} onContactRequest={handleContactRequest} contactLoading={contactLoading} contactResults={contactResults} contactsDisabled={loading} activeTab={activeTab} onTabChange={setActiveTab} domesticContent={<DomesticTab gs={gs} sessionId={sessionId} onGsUpdate={setGs} />} onBackchannel={!loading && (phase === PHASE.DIALOGUE || activeTab === 'foreign') ? handleOpenBackchannel : null} backchannelDisabled={loading} onGetIntel={handleGetIntel} intelLoading={intelLoading} intelResults={intelResults} dialogue={dialogue}>

      {/* Session 7E: Summit replaces center panel content when open */}
      {summitOpen ? (
        <SummitModal
          gs={gs}
          sessionId={sessionId}
          onClose={() => setSummitOpen(false)}
          onGsUpdate={setGs}
        />
      ) : (
      <div className="game-scroll" ref={scrollRef}>

        {error && (
          <div className="error-banner">⚠️ {error}</div>
        )}

        {/* Crisis banners */}
        {gs?.usa_sanctions_active && (
          <div className="crisis-banner">
            ⚠️ USA SANCTIONS ACTIVE — Budget penalty each turn
          </div>
        )}
        {gs?.arabia_embargo_active && (
          <div className="crisis-banner">
            ⚠️ ARABIA OIL EMBARGO ACTIVE — Oil price surcharges apply
          </div>
        )}

        {/* Blackmail warning (shows during DIALOGUE phase only) */}
        {blackmailActive && phase === PHASE.DIALOGUE && (
          <div className="blackmail-banner">
            🔴 CIA BLACKMAIL THREAT ACTIVE<br />
            Your ${gs?.personal_wealth?.toFixed(1)}B account has been flagged.<br />
            Cooperate with USA this turn to pay the &quot;fee&quot;. Refuse and face exposure.
          </div>
        )}

        {/* ITEM 2: Pre-warning system for existential thresholds */}
        {phase === PHASE.DIALOGUE && gs?.threshold_warnings?.length > 0 && (
          <details className="warnings-panel" open>
            <summary className="warnings-panel-header">⚠️ WARNINGS ({gs.threshold_warnings.length})</summary>
            {gs.threshold_warnings.map((w, i) => (
              <div key={i} className={`warning-item warning-${w.level}`}>{w.text}</div>
            ))}
          </details>
        )}

        {/* ── PHASE: DIALOGUE ── */}
        {phase === PHASE.DIALOGUE && (
          <>
            <div className="turn-divider">— TURN {gs?.current_turn}/{gs?.max_turns} —</div>

            {/* fixes_12 Fix 4: Per-turn epitaph removed — historian summary on ending screen */}

            {/* fixes_8 Fix 5: Election warning as amber banner at TOP of turn, ABOVE communiqués */}
            {gs?.election_warning_shown && !gs?.election_fired && !gs?.constitutional_revision_active &&
             gs?.current_turn < (gs?.election_turn ?? 4) && (
              <div className="alert" style={{
                background: 'rgba(255,183,77,0.12)',
                borderColor: '#ffb74d',
                borderLeft: '4px solid #ffb74d',
                color: '#ffb74d',
                textAlign: 'center',
                fontWeight: 600,
              }}>
                Elections next turn — your choices this turn will shape the outcome.
              </div>
            )}

            {/* 10B-1: Daily Briefing Screen replaces old summary card */}
            <BriefingScreen
              gameState={gs}
              sessionId={sessionId}
              currentDay={gs?.current_turn ?? 1}
              currentEra={gs?.current_era ?? 1}
              onEndDay={() => _executeSkim(1)}
              onEventResolved={async (evt, res) => {
                // BriefingScreen already called resolve-event and got consequences.
                // We just refresh gs to sync GameScreen state.
                console.log('[BRIEFING] Event resolved:', evt.id, res)
                try {
                  const data = await api.getGame(sessionId)
                  setGs(data.game_state)
                } catch (err) {
                  console.error('[BRIEFING] gs refresh after event resolve failed:', err)
                }
              }}
              onGsUpdate={setGs}
            />

            {/* 10B-2: When Foreign Affairs tab is active, BriefingScreen handles everything.
                Old content below only renders for non-foreign tabs. */}
            {/* Negotiation slide-up panel — renders on top of any tab/screen */}
            {negotiatingNpc && (() => {
              const info = NPC_INFO[negotiatingNpc]

              let activeDealSummary = null
              if (gs) {
                const summaries = []
                if (
                  negotiatingNpc === 'arabia' &&
                  gs.oil_price_locked &&
                  gs.oil_price_lock_turns_remaining > 0
                ) {
                  summaries.push(
                    `🔒 Oil locked at $${gs.oil_price_lock_value}/bbl — ${gs.oil_price_lock_turns_remaining} turn(s) remaining`
                  )
                }
                if (Array.isArray(gs.active_trade_commitments)) {
                  for (const c of gs.active_trade_commitments) {
                    if (!c.npc || c.npc === negotiatingNpc) {
                      summaries.push(
                        `🤝 ${c.description} — ${c.turns_remaining} turn(s) remaining`
                      )
                    }
                  }
                }
                if (summaries.length > 0) {
                  activeDealSummary = summaries.join(' · ')
                }
              }

              const savedHistory = chatHistories[negotiatingNpc] || {}
              return (
                <NegotiationPanel
                  key={negotiatingNpc}
                  npcKey={negotiatingNpc}
                  npcLabel={info.label}
                  npcFlag={info.flag}
                  sessionId={sessionId}
                  offerLetter={info.letter}
                  onClose={() => setNegotiatingNpc(null)}
                  onCounterOffer={handleCounterOffer}
                  initialMessages={savedHistory.messages || []}
                  initialPendingOffers={savedHistory.pendingOffers || []}
                  initialHeldOffer={savedHistory.heldOffer ?? null}
                  onHistoryChange={(msgs, offers, held) => handleHistoryChange(negotiatingNpc, msgs, offers, held)}
                  onGsUpdate={(newGs) => setGs(newGs)}
                  activeDealSummary={activeDealSummary}
                  currentTurn={gs?.current_turn ?? 1}
                  gs={gs}
                />
              )
            })()}

            {activeTab !== 'foreign' && <>

            {/* Session 7E: Summit Pending Banner */}
            {gs?.summit_due && !summitOpen && (
              <div className="summit-pending-banner">
                <div className="summit-pending-text">
                  🌐 UN SUMMIT IN SESSION — Address the assembly before advancing
                </div>
                <button
                  className="summit-pending-btn"
                  onClick={() => setSummitOpen(true)}
                >
                  OPEN SUMMIT
                </button>
              </div>
            )}

            {/* Session 7C Step 2: Advisor Assignment Panel — above communiqués, compact */}
            {gs?.advisors && typeof gs.advisors === 'object' && !Array.isArray(gs.advisors) && Object.keys(gs.advisors).length > 0 && (
              <AdvisorPanel gs={gs} sessionId={sessionId} onGsUpdate={setGs} />
            )}

            {/* Session 7D Step 3: Promise Tracker — active covert commitments */}
            <PromiseTracker gs={gs} />

            {/* Session 7E Step 3: Summit Commitment Tracker — active public commitments */}
            <SummitCommitmentTracker gs={gs} />

            {/* World event banner */}
            <EventBanner event={currentEvent} />

            <DialoguePanel
              dialogue={dialogue}
              onNegotiate={!loading && !(gs?.current_turn === (gs?.election_turn ?? 4) && !gs?.election_fired) ? handleStartNegotiation : null}
              negotiatingNpc={negotiatingNpc}
              intelActive={true}
              intelligenceLevel={gs?.cabinet_axes?.intelligence || 0}
              sessionId={sessionId}
              gs={gs}
              onGsUpdate={setGs}
            />

            {/* FEATURE 3: Brigade aftermath banner — AFTER communiqués, BEFORE choices */}
            {gs?.brigades_deployed_last_turn && !aftermathResult && (
              <div className="brigade-aftermath-banner">
                <div className="aftermath-header">
                  ⚔️ LOYALTY BRIGADE DEPLOYMENT — AFTERMATH
                </div>
                <div className="aftermath-desc">
                  The deployment has made headlines. Street protests have erupted in three districts.
                  Your press office is demanding a response. How do you proceed?
                </div>
                {aftermathLoading ? (
                  <div className="aftermath-loading">Consulting advisors…</div>
                ) : (
                  <div className="aftermath-choices">
                    <button
                      className="aftermath-btn aftermath-btn-suppress"
                      onClick={() => handleAftermath(1)}
                      disabled={aftermathLoading}
                    >
                      <span className="aftermath-btn-label">Suppress Coverage</span>
                      <span className="aftermath-btn-cost">-$3B personal · +5% stability</span>
                    </button>
                    <button
                      className="aftermath-btn aftermath-btn-aid"
                      onClick={() => handleAftermath(2)}
                      disabled={aftermathLoading}
                    >
                      <span className="aftermath-btn-label">Launch Aid Programs</span>
                      <span className="aftermath-btn-cost">-$5B budget · +8% approval · +3% stability</span>
                    </button>
                    <button
                      className="aftermath-btn aftermath-btn-favor"
                      onClick={() => handleAftermath(3)}
                      disabled={aftermathLoading}
                    >
                      <span className="aftermath-btn-label">Call in a Favor</span>
                      <span className="aftermath-btn-cost">Highest-relation NPC -10 · +8% stability · +5% approval</span>
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Aftermath resolved message */}
            {aftermathResult && (
              <div className="alert alert-success">{aftermathResult}</div>
            )}

            <div className="panel" style={{ paddingBottom: '0.5rem' }}>
              <div className="panel-header">Relations</div>
              <RelationBadges
                relations={gs?.relations}
                sanctions={gs?.usa_sanctions_active}
                embargo={gs?.arabia_embargo_active}
                unlocks={gs?.relations_100_unlocks}
              />
            </div>

            {/* Election result stash — shown after election resolves, before deal selection */}
            {electionConseqStash && (
              <div className="panel election-result-stash">
                <div className="panel-header" style={{ color: 'var(--accent)' }}>
                  🗳️ Election Result
                </div>
                {electionConseqStash.consequences.map((c, i) => (
                  <div key={i} className="consequence-line">{c}</div>
                ))}
                <p style={{ opacity: 0.7, marginTop: '0.5rem', fontSize: '0.85rem' }}>
                  Now choose your diplomatic action for this turn.
                </p>
              </div>
            )}

            {/* Session 4B: Election replaces OffersPanel on election turn */}
            {gs?.current_turn === (gs?.election_turn ?? 4) && !gs?.election_fired && !gs?.constitutional_revision_active ? (
              <ElectionPanel
                gameState={gs}
                sessionId={sessionId}
                onElectionDone={handleElectionDone}
                disabled={loading}
                onGsUpdate={setGs}
              />
            ) : (
              <OffersPanel
                offers={offers}
                onChoice={handleChoice}
                disabled={loading || (gs?.brigades_deployed_last_turn && !aftermathResult) || gs?.summit_due}
                counterOffers={counterOffers}
                summitBlocked={!!gs?.summit_due}
              />
            )}

            {/* Session 8A: Russia/China negotiated deal confirmation panels.
                These NPCs have no static choice button (A-D), so when a deal is accepted
                in NegotiationPanel it lands in counterOffers['R'] or ['W'] with no
                OffersPanel button to trigger it.  Show a dedicated confirmation card. */}
            {['russia', 'china'].map(npcKey => {
              const info = NPC_INFO[npcKey]
              if (!info) return null
              const counter = counterOffers[info.letter]
              if (!counter) return null
              // Don't show if there IS a matching static offer (future-proofing)
              if ((offers || []).some(o => o.letter === info.letter)) return null
              console.log(`[deal] Russia/China deal confirmation panel triggered: ${npcKey} ${counter.consequences?.budget ?? 'N/A'}`)
              return (
                <div key={npcKey} className="panel negotiated-deal-panel">
                  <div className="panel-header" style={{ color: 'var(--accent)' }}>
                    {info.flag} NEGOTIATED DEAL — {info.label}
                  </div>
                  <div className="negotiated-deal-text">
                    ⚡ {counter.text}
                  </div>
                  {counter.relation_warning && (
                    <div className="offer-warning" style={{ marginTop: '0.3rem' }}>{counter.relation_warning}</div>
                  )}
                  <div className="negotiated-deal-actions">
                    <button
                      className="btn-primary"
                      onClick={() => handleChoice(info.letter)}
                      disabled={loading || gs?.summit_due}
                    >
                      Accept Deal
                    </button>
                    <button
                      className="btn-ghost"
                      onClick={() => setCounterOffers(prev => {
                        const next = { ...prev }
                        delete next[info.letter]
                        return next
                      })}
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              )
            })}

            {/* Abandon moved into Shadow Cabinet drawer (with confirmation) */}
            </>}
            {/* End 10B-2 activeTab !== 'foreign' gate */}
          </>
        )}

        {/* ── PHASE: CONSEQUENCES ── */}
        {phase === PHASE.CONSEQUENCES && (
          <>
            <div className="turn-divider">— TURN {gs?.current_turn}/{gs?.max_turns} — CHOICE MADE —</div>

            <ConsequencesPanel
              consequences={consequences}
              blackmailResult={blackmailResult}
            />

            {/* FEATURE 2: Brigade tiered deployment — shown before skim if available */}
            {brigadeAvailable && !brigadeResult && (() => {
              const pw = gs?.personal_wealth ?? 0
              const hasIntel = !!gs?.corruption_upgrades?.intelligence_apparatus || (gs?.cabinet_axes?.intelligence || 0) >= 3
              const hasCovert = !!gs?.covert_security_unlocked

              // Session 3 Addendum 2: 3-tier brigade system
              const tierOps = [
                // TIER 1 — Always available
                {
                  op: 1, cost: 1, label: 'Propaganda Campaign', tier: 1,
                  desc: '+10% approval · -2% stability',
                  canAfford: pw >= 1, hasTarget: false, locked: false,
                },
                {
                  op: 2, cost: 2, label: 'Domestic Suppression', tier: 1,
                  desc: '+8% stability · -5% approval · Chosen NPC notified (-5)',
                  canAfford: pw >= 2, hasTarget: true, locked: false,
                },
                // TIER 2 — Requires Intelligence Apparatus
                {
                  op: 3, cost: 3, label: 'Foreign Influence Ops', tier: 2,
                  desc: 'Sow distrust between target NPC and their ally (-10 NPC-to-NPC)',
                  canAfford: pw >= 3, hasTarget: true, locked: !hasIntel,
                  lockReason: 'Requires Intelligence Apparatus',
                },
                {
                  op: 4, cost: 4, label: 'Covert Security Apparatus', tier: 2,
                  desc: '+15% stability · -8% approval · Regime shifts right · Unlocks Tier 3',
                  canAfford: pw >= 4, hasTarget: false, locked: !hasIntel,
                  lockReason: 'Requires Intelligence Apparatus',
                },
                // TIER 3 — Requires Covert Security Apparatus
                {
                  op: 5, cost: 6, label: 'Black Operation', tier: 3,
                  desc: 'Fabricate crisis vs target · Suspend their pressure events 2 turns · HIGH detection risk',
                  canAfford: pw >= 6, hasTarget: true, locked: !hasCovert,
                  lockReason: 'Requires Covert Security Apparatus',
                },
                {
                  op: 6, cost: 5, label: 'State Media Takeover', tier: 3,
                  desc: 'Approval floor 15% · Future approval penalties -20% · Regime shifts right · EU -8',
                  canAfford: pw >= 5, hasTarget: false, locked: !hasCovert,
                  lockReason: 'Requires Covert Security Apparatus',
                },
              ]

              let currentTier = null
              return (
                <div className="brigade-prompt-panel">
                  <div className="brigade-prompt-header">⚔️ LOYALTY BRIGADE DEPLOYMENT</div>
                  <div className="brigade-prompt-desc">
                    Choose an operation or stand down. Cost deducted from personal funds.
                  </div>
                  {brigadeLoading ? (
                    <div className="brigade-loading">Mobilising forces…</div>
                  ) : (
                    <div className="brigade-tiered-ops">
                      {tierOps.map(({ op, cost, label, desc, canAfford, hasTarget, locked, lockReason, tier }) => {
                        const showTierHeader = tier !== currentTier
                        currentTier = tier
                        const tierNames = { 1: 'TIER 1', 2: 'TIER 2', 3: 'TIER 3' }
                        return (
                          <div key={op}>
                            {showTierHeader && (
                              <div className="brigade-tier-header">{tierNames[tier]}</div>
                            )}
                            <div className={`brigade-op-row${locked ? ' brigade-op-locked' : (!canAfford ? ' brigade-op-disabled' : '')}`}>
                              <div className="brigade-op-info">
                                <span className="brigade-op-label">{locked ? '🔒 ' : ''}{label}</span>
                                <span className="brigade-op-desc">{locked ? lockReason : desc}</span>
                              </div>
                              {hasTarget && !locked && canAfford && (
                                <select
                                  className="brigade-target-select"
                                  value={brigadeTargetNpc}
                                  onChange={e => setBrigadeTargetNpc(e.target.value)}
                                >
                                  <option value="usa">🇺🇸 USA</option>
                                  <option value="arabia">🛢️ Arabia</option>
                                  <option value="eu">🇪🇺 EU</option>
                                  <option value="dprg">⚡ DPRG</option>
                                </select>
                              )}
                              <button
                                className="brigade-btn brigade-btn-yes"
                                onClick={() => handleBrigadeDeploy(op, hasTarget ? brigadeTargetNpc : '')}
                                disabled={locked || !canAfford || brigadeLoading}
                              >
                                {locked ? '🔒' : canAfford ? `$${cost}B` : `Need $${cost}B`}
                              </button>
                            </div>
                          </div>
                        )
                      })}
                      <button
                        className="brigade-btn brigade-btn-no"
                        style={{ marginTop: '0.4rem', width: '100%' }}
                        onClick={() => handleBrigadeDeploy(0)}
                        disabled={brigadeLoading}
                      >
                        Stand Down — no deployment
                      </button>
                    </div>
                  )}
                </div>
              )
            })()}

            {/* Brigade result message */}
            {brigadeResult && (
              <div className="alert alert-warn">{brigadeResult}</div>
            )}

            {/* Intel allocation gate removed — now driven by Domestic Affairs Tab */}

            {/* 9.5A-Shadow: Skim prompt removed — persistent skim slider in Cabinet.
                After brigade deploys, auto-submit skim choice 1 to trigger EOT. */}
            {brigadeResult && !loading && (
              <button
                className="btn-primary"
                style={{ marginTop: '0.5rem', width: '100%' }}
                onClick={() => _executeSkim(1)}
              >
                Continue to End of Day →
              </button>
            )}
          </>
        )}

        {/* ── PHASE: INJECT PROMPT ── */}
        {phase === PHASE.INJECT_PROMPT && (
          <>
            <div className="turn-divider">— TURN {gs?.current_turn}/{gs?.max_turns} — EMERGENCY FUNDS —</div>

            <div className="alert alert-warn">
              National treasury is critically low (${gs?.budget?.toFixed(1)}B).
            </div>

            <InjectPanel
              injectOptions={injectOptions}
              onInject={handleInject}
              disabled={loading}
            />
          </>
        )}

        {/* ── PHASE: EOT ── */}
        {phase === PHASE.EOT && (
          <>
            <div className="turn-divider">— END OF DAY {(gs?.current_day || gs?.current_turn || 1) - 1} —</div>

            {skimMessages.length > 0 && (
              <div className="panel">
                <div className="panel-header">Allocation Result</div>
                <ul className="msg-list">
                  {skimMessages.map((m, i) => <li key={i}>{m}</li>)}
                </ul>
              </div>
            )}

            {corruptionAlert && (
              <div className="alert alert-warn">{corruptionAlert}</div>
            )}

            {patriotMessage && (
              <div className="alert alert-success">{patriotMessage}</div>
            )}

            <InterceptPanel intercepts={intercepts} />

            {/* 8D: The Leak crisis card */}
            {gs?.the_leak_fired && !gs?.the_leak_resolved && (
              <div className="leak-crisis-card">
                <div className="leak-crisis-card-header">
                  <span className="leak-crisis-card-badge">\uD83D\uDD34 CRISIS</span>
                  <span className="leak-crisis-card-title">THE LEAK</span>
                </div>
                <div className="leak-crisis-card-body">
                  Classified documents reveal your back-channel with DPRG leadership. You must respond.
                </div>
                <button
                  className="leak-crisis-card-btn"
                  onClick={() => setShowLeakCrisis(true)}
                >
                  ADDRESS CRISIS
                </button>
              </div>
            )}

            <EotPanel messages={eotMessages} />

            {/* Session 7A Step 5: Era transition suggestion card */}
            {eraTransitionSuggestion && !ending && (
              <div className="era-transition-card">
                <div className="era-transition-header">
                  <span className="briefing-tag briefing-tag-briefing">BRIEFING</span>
                  📜 ERA-DEFINING MOMENT
                </div>
                <div className="era-transition-body">
                  <p>
                    {eraTransitionSuggestion.trigger === 'time_backstop'
                      ? `${eraTransitionSuggestion.days_in_era} days have passed without a defining moment.`
                      : `A threshold event has occurred: ${eraTransitionSuggestion.trigger.replace(/_/g, ' ')}.`
                    }
                  </p>
                  <p className="era-transition-prompt">
                    Close Era {eraTransitionSuggestion.era} and receive the Historian's verdict?
                  </p>
                </div>
                <div className="era-transition-actions">
                  <button
                    className="btn-ghost era-dismiss-btn"
                    onClick={handleDismissEraCard}
                    disabled={historianLoading}
                  >
                    Not Yet
                  </button>
                  <button
                    className="btn-primary era-close-btn"
                    onClick={handleCloseEra}
                    disabled={historianLoading}
                  >
                    {historianLoading ? 'Consulting historian…' : 'Close This Era'}
                  </button>
                </div>
              </div>
            )}

            <div className="continue-row">
              <button
                className="btn-primary"
                onClick={handleContinue}
                disabled={loading}
              >
                {ending ? 'See Results' : `Day ${gs?.current_day || gs?.current_turn || 1} →`}
              </button>
            </div>
          </>
        )}

        {loading && (
          <div style={{
            textAlign: 'center',
            padding: '1rem',
            fontFamily: 'var(--mono)',
            fontSize: '0.82rem',
            color: 'var(--muted)'
          }}>
            Consulting advisors…
          </div>
        )}

      </div>
      )}
      </DashboardLayout>

      {/* FEATURE 1: Confirmation modal */}
      {pendingConfirm && (
        <div className="confirm-overlay">
          <div className={`confirm-dialog ${pendingConfirm.dealConflicts?.length ? 'confirm-has-conflicts' : ''}`}>
            <div className="confirm-header">
              {pendingConfirm.type === 'choice' ? 'Confirm Diplomatic Choice' : 'Confirm Allocation'}
            </div>
            <div className="confirm-body">
              {pendingConfirm.text}
            </div>
            {/* fixes_21: Deal conflict warnings */}
            {pendingConfirm.dealConflicts?.length > 0 && (
              <div className="confirm-conflicts">
                <div className="confirm-conflicts-header">⚠️ DEAL CONFLICT WARNING</div>
                {pendingConfirm.dealConflicts.map((c, i) => (
                  <div key={i} className="confirm-conflict-item">
                    This action harms <strong>{c.npc_label}</strong> — conflicts with: {c.deal_summary}
                  </div>
                ))}
              </div>
            )}
            <div className="confirm-actions">
              <button
                className="btn-ghost confirm-back-btn"
                onClick={handleConfirmCancel}
              >
                ← Go Back
              </button>
              <button
                className="btn-primary confirm-commit-btn"
                onClick={handleConfirmExecute}
              >
                {pendingConfirm.dealConflicts?.length ? 'Proceed Anyway' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Session 2 Item 6: Diplomatic Crisis modal — broken deals */}
      {dipCrisisMessages.length > 0 && (
        <div className="confirm-overlay" style={{ zIndex: 350 }}>
          <div className="confirm-dialog" style={{ borderColor: 'var(--danger)', borderWidth: 2 }}>
            <div className="confirm-header" style={{ color: 'var(--danger)', background: 'rgba(229,74,74,0.08)' }}>
              ⚠️ DIPLOMATIC CRISIS
            </div>
            <div className="confirm-body">
              {dipCrisisMessages.map((msg, i) => (
                <p key={i} style={{ marginBottom: i < dipCrisisMessages.length - 1 ? '0.5rem' : 0, color: 'var(--danger)', fontFamily: 'var(--mono)', fontSize: '0.86rem' }}>
                  {msg.replace(/^💔\s*Deal broken:\s*/i, '')}
                </p>
              ))}
              <p style={{ marginTop: '0.75rem', fontSize: '0.84rem', color: 'var(--muted)' }}>
                Expect consequences in upcoming turns.
              </p>
            </div>
            <div className="confirm-actions">
              <button className="btn-primary" onClick={() => setDipCrisisMessages([])}>
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Session 7A Step 5: Historian verdict modal */}
      {historianModal && (
        <div className="confirm-overlay historian-overlay" style={{ zIndex: 360 }}>
          <div className="historian-modal">
            <div className="historian-modal-header">
              📜 {historianModal.isOnDemand ? 'HISTORIAN\'S ASSESSMENT' : `ERA ${historianModal.era} VERDICT`}
            </div>
            <div className="historian-modal-body">
              {historianModal.isOnDemand && (
                <p className="historian-on-demand-note">As things stand…</p>
              )}
              <p className="historian-text">{historianModal.summary}</p>
            </div>
            <div className="historian-modal-actions">
              <button
                className="btn-primary"
                onClick={() => setHistorianModal(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Session 7D: Backchannel Modal */}
      {backchannelNpc && (
        <BackchannelModal
          npcKey={backchannelNpc}
          npcLabel={NPC_INFO[backchannelNpc]?.label || backchannelNpc}
          gs={gs}
          sessionId={sessionId}
          onClose={() => setBackchannelNpc(null)}
          onGsUpdate={setGs}
        />
      )}

      {/* 8D: The Leak crisis modal */}
      {showLeakCrisis && (
        <LeakCrisisModal
          gs={gs}
          sessionId={sessionId}
          onResolve={(newGs) => {
            setShowLeakCrisis(false)
            if (newGs) setGs(newGs)
          }}
        />
      )}

      {/* 9B: Biography Modal — mid-game (draft) view */}
      <BiographyModal
        isOpen={showBiography}
        onClose={() => setShowBiography(false)}
        onPlayAgain={null}
        sessionId={sessionId}
        isDraft={true}
      />

      {/* FEATURE 1: Shadow Cabinet drawer */}
      {shadowCabinetOpen && (
        <ShadowCabinet
          gs={gs}
          sessionId={sessionId}
          onClose={() => setShadowCabinetOpen(false)}
          onUpgradePurchased={handleUpgradePurchased}
          onRestart={onRestart}
        />
      )}

      {/* # DEV FEATURE — remove before public launch */}
      {/* Addition 1: Export Debug Log — desktop only (hidden on mobile via CSS) */}
      <div className="dev-export-footer">
        <button
          className="dev-export-btn"
          onClick={handleExportDebugLog}
          title="Export full game state as .txt debug log"
        >
          ⬇ Export Debug Log
        </button>
      </div>

      {/* fixes_10 Fix 7: Debug/Cheat panel — now gated behind test account via TestPanel */}
      {debugOpen && (
        <DebugPanel
          gs={gs}
          sessionId={sessionId}
          onClose={() => setDebugOpen(false)}
          onGsUpdate={setGs}
        />
      )}

      {/* FIX 4: Persistent cheat panel toggle for automated testing (Comet etc.)
          Always visible, no env gate, survives tab navigation. */}
      <button
        className="dev-cheat-toggle"
        onClick={() => setDebugOpen(prev => !prev)}
        title="Toggle cheat panel"
      >
        DEV
      </button>

      {/* Test Panel — only renders for is_test=true accounts */}
      <TestPanel
        sessionId={sessionId}
        gs={gs}
        onGsUpdate={setGs}
        onOpenCheatPanel={() => setDebugOpen(true)}
        onSnapshotLoad={onSnapshotLoad}
      />

    </div>
  )
}
