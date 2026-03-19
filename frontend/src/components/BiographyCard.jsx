import { useRef, useCallback } from 'react'
import html2canvas from 'html2canvas'

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

const ENDING_COLORS = {
  democratic_transition: '#4a9eff',
  state_capture: '#e54a4a',
  comfortable_retirement: '#6bc95b',
  martyrdom: '#e57a4a',
  permanent_exile: '#9a6bc9',
  restoration_legacy: '#e5c44a',
  voted_out: '#7a8899',
  unknown: '#7a8899',
}

function StatBar({ label, value, max = 100, color = '#4a9eff' }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  return (
    <div style={{ marginBottom: '0.4rem' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        fontSize: '0.6rem', color: '#8899aa', marginBottom: '0.15rem',
        letterSpacing: '0.08em', textTransform: 'uppercase',
      }}>
        <span>{label}</span>
        <span>{value}</span>
      </div>
      <div style={{
        height: '4px', background: '#1a2433', borderRadius: '2px',
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: color, borderRadius: '2px',
          transition: 'width 0.6s ease-out',
        }} />
      </div>
    </div>
  )
}

export default function BiographyCard({ cardData }) {
  const cardRef = useRef(null)

  const endingType = cardData?.ending_type || 'unknown'
  const endingLabel = ENDING_LABELS[endingType] || 'End of Tenure'
  const endingColor = ENDING_COLORS[endingType] || '#7a8899'
  const epitaph = cardData?.epitaph || ''
  const totalTurns = cardData?.total_turns || 0
  const erasPlayed = cardData?.eras_played || 0
  const alignment = cardData?.alignment_label || 'Pragmatist'
  const regimeProgression = cardData?.regime_progression || []
  const exileOccurred = cardData?.exile_occurred || false
  const statesmanScore = cardData?.statesman_score ?? 50
  const reformerScore = cardData?.reformer_score ?? 50

  console.log('[9B] BiographyCard render:', { endingType, totalTurns, alignment, exileOccurred })

  const handleDownload = useCallback(() => {
    if (!cardRef.current) return
    console.log('[9B] BiographyCard downloading...')
    html2canvas(cardRef.current, {
      backgroundColor: '#0d1117',
      scale: 2,
      useCORS: true,
      logging: false,
    }).then(canvas => {
      const link = document.createElement('a')
      link.download = `world-stage-${endingType}.png`
      link.href = canvas.toDataURL('image/png')
      link.click()
      console.log('[9B] BiographyCard download triggered')
    }).catch(err => {
      console.error('[9B] BiographyCard download error:', err)
    })
  }, [endingType])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      {/* The card itself — fixed 600px for screenshot consistency */}
      <div
        ref={cardRef}
        style={{
          width: '600px',
          background: '#0d1117',
          border: `1px solid ${endingColor}33`,
          borderRadius: '12px',
          padding: '2rem 2.5rem',
          fontFamily: "'Courier New', Courier, monospace",
          color: '#c9d1d9',
          boxSizing: 'border-box',
        }}
      >
        {/* Top brand bar */}
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', marginBottom: '1.5rem',
        }}>
          <div style={{
            fontSize: '0.6rem', letterSpacing: '0.3em',
            textTransform: 'uppercase', color: '#586069',
          }}>
            World Stage
          </div>
          <div style={{
            fontSize: '0.55rem', letterSpacing: '0.15em',
            textTransform: 'uppercase', color: '#586069',
          }}>
            Political Biography
          </div>
        </div>

        {/* Ending type — hero element */}
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div style={{
            fontSize: '1.4rem', fontWeight: 700,
            color: endingColor, letterSpacing: '0.05em',
            marginBottom: '0.3rem',
          }}>
            {endingLabel}
          </div>
          <div style={{
            fontSize: '0.65rem', color: '#586069',
            letterSpacing: '0.1em', textTransform: 'uppercase',
          }}>
            Europa
          </div>
        </div>

        {/* Divider */}
        <hr style={{
          border: 'none', borderTop: `1px solid ${endingColor}33`,
          margin: '0 0 1.2rem 0',
        }} />

        {/* Regime progression */}
        {regimeProgression.length > 0 && (
          <div style={{ marginBottom: '1.2rem' }}>
            <div style={{
              fontSize: '0.55rem', letterSpacing: '0.15em',
              textTransform: 'uppercase', color: '#586069',
              marginBottom: '0.5rem',
            }}>
              Regime Arc
            </div>
            <div style={{
              display: 'flex', flexWrap: 'wrap',
              gap: '0.25rem', alignItems: 'center',
            }}>
              {regimeProgression.map((r, i) => (
                <span key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  {i > 0 && (
                    <span style={{ color: '#586069', fontSize: '0.6rem' }}>{'\u2192'}</span>
                  )}
                  <span style={{
                    fontSize: '0.6rem', padding: '0.15rem 0.5rem',
                    background: '#161b22', borderRadius: '10px',
                    border: '1px solid #21262d', color: '#8b949e',
                    whiteSpace: 'nowrap',
                  }}>
                    {r.to || r.label || r.from || 'Unknown'}
                  </span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Epitaph */}
        {epitaph && (
          <div style={{
            textAlign: 'center', margin: '1.2rem 1rem',
            padding: '1rem',
            borderLeft: `2px solid ${endingColor}66`,
            borderRight: `2px solid ${endingColor}66`,
          }}>
            <div style={{
              fontSize: '0.85rem', fontStyle: 'italic',
              lineHeight: 1.7, color: '#c9d1d9',
            }}>
              &ldquo;{epitaph}&rdquo;
            </div>
          </div>
        )}

        {/* Stats grid */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: '1rem', marginBottom: '1.2rem',
        }}>
          {/* Left column — numbers */}
          <div>
            <div style={{
              fontSize: '0.55rem', letterSpacing: '0.15em',
              textTransform: 'uppercase', color: '#586069',
              marginBottom: '0.6rem',
            }}>
              Record
            </div>
            <div style={{ display: 'flex', gap: '1.5rem' }}>
              <div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#c9d1d9' }}>
                  {totalTurns}
                </div>
                <div style={{ fontSize: '0.55rem', color: '#586069', textTransform: 'uppercase' }}>
                  Days
                </div>
              </div>
              <div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#c9d1d9' }}>
                  {erasPlayed}
                </div>
                <div style={{ fontSize: '0.55rem', color: '#586069', textTransform: 'uppercase' }}>
                  Eras
                </div>
              </div>
            </div>

            {/* Tags */}
            <div style={{ marginTop: '0.8rem', display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
              <span style={{
                fontSize: '0.58rem', padding: '0.15rem 0.5rem',
                background: '#161b22', borderRadius: '10px',
                border: '1px solid #21262d', color: endingColor,
              }}>
                {alignment}
              </span>
              {exileOccurred && (
                <span style={{
                  fontSize: '0.58rem', padding: '0.15rem 0.5rem',
                  background: '#161b22', borderRadius: '10px',
                  border: '1px solid #21262d', color: '#9a6bc9',
                }}>
                  Exiled
                </span>
              )}
            </div>
          </div>

          {/* Right column — score bars */}
          <div>
            <div style={{
              fontSize: '0.55rem', letterSpacing: '0.15em',
              textTransform: 'uppercase', color: '#586069',
              marginBottom: '0.6rem',
            }}>
              Assessment
            </div>
            <StatBar label="Statesman" value={statesmanScore} color="#4a9eff" />
            <StatBar label="Reformer" value={reformerScore} color="#6bc95b" />
          </div>
        </div>

        {/* Bottom bar */}
        <hr style={{
          border: 'none', borderTop: '1px solid #21262d',
          margin: '0 0 0.6rem 0',
        }} />
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          fontSize: '0.5rem', color: '#484f58',
          letterSpacing: '0.1em', textTransform: 'uppercase',
        }}>
          <span>worldstage.game</span>
          <span>{new Date().getFullYear()}</span>
        </div>
      </div>

      {/* Download button — outside the card ref so it's not captured */}
      <button
        onClick={handleDownload}
        className="btn-primary"
        style={{
          marginTop: '1rem',
          fontSize: '0.75rem',
          padding: '0.5rem 1.5rem',
        }}
      >
        DOWNLOAD PNG
      </button>
    </div>
  )
}
