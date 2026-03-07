"""
Tests for the Memory Engine — Session 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests cover: store_memory, retrieve_memories, build_memory_context,
relationship summaries, era summaries, and graceful degradation.

Since pgvector and Voyage AI may not be available in the test environment,
these tests focus on the logic paths and graceful degradation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock
from memory_engine import (
    _embed_text,
    build_memory_context,
    store_memory,
    retrieve_memories,
    get_relationship_summary,
    cleanup_expired_memories,
)


def test_embed_text_returns_none_without_voyage():
    """_embed_text should return None when Voyage AI client is unavailable."""
    import memory_engine
    # Save and clear the global client
    old_client = memory_engine._voyage_client
    old_has = memory_engine.HAS_VOYAGE
    memory_engine._voyage_client = None
    memory_engine.HAS_VOYAGE = False

    try:
        with patch.dict(os.environ, {"VOYAGE_API_KEY": ""}):
            # Reset so lazy init runs again
            memory_engine._voyage_client = None
            result = _embed_text("test text")
            assert result is None, f"Expected None, got {result}"
            print("  PASS: _embed_text returns None without Voyage AI")
    finally:
        memory_engine._voyage_client = old_client
        memory_engine.HAS_VOYAGE = old_has


def test_store_memory_graceful_failure():
    """store_memory should not raise even if DB is unavailable."""
    with patch('memory_engine._get_db_session', side_effect=Exception("DB unavailable")):
        # Should not raise
        store_memory(
            player_id="test-player",
            npc="usa",
            era=0,
            turn=3,
            event_type="deal_accepted",
            description="Player accepted USA trade deal"
        )
        print("  PASS: store_memory handles DB failure gracefully")


def test_retrieve_memories_returns_empty_on_failure():
    """retrieve_memories should return [] when DB is unavailable."""
    with patch('memory_engine._get_db_session', side_effect=Exception("DB unavailable")):
        result = retrieve_memories(
            player_id="test-player",
            npc="usa",
            query_text="trade deal"
        )
        assert result == [], f"Expected [], got {result}"
        print("  PASS: retrieve_memories returns [] on DB failure")


def test_get_relationship_summary_returns_none_on_failure():
    """get_relationship_summary should return None when DB is unavailable."""
    with patch('memory_engine._get_db_session', side_effect=Exception("DB unavailable")):
        result = get_relationship_summary(
            player_id="test-player",
            npc="eu"
        )
        assert result is None, f"Expected None, got {result}"
        print("  PASS: get_relationship_summary returns None on DB failure")


def test_build_memory_context_empty_when_no_data():
    """build_memory_context should return dict with empty/None values when no memories exist."""
    with patch('memory_engine.retrieve_memories', return_value=[]):
        with patch('memory_engine.get_relationship_summary', return_value=None):
            with patch('memory_engine.get_era_summaries', return_value=[]):
                result = build_memory_context(
                    player_id="test-player",
                    npc="usa",
                    query_text="trade"
                )
                assert isinstance(result, dict), f"Expected dict, got {type(result)}"
                assert result['episodic'] == [], f"Expected empty episodic list, got {result['episodic']}"
                assert result['relationship_summary'] is None, f"Expected None summary, got {result['relationship_summary']}"
                assert result['era_summaries'] == [], f"Expected empty era_summaries, got {result['era_summaries']}"
                print("  PASS: build_memory_context returns empty dict with no data")


def test_build_memory_context_includes_episodic():
    """build_memory_context includes episodic memories when available."""
    mock_memories = [
        {"turn": 3, "event_type": "deal_accepted", "description": "Accepted USA trade deal"},
        {"turn": 5, "event_type": "promise_broken", "description": "Broke promise to USA"},
    ]
    with patch('memory_engine.retrieve_memories', return_value=mock_memories):
        with patch('memory_engine.get_relationship_summary', return_value=None):
            with patch('memory_engine.get_era_summaries', return_value=[]):
                result = build_memory_context(
                    player_id="test-player",
                    npc="usa",
                    query_text="trade"
                )
                assert isinstance(result, dict), f"Expected dict, got {type(result)}"
                assert len(result['episodic']) == 2, f"Expected 2 episodic entries, got {len(result['episodic'])}"
                assert result['episodic'][0]['event_type'] == 'deal_accepted', \
                    f"First episodic entry should be deal_accepted"
                print("  PASS: build_memory_context includes episodic memories")


def test_build_memory_context_includes_relationship_summary():
    """build_memory_context includes relationship summary when available."""
    mock_summary = "USA-Europa relations are strained after multiple broken promises."
    with patch('memory_engine.retrieve_memories', return_value=[]):
        with patch('memory_engine.get_relationship_summary', return_value=mock_summary):
            with patch('memory_engine.get_era_summaries', return_value=[]):
                result = build_memory_context(
                    player_id="test-player",
                    npc="usa",
                    query_text="trade"
                )
                assert isinstance(result, dict), f"Expected dict, got {type(result)}"
                assert result['relationship_summary'] == mock_summary, \
                    f"Expected summary text, got: {result['relationship_summary']}"
                print("  PASS: build_memory_context includes relationship summary")


def test_cleanup_expired_memories_graceful_failure():
    """cleanup_expired_memories should not raise on DB failure."""
    with patch('memory_engine._get_db_session', side_effect=Exception("DB unavailable")):
        # Should not raise
        cleanup_expired_memories(player_id="test-player")
        print("  PASS: cleanup_expired_memories handles DB failure gracefully")


if __name__ == '__main__':
    print("\n=== test_memory.py ===\n")
    test_embed_text_returns_none_without_voyage()
    test_store_memory_graceful_failure()
    test_retrieve_memories_returns_empty_on_failure()
    test_get_relationship_summary_returns_none_on_failure()
    test_build_memory_context_empty_when_no_data()
    test_build_memory_context_includes_episodic()
    test_build_memory_context_includes_relationship_summary()
    test_cleanup_expired_memories_graceful_failure()
    print("\nAll test_memory tests passed!")
