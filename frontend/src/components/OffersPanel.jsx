/**
 * Offers panel — list of A-G buttons the player can click.
 *
 * Props:
 *   offers        : array of offer objects from backend
 *   onChoice      : (letter) => void
 *   disabled      : bool
 *   counterOffers : { [letter]: counterOffer } — negotiated override offers keyed by letter
 */
export default function OffersPanel({ offers, onChoice, disabled, counterOffers = {}, summitBlocked }) {
  if (!offers || offers.length === 0) return null

  return (
    <div className="panel offers-panel">
      <div className="panel-header">Your Move</div>
      {summitBlocked && (
        <div className="summit-blocked-notice">
          🌐 Address the UN Summit before making your move
        </div>
      )}
      {offers.map((offer) => {
        const isEscape   = offer.type === 'escape'
        const isInject   = offer.type === 'inject_funds'
        const isNothing  = offer.type === 'do_nothing'
        const isBrigades = offer.type === 'deploy_brigades'
        const counter    = counterOffers[offer.letter]

        const extraClass = isEscape   ? 'escape-btn'
                         : isInject   ? 'inject-btn'
                         : isNothing  ? 'nothing-btn'
                         : isBrigades ? 'brigades-btn'
                         : counter    ? 'counter-btn'
                         : ''

        return (
          <button
            key={offer.letter}
            className={`offer-btn ${extraClass}`}
            onClick={() => onChoice(offer.letter)}
            disabled={disabled}
          >
            <span className="offer-letter">{offer.letter})</span>
            <span className="offer-text">
              {counter ? (
                <>
                  <span className="counter-badge">⚡ NEGOTIATED</span>
                  {' '}{counter.text}
                </>
              ) : offer.text}
              {/* Session 3 Addendum 2: Consequence warning flag (FIX G: show for counters too) */}
              {(counter ? counter.relation_warning : offer.relation_warning) && (
                <span className="offer-warning">{counter ? counter.relation_warning : offer.relation_warning}</span>
              )}
            </span>
          </button>
        )
      })}
    </div>
  )
}
