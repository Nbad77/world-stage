/**
 * NegotiationPanel — slide-up per-NPC chat panel.
 *
 * Props:
 *   npcKey           : 'usa' | 'arabia' | 'eu' | 'dprg'
 *   npcLabel         : display name (e.g. "Bill Washington")
 *   npcFlag          : emoji flag
 *   sessionId        : game session ID
 *   onClose          : () => void  — called when "Done Negotiating" is clicked
 *   onCounterOffer   : (letter, counterOffer) => void — called when NPC offers new terms
 *   offerLetter      : the letter of this NPC's current offer (e.g. "A")
 *   initialMessages  : [{role, content}]  — history restored from GameScreen (BUG 5)
 *   onHistoryChange  : (messages) => void — notify parent of history updates (BUG 5)
 *   activeDealSummary: string | null — one-line summary of active deals with this NPC (FEATURE 2)
 */

import { useState, useRef, useEffect } from 'react'
import { api } from '../api'

function renderWithStageDirections(text) {
  const parts = text.split(/(\*[^*]+\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('*') && part.endsWith('*')) {
      return (
        <em key={i} style={{ color: 'var(--muted)', fontStyle: 'italic' }}>
          {part.slice(1, -1)}
        </em>
      )
    }
    return <span key={i}>{part}</span>
  })
}

export default function NegotiationPanel({
  npcKey,
  npcLabel,
  npcFlag,
  sessionId,
  onClose,
  onCounterOffer,
  offerLetter,
  initialMessages = [],   // BUG 5: restored history from GameScreen
  onHistoryChange,        // BUG 5: notify parent when history changes
  activeDealSummary = null, // FEATURE 2: one-line summary of active deals
}) {
  // BUG 5: seed from initialMessages so closing/reopening restores the conversation
  const [messages, setMessages] = useState(initialMessages)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  // BUG 5: restore any pending counter-offer that was in the last message set
  const [counterOffer, setCounterOffer] = useState(null)
  // FEATURE 3: last offer persists in footer after player clicks "Keep Negotiating"
  const [lastOffer, setLastOffer] = useState(null)
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // BUG 5: helper that sets messages AND notifies parent of new history
  function pushMessages(newMessages) {
    setMessages(newMessages)
    onHistoryChange && onHistoryChange(newMessages)
  }

  async function handleSend() {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { role: 'user', content: text }
    const withUser = [...messages, userMsg]
    pushMessages(withUser)
    setInput('')
    setLoading(true)

    try {
      // Convert to API history format (exclude the just-added user message — it's passed as `message`)
      const history = messages.map(m => ({
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content,
      }))

      const res = await api.negotiate(sessionId, npcKey, text, history)

      const withNpc = [...withUser, { role: 'npc', content: res.response }]
      pushMessages(withNpc)

      if (res.counter_offer) {
        setCounterOffer(res.counter_offer)
      }
    } catch (e) {
      const withErr = [...withUser, {
        role: 'npc',
        content: '… [Transmission error. Try again.]'
      }]
      pushMessages(withErr)
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

  function handleAcceptCounterOffer(offerToAccept) {
    const target = offerToAccept || counterOffer
    if (target && onCounterOffer) {
      onCounterOffer(offerLetter, target)
    }
    onClose()
  }

  // Stage 4 Polish: when closing via "Done Negotiating", persist any staged offer
  // so the NEGOTIATED badge remains visible in OffersPanel.
  function handleDoneNegotiating() {
    const stagedOffer = counterOffer || lastOffer
    if (stagedOffer && onCounterOffer) {
      onCounterOffer(offerLetter, stagedOffer)
    }
    onClose()
  }

  // FEATURE 3: dismiss the banner but keep the offer accessible in the footer
  function handleKeepNegotiating() {
    setLastOffer(counterOffer)
    setCounterOffer(null)
  }

  // FEATURE: parse a counter-offer's consequences and return a money direction label.
  // Returns { label: string, isPositive: bool } | null if no money involved.
  // All values use player-perspective sign: positive = Europa receives, negative = Europa pays.
  function getMoneyDirection(offer) {
    if (!offer || !offer.consequences) return null
    const c = offer.consequences

    // Immediate budget payment (one-time this turn)
    const national = (c.budget ?? 0) + (c.budget_delta ?? 0)
    const personal = c.personal_wealth_delta ?? 0

    // Installment streams — new array format takes priority over legacy single fields
    const installmentStreams = Array.isArray(c.installments)
      ? c.installments
      : (c.installment_amount != null && c.installment_turns != null)
        ? [{ amount: c.installment_amount, turns: c.installment_turns }]
        : []

    // Build annotated parts with sign-aware value and display label
    const parts = []
    if (national !== 0) {
      parts.push({ value: national, label: `$${Math.abs(national).toFixed(1)}B national treasury` })
    }
    for (const s of installmentStreams) {
      const amt = s.amount ?? 0
      const turns = s.turns ?? 0
      if (amt !== 0 && turns > 0) {
        const desc = s.description ? ` (${s.description})` : ''
        // Human-readable: "next turn" for 1 EOT payment, "$/turn × N turns" for more
        const label = turns === 1
          ? `$${Math.abs(amt).toFixed(1)}B next turn${desc}`
          : `$${Math.abs(amt).toFixed(1)}B/turn × ${turns} turns${desc}`
        parts.push({ value: amt * turns, label })
      }
    }
    if (personal !== 0) {
      parts.push({ value: personal, label: `$${Math.abs(personal).toFixed(1)}B personal account` })
    }

    if (parts.length === 0) return null

    // Separate receive / pay buckets so mixed deals show both lines
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
  }[npcKey] || 'usa'

  return (
    <div className="negotiation-overlay">
      <div className="negotiation-panel">

        {/* Header */}
        <div className={`negotiation-header npc-color-${npcColorClass}`}>
          <span className="negotiation-npc-name">
            {npcFlag} {npcLabel} — Private Channel
          </span>
          <button className="negotiation-close-btn" onClick={onClose}>✕</button>
        </div>

        {/* FEATURE 2: Active deal summary — one line shown only when a deal is active */}
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
            <div
              key={i}
              className={`negotiation-msg ${m.role === 'user' ? 'msg-user' : `msg-npc msg-${npcColorClass}`}`}
            >
              {m.role === 'user'
                ? <span>{m.content}</span>
                : <span>{renderWithStageDirections(m.content)}</span>
              }
            </div>
          ))}
          {loading && (
            <div className="negotiation-msg msg-loading">…</div>
          )}
        </div>

        {/* Counter-offer banner — FEATURE 3: two-button layout */}
        {counterOffer && (() => {
          const moneyDir = getMoneyDirection(counterOffer)
          return (
            <div className="counter-offer-banner">
              <div className="counter-offer-label">⚡ Counter-Offer on the Table</div>
              <div className="counter-offer-text">{counterOffer.text}</div>
              {/* FEATURE: money direction clarity label — mixed deals show both lines */}
              {moneyDir && (
                <div className={`counter-offer-money-dir ${moneyDir.isMixed ? 'money-mixed' : moneyDir.isPositive ? 'money-receive' : 'money-pay'}`}>
                  {moneyDir.label}
                </div>
              )}
              <div className="counter-offer-actions">
                <button
                  className="btn-accept-counter"
                  onClick={() => handleAcceptCounterOffer(counterOffer)}
                >
                  Accept & Close
                </button>
                <button
                  className="btn-keep-negotiating"
                  onClick={handleKeepNegotiating}
                >
                  Keep Negotiating
                </button>
              </div>
            </div>
          )
        })()}

        {/* FEATURE 3: Persistent last-offer footer — visible after "Keep Negotiating" */}
        {!counterOffer && lastOffer && (() => {
          const moneyDir = getMoneyDirection(lastOffer)
          return (
            <div className="last-offer-bar">
              <span className="last-offer-label">Last offer:</span>
              <span className="last-offer-text" title={lastOffer.text}>{lastOffer.text}</span>
              {moneyDir && (
                <span className={`last-offer-money-dir ${moneyDir.isMixed ? 'money-mixed' : moneyDir.isPositive ? 'money-receive' : 'money-pay'}`}>
                  {moneyDir.label}
                </span>
              )}
              <button
                className="btn-accept-last-offer"
                onClick={() => handleAcceptCounterOffer(lastOffer)}
              >
                Accept
              </button>
            </div>
          )
        })()}

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
