import { useState, useEffect } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { api, setTokenGetter } from './api'
import TitleScreen from './components/TitleScreen'
import GameScreen from './components/GameScreen'

const SESSION_KEY = 'worldstage_session_id'
const CLERK_AVAILABLE = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

/**
 * ClerkTokenSync — renders only when Clerk is available (inside ClerkProvider).
 * Registers Clerk's getToken with the API module so requests include JWT.
 * Separated so useAuth() hook is never called outside ClerkProvider.
 */
function ClerkTokenSync() {
  const { getToken } = useAuth()
  useEffect(() => {
    setTokenGetter(getToken)
  }, [getToken])
  return null
}

/**
 * Root app — manages which screen is visible.
 * VIEW: 'title' | 'game'
 *
 * Auth: When Clerk is configured, JWT is attached to all API requests.
 * When Clerk is not available, the app runs in guest mode — fully playable
 * but game state is not linked to a user account.
 */
export default function App() {
  const [view, setView]           = useState('title')
  const [sessionId, setSessionId] = useState(null)
  const [initialData, setInitialData] = useState(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)
  const [gameKey, setGameKey]     = useState(0)   // increments to force GameScreen remount

  // hasResumable: null = checking backend, false = no session, true = session ready
  const [hasResumable, setHasResumable] = useState(
    localStorage.getItem(SESSION_KEY) ? null : false
  )
  const [resumeData, setResumeData]     = useState(null)   // data from GET /game/{id}

  // ── On mount: probe localStorage for an existing active session ──────────
  useEffect(() => {
    const saved = localStorage.getItem(SESSION_KEY)
    if (!saved) {
      console.log('[RESUME] No saved session in localStorage')
      setHasResumable(false)
      return
    }
    console.log('[RESUME] Found saved session:', saved.slice(0, 8) + '…')
    // Attempt to fetch the saved session from backend
    api.getGame(saved)
      .then(data => {
        console.log('[RESUME] Backend returned status:', data.status)
        if (data.status === 'active') {
          setResumeData(data)
          setHasResumable(true)
        } else {
          // Game ended — clear stale entry
          localStorage.removeItem(SESSION_KEY)
          setHasResumable(false)
        }
      })
      .catch((err) => {
        // fixes_21 Fix F: Only clear localStorage on definitive 404 (session gone).
        // Transient errors (500, network timeout, cold start) should NOT destroy
        // the saved session reference — next refresh can retry.
        const is404 = /404|not found|expired/i.test(err.message)
        if (is404) {
          console.log('[RESUME] Session not found/expired — clearing localStorage')
          localStorage.removeItem(SESSION_KEY)
        } else {
          console.warn('[RESUME] Transient error checking session (kept for retry):', err.message)
        }
        setHasResumable(false)
      })
  }, [])

  // ── New game ─────────────────────────────────────────────────────────────
  async function handleStart() {
    setError(null)
    setLoading(true)
    // Clear any existing saved session before starting fresh
    localStorage.removeItem(SESSION_KEY)
    try {
      const data = await api.newGame()
      localStorage.setItem(SESSION_KEY, data.session_id)
      setSessionId(data.session_id)
      setInitialData(data)
      setHasResumable(false)
      setResumeData(null)
      setView('game')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── Resume existing session ───────────────────────────────────────────────
  async function handleResume() {
    if (!resumeData) return
    setError(null)
    setLoading(true)
    try {
      // Fetch fresh dialogue for the current turn so the panel is populated
      const saved = localStorage.getItem(SESSION_KEY)
      const freshData = await api.getGame(saved)
      setSessionId(saved)
      setInitialData(freshData)
      setView('game')
    } catch (e) {
      // Session vanished between check and resume — start fresh
      localStorage.removeItem(SESSION_KEY)
      setHasResumable(false)
      setResumeData(null)
      setError('Session expired — please start a new game.')
    } finally {
      setLoading(false)
    }
  }

  // ── Snapshot loaded (from TestPanel) — navigate into game with new state ──
  async function handleSnapshotLoad(gameId) {
    console.log('[TEST] handleSnapshotLoad called with gameId:', gameId)
    console.log('[TEST] current sessionId:', sessionId)
    try {
      const data = await api.getGame(gameId)
      console.log('[TEST] Game state fetched for snapshot, turn:', data?.game_state?.current_turn)
      console.log('[TEST] Snapshot fully loaded: turn=', data?.game_state?.current_turn)
      localStorage.setItem(SESSION_KEY, gameId)
      setSessionId(gameId)
      setInitialData(data)
      setGameKey(k => k + 1)  // force GameScreen remount even if sessionId unchanged
      setView('game')
    } catch (e) {
      console.error('[TEST] handleSnapshotLoad error:', e.message)
      setError(`Snapshot load failed: ${e.message}`)
    }
  }

  // ── Restart / end game ────────────────────────────────────────────────────
  function handleRestart() {
    // Called from EndingScreen "Start New Game" button — clear saved session
    localStorage.removeItem(SESSION_KEY)
    setView('title')
    setSessionId(null)
    setInitialData(null)
    setError(null)
    setHasResumable(false)
    setResumeData(null)
  }

  // ── Build content based on view ─────────────────────────────────────────
  let content
  if (view === 'game' && sessionId && initialData) {
    content = (
      <GameScreen
        key={`${sessionId}-${gameKey}`}
        sessionId={sessionId}
        initialData={initialData}
        onGameEnd={() => {}}
        onRestart={handleRestart}
        onSnapshotLoad={handleSnapshotLoad}
      />
    )
  } else {
    content = (
      <div className="app-container">
        <TitleScreen
          onStart={handleStart}
          onResume={handleResume}
          hasResumable={hasResumable}
          resumeData={resumeData}
          loading={loading}
        />
        {error && (
          <div className="error-banner" style={{ margin: '0 1rem 1rem' }}>
            {error} — Is the API server running?
          </div>
        )}
      </div>
    )
  }

  return (
    <>
      {CLERK_AVAILABLE && <ClerkTokenSync />}
      {content}
    </>
  )
}
