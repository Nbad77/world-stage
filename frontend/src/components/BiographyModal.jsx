import { useState, useEffect } from 'react'
import { api } from '../api'
import BiographyCard from './BiographyCard'

const ENDING_LABELS = {
  democratic_transition: 'Democratic Transition',
  state_capture: 'State Capture',
  comfortable_retirement: 'Comfortable Retirement',
  martyrdom: 'Martyrdom',
  permanent_exile: 'Permanent Exile',
  restoration_legacy: 'Restoration',
  voted_out: 'Voted Out',
  unknown: 'End of Tenure',
}

const SECTION_LABELS = {
  rise: 'RISE',
  fall: 'THE FALL',
  exile: 'YEARS IN EXILE',
  restoration: 'THE RETURN',
  consolidation: 'IN POWER',
  exit: 'DEPARTURE',
  legacy: 'LEGACY',
}

export default function BiographyModal({ isOpen, onClose, onPlayAgain, sessionId, isDraft }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [visibleSections, setVisibleSections] = useState([])
  const [showCard, setShowCard] = useState(false)

  useEffect(() => {
    if (!isOpen || !sessionId) return
    setLoading(true)
    setError(null)
    setData(null)
    setVisibleSections([])
    setShowCard(false)

    api.getBiography(sessionId)
      .then(result => {
        console.log('[9B] biography loaded:', Object.keys(result))
        console.log(`[9B] BiographyModal isDraft=${isDraft} sections=${(result.section_order || []).length}`)
        setData(result)
        // Staggered reveal
        const order = result.section_order || []
        order.forEach((key, i) => {
          setTimeout(() => {
            setVisibleSections(prev => [...prev, key])
          }, i * 1500)
        })
      })
      .catch(err => {
        console.error('[9B] biography error:', err)
        setError(err.message)
      })
      .finally(() => setLoading(false))
  }, [isOpen, sessionId])

  if (!isOpen) return null

  const endingType = data?.card_data?.ending_type || 'unknown'
  const endingLabel = ENDING_LABELS[endingType] || 'End of Tenure'
  const regimeProgression = data?.card_data?.regime_progression || []

  return (
    <div className="confirm-overlay" style={{ zIndex: 400 }} onClick={onClose}>
      <div
        className="biography-modal"
        onClick={e => e.stopPropagation()}
        style={{
          maxWidth: '700px',
          width: '90vw',
          maxHeight: '85vh',
          overflowY: 'auto',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '2rem',
          color: 'var(--text)',
          position: 'relative',
        }}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: '0.75rem', right: '1rem',
            background: 'none', border: 'none', color: 'var(--muted)',
            fontSize: '1.2rem', cursor: 'pointer',
          }}
        >
          &#x2715;
        </button>

        {/* Loading */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--muted)', fontStyle: 'italic' }}>
            Compiling the historical record...
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#e57a4a' }}>
            Failed to generate biography: {error}
          </div>
        )}

        {/* Content */}
        {data && !loading && (
          <>
            {/* Draft note */}
            {isDraft && (
              <div style={{
                fontSize: '0.75rem', color: 'var(--muted)', fontStyle: 'italic',
                textAlign: 'center', marginBottom: '1rem', padding: '0.5rem',
                border: '1px dashed var(--border)', borderRadius: '4px',
              }}>
                Draft biography — your story is still being written.
              </div>
            )}

            {/* Header */}
            <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
              <div style={{
                fontSize: '0.7rem', letterSpacing: '0.2em',
                textTransform: 'uppercase', color: 'var(--muted)', marginBottom: '0.3rem',
              }}>
                Political Biography
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                Europa — {endingLabel}
              </div>
            </div>

            {/* Regime timeline */}
            {regimeProgression.length > 0 && (
              <div style={{
                textAlign: 'center', marginBottom: '1.5rem',
                fontSize: '0.68rem', color: 'var(--muted)',
                fontVariant: 'small-caps', letterSpacing: '0.05em',
              }}>
                {regimeProgression.map((entry, i) => (
                  <span key={i}>
                    <span className="regime-pill" style={{
                      display: 'inline-block', padding: '0.15rem 0.5rem',
                      background: 'var(--bg-panel, rgba(255,255,255,0.04))',
                      borderRadius: '10px', color: 'var(--text)',
                      fontSize: '0.68rem', fontVariant: 'small-caps',
                    }}>
                      {entry.label || entry.to || entry.from || 'Unknown'}
                    </span>
                    {i < regimeProgression.length - 1 && ' \u2192 '}
                  </span>
                ))}
              </div>
            )}

            {/* Sections */}
            {(data.section_order || []).map((key) => {
              const section = data.sections?.[key]
              if (!section) return null
              const isVisible = visibleSections.includes(key)
              const isLegacy = key === 'legacy'

              return (
                <div
                  key={key}
                  style={{
                    opacity: isVisible ? 1 : 0,
                    transition: 'opacity 0.8s ease-in',
                    marginBottom: '1.5rem',
                  }}
                >
                  {/* Section divider */}
                  <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '0 0 1rem 0' }} />

                  {/* Section label */}
                  <div style={{
                    fontSize: '0.65rem', letterSpacing: '0.15em',
                    textTransform: 'uppercase', color: 'var(--muted)',
                    marginBottom: '0.6rem',
                  }}>
                    {SECTION_LABELS[key] || key.toUpperCase()}
                  </div>

                  {/* Prose */}
                  <div style={{
                    fontFamily: 'monospace', fontSize: '0.82rem',
                    lineHeight: 1.8, paddingLeft: '1rem',
                    color: 'var(--text)', whiteSpace: 'pre-wrap',
                  }}>
                    {section.text}
                  </div>

                  {/* Legacy epitaph */}
                  {isLegacy && section.epitaph && (
                    <div style={{
                      textAlign: 'center', marginTop: '1.5rem',
                      fontSize: '1.05rem', fontStyle: 'italic',
                      color: 'var(--text)', lineHeight: 1.6,
                    }}>
                      &mdash; {section.epitaph} &mdash;
                    </div>
                  )}
                </div>
              )
            })}

            {/* Footer */}
            <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '1.5rem 0 1rem 0' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button
                className="btn-secondary"
                onClick={() => setShowCard(true)}
                style={{ fontSize: '0.78rem' }}
              >
                SHARE
              </button>
              {onPlayAgain && (
                <button
                  className="btn-primary"
                  onClick={onPlayAgain}
                  style={{ fontSize: '0.78rem' }}
                >
                  PLAY AGAIN
                </button>
              )}
            </div>
          </>
        )}

        {/* Biography Card overlay */}
        {showCard && data?.card_data && (
          <div
            style={{
              position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
              background: 'rgba(0,0,0,0.7)', zIndex: 410,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
            onClick={() => setShowCard(false)}
          >
            <div onClick={e => e.stopPropagation()}>
              <BiographyCard cardData={data.card_data} />
              <div style={{ textAlign: 'center', marginTop: '0.75rem' }}>
                <button
                  className="btn-secondary"
                  onClick={() => setShowCard(false)}
                  style={{ fontSize: '0.75rem' }}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
