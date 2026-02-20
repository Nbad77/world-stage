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
 */

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
  // Line 0: "EMOJI Name (Subtitle):"
  // Line 1+: dialogue text
  const hasDashes = lines.some(l => l.match(/^─+$/))

  let subtitle = ''
  let textLines = []

  if (!hasDashes && lines.length >= 1) {
    // First line is the name line if it ends with ":"
    const firstLine = lines[0]
    if (firstLine.endsWith(':')) {
      const parenMatch = firstLine.match(/\(([^)]+)\)/)
      if (parenMatch) subtitle = parenMatch[1]
      textLines = lines.slice(1)
    } else {
      // No name line detected — whole thing is text
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

  // Join text lines and clean up
  let text = textLines.join(' ').trim()

  // Strip surrounding quotes
  if (text.startsWith('"') && text.endsWith('"')) {
    text = text.slice(1, -1).trim()
  }

  // Strip any lingering NPC name prefix (e.g. "SADAM: " or "JI-WON: ")
  text = stripNpcPrefix(text)

  // Final quote strip in case prefix removal exposed them
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

/**
 * Props:
 *   dialogue        : array of 4 raw NPC strings
 *   onNegotiate     : (npcKey) => void — optional, if provided shows Negotiate buttons
 *   negotiatingNpc  : string | null — which NPC panel is currently open
 */
export default function DialoguePanel({ dialogue, onNegotiate, negotiatingNpc }) {
  if (!dialogue || dialogue.length === 0) return null

  return (
    <div className="panel dialogue-panel">
      <div className="panel-header">Diplomatic Communiqués</div>
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
          </div>
        )
      })}
    </div>
  )
}
