"""
Memory Engine — Three-Tier NPC Memory System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tier 1: Episodic memories — individual events stored with Voyage AI embeddings.
        Retrieved via cosine similarity for relevant context injection.
Tier 2: Relationship summaries — 2-3 sentence gist per NPC, rewritten each EOT.
Tier 3: Era summaries — paragraph-length compression on regime collapse.

All operations are failure-tolerant: if Voyage AI or pgvector is unavailable,
the system degrades gracefully (text-only storage, recency-based retrieval).
"""

import json
import os
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

# ── Voyage AI Client (lazy singleton) ──────────────────────────────────────

_voyage_client = None
HAS_VOYAGE = False


def _get_voyage_client():
    """Lazy-init Voyage AI client. Returns None if unavailable."""
    global _voyage_client, HAS_VOYAGE
    if _voyage_client is not None:
        return _voyage_client
    try:
        import voyageai
        api_key = os.getenv("VOYAGE_API_KEY", "")
        if not api_key:
            print("  [memory_engine] VOYAGE_API_KEY not set — embeddings disabled")
            return None
        _voyage_client = voyageai.Client(api_key=api_key)
        HAS_VOYAGE = True
        print("  [memory_engine] Voyage AI client initialized")
        return _voyage_client
    except Exception as e:
        print(f"  [memory_engine] Voyage AI unavailable: {e}")
        return None


def _embed_text(text: str) -> list | None:
    """Generate a 512-dim embedding for text. Returns None on failure."""
    client = _get_voyage_client()
    if client is None:
        return None
    try:
        result = client.embed([text], model="voyage-3-lite")
        return result.embeddings[0]
    except Exception as e:
        print(f"  [memory_engine] Embedding failed: {e}")
        return None


# ── Database helpers ────────────────────────────────────────────────────────

def _get_db_session():
    """Get a fresh DB session. Caller must close."""
    from db import SessionLocal
    return SessionLocal()


# ── Tier 1: Episodic Memory ────────────────────────────────────────────────

def store_memory(player_id: str, npc: str, era: int, turn: int,
                 event_type: str, description: str):
    """
    Store an episodic memory event. Non-blocking — failures logged, not raised.
    Generates embedding via Voyage AI; stores row even if embedding fails.
    """
    try:
        from db import NpcMemory, HAS_PGVECTOR
        db = _get_db_session()
        try:
            embedding = _embed_text(description) if HAS_PGVECTOR else None
            memory = NpcMemory(
                player_id=player_id,
                npc=npc,
                era=era,
                turn=turn,
                event_type=event_type,
                description=description,
                embedding=embedding,
                created_at=datetime.now(timezone.utc),
                last_accessed=datetime.now(timezone.utc),
            )
            db.add(memory)
            db.commit()
            print(f"  [memory_engine] STORED: {event_type} for {npc} (turn {turn}, "
                  f"embedding={'yes' if embedding else 'no'})")
        finally:
            db.close()
    except Exception as e:
        print(f"  [memory_engine] store_memory FAILED: {e}")
        traceback.print_exc()


def retrieve_memories(player_id: str, npc: str, query_text: str = "",
                      top_k: int = 3) -> list[dict]:
    """
    Retrieve top-K episodic memories for a player+NPC.
    Uses cosine similarity if embeddings available, falls back to most-recent-by-turn.
    Updates last_accessed on returned rows.
    Returns list of dicts: [{ turn, event_type, description }]
    """
    try:
        from db import NpcMemory, HAS_PGVECTOR
        db = _get_db_session()
        try:
            query_embedding = None
            if HAS_PGVECTOR and query_text:
                query_embedding = _embed_text(query_text)

            if query_embedding is not None:
                # Vector similarity search
                rows = (
                    db.query(NpcMemory)
                    .filter(NpcMemory.player_id == player_id)
                    .filter(NpcMemory.npc == npc)
                    .filter(NpcMemory.embedding.isnot(None))
                    .order_by(NpcMemory.embedding.cosine_distance(query_embedding))
                    .limit(top_k)
                    .all()
                )
            else:
                # Fallback: most recent by turn
                rows = (
                    db.query(NpcMemory)
                    .filter(NpcMemory.player_id == player_id)
                    .filter(NpcMemory.npc == npc)
                    .order_by(NpcMemory.turn.desc())
                    .limit(top_k)
                    .all()
                )

            # Update last_accessed
            now = datetime.now(timezone.utc)
            for row in rows:
                row.last_accessed = now
            db.commit()

            return [
                {
                    "turn": row.turn,
                    "event_type": row.event_type,
                    "description": row.description,
                }
                for row in rows
            ]
        finally:
            db.close()
    except Exception as e:
        print(f"  [memory_engine] retrieve_memories FAILED: {e}")
        return []


# ── Tier 2: Relationship Summaries ──────────────────────────────────────────

def get_relationship_summary(player_id: str, npc: str) -> str | None:
    """Read the current relationship summary for one player+NPC. Returns None if absent."""
    try:
        from db import NpcRelationshipSummary
        db = _get_db_session()
        try:
            row = (
                db.query(NpcRelationshipSummary)
                .filter(NpcRelationshipSummary.player_id == player_id)
                .filter(NpcRelationshipSummary.npc == npc)
                .first()
            )
            return row.summary_text if row else None
        finally:
            db.close()
    except Exception as e:
        print(f"  [memory_engine] get_relationship_summary FAILED: {e}")
        return None


def update_relationship_summaries(player_id: str, npcs_context: dict):
    """
    Batch-rewrite relationship summaries for all NPCs via a single Haiku call.
    npcs_context: { 'usa': 'recent events text', 'arabia': '...', ... }
    Called once in EOT after all other effects resolve.
    """
    try:
        import anthropic
        from db import NpcRelationshipSummary

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("  [memory_engine] No ANTHROPIC_API_KEY — skipping summary update")
            return

        # Build prompt
        npc_blocks = []
        for npc_id, events_text in npcs_context.items():
            if events_text:
                npc_blocks.append(f"NPC: {npc_id} — Recent events: {events_text}")

        if not npc_blocks:
            return

        prompt = (
            "For each NPC below, write a 2-3 sentence summary of their relationship "
            "with Europa's leader based on recent events. Return ONLY valid JSON: "
            '{"usa": "summary...", "arabia": "summary...", "eu": "summary...", "dprg": "summary..."}\n\n'
            + "\n".join(npc_blocks)
        )

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Parse JSON
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        summaries = json.loads(raw)

        # Upsert into DB
        db = _get_db_session()
        try:
            now = datetime.now(timezone.utc)
            for npc_id, summary_text in summaries.items():
                if not summary_text:
                    continue
                existing = (
                    db.query(NpcRelationshipSummary)
                    .filter(NpcRelationshipSummary.player_id == player_id)
                    .filter(NpcRelationshipSummary.npc == npc_id)
                    .first()
                )
                if existing:
                    existing.summary_text = summary_text
                    existing.updated_at = now
                else:
                    db.add(NpcRelationshipSummary(
                        player_id=player_id,
                        npc=npc_id,
                        summary_text=summary_text,
                        updated_at=now,
                    ))
            db.commit()
            print(f"  [memory_engine] Relationship summaries updated for {list(summaries.keys())}")
        finally:
            db.close()
    except Exception as e:
        print(f"  [memory_engine] update_relationship_summaries FAILED: {e}")
        traceback.print_exc()


# ── Tier 3: Era Summaries ──────────────────────────────────────────────────

def get_era_summaries(player_id: str, npc: str, last_n: int = 2) -> list[dict]:
    """Read the last N era summaries for one player+NPC."""
    try:
        from db import EraSummary
        db = _get_db_session()
        try:
            rows = (
                db.query(EraSummary)
                .filter(EraSummary.player_id == player_id)
                .filter(EraSummary.npc == npc)
                .order_by(EraSummary.era.desc())
                .limit(last_n)
                .all()
            )
            return [
                {"era": row.era, "summary": row.summary_text}
                for row in rows
            ]
        finally:
            db.close()
    except Exception as e:
        print(f"  [memory_engine] get_era_summaries FAILED: {e}")
        return []


def create_era_summary(player_id: str, npc: str, era_number: int):
    """
    Compress all episodic memories for this player+NPC+era into a paragraph.
    Called when regime collapse fires.
    """
    try:
        import anthropic
        from db import NpcMemory, EraSummary

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return

        # Retrieve all episodic memories for this era
        db = _get_db_session()
        try:
            rows = (
                db.query(NpcMemory)
                .filter(NpcMemory.player_id == player_id)
                .filter(NpcMemory.npc == npc)
                .filter(NpcMemory.era == era_number)
                .order_by(NpcMemory.turn.asc())
                .all()
            )

            if not rows:
                return

            events_text = "\n".join(
                f"Turn {r.turn} ({r.event_type}): {r.description}"
                for r in rows
            )

            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                temperature=0.3,
                messages=[{"role": "user", "content": (
                    f"Compress these events between {npc.upper()} and Europa's leader "
                    f"into one paragraph (3-4 sentences max):\n\n{events_text}"
                )}],
            )
            summary_text = response.content[0].text.strip()

            db.add(EraSummary(
                player_id=player_id,
                npc=npc,
                era=era_number,
                summary_text=summary_text,
                created_at=datetime.now(timezone.utc),
            ))
            db.commit()
            print(f"  [memory_engine] Era {era_number} summary created for {npc}")
        finally:
            db.close()
    except Exception as e:
        print(f"  [memory_engine] create_era_summary FAILED: {e}")
        traceback.print_exc()


# ── Memory Context Builder ─────────────────────────────────────────────────

TOKEN_CEILING = 500  # rough ceiling for injected memory context


def build_memory_context(player_id: str, npc: str,
                         query_text: str = "") -> dict:
    """
    Assemble all 3 tiers into a dict for injection into NPC context.
    Enforces a ~500 token ceiling (rough: len(text) / 4).
    Returns { episodic: [...], relationship_summary: str|None, era_summaries: [...] }
    """
    # Tier 1: Episodic (top 3)
    episodic = retrieve_memories(player_id, npc, query_text, top_k=3)

    # Tier 2: Relationship summary
    rel_summary = get_relationship_summary(player_id, npc)

    # Tier 3: Era summaries (last 2)
    era_summaries = get_era_summaries(player_id, npc, last_n=2)

    # Token budget enforcement
    total_text = ""
    if rel_summary:
        total_text += rel_summary
    for es in era_summaries:
        total_text += es.get("summary", "")
    for ep in episodic:
        total_text += ep.get("description", "")

    est_tokens = len(total_text) / 4

    # If over budget, trim episodic entries first
    while est_tokens > TOKEN_CEILING and episodic:
        removed = episodic.pop()
        est_tokens -= len(removed.get("description", "")) / 4

    return {
        "episodic": episodic,
        "relationship_summary": rel_summary,
        "era_summaries": era_summaries,
    }


# ── Cleanup ─────────────────────────────────────────────────────────────────

def cleanup_expired_memories(player_id: str):
    """Delete memories not accessed in 90 days. Called on POST /game/new."""
    try:
        from db import NpcMemory
        db = _get_db_session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            deleted = (
                db.query(NpcMemory)
                .filter(NpcMemory.player_id == player_id)
                .filter(NpcMemory.last_accessed < cutoff)
                .delete(synchronize_session=False)
            )
            db.commit()
            if deleted:
                print(f"  [memory_engine] Cleaned up {deleted} expired memories for player {player_id[:8]}...")
        finally:
            db.close()
    except Exception as e:
        print(f"  [memory_engine] cleanup_expired_memories FAILED: {e}")
