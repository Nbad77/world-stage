/**
 * Shows consequence messages after a diplomatic choice,
 * plus optional blackmail result.
 */
export default function ConsequencesPanel({ consequences, blackmailResult }) {
  const hasConsequences = consequences && consequences.length > 0
  const hasBlackmail = blackmailResult && blackmailResult.messages && blackmailResult.messages.length > 0

  if (!hasConsequences && !hasBlackmail) return null

  return (
    <div className="panel">
      <div className="panel-header">Consequences</div>

      {hasConsequences && (
        <ul className="msg-list">
          {consequences.map((msg, i) => (
            <li key={i}>{msg}</li>
          ))}
        </ul>
      )}

      {hasBlackmail && (
        <>
          <div className="msg-section-title" style={{ color: 'var(--danger)' }}>
            🔴 CIA BLACKMAIL
          </div>
          <ul className="msg-list" style={{ color: 'var(--danger)' }}>
            {blackmailResult.messages.map((msg, i) => (
              <li key={i}>{msg}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
