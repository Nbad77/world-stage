/**
 * Test Panel — only renders for test accounts (is_test=True in Clerk public metadata).
 * Collapsible panel, bottom right corner, red border.
 * Buttons: Reset Game, Load Snapshot (dropdown), Open Cheat Panel.
 */
import { useState, useEffect } from 'react'
import { useUser } from '@clerk/clerk-react'
import { api } from '../api'

export default function TestPanel({ sessionId, gs, onGsUpdate, onOpenCheatPanel, onSnapshotLoad }) {
  const { user } = useUser()
  const [collapsed, setCollapsed] = useState(true)
  const [snapshots, setSnapshots] = useState([])
  const [selectedSnapshot, setSelectedSnapshot] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)

  // Fetch snapshots on mount — all hooks must be called before any early return
  useEffect(() => {
    api.testListSnapshots()
      .then(data => setSnapshots(data.snapshots || []))
      .catch(e => console.warn('[TEST] Failed to load snapshots:', e.message))
  }, [])

  // Render for test accounts, ?cheat=true URL param, or dev_mode localStorage
  const searchParams = new URLSearchParams(window.location.search)
  const showDevPanel =
    user?.publicMetadata?.is_test === true ||
    searchParams.get('cheat') === 'true' ||
    localStorage.getItem('dev_mode') === 'true'
  if (!showDevPanel) return null
  console.log('[dev] TestPanel rendered via auth gate bypass')

  console.log('[TEST] Test panel rendered for test account')

  async function handleReset() {
    setLoading(true)
    setMessage(null)
    try {
      const res = await api.testReset()
      setMessage(`Reset complete — ${res.deleted} game(s) deleted`)
    } catch (e) {
      setMessage(`Reset failed: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function handleLoadSnapshot() {
    if (!selectedSnapshot) return
    setLoading(true)
    setMessage(null)
    try {
      const snapRes = await api.testGetSnapshot(selectedSnapshot)
      const setRes = await api.testSetState(snapRes.state_data)
      console.log('[TEST] Snapshot game_id returned:', setRes.game_id)
      setMessage(`Loaded snapshot: ${selectedSnapshot}`)
      // Navigate into game with the injected state
      if (onSnapshotLoad && setRes.game_id) {
        onSnapshotLoad(setRes.game_id)
      }
    } catch (e) {
      setMessage(`Snapshot load failed: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        style={{
          position: 'fixed',
          bottom: '1rem',
          right: '1rem',
          zIndex: 9999,
          background: '#1a0a0a',
          color: '#ff4444',
          border: '2px solid #ff4444',
          borderRadius: '6px',
          padding: '0.4rem 0.8rem',
          cursor: 'pointer',
          fontFamily: 'monospace',
          fontSize: '0.75rem',
          fontWeight: 'bold',
        }}
      >
        TEST
      </button>
    )
  }

  return (
    <div style={{
      position: 'fixed',
      bottom: '1rem',
      right: '1rem',
      zIndex: 9999,
      background: '#1a0a0a',
      border: '2px solid #ff4444',
      borderRadius: '8px',
      padding: '1rem',
      minWidth: '260px',
      maxWidth: '320px',
      fontFamily: 'monospace',
      fontSize: '0.8rem',
      color: '#e0e0e0',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '0.75rem',
        borderBottom: '1px solid #ff4444',
        paddingBottom: '0.5rem',
      }}>
        <span style={{ color: '#ff4444', fontWeight: 'bold', fontSize: '0.85rem' }}>
          TEST PANEL
        </span>
        <button
          onClick={() => setCollapsed(true)}
          style={{
            background: 'none',
            border: 'none',
            color: '#ff4444',
            cursor: 'pointer',
            fontSize: '1rem',
            fontWeight: 'bold',
          }}
        >
          X
        </button>
      </div>

      {/* Reset Button */}
      <button
        onClick={handleReset}
        disabled={loading}
        style={{
          width: '100%',
          padding: '0.4rem',
          marginBottom: '0.5rem',
          background: '#2a0a0a',
          color: '#ff6666',
          border: '1px solid #ff4444',
          borderRadius: '4px',
          cursor: loading ? 'not-allowed' : 'pointer',
          fontFamily: 'monospace',
          fontSize: '0.75rem',
        }}
      >
        {loading ? 'Working...' : 'Reset Game'}
      </button>

      {/* Snapshot Dropdown + Load */}
      <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.5rem' }}>
        <select
          value={selectedSnapshot}
          onChange={e => setSelectedSnapshot(e.target.value)}
          style={{
            flex: 1,
            padding: '0.3rem',
            background: '#0a0a0a',
            color: '#e0e0e0',
            border: '1px solid #444',
            borderRadius: '4px',
            fontFamily: 'monospace',
            fontSize: '0.7rem',
          }}
        >
          <option value="">-- Select Snapshot --</option>
          {snapshots.map(s => (
            <option key={s.name} value={s.name}>
              {s.name} (T{s.turn})
            </option>
          ))}
        </select>
        <button
          onClick={handleLoadSnapshot}
          disabled={loading || !selectedSnapshot}
          style={{
            padding: '0.3rem 0.6rem',
            background: '#2a0a0a',
            color: '#ff6666',
            border: '1px solid #ff4444',
            borderRadius: '4px',
            cursor: (loading || !selectedSnapshot) ? 'not-allowed' : 'pointer',
            fontFamily: 'monospace',
            fontSize: '0.7rem',
            whiteSpace: 'nowrap',
          }}
        >
          Load
        </button>
      </div>

      {/* Open Cheat Panel */}
      <button
        onClick={onOpenCheatPanel}
        style={{
          width: '100%',
          padding: '0.4rem',
          marginBottom: '0.5rem',
          background: '#2a0a0a',
          color: '#ffaa44',
          border: '1px solid #ffaa44',
          borderRadius: '4px',
          cursor: 'pointer',
          fontFamily: 'monospace',
          fontSize: '0.75rem',
        }}
      >
        Open Cheat Panel
      </button>

      {/* Trigger Summit */}
      <button
        onClick={async () => {
          if (!sessionId) { setMessage('No active session'); return }
          setLoading(true)
          setMessage(null)
          try {
            const res = await api.debugSetState(sessionId, { summit_due: true })
            if (res.game_state) onGsUpdate(res.game_state)
            setMessage('Summit triggered')
          } catch (e) {
            setMessage(`Summit trigger failed: ${e.message}`)
          } finally {
            setLoading(false)
          }
        }}
        disabled={loading || !sessionId}
        style={{
          width: '100%',
          padding: '0.4rem',
          marginBottom: '0.5rem',
          background: '#2a0a0a',
          color: '#44aaff',
          border: '1px solid #44aaff',
          borderRadius: '4px',
          cursor: loading ? 'not-allowed' : 'pointer',
          fontFamily: 'monospace',
          fontSize: '0.75rem',
        }}
      >
        Trigger Summit
      </button>

      {/* Status message */}
      {message && (
        <div style={{
          padding: '0.3rem',
          background: '#0a0a0a',
          border: '1px solid #444',
          borderRadius: '4px',
          fontSize: '0.7rem',
          color: '#aaa',
          wordBreak: 'break-word',
        }}>
          {message}
        </div>
      )}
    </div>
  )
}
