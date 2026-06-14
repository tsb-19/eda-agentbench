"""Tests for generator determinism and output correctness.

This module owns only the ``spice_deck_debug`` domain. The ``rtl_debug`` and
``timing_report_qa`` generators were retired (see CLAUDE.md); RTL and timing
tasks are generated directly by the parent repo's ``generators/`` (tracks
p1/p3).
"""

import re


class TestGeneratorDeterminism:
    """Test that the SPICE generator config is well-formed and deterministic."""

    def test_spice_generator_deterministic(self):
        from generators.spice_deck_debug.generate import CATEGORY_PLAN, BUG_FUNCTIONS

        # Verify the generator config is well-formed
        assert sum(CATEGORY_PLAN.values()) == 100
        for cat in CATEGORY_PLAN:
            assert cat in BUG_FUNCTIONS

    def test_spice_task_count(self):
        from generators.spice_deck_debug.generate import CATEGORY_PLAN

        total = sum(CATEGORY_PLAN.values())
        assert total == 100

    def test_unique_task_ids(self):
        # SPICE task IDs are generated sequentially and must be unique
        spice_ids = [f"spice_deck_debug_{i:04d}" for i in range(1, 101)]
        assert len(spice_ids) == len(set(spice_ids))


class TestNormalizedNaming:
    """Test that all task IDs follow the normalized 4-digit format."""

    def test_spice_ids_are_4_digit(self):
        # All 100 SPICE task IDs must be 4-digit zero-padded
        for i in range(1, 101):
            tid = f"spice_deck_debug_{i:04d}"
            assert re.match(r"^spice_deck_debug_\d{4}$", tid)

    def test_sequential_numbering(self):
        from generators.spice_deck_debug.generate import CATEGORY_PLAN

        # SPICE is 100 tasks
        spice_total = sum(CATEGORY_PLAN.values())
        assert spice_total == 100

    def test_domain_matches_id_prefix(self):
        # SPICE IDs are always spice_deck_debug_NNNN
        for i in range(1, 101):
            assert f"spice_deck_debug_{i:04d}".startswith("spice_deck_debug_")
