/**
 * MobileEotScreen — full-screen EOT takeover for narrow viewports.
 * Reads the same eotData shape produced by the EOT pipeline (see EotPanel.jsx)
 * but lays it out vertically with a fixed bottom CONTINUE button.
 * Falls back to legacy `eotMessages` if structured eotData is unavailable.
 */
import { useEffect, useRef } from 'react'

function fmtB(n) {
  if (n == null || Number.isNaN(n)) return '—'
  const sign = n > 0 ? '+' : ''
  return `${sign}$${Number(n).toFixed(1)}B`
}
function deltaCls(n) {
  if (n == null) return ''
  if (n > 0) return 'delta-up'
  if (n < 0) return 'delta-down'
  return ''
}
function arrow(n) {
  if (n == null) return ''
  if (n > 0) return '↑'
  if (n < 0) return '↓'
  return '—'
}

export default function MobileEotScreen({ gs, eotData, eotMessages, onContinue, ending }) {
  const scrollRef = useRef(null)
  const refs = {
    treasury: useRef(null),
    state:    useRef(null),
    relations: useRef(null),
    events:   useRef(null),
  }

  useEffect(() => {
    console.log('[MOBILE_EOT] rendered, eot_data=', !!eotData)
  }, [eotData])

  function jumpTo(key) {
    const el = refs[key]?.current
    if (el && scrollRef.current) {
      scrollRef.current.scrollTo({ top: el.offsetTop - 8, behavior: 'smooth' })
    }
  }

  const era = gs?.current_era ?? 1
  const day = gs?.current_day ?? gs?.current_turn ?? 1

  const treasury = eotData?.treasury || {}
  const state = eotData?.state || {}
  const relations = eotData?.relations || []
  const worldEvents = eotData?.world_events || []
  const declEffects = eotData?.declaration_effects || {}

  const netBudget = treasury?.net
  const installments = gs?.active_installments || []

  return (
    <div className="mobile-eot">
      <header className="mobile-eot-header">
        <div className="mobile-eot-title">END OF TURN</div>
        <div className="mobile-eot-subtitle">ERA {era} · DAY {day}</div>
      </header>

      <div className="mobile-eot-pills">
        <button className="mobile-eot-pill" onClick={() => jumpTo('treasury')}>Treasury</button>
        <button className="mobile-eot-pill" onClick={() => jumpTo('state')}>State</button>
        <button className="mobile-eot-pill" onClick={() => jumpTo('relations')}>Relations</button>
        <button className="mobile-eot-pill" onClick={() => jumpTo('events')}>World Events</button>
      </div>

      <div className="mobile-eot-body" ref={scrollRef}>
        {/* TREASURY */}
        <section className="mobile-eot-section" ref={refs.treasury}>
          <div className="mobile-eot-section-title">Treasury</div>
          {netBudget != null && (
            <div className="mobile-eot-row">
              <span className="label">Net change</span>
              <span className={`value ${deltaCls(netBudget)}`}>{fmtB(netBudget)}</span>
            </div>
          )}
          <div className="mobile-eot-row">
            <span className="label">Treasury balance</span>
            <span className="value">${(gs?.budget ?? 0).toFixed(1)}B</span>
          </div>
          {treasury?.income?.tax_revenue != null && (
            <div className="mobile-eot-row">
              <span className="label">Tax revenue</span>
              <span className={`value ${deltaCls(treasury.income.tax_revenue)}`}>{fmtB(treasury.income.tax_revenue)}</span>
            </div>
          )}
          {treasury?.income?.oil_modifier != null && (
            <div className="mobile-eot-row">
              <span className="label">Oil modifier</span>
              <span className={`value ${deltaCls(treasury.income.oil_modifier)}`}>{fmtB(treasury.income.oil_modifier)}</span>
            </div>
          )}
          {treasury?.costs?.commitments != null && (
            <div className="mobile-eot-row">
              <span className="label">Commitments</span>
              <span className={`value ${deltaCls(treasury.costs.commitments)}`}>{fmtB(treasury.costs.commitments)}</span>
            </div>
          )}
          {treasury?.costs?.oil_imports != null && (
            <div className="mobile-eot-row">
              <span className="label">Oil imports</span>
              <span className={`value ${deltaCls(treasury.costs.oil_imports)}`}>{fmtB(treasury.costs.oil_imports)}</span>
            </div>
          )}
          {treasury?.costs?.government != null && (
            <div className="mobile-eot-row">
              <span className="label">Government</span>
              <span className={`value ${deltaCls(treasury.costs.government)}`}>{fmtB(treasury.costs.government)}</span>
            </div>
          )}
          {installments.length > 0 && (
            <>
              <div className="mobile-eot-row" style={{ marginTop: 6 }}>
                <span className="label" style={{ opacity: 0.7 }}>Active installments</span>
                <span className="value" style={{ opacity: 0.7 }}>{installments.length}</span>
              </div>
              {installments.map((it, i) => (
                <div key={i} className="mobile-eot-row">
                  <span className="label">↳ {it.npc || it.npc_id || '?'}</span>
                  <span className="value">
                    ${(it.amount ?? it.amount_per_turn ?? 0).toFixed(1)}B
                    {it.turns_remaining != null && ` · ${it.turns_remaining}t`}
                  </span>
                </div>
              ))}
            </>
          )}
        </section>

        {/* STATE */}
        <section className="mobile-eot-section" ref={refs.state}>
          <div className="mobile-eot-section-title">State</div>
          {[
            ['stability', 'Stability', '%'],
            ['approval', 'Approval', '%'],
            ['military', 'Military', ''],
            ['tech', 'Tech', ''],
            ['education', 'Education', ''],
            ['soft_power', 'Soft Power', ''],
            ['dip_capital', 'Dip. Capital', ''],
          ].map(([key, label, suffix]) => {
            const m = state?.[key]
            if (!m) return null
            return (
              <div key={key} className="mobile-eot-row">
                <span className="label">{label}</span>
                <span className="value">
                  {typeof m.value === 'number' ? `${m.value}${suffix}` : (m.value ?? '—')}
                  {m.delta != null && m.delta !== 0 && (
                    <span className={` ${deltaCls(m.delta)}`} style={{ marginLeft: 8 }}>
                      {arrow(m.delta)} {m.delta > 0 ? '+' : ''}{Number(m.delta).toFixed(1)}
                    </span>
                  )}
                </span>
              </div>
            )
          })}
          {!Object.keys(state || {}).length && (
            <div className="mobile-empty" style={{ padding: '8px 0' }}>No state changes recorded.</div>
          )}
        </section>

        {/* RELATIONS */}
        <section className="mobile-eot-section" ref={refs.relations}>
          <div className="mobile-eot-section-title">Relations</div>
          {(relations || []).length === 0 && Object.keys(declEffects).length === 0 && (
            <div className="mobile-empty" style={{ padding: '8px 0' }}>No relation changes this turn.</div>
          )}
          {(relations || []).map((r, i) => {
            const before = (r.value ?? 0) - (r.delta ?? 0)
            return (
              <div key={i} className="mobile-eot-row">
                <span className="label">
                  {r.npc_name || r.npc || '?'} {Math.round(before)} → {Math.round(r.value)}
                </span>
                <span className={`value ${deltaCls(r.delta)}`}>
                  {arrow(r.delta)} {r.delta > 0 ? '+' : ''}{Number(r.delta).toFixed(1)}
                </span>
              </div>
            )
          })}
          {Object.entries(declEffects).map(([npc, delta]) => (
            <div key={npc} className="mobile-eot-row">
              <span className="label">⚑ {npc.toUpperCase()} (declaration)</span>
              <span className={`value ${deltaCls(delta)}`}>
                {arrow(delta)} {delta > 0 ? '+' : ''}{delta}
              </span>
            </div>
          ))}
        </section>

        {/* WORLD EVENTS */}
        <section className="mobile-eot-section" ref={refs.events}>
          <div className="mobile-eot-section-title">World Events</div>
          {(worldEvents || []).length === 0 ? (
            <div className="mobile-empty" style={{ padding: '8px 0' }}>No world events this turn.</div>
          ) : (
            (worldEvents || []).map((evt, i) => (
              <div key={i} className="mobile-eot-row" style={{ display: 'block' }}>
                <span className="value">{evt.text || evt.title || JSON.stringify(evt)}</span>
              </div>
            ))
          )}
        </section>

        {/* Legacy fallback */}
        {!eotData && Array.isArray(eotMessages) && eotMessages.length > 0 && (
          <section className="mobile-eot-section">
            <div className="mobile-eot-section-title">Summary</div>
            {eotMessages.map((m, i) => (
              <div key={i} className="mobile-eot-row" style={{ display: 'block' }}>
                <span className="value">{m}</span>
              </div>
            ))}
          </section>
        )}
      </div>

      <div className="mobile-eot-continue-row">
        <button className="mobile-eot-continue-btn" onClick={onContinue}>
          {ending ? 'SEE RESULTS →' : 'CONTINUE →'}
        </button>
      </div>
    </div>
  )
}
