/**
 * Title / splash screen shown before the game starts.
 */
export default function TitleScreen({ onStart, loading }) {
  return (
    <div className="title-screen">
      <div>
        <h1>The World Stage</h1>
        <p className="title-subtitle">A Geopolitical Simulation</p>
      </div>

      <p className="title-flavour">
        You are the newly installed leader of <strong>Europa</strong> —
        a small nation caught between superpowers. Manage your budget,
        keep the people appeased, and navigate the demands of four
        ruthless diplomatic actors. You have <strong>10 turns</strong>.
        Choose wisely.
      </p>

      <div style={{ fontFamily: 'var(--mono)', fontSize: '0.78rem', color: 'var(--muted)', lineHeight: 1.8 }}>
        <div>🇺🇸 Bill Washington — USA</div>
        <div>🛢️ Sadam — Arabia</div>
        <div>🇪🇺 Marsha — European Union</div>
        <div>💀 Ji-won Ryang — DPRG</div>
      </div>

      <button
        className="btn-primary"
        onClick={onStart}
        disabled={loading}
      >
        {loading ? 'Starting…' : 'Begin Tenure'}
      </button>

      <p style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
        Sessions last 24 hours
      </p>
    </div>
  )
}
