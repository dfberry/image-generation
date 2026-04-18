"""
TDD Red Phase — Batch Generation tests.

These tests are written BEFORE the implementation exists.
ALL tests in this file are expected to FAIL until Trinity implements
`batch_generate()` in generate.py (or batch.py).

Feature contract under test:
    batch_generate(prompts: list[dict], device: str = "mps") -> list[dict]

    Each input dict: {"prompt": str, "output": str, "seed": int (optional)}
    Each output dict: {"prompt": str, "output": str, "status": "ok"|"error", "error": str|None}

Mocking strategy: patch the underlying generate() so no real model loads.
No GPU required.
"""

from unittest.mock import patch

# ---------------------------------------------------------------------------
# Import target — expected to be importable from generate (or batch).
# If batch_generate lives in batch.py, change the import accordingly.
# Either works; Trinity decides the location.
# ---------------------------------------------------------------------------
try:
    from generate import batch_generate
except ImportError:
    try:
        from batch import batch_generate
    except ImportError:
        batch_generate = None  # Will cause tests to fail with clear AttributeError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_prompts(*items):
    """Build a prompts list from (prompt, output[, seed]) tuples."""
    result = []
    for item in items:
        d = {"prompt": item[0], "output": item[1]}
        if len(item) > 2:
            d["seed"] = item[2]
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Test 1 — batch_generate calls generate() once per prompt item
# ---------------------------------------------------------------------------

class TestBatchCallsGeneratePerItem:
    """batch_generate must delegate to generate() exactly N times for N prompts."""

    def test_single_prompt_calls_generate_once(self):
        """One prompt → generate() called exactly once."""
        prompts = _make_prompts(("a tropical scene", "out/01.png"))

        with patch("generate.generate") as mock_gen:
            mock_gen.return_value = "out/01.png"
            batch_generate(prompts, device="cpu")

        assert mock_gen.call_count == 1, (
            "batch_generate must call generate() exactly once for a single-item list"
        )

    def test_three_prompts_calls_generate_three_times(self):
        """Three prompts → generate() called exactly three times."""
        prompts = _make_prompts(
            ("prompt A", "out/a.png"),
            ("prompt B", "out/b.png"),
            ("prompt C", "out/c.png"),
        )

        with patch("generate.generate") as mock_gen:
            mock_gen.return_value = "out/a.png"
            batch_generate(prompts, device="cpu")

        assert mock_gen.call_count == 3, (
            "batch_generate must call generate() once per item"
        )

    def test_generate_called_with_correct_args_per_item(self):
        """generate() must receive the right prompt and output for each item."""
        prompts = _make_prompts(
            ("mountain sunrise", "out/01.png", 42),
            ("ocean waves", "out/02.png", 99),
        )

        captured_args = []

        def capture(args):
            captured_args.append(args)
            return args.output

        with patch("generate.generate", side_effect=capture):
            batch_generate(prompts, device="cpu")

        assert len(captured_args) == 2
        # First call
        assert captured_args[0].prompt == "mountain sunrise"
        assert captured_args[0].output == "out/01.png"
        assert captured_args[0].seed == 42
        # Second call
        assert captured_args[1].prompt == "ocean waves"
        assert captured_args[1].output == "out/02.png"
        assert captured_args[1].seed == 99


# ---------------------------------------------------------------------------
# Test 2 — GPU memory flushed BETWEEN items, not just at the end
# ---------------------------------------------------------------------------

class TestMemoryFlushBetweenItems:
    """gc.collect and cache clears must interleave with generate() calls."""

    def test_gc_collect_fires_between_items(self):
        """gc.collect() must be called between each generate() invocation."""
        prompts = _make_prompts(
            ("scene one", "out/01.png"),
            ("scene two", "out/02.png"),
        )
        call_log = []

        def track_generate(args):
            call_log.append(("generate", args.output))
            return args.output

        def track_gc():
            call_log.append(("gc.collect",))

        with patch("generate.generate", side_effect=track_generate), \
             patch("generate.gc") as mock_gc:
            mock_gc.collect.side_effect = track_gc
            batch_generate(prompts, device="cpu")

        # gc.collect must appear between the two generate() calls
        gen_positions = [i for i, e in enumerate(call_log) if e[0] == "generate"]
        gc_positions  = [i for i, e in enumerate(call_log) if e[0] == "gc.collect"]

        assert len(gen_positions) == 2, "Expected two generate() calls"
        assert any(
            gen_positions[0] < gc_pos < gen_positions[1]
            for gc_pos in gc_positions
        ), (
            "gc.collect() must fire between generate() call 1 and generate() call 2, "
            "not just at the end"
        )

    def test_cuda_cache_cleared_between_items_on_cuda(self):
        """torch.cuda.empty_cache() must fire between items on a CUDA device."""
        prompts = _make_prompts(
            ("scene one", "out/01.png"),
            ("scene two", "out/02.png"),
        )
        call_log = []

        def track_generate(args):
            call_log.append(("generate", args.output))
            return args.output

        def track_cuda():
            call_log.append(("cuda.empty_cache",))

        with patch("generate.generate", side_effect=track_generate), \
             patch("generate.torch") as mock_torch:
            mock_torch.cuda.empty_cache.side_effect = track_cuda
            mock_torch.cuda.is_available.return_value = True
            mock_torch.backends.mps.is_available.return_value = False
            batch_generate(prompts, device="cuda")

        gen_positions  = [i for i, e in enumerate(call_log) if e[0] == "generate"]
        cuda_positions = [i for i, e in enumerate(call_log) if e[0] == "cuda.empty_cache"]

        assert len(gen_positions) == 2
        assert any(
            gen_positions[0] < p < gen_positions[1]
            for p in cuda_positions
        ), "torch.cuda.empty_cache() must fire between items, not only at end"

    def test_mps_cache_cleared_between_items_on_mps(self):
        """torch.mps.empty_cache() must fire between items on MPS."""
        prompts = _make_prompts(
            ("scene one", "out/01.png"),
            ("scene two", "out/02.png"),
        )
        call_log = []

        def track_generate(args):
            call_log.append(("generate", args.output))
            return args.output

        def track_mps():
            call_log.append(("mps.empty_cache",))

        with patch("generate.generate", side_effect=track_generate), \
             patch("generate.torch") as mock_torch:
            mock_torch.mps.empty_cache.side_effect = track_mps
            mock_torch.cuda.is_available.return_value = False
            mock_torch.backends.mps.is_available.return_value = True
            batch_generate(prompts, device="mps")

        gen_positions = [i for i, e in enumerate(call_log) if e[0] == "generate"]
        mps_positions = [i for i, e in enumerate(call_log) if e[0] == "mps.empty_cache"]

        assert len(gen_positions) == 2
        assert any(
            gen_positions[0] < p < gen_positions[1]
            for p in mps_positions
        ), "torch.mps.empty_cache() must fire between items, not only at end"


# ---------------------------------------------------------------------------
# Test 3 — A failure on one item is caught; batch continues; partial results returned
# ---------------------------------------------------------------------------

class TestPartialFailureHandling:
    """One bad item must not abort the whole batch."""

    def test_failure_on_first_item_continues_to_second(self):
        """If item 0 raises, item 1 must still be processed."""
        prompts = _make_prompts(
            ("bad prompt", "out/01.png"),
            ("good prompt", "out/02.png"),
        )

        def selective_fail(args):
            if "bad" in args.prompt:
                raise RuntimeError("inference exploded")
            return args.output

        with patch("generate.generate", side_effect=selective_fail), \
             patch("generate.gc"):
            results = batch_generate(prompts, device="cpu")

        assert len(results) == 2, "Results must contain an entry for every input item"
        statuses = {r["output"]: r["status"] for r in results}
        assert statuses["out/01.png"] == "error", "Failed item must have status='error'"
        assert statuses["out/02.png"] == "ok",    "Successful item must have status='ok'"

    def test_failure_on_middle_item_continues_rest(self):
        """Middle item failure must not prevent later items from running."""
        prompts = _make_prompts(
            ("good A", "out/a.png"),
            ("bad B", "out/b.png"),
            ("good C", "out/c.png"),
        )

        def selective_fail(args):
            if "bad" in args.prompt:
                raise ValueError("bad prompt rejected")
            return args.output

        with patch("generate.generate", side_effect=selective_fail), \
             patch("generate.gc"):
            results = batch_generate(prompts, device="cpu")

        assert len(results) == 3
        by_output = {r["output"]: r for r in results}
        assert by_output["out/a.png"]["status"] == "ok"
        assert by_output["out/b.png"]["status"] == "error"
        assert by_output["out/c.png"]["status"] == "ok"

    def test_error_entry_contains_exception_info(self):
        """Error entries must capture the exception message — no silent failures."""
        prompts = _make_prompts(("exploding prompt", "out/01.png"))

        with patch("generate.generate", side_effect=RuntimeError("VRAM exploded")), \
             patch("generate.gc"):
            results = batch_generate(prompts, device="cpu")

        assert results[0]["status"] == "error"
        assert "error" in results[0], "Error entry must have an 'error' key"
        assert "VRAM exploded" in str(results[0]["error"]), (
            "The error entry must preserve the original exception message"
        )


# ---------------------------------------------------------------------------
# Test 4 — Empty prompts list returns empty results without calling generate
# ---------------------------------------------------------------------------

class TestEmptyBatch:

    def test_empty_list_returns_empty_results(self):
        """batch_generate([]) must return [] immediately."""
        with patch("generate.generate") as mock_gen:
            results = batch_generate([], device="cpu")

        assert results == [], "Empty input must produce empty output"
        mock_gen.assert_not_called()

    def test_empty_list_does_not_call_gc(self):
        """No-op batches should not run memory cleanup."""
        with patch("generate.generate"), \
             patch("generate.gc") as mock_gc:
            batch_generate([], device="cpu")

        mock_gc.collect.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5 — Results list preserves order and includes output_path
# ---------------------------------------------------------------------------

class TestResultOrdering:

    def test_results_preserve_input_order(self):
        """Outputs must appear in the same order as inputs."""
        prompts = _make_prompts(
            ("first",  "out/01.png"),
            ("second", "out/02.png"),
            ("third",  "out/03.png"),
        )

        with patch("generate.generate", side_effect=lambda a: a.output), \
             patch("generate.gc"):
            results = batch_generate(prompts, device="cpu")

        assert [r["output"] for r in results] == ["out/01.png", "out/02.png", "out/03.png"], (
            "Results must preserve the same order as the input prompts list"
        )

    def test_successful_result_includes_output_path(self):
        """Every successful result dict must have an 'output' key."""
        prompts = _make_prompts(("a scene", "out/img.png"))

        with patch("generate.generate", return_value="out/img.png"), \
             patch("generate.gc"):
            results = batch_generate(prompts, device="cpu")

        assert results[0]["output"] == "out/img.png", (
            "Successful result must include output_path from generate()"
        )

    def test_successful_result_has_ok_status(self):
        """Every successful result must have status='ok'."""
        prompts = _make_prompts(("a scene", "out/img.png"))

        with patch("generate.generate", return_value="out/img.png"), \
             patch("generate.gc"):
            results = batch_generate(prompts, device="cpu")

        assert results[0]["status"] == "ok"

    def test_result_includes_original_prompt_text(self):
        """Each result dict must echo back the prompt string."""
        prompts = _make_prompts(("tropical magic realism", "out/01.png"))

        with patch("generate.generate", return_value="out/01.png"), \
             patch("generate.gc"):
            results = batch_generate(prompts, device="cpu")

        assert results[0]["prompt"] == "tropical magic realism"


# ---------------------------------------------------------------------------
# Test 6 — All items fail → returns list of errors, does not raise
# ---------------------------------------------------------------------------

class TestAllItemsFail:

    def test_all_failures_returns_list_not_raises(self):
        """Even if every item fails, batch_generate must return a list, not raise."""
        prompts = _make_prompts(
            ("bad 1", "out/01.png"),
            ("bad 2", "out/02.png"),
        )

        with patch("generate.generate", side_effect=RuntimeError("always fails")), \
             patch("generate.gc"):
            # Must NOT raise — must return error list
            results = batch_generate(prompts, device="cpu")

        assert isinstance(results, list), "batch_generate must return a list even on total failure"
        assert len(results) == 2, "Must return one result entry per input item"
        assert all(r["status"] == "error" for r in results), (
            "All result entries must have status='error' when all items fail"
        )

    def test_all_failures_no_successful_output_path(self):
        """Error results must not fabricate a successful output_path."""
        prompts = _make_prompts(("bad", "out/01.png"))

        with patch("generate.generate", side_effect=ValueError("total failure")), \
             patch("generate.gc"):
            results = batch_generate(prompts, device="cpu")

        # The output key should be present (from input), but status must be error
        assert results[0]["status"] == "error"
        assert results[0].get("error") is not None, "Error entry must document the failure"
