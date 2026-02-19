/**
 * Intelligence Intercepts — one-shot wealth threshold comments.
 *
 * npc_engine returns strings like:
 *   '🇺🇸 USA (Intelligence): "raw text here"'
 *   '🛢️  SADAM: "raw text here"'
 *
 * We split at the first ": " to get label vs text, strip surrounding quotes,
 * and render *stage directions* as italic.
 */

function parseIntercept(raw) {
  if (!raw) return { label: '', text: '' }

  const colonIdx = raw.indexOf(': ')
  if (colonIdx === -1) return { label: '', text: raw }

  const label = raw.slice(0, colonIdx).trim()
  let text = raw.slice(colonIdx + 2).trim()

  // Strip surrounding quotes
  if (text.startsWith('"') && text.endsWith('"')) {
    text = text.slice(1, -1).trim()
  }

  return { label, text }
}

function renderWithStageDirections(text) {
  const parts = text.split(/(\*[^*]+\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('*') && part.endsWith('*')) {
      return (
        <em key={i} style={{ fontStyle: 'italic', opacity: 0.8 }}>
          {part.slice(1, -1)}
        </em>
      )
    }
    return <span key={i}>{part}</span>
  })
}

export default function InterceptPanel({ intercepts }) {
  if (!intercepts || intercepts.length === 0) return null

  return (
    <div className="intercept-panel">
      <div className="intercept-header">🔍 Intelligence Intercepts — CLASSIFIED</div>
      {intercepts.map((raw, i) => {
        const { label, text } = parseIntercept(raw)
        return (
          <div key={i} className="intercept-item">
            {label && (
              <span style={{ opacity: 0.55, fontSize: '0.7rem', display: 'block', marginBottom: '0.1rem' }}>
                {label}
              </span>
            )}
            {renderWithStageDirections(text)}
          </div>
        )
      })}
    </div>
  )
}
