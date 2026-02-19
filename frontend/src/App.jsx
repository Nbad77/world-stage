import { useState } from 'react'
import { api } from './api'
import TitleScreen from './components/TitleScreen'
import GameScreen from './components/GameScreen'

/**
 * Root app — manages which screen is visible.
 * VIEW: 'title' | 'game'
 */
export default function App() {
  const [view, setView] = useState('title')
  const [sessionId, setSessionId] = useState(null)
  const [initialData, setInitialData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleStart() {
    setError(null)
    setLoading(true)
    try {
      const data = await api.newGame()
      setSessionId(data.session_id)
      setInitialData(data)
      setView('game')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleRestart() {
    setView('title')
    setSessionId(null)
    setInitialData(null)
    setError(null)
  }

  if (view === 'game' && sessionId && initialData) {
    return (
      <GameScreen
        sessionId={sessionId}
        initialData={initialData}
        onGameEnd={() => {}}
        onRestart={handleRestart}
      />
    )
  }

  return (
    <div className="app-container">
      <TitleScreen onStart={handleStart} loading={loading} />
      {error && (
        <div className="error-banner" style={{ margin: '0 1rem 1rem' }}>
          ⚠️ {error} — Is the API server running?
        </div>
      )}
    </div>
  )
}
