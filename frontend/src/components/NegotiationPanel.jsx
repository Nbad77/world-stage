/**
 * NegotiationPanel — slide-up per-NPC chat panel.
 *
 * Props:
 *   npcKey              : 'usa' | 'arabia' | 'eu' | 'dprg'
 *   npcLabel            : display name (e.g. "Bill Washington")
 *   npcFlag             : emoji flag
 *   sessionId           : game session ID
 *   onClose             : () => void  — called when "Done Negotiating" is clicked
 *   onCounterOffer      : (letter, counterOffer) => void — called when player accepts an offer
 *   offerLetter         : the letter of this NPC's current offer (e.g. "A")
 *   initialMessages     : [{role, content}]  — history restored from GameScreen
 *   initialPendingOffers: [counterOffer, ...]  — all offers made this session, newest last
 *   onHistoryChange     : (messages, pendingOffers) => void — notify parent of state updates
 *   activeDealSummary   : string | null — one-line summary of active deals with this NPC
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
  initialMessages = [],
  initialPendingOffers = [],  // all counter-offers made this session, survives minimize
  onHistoryChange,
  activeDealSummary = null,
}) {
  const [messages, setMessages] = useState(initialMessages)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  // All counter-offers made in this session with this NPC, newest last.
  // Seeded from initialPendingOffers so they survive minimize/reopen.
  const [pendingOffers, setPendingOffers] = useState(initialPendingOffers)

  // When "Keep Negotiating" is clicked we hide the banner but hold the offer here.
  // If the NPC's next reply has no new counter_offer, we restore it automatically
  // so the Accept button stays reachable.
  const [heldOffer, setHeldOffer] = useState(null)

  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Helper: update messages + pendingOffers and notify parent together
  function pushState(newMessages, newPendingOffers) {
    setMessages(newMessages)
    setPendingOffers(newPendingOffers)
    onHistoryChange && onHistoryChange(newMessages, newPendingOffers)
  }

  async function handleSend() {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { role: 'user', content: text }
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

      const withNpc = [...withUser, { role: 'npc', content: res.response }]

      // If a new counter-offer arrived, append it to the stack and clear held offer.
      // Dedup: if the backend re-emitted the same offer as the fallback
      // (identical text), don't push a second copy.
      let newPendingOffers = pendingOffers
      let newHeldOffer = heldOffer
      if (res.counter_offer) {
        const lastText = pendingOffers.length > 0
          ? pendingOffers[pendingOffers.length - 1]?.text
          : null
        if (res.counter_offer.text !== lastText) {
          newPendingOffers = [...pendingOffers, res.counter_offer]
        }
        newHeldOffer = null  // new offer supersedes held offer
      } else if (heldOffer) {
        // No new offer — restore the held offer back into the banner
        const lastText = pendingOffers.length > 0
          ? pendingOffers[pendingOffers.length - 1]?.text
          : null
        if (heldOffer.text !== lastText) {
          newPendingOffers = [...pendingOffers, heldOffer]
        }
        newHeldOffer = null
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

  function handleAcceptOffer(offer) {
    if (offer && onCounterOffer) {
      onCounterOffer(offerLetter, offer)
    }
    onClose()
  }

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
    pushState(messages, newOffers)
  }

  // Remove an older offer from the stack permanently (player explicitly dismisses it)
  function handleDismissOffer(idx) {
    const newOffers = pendingOffers.filter((_, i) => i !== idx)
    pushState(messages, newOffers)
  }

  // FEATURE: parse a counter-offer's consequences and return a money direction label.
  function getMoneyDirection(offer) {
    if (!offer || !offer.consequences) return null
    const c = offer.consequences

    const national = (c.budget ?? 0) + (c.budget_delta ?? 0)
    const personal = c.personal_wealth_delta ?? 0

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
      const amt = s.amount ?? 0
      const turns = s.turns ?? 0
      if (amt !== 0 && turns > 0) {
        const desc = s.description ? ` (${s.description})` : ''
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

  // Separate newest offer (full banner) from older ones (compact rows)
  const latestOffer = pendingOffers.length > 0 ? pendingOffers[pendingOffers.length - 1] : null
  const olderOffers = pendingOffers.length > 1 ? pendingOffers.slice(0, -1) : []

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

        {/* Older offers — compact rows above the latest banner */}
        {olderOffers.length > 0 && (
          <div className="older-offers-stack">
            <div className="older-offers-label">Earlier offers on the table:</div>
            {olderOffers.map((offer, idx) => {
              const moneyDir = getMoneyDirection(offer)
              return (
                <div key={idx} className="older-offer-row">
                  <span className="older-offer-text" title={offer.text}>{offer.text}</span>
                  {moneyDir && (
                    <span className={`older-offer-money ${moneyDir.isMixed ? 'money-mixed' : moneyDir.isPositive ? 'money-receive' : 'money-pay'}`}>
                      {moneyDir.label}
                    </span>
                  )}
                  <div className="older-offer-actions">
                    <button
                      className="btn-accept-counter"
                      onClick={() => handleAcceptOffer(offer)}
                    >
                      Accept
                    </button>
                    <button
                      className="btn-ghost older-offer-dismiss"
                      onClick={() => handleDismissOffer(idx)}
                      title="Remove this offer"
                    >
                      ✕
                    </button>
                  </div>
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
