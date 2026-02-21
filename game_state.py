"""
Game State Management - The World Stage v3
Enhanced with personality tracking, betrayal detection, and public approval
"""

class GameState:
    """Central state manager with NPC memory and relationship tracking"""

    def __init__(self):
        # Core resources
        self.budget = 65.0  # Billions (national treasury)
        self.stability = 70  # Percentage
        self.oil_price = 75  # Dollars per barrel (min $20)
        self.public_approval = 60  # Percentage (0-100), drifts stability each turn

        # Personal corruption system
        self.personal_wealth = 0.0  # Leader's hidden skimmed funds (billions)
        # Track which NPC corruption messages have already fired (one-shot)
        self.corruption_warned = {
            'usa_5': False, 'usa_15': False, 'usa_30': False,
            'arabia_5': False, 'arabia_15': False, 'arabia_30': False,
            'eu_5': False, 'eu_15': False, 'eu_30': False,
            'dprg_5': False, 'dprg_15': False, 'dprg_30': False,
        }

        # Turn tracking
        self.current_turn = 1
        self.max_turns = 10

        # NPC relationships (0-100)
        self.relations = {
            'usa': 50,
            'arabia': 50,
            'eu': 50,
            'dprg': 50
        }

        # NPC memory - tracks player behavior
        self.times_sided_with = {'usa': 0, 'arabia': 0, 'eu': 0, 'dprg': 0}
        self.times_ignored = {'usa': 0, 'arabia': 0, 'eu': 0, 'dprg': 0}
        self.consecutive_sides = {'usa': 0, 'arabia': 0, 'eu': 0, 'dprg': 0}
        self.consecutive_ignores = {'usa': 0, 'arabia': 0, 'eu': 0, 'dprg': 0}

        # Last 5 actions for context
        self.action_history = []

        # Active crises
        self.usa_sanctions_active = False
        self.arabia_embargo_active = False

        # Sanctions/embargo tier ramp limiters (max +1 tier per turn)
        self.usa_sanctions_tier = 0
        self.arabia_embargo_tier = 0

        # Betrayal tracking
        self.took_arabia_oil = False
        self.took_usa_side_after_arabia_oil = False
        self.took_arabia_side_after_usa_alliance = False

        # USA blackmail mechanic — fires once per game
        self.blackmail_used = False

        # Stage 4: World Events & Negotiation
        self.current_event = None        # dict | None — world event active this turn
        self.options_override = None     # list | None — negotiated counter-offers

        # Stage 4: Persistent negotiated deal effects
        self.oil_price_locked = False           # True while a negotiated oil lock is active
        self.oil_price_lock_value = 0.0         # The locked price per barrel
        self.oil_price_lock_turns_remaining = 0  # Turns left on the lock
        self.active_trade_commitments = []      # list of {description, turns_remaining}
        self.active_installments = []           # list of {amount, turns_remaining, description, npc}
        # Persistent oil price modifiers — applied on top of relation-based price each EOT.
        # list of {delta: float, turns_remaining: int, description: str}
        # Negative delta = cheaper oil (e.g. Arabia deal -$5 → price drops $5).
        # Positive delta = more expensive (e.g. supply shock +$10).
        # Used for world events and negotiated per-barrel discounts.
        self.oil_price_modifiers = []

    def record_action(self, choice_type, npc_target=None):
        """
        Record player action with full context
        choice_type: 'side_with', 'ignore', 'accept_deal', 'do_nothing'
        """
        action = {
            'turn': self.current_turn,
            'type': choice_type,
            'npc': npc_target
        }
        self.action_history.append(action)

        # Keep last 5
        if len(self.action_history) > 5:
            self.action_history.pop(0)

        # Update counters
        if choice_type == 'side_with' and npc_target:
            self.times_sided_with[npc_target] += 1
            self.consecutive_sides[npc_target] += 1
            # Reset others
            for npc in self.consecutive_sides:
                if npc != npc_target:
                    self.consecutive_sides[npc] = 0

        elif choice_type == 'ignore' and npc_target:
            self.times_ignored[npc_target] += 1
            self.consecutive_ignores[npc_target] += 1

        elif choice_type in ['accept_deal', 'side_with']:
            # Reset ignore counters when engaging
            if npc_target:
                self.consecutive_ignores[npc_target] = 0

        # Betrayal detection
        if choice_type == 'accept_deal' and npc_target == 'arabia':
            self.took_arabia_oil = True

        if self.took_arabia_oil and choice_type == 'side_with' and npc_target == 'usa':
            self.took_usa_side_after_arabia_oil = True

    def update_relations(self, npc, change):
        """Update relationship and check crisis thresholds"""
        self.relations[npc] = max(0, min(100, self.relations[npc] + change))
        # BUG 4: Arabia relations capped at 90 — Sadam never fully trusts outsiders
        if npc == 'arabia':
            self.relations[npc] = min(90, self.relations[npc])

        # Crisis triggers
        if npc == 'usa':
            if self.relations['usa'] < 25:
                self.usa_sanctions_active = True
            else:
                self.usa_sanctions_active = False

        if npc == 'arabia':
            if self.relations['arabia'] < 25:
                self.arabia_embargo_active = True
            else:
                self.arabia_embargo_active = False

    def update_budget(self, change):
        """Update budget (can go negative for loss condition)"""
        self.budget += change

    def update_stability(self, change):
        """Update stability (0-90 max — mirrors approval cap)"""
        self.stability = max(0, min(90, self.stability + change))

    def update_oil_price(self, change):
        """Update oil price with ENFORCED $20 minimum"""
        self.oil_price += change
        if self.oil_price < 20:
            self.oil_price = 20

    def update_approval(self, change):
        """Update public approval (0-90 max — 100% unrealistic under geopolitical pressure)"""
        self.public_approval = max(0, min(90, self.public_approval + change))

    def advance_turn(self):
        """Move to next turn - ENFORCED 10 TURN MAX"""
        if self.current_turn < self.max_turns:
            self.current_turn += 1
            return True
        return False

    def get_last_n_actions(self, n=3):
        """Get last N actions for NPC reference"""
        return self.action_history[-n:] if len(self.action_history) >= n else self.action_history

    def get_approval_indicator(self):
        """Return color-coded approval indicator (max 90%)"""
        a = self.public_approval
        if a >= 70:
            return f"🟢 {a}%"
        elif a >= 50:
            return f"🟡 {a}%"
        elif a >= 30:
            return f"🔴 {a}%"
        else:
            return f"💀 {a}%"

    def set_oil_price_from_relations(self):
        """
        Recalculate oil price each turn based on Arabia relations.
        Does NOT carry forward previous price — resets to relation-based value.
        Base oil price = $75. Then apply multiplier from Arabia relations.
        Returns the new base price (before embargo tier surcharges).
        """
        base = 75.0
        arabia_rel = self.relations['arabia']
        if arabia_rel >= 80:
            new_price = base * 0.70   # ~$52
        elif arabia_rel >= 60:
            new_price = base * 0.85   # ~$64
        elif arabia_rel >= 40:
            new_price = base * 1.00   # $75
        elif arabia_rel >= 20:
            new_price = base * 1.25   # ~$94
        else:
            new_price = base * 1.60   # ~$120
        self.oil_price = max(20.0, round(new_price))

    def get_status_display(self):
        """Generate status display"""
        sanctions_flag = " ⚠️ SANCTIONS!" if self.usa_sanctions_active else ""
        embargo_flag = " ⚠️ EMBARGO!" if self.arabia_embargo_active else ""
        approval_str = self.get_approval_indicator()
        personal_str = f"🏦 Personal: ${self.personal_wealth:.1f}B" if self.personal_wealth > 0 else "🏦 Personal: $0"

        return f"""
{'='*60}
TURN {self.current_turn}/{self.max_turns} - EUROPA STATUS
Budget: ${self.budget:.1f}B | {personal_str} | Stability: {self.stability}%
Oil: ${self.oil_price:.0f}/barrel | Approval: {approval_str}
Relations: USA {self.relations['usa']} | Arabia {self.relations['arabia']} | EU {self.relations['eu']} | DPRG {self.relations['dprg']}
{sanctions_flag}{embargo_flag}
{'='*60}
"""

    def serialize(self):
        """Convert full GameState to a JSON-serializable dict for database storage."""
        return {
            'budget': self.budget,
            'stability': self.stability,
            'oil_price': self.oil_price,
            'public_approval': self.public_approval,
            'personal_wealth': self.personal_wealth,
            'corruption_warned': self.corruption_warned,
            'current_turn': self.current_turn,
            'max_turns': self.max_turns,
            'relations': self.relations,
            'times_sided_with': self.times_sided_with,
            'times_ignored': self.times_ignored,
            'consecutive_sides': self.consecutive_sides,
            'consecutive_ignores': self.consecutive_ignores,
            'action_history': self.action_history,
            'usa_sanctions_active': self.usa_sanctions_active,
            'arabia_embargo_active': self.arabia_embargo_active,
            'usa_sanctions_tier': self.usa_sanctions_tier,
            'arabia_embargo_tier': self.arabia_embargo_tier,
            'took_arabia_oil': self.took_arabia_oil,
            'took_usa_side_after_arabia_oil': self.took_usa_side_after_arabia_oil,
            'took_arabia_side_after_usa_alliance': self.took_arabia_side_after_usa_alliance,
            'blackmail_used': self.blackmail_used,
            'current_event': self.current_event,
            'options_override': self.options_override,
            'oil_price_locked': self.oil_price_locked,
            'oil_price_lock_value': self.oil_price_lock_value,
            'oil_price_lock_turns_remaining': self.oil_price_lock_turns_remaining,
            'active_trade_commitments': self.active_trade_commitments,
            'active_installments': self.active_installments,
            'oil_price_modifiers': self.oil_price_modifiers,
        }

    @classmethod
    def deserialize(cls, data):
        """Reconstruct a GameState from a dict (loaded from database)."""
        gs = cls()
        gs.budget = data['budget']
        gs.stability = data['stability']
        gs.oil_price = data['oil_price']
        gs.public_approval = data['public_approval']
        gs.personal_wealth = data['personal_wealth']
        gs.corruption_warned = data['corruption_warned']
        gs.current_turn = data['current_turn']
        gs.max_turns = data['max_turns']
        gs.relations = data['relations']
        gs.times_sided_with = data['times_sided_with']
        gs.times_ignored = data['times_ignored']
        gs.consecutive_sides = data['consecutive_sides']
        gs.consecutive_ignores = data['consecutive_ignores']
        gs.action_history = data['action_history']
        gs.usa_sanctions_active = data['usa_sanctions_active']
        gs.arabia_embargo_active = data['arabia_embargo_active']
        gs.usa_sanctions_tier = data['usa_sanctions_tier']
        gs.arabia_embargo_tier = data['arabia_embargo_tier']
        gs.took_arabia_oil = data['took_arabia_oil']
        gs.took_usa_side_after_arabia_oil = data['took_usa_side_after_arabia_oil']
        gs.took_arabia_side_after_usa_alliance = data['took_arabia_side_after_usa_alliance']
        gs.blackmail_used = data['blackmail_used']
        gs.current_event = data.get('current_event', None)
        gs.options_override = data.get('options_override', None)
        gs.oil_price_locked = data.get('oil_price_locked', False)
        gs.oil_price_lock_value = data.get('oil_price_lock_value', 0.0)
        gs.oil_price_lock_turns_remaining = data.get('oil_price_lock_turns_remaining', 0)
        gs.active_trade_commitments = data.get('active_trade_commitments', [])
        gs.active_installments = data.get('active_installments', [])
        gs.oil_price_modifiers = data.get('oil_price_modifiers', [])
        return gs
