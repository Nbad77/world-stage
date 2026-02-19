/**
 * End-of-turn effects panel (oil adjustments, sanctions ticks, etc.)
 */
export default function EotPanel({ messages }) {
  if (!messages || messages.length === 0) return null

  return (
    <div className="eot-panel">
      <div className="panel-header">End of Turn Effects</div>
      <ul className="msg-list">
        {messages.map((msg, i) => (
          <li key={i}>{msg}</li>
        ))}
      </ul>
    </div>
  )
}
