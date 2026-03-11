/**
 * BackchannelModal — Session 7D Step 2: Covert diplomatic channel UI.
 * Dark modal overlay with crimson header, conversation history,
 * detection risk meter, promise banners, and text input.
 *
 * Props:
 *   npcKey       : 'usa'|'arabia'|'eu'|'dprg'
 *   npcLabel     : display name
 *   gs           : game_state
 *   sessionId    : string
 *   onClose      : () => void
 *   onGsUpdate   : (newGs) => void
 */

import { useState, useRef, useEffect } from 'react'
import { api } from '../api'

// Client-side detection risk — mirrors npc_engine.calculate_detection_risk
const BASE_RISK = { usa: 0.25, arabia: 0.20, eu: 0.15, dprg: 0.10, russia: 0.20, china: 0.18 }
const OPSEC_MULT = { 0: 1.0, 1: 0.7, 2: 0.45 }

function calcDetectionRisk(npcKey, gs) {
  const base = BASE_RISK[npcKey] ?? 0.20
  const opsec = gs?.opsec_level ?? 0
  const mult = OPSEC_MULT[opsec] ?? 1.0
  let risk = base * mult

  const rel = gs?.relations || {}
  if (npcKey === 'usa' && (rel.usa ?? 50) < 30) risk *= 1.3
  if (npcKey === 'eu' && (rel.eu ?? 50) < 30) risk *= 1.2
  if (npcKey === 'dprg') risk *= 0.8

  return Math.min(1.0, risk)
}

function riskTier(risk) {
  if (risk < 0.15) return { label: 'LOW',      color: '#4db6ac' }
  if (risk < 0.30) return { label: 'MODERATE', color: '#ffb74d' }
  if (risk < 0.50) return { label: 'HIGH',     color: '#ff8a65' }
  return              { label: 'CRITICAL', color: '#ef5350' }
}

export default function BackchannelModal({ npcKey, npcLabel, gs, sessionId, onClose, onGsUpdate }) {
  const [messages, setMessages] = useState([])   // { role: 'player'|'npc', text: string }
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)
  const [promiseFlash, setPromiseFlash] = useState(null)  // promise summary text
  const [activePromises, setActivePromises] = useState(
    (gs?.active_backchannel_promises || []).filter(p => p.npc_id === npcKey && p.promise_text)
  )
  const scrollRef = useRef(null)

  // Load existing backchannel history for this NPC on mount
  useEffect(() => {
    const history = gs?.backchannel_history || []
    const npcHistory = history.filter(h => h.npc_id === npcKey)
    const loaded = []
    npcHistory.forEach(h => {
      loaded.push({ role: 'player', text: h.player_message })
      loaded.push({ role: 'npc', text: h.response_text })
    })
    if (loaded.length > 0) setMessages(loaded)
    console.log('[BACKCHANNEL] Modal opened for:', npcKey)
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const risk = calcDetectionRisk(npcKey, gs)
  const tier = riskTier(risk)

  async function handleSend() {
    const trimmed = input.trim()
    if (!trimmed || sending) return

    // Add player message immediately
    setMessages(prev => [...prev, { role: 'player', text: trimmed }])
    setInput('')
    setSending(true)
    setError(null)

    try {
      const res = await api.backchannel(sessionId, npcKey, trimmed)
      console.log('[BACKCHANNEL] Response received:', npcKey)

      // Add NPC response
      setMessages(prev => [...prev, { role: 'npc', text: res.response_text }])

      // Promise flash
      if (res.promise_recorded && res.promise_summary) {
        setPromiseFlash(res.promise_summary)
        setActivePromises(prev => [...prev, {
          npc_id: npcKey,
          summary: res.promise_summary,
          turn_created: gs?.current_turn
        }])
        setTimeout(() => setPromiseFlash(null), 5000)
      }

      // Update game state if returned
      if (res.game_state && onGsUpdate) {
        onGsUpdate(res.game_state)
      }
    } catch (e) {
      console.error('[BACKCHANNEL] Send failed:', e)
      setError(e.message)
      setTimeout(() => setError(null), 4000)
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="backchannel-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="backchannel-modal">
        {/* Detection risk meter — thin bar at top */}
        <div className="backchannel-risk-meter">
          <div
            className="backchannel-risk-meter-fill"
            style={{
              width: `${Math.min(100, risk * 100)}%`,
              background: tier.color
            }}
          />
        </div>

        {/* Header */}
        <div className="backchannel-header">
          <div className="backchannel-title">
            🔒 COVERT CHANNEL — {npcLabel?.toUpperCase()}
          </div>
          <div className="backchannel-subtitle">
            NOT LOGGED IN OFFICIAL RECORD — DETECTION RISK:{' '}
            <span style={{ color: tier.color, fontWeight: 700 }}>{tier.label}</span>
          </div>
        </div>

        {/* Promise recorded flash */}
        {promiseFlash && (
          <div className="backchannel-promise-banner">
            📋 PROMISE RECORDED — {promiseFlash}
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="backchannel-error">{error}</div>
        )}

        {/* Conversation history */}
        <div className="backchannel-messages" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="backchannel-empty">
              Channel open. Your messages will not appear in official diplomatic records.
              <br />Exercise caution — discovery carries severe consequences.
            </div>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`backchannel-message ${msg.role === 'player' ? 'msg-player' : 'msg-npc'}`}
            >
              <div className="backchannel-msg-label">
                {msg.role === 'player' ? 'YOU (COVERT)' : npcLabel?.toUpperCase()}
              </div>
              <div className="backchannel-msg-text">{msg.text}</div>
            </div>
          ))}
          {sending && (
            <div className="backchannel-message msg-npc">
              <div className="backchannel-msg-label">{npcLabel?.toUpperCase()}</div>
              <div className="backchannel-msg-text backchannel-typing">
                Decrypting…
              </div>
            </div>
          )}
        </div>

        {/* Active promises list */}
        {activePromises.length > 0 && (
          <div className="backchannel-promises-list">
            <div className="backchannel-promises-header">ACTIVE COVERT PROMISES</div>
            {activePromises.map((p, i) => (
              <div key={i} className="backchannel-promise-item">
                • {p.promise_text || p.summary}
              </div>
            ))}
          </div>
        )}

        {/* Input area — no form tags */}
        <div className="backchannel-input-area">
          <textarea
            className="backchannel-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type covert message…"
            rows={2}
            disabled={sending}
          />
          <button
            className="backchannel-send-btn"
            onClick={handleSend}
            disabled={sending || !input.trim()}
          >
            {sending ? 'Sending…' : 'Send'}
          </button>
        </div>

        {/* Close button */}
        <button className="backchannel-close-btn" onClick={onClose}>
          CLOSE CHANNEL
        </button>
      </div>
    </div>
  )
}
