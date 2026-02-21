/**
 * NPC dialogue panel — shows 4 NPC messages for the current turn.
 *
 * The live API format (from npc_engine._format_* wrappers) is:
 *   Line 1: "🇺🇸 USA (State Department):"   ← name + optional (subtitle)
 *   Line 2: '"dialogue text here"'           ← text, may have surrounding quotes
 *
 * Arabia / DPRG may also have inline stage directions on line 2:
 *   Line 2: '*lighting cigar* "text"'
 *   or just: '*lighting cigar* text'
 *
 * The fallback (static) format uses ─ separators but we handle both.
 *
 * We extract:
 *   subtitle — e.g. "State Department", "Brotherhood Offer"
 *   text     — raw dialogue, quotes stripped
 * Then render *stage directions* as <em> italic.
 *
 * FEATURE 4: Dynamic intelligence apparatus — replaces static NPC_INTEL with
 *   tier-gated Claude-generated intel fetched from /get_intel endpoint.
 *   Tier label shown: "🕵️ TIER 2 INTEL — Operational"
 */

import { useState, useEffect, useRef } from 'react'
import { api } from '../api'

const NPC_ORDER = [
  { key: 'usa',    label: 'Bill Washington',  flag: '🇺🇸' },
  { key: 'arabia', label: 'Sadam',            flag: '🛢️' },
  { key: 'eu',     label: 'Marsha',           flag: '🇪🇺' },
  { key: 'dprg',   label: 'Ji-won Ryang',     flag: '⚡' },
]

// Known NPC name prefixes that Claude sometimes adds verbatim — strip these
const NPC_PREFIX_RE = /^(?:🇺🇸\s*)?(?:USA|BILL)[^:]*:\s*/i
const ARABIA_PREFIX_RE = /^(?:🛢️?\s*)?SADAM[^:]*:\s*/i
const EU_PREFIX_RE = /^(?:🇪🇺\s*)?(?:EU|MARSHA)[^:]*:\s*/i
const DPRG_PREFIX_RE = /^(?:⚡\s*)?(?:JI-WON|JIWON)[^:]*:\s*/i
const ALL_PREFIXES = [NPC_PREFIX_RE, ARABIA_PREFIX_RE, EU_PREFIX_RE, DPRG_PREFIX_RE]

function stripNpcPrefix(text) {
  for (const re of ALL_PREFIXES) {
    text = text.replace(re, '')
  }
  return text.trim()
}

/**
 * Parse a raw npc_engine string into { subtitle, text }.
 * Handles both the live API format (2 lines, no ─) and the
 * CLI fallback format (with ─ separators).
 */
function parseNpcString(raw) {
  if (!raw) return { subtitle: '', text: '…' }

  const lines = raw.split('\n').map(l => l.trim()).filter(Boolean)

  // ── Case A: live API format — no ─ lines ──────────────────────────────
  const hasDashes = lines.some(l => l.match(/^─+$/))

  let subtitle = ''
  let textLines = []

  if (!hasDashes && lines.length >= 1) {
    const firstLine = lines[0]
    if (firstLine.endsWith(':')) {
      const parenMatch = firstLine.match(/\(([^)]+)\)/)
      if (parenMatch) subtitle = parenMatch[1]
      textLines = lines.slice(1)
    } else {
      textLines = lines
    }
  } else {
    // ── Case B: CLI fallback format with ─ separators ──────────────────
    const nameLine = lines.find(l => l.includes(':') && !l.match(/^─+$/))
    if (nameLine) {
      const parenMatch = nameLine.match(/\(([^)]+)\)/)
      if (parenMatch) subtitle = parenMatch[1]
    }
    const dashIndices = lines
      .map((l, i) => (l.match(/^─+$/) ? i : -1))
      .filter(i => i >= 0)
    const lastDashIdx = dashIndices[dashIndices.length - 1]
    textLines = lastDashIdx !== undefined ? lines.slice(lastDashIdx + 1) : lines
  }

  let text = textLines.join(' ').trim()

  if (text.startsWith('"') && text.endsWith('"')) {
    text = text.slice(1, -1).trim()
  }

  text = stripNpcPrefix(text)

  if (text.startsWith('"') && text.endsWith('"')) {
    text = text.slice(1, -1).trim()
  }

  return { subtitle, text: text || '…' }
}

/**
 * Render text with *stage directions* as italic.
 * e.g. "*lighting cigar* Hello" → <em>lighting cigar</em> Hello
 */
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

// Intel tier label display
const TIER_LABELS = {
  1: '🕵️ TIER 1 INTEL — Surface',
  2: '🕵️ TIER 2 INTEL — Operational',
  3: '🕵️ TIER 3 INTEL — Deep Cover',
}

/**
 * Single NPC intel dossier — fetches dynamically via /get_intel
 * Caches result in a ref to avoid refetching on re-renders within same turn.
 */
function IntelDossier({ npcKey, sessionId, gs }) {
  const [intelData, setIntelData] = useState(null)
  const [loading, setLoading] = useState(false)
  const fetchedRef = useRef(false)

  // Determine tier from current gs.relations (to check cache validity)
  const relation = gs?.relations?.[npcKey] || 50
  const tier = relation >= 80 ? 3 : relation >= 60 ? 2 : 1

  useEffect(() => {
    // Use cached intel from game_state if available and valid
    const cached = gs?.intel?.[npcKey]
    if (cached) {
      setIntelData(cached)
      fetchedRef.current = true
      return
    }

    // Fetch from backend
    if (fetchedRef.current) return
    fetchedRef.current = true

    setLoading(true)
    api.getIntel(sessionId, npcKey)
      .then(res => {
        setIntelData(res)
      })
      .catch(err => {
        console.warn(`getIntel ${npcKey} failed:`, err.message)
        // Graceful fallback — show nothing
      })
      .finally(() => {
        setLoading(false)
      })
  }, [npcKey, sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <div className="intel-dossier">
        <span className="intel-dossier-label">🕵️ FETCHING INTEL…</span>
      </div>
    )
  }

  if (!intelData) return null

  const tierLabel = TIER_LABELS[intelData.tier || tier] || TIER_LABELS[1]

  return (
    <div className="intel-dossier">
      <span className="intel-dossier-label">{tierLabel}</span>
      {intelData.text}
    </div>
  )
}

/**
 * Props:
 *   dialogue        : array of 4 raw NPC strings
 *   onNegotiate     : (npcKey) => void — optional, if provided shows Negotiate buttons
 *   negotiatingNpc  : string | null — which NPC panel is currently open
 *   intelActive     : bool — true when Intelligence Apparatus upgrade is purchased
 *   sessionId       : string — needed for dynamic intel fetch
 *   gs              : game_state object — needed for relation tier + intel cache
 */
export default function DialoguePanel({
  dialogue,
  onNegotiate,
  negotiatingNpc,
  intelActive = false,
  sessionId,
  gs,
}) {
  if (!dialogue || dialogue.length === 0) return null

  return (
    <div className="panel dialogue-panel">
      <div className="panel-header">
        Diplomatic Communiqués
        {intelActive && (
          <span className="intel-active-badge">🕵️ INTEL ACTIVE</span>
        )}
      </div>
      {NPC_ORDER.map(({ key, label, flag }, i) => {
        const { subtitle, text } = parseNpcString(dialogue[i])
        const isNegotiating = negotiatingNpc === key
        return (
          <div key={key} className="npc-row">
            <div className="npc-row-header">
              <span className={`npc-name ${key}`}>
                {flag} {label}
                {subtitle && (
                  <span style={{ fontWeight: 400, opacity: 0.65, marginLeft: '0.4rem', fontSize: '0.65rem' }}>
                    — {subtitle}
                  </span>
                )}
              </span>
              {onNegotiate && (
                <button
                  className={`negotiate-btn ${isNegotiating ? 'negotiate-btn-active' : ''}`}
                  onClick={() => onNegotiate(isNegotiating ? null : key)}
                  title="Open private negotiation channel"
                >
                  {isNegotiating ? 'Close ✕' : 'Negotiate →'}
                </button>
              )}
            </div>
            <span className="npc-text">{renderWithStageDirections(text)}</span>
            {/* FEATURE 4: Dynamic intelligence apparatus dossier */}
            {intelActive && sessionId && gs && (
              <IntelDossier
                key={`intel-${key}-${gs?.current_turn}`}
                npcKey={key}
                sessionId={sessionId}
                gs={gs}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
