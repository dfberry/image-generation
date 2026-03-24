# Decision Note: PR #6 — Neo Assert Fix

**Date:** 2026-03-25
**Author:** Neo (Tester)
**Branch:** `squad/pr6-pil-leak-fix`

## Summary

Fixed 3 orphaned test assertion messages in `tests/test_memory_cleanup.py` flagged by Morpheus during PR #5 review.

## Problem

Python/pytest silently ignores the message string in `mock.assert_called(), "message"` because the comma makes it a tuple expression, not a function argument. The assertion fires correctly, but on failure pytest shows no custom message — just the mock name.

## Fix Applied

All 3 tests were in `TestEntryPointFlush`. Changed from orphaned tuple to `assert mock.called, "message"`:

| Test | Before | After |
|------|--------|-------|
| `test_gc_collect_called_at_entry_cuda` | `mock_gc.collect.assert_called(), "gc.collect() should fire before load_base on CUDA"` | `assert mock_gc.collect.called, "gc.collect() should fire before load_base on CUDA"` |
| `test_cuda_cache_flush_at_entry` | `mock_cuda.assert_called(), "torch.cuda.empty_cache() should fire before load_base"` | `assert mock_cuda.called, "torch.cuda.empty_cache() should fire before load_base"` |
| `test_mps_cache_flush_at_entry` | `mock_mps.assert_called(), "torch.mps.empty_cache() should fire before load_base"` | `assert mock_mps.called, "torch.mps.empty_cache() should fire before load_base"` |

## Decision Rule

- Use `assert mock.called, "message"` when the message explains ordering or intent (diagnostic value)
- Use bare `mock.assert_called()` when pytest's default output is sufficient
- Never use `mock.assert_called(), "message"` — the message is silently dropped

## Verification

All 22 tests pass (`pytest tests/ -v`, ~1.9s, no GPU required).
