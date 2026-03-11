/**
 * NegotiationPanel — slide-up per-NPC chat panel.
 *
 * Props:
 *   npcKey              : 'usa' | 'arabia' | 'eu' | 'dprg'
 *   npcLabel            : display name (e.g. "Bill Hartwell")
 *   npcFlag             : emoji flag
 *   sessionId           : game session ID
 *   onClose             : () => void  — called when "Done Negotiating" is clicked
 *   onCounterOffer      : (letter, counterOffer) => void — called when player accepts an offer
 *   offerLetter         : the letter of this NPC's current offer (e.g. "A")
 *   initialMessages     : [{role, content}]  — history restored from GameScreen
 *   initialPendingOffers: [counterOffer, ...]  — all offers made this session, newest last
 *   onHistoryChange     : (messages, pendingOffers) => void — notify parent of state updates
 *   activeDealSummary   : string | null — one-line summary of active deals with this NPC
 *   currentTurn         : number — current game turn (for calculating specific turn numbers)
 */

import { useState, useRef, useEffect } from 'react'
import { api } from '../api'

// fixes_13 Fix 8: Strip *stage directions* from all Claude-generated text
function renderWithStageDirections(text) {
  if (!text) return <span></span>
  const cleaned = text.replace(/\*[^*]+\*/g, '').replace(/\s{2,}/g, ' ').trim()
  return <span>{cleaned}</span>
}

// Session 7A Feature 10: Client-side energy keyword detection (mirrors gm_engine.py)
const ENERGY_KEYWORDS = [
  'energy', 'oil', 'exclusive', 'partner', 'supply',
  'barrel', 'crude', 'pipeline', 'contract', 'deal',
]
function isEnergyProposal(text) {
  const lower = (text || '').toLowerCase()
  let matches = 0
  for (const kw of ENERGY_KEYWORDS) {
    if (lower.includes(kw)) matches++
  }
  return matches >= 2
}

export default function NegotiationPanel({
  npcKey,
  npcLabel,
  npcFlag,
  sessionId,
  onClose,
  onCounterOffer,
  offerLetter,
  initialMessages = [],
  initialPendingOffers = [],  // all counter-offers made this session, survives minimize
  initialHeldOffer = null,    // held offer (Keep Negotiating state) — survives minimize
  onHistoryChange,
  onGsUpdate = null,  // BUG 6: callback to sync updated game_state (incl. negotiation_log) to parent
  activeDealSummary = null,
  currentTurn = 1,    // FIX O: current game turn for specific turn number display
  gs = null,          // fixes_13 Fix 24: game state needed for covert deal eligibility check
}) {
  const [messages, setMessages] = useState(initialMessages)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  // Session 7A Feature 10: GM consequence object from last energy proposal
  const [gmConsequence, setGmConsequence] = useState(null)

  // All counter-offers made in this session with this NPC, newest last.
  // Seeded from initialPendingOffers so they survive minimize/reopen.
  const [pendingOffers, setPendingOffers] = useState(initialPendingOffers)

  // When "Keep Negotiating" is clicked we hide the banner but hold the offer here.
  // Seeded from initialHeldOffer so it survives minimize/reopen.
  const [heldOffer, setHeldOffer] = useState(initialHeldOffer)

  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Sync messages + offers + heldOffer to parent whenever any of them change,
  // so the full conversation state survives minimize/reopen at any negotiation stage.
  // Also fires on mount so even a panel opened-then-immediately-closed saves state.
  useEffect(() => {
    onHistoryChange && onHistoryChange(messages, pendingOffers, heldOffer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, pendingOffers, heldOffer])

  // Helper: update messages + pendingOffers and notify parent together
  function pushState(newMessages, newPendingOffers) {
    setMessages(newMessages)
    setPendingOffers(newPendingOffers)
    onHistoryChange && onHistoryChange(newMessages, newPendingOffers, heldOffer)
  }

  async function handleSend() {
    const text = input.trim()
    if (!text || loading) return

    // Session 7A Feature 10: Tag user message if it triggers energy detection (Arabia only)
    const energyDetected = npcKey === 'arabia' && isEnergyProposal(text)
    const userMsg = { role: 'user', content: text, energyProposal: energyDetected }
    const withUser = [...messages, userMsg]
    // Optimistically update messages (keep current pendingOffers)
    setMessages(withUser)
    onHistoryChange && onHistoryChange(withUser, pendingOffers)
    setInput('')
    setLoading(true)

    try {
      const history = messages.map(m => ({
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content,
      }))

      // Pass the most recent pending offer (or held offer) so the backend can re-emit it
      // if the model returns null while the player is signalling acceptance.
      const lastKnownOffer = pendingOffers.length > 0
        ? pendingOffers[pendingOffers.length - 1]
        : (heldOffer ?? null)
      const res = await api.negotiate(sessionId, npcKey, text, history, lastKnownOffer)

      // BUG 6: sync updated game_state (with fresh negotiation_log) to parent
      if (res.game_state && onGsUpdate) onGsUpdate(res.game_state)

      // Session 7A Feature 10: Capture GM consequence object
      const _gmResult = res.gm_consequence || null
      if (_gmResult) {
        setGmConsequence(_gmResult)
        console.log('[GM] Consequence preview received:', _gmResult)
      }

      const withNpc = [...withUser, { role: 'npc', content: res.response, gmConsequence: _gmResult }]

      // If a new counter-offer arrived, append it to the stack and clear held offer.
      // Dedup: if the backend re-emitted the same offer as the fallback
      // (identical text), don't push a second copy.
      let newPendingOffers = pendingOffers
      let newHeldOffer = heldOffer

      // fixes_13 Fix 11: Detect if player explicitly declined the offer
      const _declineSignals = /\b(no|decline|reject|refuse|pass|not interested|no deal|walk away|forget it)\b/i
      const _playerDeclined = _declineSignals.test(text)

      if (res.counter_offer) {
        const lastText = pendingOffers.length > 0
          ? pendingOffers[pendingOffers.length - 1]?.text
          : null
        if (res.counter_offer.text !== lastText) {
          newPendingOffers = [...pendingOffers, res.counter_offer]
        }
        newHeldOffer = null  // new offer supersedes held offer
      } else if (heldOffer && !_playerDeclined) {
        // No new offer and player didn't decline — restore held offer
        const lastText = pendingOffers.length > 0
          ? pendingOffers[pendingOffers.length - 1]?.text
          : null
        if (heldOffer.text !== lastText) {
          newPendingOffers = [...pendingOffers, heldOffer]
        }
        newHeldOffer = null
      } else if (_playerDeclined) {
        // fixes_13 Fix 11: Player declined — clear all pending offers and held offer
        newPendingOffers = []
        newHeldOffer = null
        console.log('[NegotiationPanel] fixes_13 Fix 11: Player declined — counter-offer panel cleared')
      }

      setHeldOffer(newHeldOffer)
      pushState(withNpc, newPendingOffers)
    } catch (e) {
      const withErr = [...withUser, {
        role: 'npc',
        content: '… [Transmission error. Try again.]'
      }]
      pushState(withErr, pendingOffers)
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleAcceptOffer(offer, covert = false) {
    if (offer && onCounterOffer) {
      onCounterOffer(offerLetter, offer, covert)
      if (covert) console.log(`[NegotiationPanel] Fix 24: Covert deal accepted with ${npcKey}`)
    }
    onClose()
  }

  // fixes_13 Fix 24: Check if covert deal is available (DPRG 60+)
  const canCovert = npcKey === 'dprg' && (gs?.relations?.dprg ?? 0) >= 60

  // When closing via "Done Negotiating", persist the most recent offer (or held offer)
  // to OffersPanel so the NEGOTIATED badge stays visible even without accepting.
  function handleDoneNegotiating() {
    const latestOffer = pendingOffers.length > 0
      ? pendingOffers[pendingOffers.length - 1]
      : (heldOffer ?? null)
    if (latestOffer && onCounterOffer) {
      onCounterOffer(offerLetter, latestOffer)
    }
    onClose()
  }

  // "Keep Negotiating" on the latest offer: move it to heldOffer so the banner
  // hides but the offer can be restored after the next NPC reply.
  // For older offer rows the X button still permanently dismisses them.
  function handleKeepNegotiating(idx) {
    const offer = pendingOffers[idx]
    const newOffers = pendingOffers.filter((_, i) => i !== idx)
    setHeldOffer(offer)
    // Notify parent with the new held offer so it survives minimize
    setMessages(messages)
    setPendingOffers(newOffers)
    onHistoryChange && onHistoryChange(messages, newOffers, offer)
  }

  // Remove an older offer from the stack permanently (player explicitly dismisses it)
  function handleDismissOffer(idx) {
    const newOffers = pendingOffers.filter((_, i) => i !== idx)
    setMessages(messages)
    setPendingOffers(newOffers)
    onHistoryChange && onHistoryChange(messages, newOffers, heldOffer)
  }

  // FEATURE: parse a counter-offer's consequences and return a money direction label.
  // Normalize a value to billions. The model sometimes emits raw dollar integers
  // (e.g. 3000000000) instead of billions (3.0). Any absolute value ≥ 1 000 000
  // is assumed to be in raw dollars and is divided by 1e9.
  function normB(v) {
    if (typeof v !== 'number') return 0
    return Math.abs(v) >= 1_000_000 ? v / 1e9 : v
  }

  function getMoneyDirection(offer) {
    if (!offer || !offer.consequences) return null
    const c = offer.consequences

    const national = normB((c.budget ?? 0) + (c.budget_delta ?? 0))
    const personal = normB(c.personal_wealth_delta ?? 0)

    const installmentStreams = Array.isArray(c.installments)
      ? c.installments
      : (c.installment_amount != null && c.installment_turns != null)
        ? [{ amount: c.installment_amount, turns: c.installment_turns }]
        : []

    const parts = []
    if (national !== 0) {
      parts.push({ value: national, label: `$${Math.abs(national).toFixed(1)}B national treasury` })
    }
    for (const s of installmentStreams) {
      const amt = normB(s.amount ?? 0)
      const turns = s.turns ?? 0
      const desc = s.description ?? ''
      if (amt !== 0 && turns > 0) {
        const descLabel = desc ? ` (${desc})` : ''
        // FIX O: Use specific turn numbers, show condition if present
        const startTurn = s.start_turn ?? (currentTurn + 1)
        const condType = s.condition_type ?? null
        const condNpc = s.condition_npc ?? null
        const condThresh = s.condition_threshold ?? null
        const condNarrative = s.condition_narrative ?? null
        const npcLabels = { usa: 'USA', arabia: 'Arabia', eu: 'EU', dprg: 'DPRG', europa: 'EU', russia: 'Russia', china: 'China' }
        // fixes_18 Fix A: Show both numeric and narrative conditions
        const numericStr = condType && condNpc
          ? `${npcLabels[condNpc] ?? condNpc} ${condType === 'relation_below' ? 'below' : 'above'} ${condThresh ?? '?'}`
          : ''
        const narrativeStr = condNarrative ? condNarrative : ''
        const condParts = [numericStr, narrativeStr].filter(Boolean)
        const condStr = condParts.length > 0 ? ` (conditional: ${condParts.join(' AND ')})` : ''
        if (turns === 1) {
          parts.push({ value: amt, label: `$${Math.abs(amt).toFixed(1)}B on turn ${startTurn}${condStr}${descLabel}` })
        } else {
          // FIX O: Show specific turn numbers instead of "next turn" / "turn after that"
          const trancheLabels = []
          for (let t = 0; t < turns; t++) {
            trancheLabels.push(`$${Math.abs(amt).toFixed(1)}B turn ${startTurn + t}`)
          }
          parts.push({ value: amt * turns, label: trancheLabels.join(' + ') + condStr + descLabel })
        }
      }
    }
    if (personal !== 0) {
      parts.push({ value: personal, label: `$${Math.abs(personal).toFixed(1)}B personal account` })
    }

    if (parts.length === 0) return null

    const receive = parts.filter(p => p.value > 0)
    const pay = parts.filter(p => p.value < 0)
    const netTotal = parts.reduce((sum, p) => sum + p.value, 0)

    const lines = []
    if (receive.length > 0) lines.push(`✅ YOU RECEIVE: ${receive.map(p => p.label).join(' + ')}`)
    if (pay.length > 0)     lines.push(`❌ YOU PAY: ${pay.map(p => p.label).join(' + ')}`)

    return {
      label: lines.join('\n'),
      isPositive: netTotal >= 0,
      isMixed: receive.length > 0 && pay.length > 0,
    }
  }

  const npcColorClass = {
    usa:    'usa',
    arabia: 'arabia',
    eu:     'eu',
    dprg:   'dprg',
    russia: 'russia',
    china:  'china',
  }[npcKey] || 'usa'

  // Separate newest offer (full banner) from older ones (compact rows)
  const latestOffer = pendingOffers.length > 0 ? pendingOffers[pendingOffers.length - 1] : null
  const olderOffers = pendingOffers.length > 1 ? pendingOffers.slice(0, -1) : []

  return (
    <div className="negotiation-overlay">
      <div className="negotiation-panel">

        {/* Header */}
        <div className={`negotiation-header npc-color-${npcColorClass}`}>
          <span className="negotiation-npc-name">
            {npcFlag} {npcLabel} — Negotiation
          </span>
          <button className="negotiation-close-btn" onClick={onClose}>✕</button>
        </div>

        {/* Active deal summary */}
        {activeDealSummary && (
          <div className="negotiation-active-deal">
            Active: {activeDealSummary}
          </div>
        )}

        {/* Chat log */}
        <div className="negotiation-log" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="negotiation-hint">
              Open a private channel. Ask for better terms, share intelligence, or make a side deal.
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i}>
              <div
                className={`negotiation-msg ${m.role === 'user' ? 'msg-user' : `msg-npc msg-${npcColorClass}`}`}
              >
                {m.role === 'user'
                  ? <>
                      {m.energyProposal && (
                        <span className="gm-energy-badge">Energy Proposal</span>
                      )}
                      <span>{m.content}</span>
                    </>
                  : <span>{renderWithStageDirections(m.content)}</span>
                }
              </div>
              {/* Session 7A Feature 10: GM Assessment card after NPC response */}
              {m.role === 'npc' && m.gmConsequence && (
                <div className="gm-assessment-card">
                  <div className="gm-assessment-header">GM Assessment</div>
                  <div className="gm-assessment-body">
                    <div className="gm-assessment-row">
                      <span className="gm-label">Proposal</span>
                      <span className="gm-value">{m.gmConsequence.proposal_summary}</span>
                    </div>
                    <div className="gm-assessment-row">
                      <span className="gm-label">Type</span>
                      <span className="gm-value">{m.gmConsequence.commitment_type}</span>
                    </div>
                    <div className="gm-assessment-row">
                      <span className="gm-label">Credibility</span>
                      <span className={`gm-value gm-cred-${m.gmConsequence.credibility_assessment}`}>
                        {m.gmConsequence.credibility_assessment}
                      </span>
                    </div>
                    {m.gmConsequence.affected_parties?.length > 0 && (
                      <div className="gm-assessment-row">
                        <span className="gm-label">Also affected</span>
                        <span className="gm-value">{m.gmConsequence.affected_parties.join(', ')}</span>
                      </div>
                    )}
                    {m.gmConsequence.contradicted_deals?.length > 0 && (
                      <div className="gm-assessment-row">
                        <span className="gm-label">Conflicts with</span>
                        <span className="gm-value gm-conflict">{m.gmConsequence.contradicted_deals.join(', ')}</span>
                      </div>
                    )}
                    {m.gmConsequence.second_order_consequences?.length > 0 && (
                      <div className="gm-assessment-row">
                        <span className="gm-label">Ripple effects</span>
                        <span className="gm-value">{m.gmConsequence.second_order_consequences.join('; ')}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="negotiation-msg msg-loading">…</div>
          )}
        </div>

        {/* FIX K: Older offers — greyed out with "Superseded" label, no Accept button */}
        {olderOffers.length > 0 && (
          <div className="older-offers-stack">
            <div className="older-offers-label">Previous offers (superseded):</div>
            {olderOffers.map((offer, idx) => {
              const moneyDir = getMoneyDirection(offer)
              return (
                <div key={idx} className="older-offer-row older-offer-superseded">
                  <span className="older-offer-text" title={offer.text}>
                    <span className="superseded-badge">Superseded</span>
                    {offer.text}
                  </span>
                  {moneyDir && (
                    <span className={`older-offer-money money-superseded`}>
                      {moneyDir.label}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* Latest offer — full banner */}
        {latestOffer && (() => {
          const moneyDir = getMoneyDirection(latestOffer)
          return (
            <div className="counter-offer-banner">
              <div className="counter-offer-label">⚡ Counter-Offer on the Table</div>
              <div className="counter-offer-text">{latestOffer.text}</div>
              {moneyDir && (
                <div className={`counter-offer-money-dir ${moneyDir.isMixed ? 'money-mixed' : moneyDir.isPositive ? 'money-receive' : 'money-pay'}`}>
                  {moneyDir.label}
                </div>
              )}
              <div className="counter-offer-actions">
                <button
                  className="btn-accept-counter"
                  onClick={() => handleAcceptOffer(latestOffer)}
                >
                  Accept & Close
                </button>
                {canCovert && (
                  <button
                    className="btn-accept-counter btn-covert"
                    onClick={() => handleAcceptOffer(latestOffer, true)}
                    title="Covert deal: zero diplomatic footprint, no cross-NPC penalties, no heat, no EOT log entry"
                  >
                    🕶️ Accept Covert
                  </button>
                )}
                <button
                  className="btn-keep-negotiating"
                  onClick={() => handleKeepNegotiating(pendingOffers.length - 1)}
                >
                  Keep Negotiating
                </button>
              </div>
            </div>
          )
        })()}

        {/* Held offer pill — shown when player clicked "Keep Negotiating" */}
        {heldOffer && !latestOffer && (
          <div className="held-offer-pill">
            <span className="held-offer-icon">⏸</span>
            <span className="held-offer-text" title={heldOffer.text}>Offer held: {heldOffer.text}</span>
            <button
              className="btn-accept-counter held-offer-accept"
              onClick={() => handleAcceptOffer(heldOffer)}
            >
              Accept
            </button>
            {canCovert && (
              <button
                className="btn-accept-counter held-offer-accept btn-covert"
                onClick={() => handleAcceptOffer(heldOffer, true)}
                title="Covert deal: zero diplomatic footprint"
              >
                🕶️ Covert
              </button>
            )}
            <button
              className="btn-ghost held-offer-dismiss"
              onClick={() => setHeldOffer(null)}
              title="Discard this offer"
            >
              ✕
            </button>
          </div>
        )}

        {/* Input row */}
        <div className="negotiation-input-row">
          <textarea
            className="negotiation-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Your message… (Enter to send)"
            rows={2}
            disabled={loading}
          />
          <button
            className="btn-send"
            onClick={handleSend}
            disabled={loading || !input.trim()}
          >
            Send
          </button>
        </div>

        {/* Footer */}
        <div className="negotiation-footer">
          <button className="btn-ghost negotiation-done-btn" onClick={handleDoneNegotiating}>
            Done Negotiating
          </button>
        </div>
      </div>
    </div>
  )
}
