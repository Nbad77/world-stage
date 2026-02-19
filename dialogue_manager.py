"""
Dialogue Manager - STRICT message uniqueness enforcement
NO MESSAGE SHOULD EVER REPEAT IN A 10-TURN GAME
"""

import random


class DialogueManager:
    """Prevents exact message repetition with strict enforcement"""

    def __init__(self):
        # Track EXACT messages sent per NPC (never repeat these)
        self.sent_messages = {
            'usa': set(),
            'arabia': set(),
            'eu': set(),
            'dprg': set()
        }

    def get_unique_message(self, npc, message_variants, context_vars=None):
        """
        Get a message that has NEVER been sent before

        Args:
            npc: 'usa', 'arabia', 'eu', or 'dprg'
            message_variants: List of message templates
            context_vars: Dict with {turn, relations, budget, etc} for dynamic insertion

        Returns:
            A message guaranteed to be unique
        """
        if context_vars is None:
            context_vars = {}

        # Format all variants with context variables
        formatted_variants = []
        for template in message_variants:
            try:
                formatted = template.format(**context_vars)
                formatted_variants.append(formatted)
            except KeyError:
                # If template doesn't use variables, use as-is
                formatted_variants.append(template)

        # Find unused messages
        unused = [m for m in formatted_variants if m not in self.sent_messages[npc]]

        if unused:
            # Pick from unused messages
            selected = random.choice(unused)
        else:
            # ALL variants used - generate unique fallback with turn number
            turn = context_vars.get('turn', 0)

            # Create truly unique message by adding turn-specific suffix
            base = random.choice(message_variants)
            try:
                base_formatted = base.format(**context_vars)
            except KeyError:
                base_formatted = base

            # Add unique suffix to guarantee no repetition
            selected = f"{base_formatted} [Turn {turn} update]"

        # Record this exact message as sent
        self.sent_messages[npc].add(selected)
        return selected

    def format_npc_message(self, npc_name, title, message, stage_direction=None):
        """
        Format NPC dialogue with personality
        stage_direction: Optional physical action/mood (e.g., "*lighting cigar*")
        """
        icons = {
            'usa': '🇺🇸',
            'arabia': '🛢️',
            'eu': '🇪🇺',
            'dprg': '⚡'
        }

        icon = icons.get(npc_name, '📢')

        # Format with stage direction if present
        if stage_direction:
            formatted = f"{icon} {title}: {stage_direction}\n\"{message}\"\n"
        else:
            formatted = f"{icon} {title}:\n\"{message}\"\n"

        return formatted

    def debug_print_sent_counts(self):
        """Debug: Print how many messages each NPC has sent"""
        for npc, messages in self.sent_messages.items():
            print(f"{npc.upper()}: {len(messages)} unique messages sent")
