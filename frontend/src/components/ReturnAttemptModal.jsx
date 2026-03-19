/**
 * ReturnAttemptModal — 9A: Confirmation + result modal for return attempts.
 * Shows probability estimate pre-attempt, then success/failure narrative.
 */
import { useState, useEffect } from 'react'

export default function ReturnAttemptModal({ gs, onAttempt, onClose, loading }) {
  const [phase, setPhase] = useState('confirm') // 'confirm' | 'result'
  const [result, setResult] = useState(null) // response from API
  const [submitting, setSubmitting] = useState(false)

  const progress = gs.return_progress || 0
  const threshold = gs.return_threshold || 100
  const attempts = gs.return_attempts || 0
  const attemptsLeft = 3 - attempts

  // Client-side probability estimate (approximation of backend formula)
  const basePct = Math.min(progress / Math.max(threshold, 1), 0.90)
  // NPC bonus: best tier * 2%
  const npcTiers = gs.npc_assistance_tiers || {}
  const bestTier = Math.max(0, ...Object.values(npcTiers))
  const npcBonus = bestTier * 0.02
  // Faction bonus: 3% per committed faction
  const factionContacts = gs.faction_contacts || {}
  const committedCount = Object.values(factionContacts).filter(f => f?.committed).length
  const factionBonus = committedCount * 0.03
  // Detection penalty: 3% per event
  const detectionPenalty = (gs.detection_events || []).length * 0.03
  // Attempt penalty: 5% per prior attempt
  const attemptPenalty = attempts * 0.05

  const estProb = Math.max(0.05, Math.min(0.90, basePct + npcBonus + factionBonus - detectionPenalty - attemptPenalty))
  const estPctDisplay = Math.round(estProb * 100)

  // Color for probability display
  const probColor = estProb >= 0.60 ? 'var(--success)' : estProb >= 0.35 ? 'var(--warning)' : 'var(--danger)'

  const handleConfirm = async () => {
    setSubmitting(true)
    try {
      const res = await onAttempt()
      console.log('[FIXB] attempt-return response keys:', Object.keys(res))
      setResult(res)
      setPhase('result')
    } catch (e) {
      // Error handled by parent — close modal
      onClose()
    } finally {
      setSubmitting(false)
    }
  }

  // FIX B: Log narrative display
  useEffect(() => {
    if (phase === 'result' && result) {
      console.log(`[FIXB] narrative length=${(result.narrative || '').length} showing=${phase === 'result'}`)
    }
  }, [phase, result])

  return (
    <div className="exile-modal-overlay" onClick={() => { if (phase !== 'result' || !result?.success) onClose() }}>
      <div className="exile-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '440px' }}>

        {phase === 'confirm' && (
          <>
            <div className="exile-modal-title">ATTEMPT RETURN</div>

            <div style={{ fontSize: '0.76rem', color: 'var(--muted)', marginBottom: '0.5rem' }}>
              You are about to attempt a return to Europa. This action cannot be undone.
            </div>

            {/* Probability breakdown */}
            <div style={{
              background: 'var(--bg)', borderRadius: '6px', padding: '0.5rem',
              marginBottom: '0.5rem', border: '1px solid var(--border)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <span style={{ fontSize: '0.74rem', fontWeight: 600 }}>Estimated Probability</span>
                <span style={{ fontSize: '1.1rem', fontWeight: 700, color: probColor }}>{estPctDisplay}%</span>
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--muted)', display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Base (progress/threshold)</span>
                  <span>{Math.round(basePct * 100)}%</span>
                </div>
                {npcBonus > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--success)' }}>
                    <span>NPC backing (tier {bestTier})</span>
                    <span>+{Math.round(npcBonus * 100)}%</span>
                  </div>
                )}
                {factionBonus > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--success)' }}>
                    <span>Faction contacts ({committedCount})</span>
                    <span>+{Math.round(factionBonus * 100)}%</span>
                  </div>
                )}
                {detectionPenalty > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--danger)' }}>
                    <span>Detection events ({(gs.detection_events || []).length})</span>
                    <span>-{Math.round(detectionPenalty * 100)}%</span>
                  </div>
                )}
                {attemptPenalty > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--danger)' }}>
                    <span>Prior attempts ({attempts})</span>
                    <span>-{Math.round(attemptPenalty * 100)}%</span>
                  </div>
                )}
              </div>
            </div>

            {/* Attempt counter */}
            <div style={{ fontSize: '0.74rem', color: 'var(--muted)', marginBottom: '0.4rem' }}>
              This will be attempt <strong style={{ color: 'var(--text)' }}>{attempts + 1} of 3</strong>.
              {attemptsLeft <= 1 && (
                <span style={{ color: 'var(--danger)', marginLeft: '0.3rem', fontWeight: 600 }}>
                  {attemptsLeft === 1 ? 'This is your last attempt.' : ''}
                </span>
              )}
            </div>

            {/* Failure penalties warning */}
            <div style={{
              fontSize: '0.7rem', color: 'var(--warning)', background: 'rgba(229,163,74,0.08)',
              padding: '0.4rem', borderRadius: '4px', marginBottom: '0.5rem',
              border: '1px solid rgba(229,163,74,0.15)'
            }}>
              <div style={{ fontWeight: 600, marginBottom: '0.2rem' }}>{'\u26A0'} If this attempt fails:</div>
              <div>{'\u2022'} Progress reduced by {20 + (attempts + 1) * 5} points</div>
              <div>{'\u2022'} All NPC relations drop by 5</div>
              <div>{'\u2022'} Return threshold increases by 10</div>
              <div>{'\u2022'} Successor hostility increases</div>
            </div>

            <div className="exile-modal-actions">
              <button
                className="exile-btn exile-btn-accept"
                disabled={submitting || loading}
                onClick={handleConfirm}
                style={{ flex: 1 }}
              >
                {submitting ? 'Attempting...' : 'ATTEMPT RETURN'}
              </button>
              <button
                className="exile-btn exile-btn-cancel"
                onClick={onClose}
                disabled={submitting}
                style={{ flex: 1 }}
              >
                Cancel
              </button>
            </div>
          </>
        )}

        {phase === 'result' && result && (
          <>
            <div className="exile-modal-title" style={{
              color: result.success ? 'var(--success)' : 'var(--danger)'
            }}>
              {result.success ? 'RETURN SUCCESSFUL' : 'ATTEMPT FAILED'}
            </div>

            {/* Probability that was rolled */}
            <div style={{
              fontSize: '0.72rem', color: 'var(--muted)', marginBottom: '0.4rem',
              textAlign: 'center'
            }}>
              Probability was {Math.round((result.probability || 0) * 100)}%
              {' '}{'\u2014'}{' '}Attempt {result.attempt_number} of 3
            </div>

            {/* Narrative text */}
            <div style={{
              fontSize: '0.82rem', lineHeight: '1.5', color: 'var(--text)',
              padding: '0.6rem', background: 'var(--bg)', borderRadius: '6px',
              border: `1px solid ${result.success ? 'rgba(76,175,110,0.3)' : 'rgba(229,74,74,0.3)'}`,
              marginBottom: '0.5rem', fontStyle: 'italic'
            }}>
              {result.narrative}
            </div>

            {/* Result summary */}
            {result.success ? (
              <div style={{
                fontSize: '0.74rem', color: 'var(--success)', background: 'rgba(76,175,110,0.08)',
                padding: '0.4rem', borderRadius: '4px', marginBottom: '0.5rem',
                border: '1px solid rgba(76,175,110,0.2)'
              }}>
                <div style={{ fontWeight: 600, marginBottom: '0.2rem' }}>The Restoration begins.</div>
                <div>You have returned to Europa. The shape of your new regime will be determined by the choices ahead.</div>
                {result.backing_npc && (
                  <div style={{ marginTop: '0.2rem', fontSize: '0.7rem', color: 'var(--muted)' }}>
                    Primary backer: {result.backing_npc}
                  </div>
                )}
              </div>
            ) : (
              <div style={{
                fontSize: '0.74rem', color: 'var(--danger)', background: 'rgba(229,74,74,0.08)',
                padding: '0.4rem', borderRadius: '4px', marginBottom: '0.5rem',
                border: '1px solid rgba(229,74,74,0.2)'
              }}>
                <div style={{ fontWeight: 600, marginBottom: '0.2rem' }}>The attempt has failed.</div>
                <div>Progress: {Math.round(result.new_progress || 0)} / {Math.round(result.new_threshold || 100)}</div>
                <div>{3 - (result.attempt_number || 0)} attempts remaining</div>
              </div>
            )}

            <div className="exile-modal-actions">
              <button
                className="exile-btn exile-btn-accept"
                onClick={() => onClose(result.success ? result.game_state : undefined)}
                style={{ width: '100%' }}
              >
                {result.success ? 'Begin Restoration' : 'Continue'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
