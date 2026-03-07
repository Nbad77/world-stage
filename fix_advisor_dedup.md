# WORLD STAGE — fix_advisor_dedup
Single fix. Verify in browser before proceeding to next fix.

---

## THE PROBLEM

Advisor pool showing duplicate archetypes (two Diplomats, two Technocrats)
simultaneously. Finance Minister never appearing despite being always-available.

Fix D from fixes_16 implemented ADVISOR_AVAILABILITY gating but the
deduplication check (max one per archetype) is not enforcing correctly.

---

## THE FIX

In the advisor pool generation function (api.py or game_state.py),
after filtering candidates by availability, deduplicate by archetype
before returning the pool:

```python
def generate_advisor_pool(game_state, pool_size=4):
    all_candidates = get_all_possible_advisors()

    # Filter by availability (existing Fix D logic — keep as-is)
    available = [a for a in all_candidates if is_advisor_available(a, game_state)]

    # NEW: Deduplicate by archetype — max one per archetype in pool
    seen_archetypes = set()
    deduplicated = []
    for candidate in available:
        if candidate['archetype'] not in seen_archetypes:
            seen_archetypes.add(candidate['archetype'])
            deduplicated.append(candidate)

    # Shuffle and return pool_size candidates
    random.shuffle(deduplicated)
    return deduplicated[:pool_size]
```

Also verify Finance Minister is in the always-available archetype list.
If missing, add it:

```python
ADVISOR_AVAILABILITY = {
    'technocrat':        {'always': True},
    'diplomat':          {'always': True},
    'finance_minister':  {'always': True},  # confirm this exists
    ...
}
```

---

## VERIFICATION

One console.log to add:
`[api] ADVISOR POOL: archetypes in pool = {[a['archetype'] for a in pool]}`

After fix:
- Open new game, check advisor pool
- Confirm no duplicate archetypes
- Confirm Finance Minister appears in pool within first 2-3 new games
- Confirm pool still shows 4 candidates

---

## CLAUDE CODE PROMPT

```
In the advisor pool generation function, add deduplication by archetype
after the availability filter — max one candidate per archetype in the
returned pool. Shuffle before truncating to pool size so the selection
is random within the deduplicated set.

Also confirm finance_minister is in the always-available list in
ADVISOR_AVAILABILITY. If missing, add it.

Add one console.log: the list of archetypes in the generated pool.

Do not change any other advisor logic.
Do not implement any other fixes.
Do not add new features.
```
