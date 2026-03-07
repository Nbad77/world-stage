/**
 * SummitModal — Session 7E Step 2: UN Summit group chat UI.
 * Replaces center panel content (sidebars remain visible).
 * Player declares, all NPCs react in parallel, commitments tracked.
 *
 * Props:
 *   gs           : game_state
 *   sessionId    : string
 *   onClose      : () => void   — closes summit, unblocks End Day
 *   onGsUpdate   : (newGs) => void
 */

import { useState, useRef, useEffect } from 'react'
import { api } from '../api'

const NPC_INFO = {
  usa:    { name: 'Bill Hartwell',  flag: '🇺🇸', isObserver: false },
  arabia: { name: 'Sadam',          flag: '🛢️',  isObserver: false },
  eu:     { name: 'Marsha',         flag: '🇪🇺', isObserver: false },
  dprg:   { name: 'Ji-won Ryang',   flag: '⚡',  isObserver: false },
  russia: { name: 'Russia',         flag: '🇷🇺', isObserver: true },
  china:  { name: 'China',          flag: '🇨🇳', isObserver: true },
}

const REACTION_BADGES = {
  endorse:   { label: 'ENDORSES',   color: '#4caf50' },
  challenge: { label: 'CHALLENGES', color: '#ef5350' },
  neutral:   { label: 'OBSERVES',   color: '#90a4ae' },
  silence:   { label: '—',          color: '#546e7a' },
}

export default function SummitModal({ gs, sessionId, onClose, onGsUpdate }) {
  const [thread, setThread] = useState([])      // { type: 'declaration'|'reaction', ... }
  const [input, setInput] = useState('')
  const [declaring, setDeclaring] = useState(false)
  const [autoLoading, setAutoLoading] = useState(false)
  const [autoLoaded, setAutoLoaded] = useState(false)
  const [commitmentFlash, setCommitmentFlash] = useState(null)
  const [error, setError] = useState(null)
  const [hasDeclared, setHasDeclared] = useState(false)
  const scrollRef = useRef(null)

  // Load any existing summit history for current day on mount
  useEffect(() => {
    const history = gs?.summit_history || []
    const currentDay = gs?.current_day ?? gs?.current_turn ?? 0
    const todaySummit = history.find(h => h.day === currentDay)
    if (todaySummit) {
      const loaded = []
      loaded.push({ type: 'declaration', text: todaySummit.player_declaration })
      if (todaySummit.npc_reactions) {
        todaySummit.npc_reactions.forEach(r => {
          loaded.push({ type: 'reaction', ...r })
        })
      }
      setThread(loaded)
      setHasDeclared(true)
    }
    console.log('[SUMMIT] Modal opened, era:', gs?.current_era, 'day:', currentDay)
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [thread])

  async function handleAutoPosition() {
    if (autoLoading) return
    setAutoLoading(true)
    setError(null)
    try {
      const res = await api.summitAutoPosition(sessionId)
      setInput(res.position_text || '')
      setAutoLoaded(true)
      console.log('[SUMMIT] Auto-position loaded')
    } catch (e) {
      console.error('[SUMMIT] Auto-position failed:', e)
      setError(e.message)
    } finally {
      setAutoLoading(false)
    }
  }

  async function handleDeclare() {
    const trimmed = input.trim()
    if (!trimmed || declaring) return

    setDeclaring(true)
    setError(null)
    setAutoLoaded(false)

    // Add declaration to thread immediately
    setThread(prev => [...prev, { type: 'declaration', text: trimmed }])
    setInput('')

    try {
      const res = await api.summitDeclare(sessionId, trimmed)
      console.log('[SUMMIT] Declaration processed, reactions:', res.reactions?.length)

      // Add all NPC reactions to thread
      if (res.reactions) {
        setThread(prev => [
          ...prev,
          ...res.reactions.map(r => ({ type: 'reaction', ...r }))
        ])
      }

      // Commitment flash
      if (res.commitments_recorded > 0) {
        setCommitmentFlash(res.commitments_recorded)
        setTimeout(() => setCommitmentFlash(null), 5000)
      }

      // Update game state
      if (res.game_state && onGsUpdate) {
        onGsUpdate(res.game_state)
      }

      setHasDeclared(true)
    } catch (e) {
      console.error('[SUMMIT] Declaration failed:', e)
      setError(e.message)
      setTimeout(() => setError(null), 5000)
    } finally {
      setDeclaring(false)
    }
  }

  async function handleCloseSummit() {
    try {
      const res = await api.summitClose(sessionId)
      if (res.game_state && onGsUpdate) {
        onGsUpdate(res.game_state)
      }
      console.log('[SUMMIT] Summit closed')
      onClose()
    } catch (e) {
      console.error('[SUMMIT] Close failed:', e)
      setError(e.message)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey && !declaring) {
      e.preventDefault()
      handleDeclare()
    }
  }

  const era = gs?.current_era ?? 1
  const day = gs?.current_day ?? gs?.current_turn ?? 1

  return (
    <div className="summit-modal">
      {/* Header */}
      <div className="summit-header">
        <div className="summit-title">
          🌐 UN SUMMIT — ERA {era} · DAY {day}
        </div>
        <div className="summit-subtitle">
          PUBLIC DECLARATIONS ARE HEARD BY ALL PARTIES
        </div>
      </div>

      {/* Commitment flash */}
      {commitmentFlash && (
        <div className="summit-commitment-flash">
          📋 {commitmentFlash} PUBLIC COMMITMENT{commitmentFlash > 1 ? 'S' : ''} RECORDED — these will be tracked
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="summit-error">{error}</div>
      )}

      {/* Thread area */}
      <div className="summit-thread" ref={scrollRef}>
        {thread.length === 0 && (
          <div className="summit-empty">
            The assembly awaits your statement.
            <br />Use AUTO-POSITION for a safe holding statement, or draft your own declaration.
          </div>
        )}

        {thread.map((item, i) => {
          if (item.type === 'declaration') {
            return (
              <div key={i} className="summit-declaration">
                <div className="summit-declaration-label">YOU DECLARED:</div>
                <div className="summit-declaration-text">{item.text}</div>
              </div>
            )
          }

          // NPC reaction
          const info = NPC_INFO[item.npc_id] || { name: item.npc_name, flag: '🏳️', isObserver: false }
          const badge = REACTION_BADGES[item.reaction_type] || REACTION_BADGES.neutral
          const isSilence = item.reaction_type === 'silence' || !item.reaction_text

          return (
            <div
              key={i}
              className={`summit-message ${item.reaction_type || 'neutral'} ${info.isObserver ? 'summit-observer' : ''}`}
            >
              <div className="summit-message-header">
                <div className="summit-npc-identity">
                  <span className="summit-npc-flag">{info.flag}</span>
                  <span className="summit-npc-name">{info.name}</span>
                  {info.isObserver && <span className="summit-observer-badge">OBSERVER</span>}
                </div>
                <span className="summit-reaction-badge" style={{ color: badge.color }}>
                  {badge.label}
                </span>
              </div>
              {isSilence ? (
                <div className="summit-silence">— [said nothing publicly]</div>
              ) : (
                <div className="summit-reaction-text">{item.reaction_text}</div>
              )}
            </div>
          )
        })}

        {declaring && (
          <div className="summit-loading">
            Delegates are responding…
          </div>
        )}
      </div>

      {/* Action area */}
      <div className="summit-action-area">
        <textarea
          className="summit-input"
          value={input}
          onChange={e => { setInput(e.target.value); setAutoLoaded(false) }}
          onKeyDown={handleKeyDown}
          placeholder="Address the assembly…"
          rows={3}
          disabled={declaring}
        />
        {autoLoaded && (
          <div className="summit-auto-note">
            ⚠ Auto-drafted — review before declaring
          </div>
        )}
        <div className="summit-buttons">
          <button
            className="summit-btn summit-btn-auto"
            onClick={handleAutoPosition}
            disabled={declaring || autoLoading}
          >
            {autoLoading ? 'Drafting…' : 'AUTO-POSITION'}
          </button>
          <button
            className="summit-btn summit-btn-declare"
            onClick={handleDeclare}
            disabled={declaring || !input.trim()}
          >
            {declaring ? 'Declaring…' : 'DECLARE'}
          </button>
          <button
            className="summit-btn summit-btn-close"
            onClick={handleCloseSummit}
            disabled={declaring}
            title={!hasDeclared ? 'You may close without declaring' : 'Close summit and return to briefing'}
          >
            CLOSE SUMMIT
          </button>
        </div>
      </div>
    </div>
  )
}
