/**
 * Offers panel — list of A-G buttons the player can click.
 * onChoice: (letter) => void
 */
export default function OffersPanel({ offers, onChoice, disabled }) {
  if (!offers || offers.length === 0) return null

  return (
    <div className="panel offers-panel">
      <div className="panel-header">Your Move</div>
      {offers.map((offer) => {
        const isEscape = offer.type === 'escape'
        const isInject = offer.type === 'inject_funds'
        const isNothing = offer.type === 'do_nothing'

        const extraClass = isEscape ? 'escape-btn' : isInject ? 'inject-btn' : isNothing ? 'nothing-btn' : ''

        return (
          <button
            key={offer.letter}
            className={`offer-btn ${extraClass}`}
            onClick={() => onChoice(offer.letter)}
            disabled={disabled}
          >
            <span className="offer-letter">{offer.letter})</span>
            <span className="offer-text">{offer.text}</span>
          </button>
        )
      })}
    </div>
  )
}
