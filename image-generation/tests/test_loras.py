"""test_loras.py — Unit tests for the LoRA registry system.

Covers test cases TL-1 through TL-12 from PRD §15.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure image-generation/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from presets import LORAS, load_loras

_IMAGE_GEN_DIR = Path(__file__).parent.parent
_LORAS_JSON = _IMAGE_GEN_DIR / "loras.json"
_SCHEMA_JSON = _IMAGE_GEN_DIR / "loras.schema.json"
_VALID_MODEL_TYPES = {"sdxl", "flux", "sd3"}


# ---------------------------------------------------------------------------
# TL-1 — Schema completeness: every entry has required fields
# ---------------------------------------------------------------------------


class TestSchemaCompleteness:
    _REQUIRED = {"model_id", "default_weight", "compatible_models", "description"}

    def test_all_entries_have_required_fields(self):
        """TL-1: Every entry in loras.json has required fields."""
        assert _LORAS_JSON.exists(), "loras.json must exist"
        loras = load_loras()
        for name, entry in loras.items():
            missing = self._REQUIRED - entry.keys()
            assert not missing, f"Entry '{name}' is missing required fields: {missing}"


# ---------------------------------------------------------------------------
# TL-2 — Schema types: compatible_models is a list of valid values
# ---------------------------------------------------------------------------


class TestSchemaTypes:
    def test_compatible_models_is_list(self):
        """TL-2: compatible_models is a list for every entry."""
        loras = load_loras()
        for name, entry in loras.items():
            assert isinstance(entry["compatible_models"], list), (
                f"'{name}'.compatible_models must be a list"
            )

    def test_compatible_models_values_are_valid(self):
        """TL-2: Each compatible_models value is in {sdxl, flux, sd3}."""
        loras = load_loras()
        for name, entry in loras.items():
            for m in entry["compatible_models"]:
                assert m in _VALID_MODEL_TYPES, (
                    f"'{name}'.compatible_models contains unknown type '{m}'"
                )


# ---------------------------------------------------------------------------
# TL-3 — Weight range: all default_weight values are 0.0 ≤ w ≤ 1.5
# ---------------------------------------------------------------------------


class TestWeightRange:
    def test_all_default_weights_in_range(self):
        """TL-3: All default_weight values are within 0.0–1.5."""
        loras = load_loras()
        for name, entry in loras.items():
            w = entry["default_weight"]
            assert 0.0 <= w <= 1.5, (
                f"'{name}'.default_weight={w} is outside the 0.0–1.5 range"
            )


# ---------------------------------------------------------------------------
# TL-4 — JSON Schema validation using jsonschema
# ---------------------------------------------------------------------------


class TestJsonSchemaValidation:
    def test_loras_json_validates_against_schema(self):
        """TL-4: loras.json validates against loras.schema.json with no errors."""
        pytest.importorskip("jsonschema", reason="jsonschema not installed")
        import jsonschema  # noqa: PLC0415

        assert _LORAS_JSON.exists(), "loras.json must exist"
        assert _SCHEMA_JSON.exists(), "loras.schema.json must exist"

        data = json.loads(_LORAS_JSON.read_text(encoding="utf-8"))
        schema = json.loads(_SCHEMA_JSON.read_text(encoding="utf-8"))
        # Raises jsonschema.ValidationError if invalid
        jsonschema.validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# TL-5 — Compatibility check pass: known-compatible pair raises no exception
# ---------------------------------------------------------------------------


class TestCompatibilityCheckPass:
    def test_aether_watercolor_precise_no_exception(self):
        """TL-5: check_lora_compatibility('aether-watercolor', 'precise', LORAS) raises nothing."""
        from simple_config import check_lora_compatibility  # noqa: PLC0415

        # Should not raise
        check_lora_compatibility("aether-watercolor", "precise", LORAS)


# ---------------------------------------------------------------------------
# TL-6 — Trigger word present → prompt unchanged
# ---------------------------------------------------------------------------


class TestTriggerWordPresent:
    def test_trigger_word_already_in_prompt_no_injection(self):
        """TL-6: If trigger word is already in prompt, returned prompt is unchanged."""
        from simple_config import check_and_inject_trigger_words  # noqa: PLC0415

        # Build a synthetic registry entry with a trigger word
        loras = {
            "test-trigger": {
                "trigger_words": ["sketch style"],
                "compatible_models": ["sdxl"],
                "model_id": "test/model",
                "default_weight": 0.7,
                "description": "test",
            }
        }
        prompt = "A tropical scene, sketch style, no text"
        result = check_and_inject_trigger_words(prompt, "test-trigger", loras, interactive=False)
        assert result == prompt, "Prompt should be unchanged when trigger word is present"


# ---------------------------------------------------------------------------
# TL-7 — Trigger word absent → injected prompt contains trigger word
# ---------------------------------------------------------------------------


class TestTriggerWordAbsent:
    def test_missing_trigger_word_is_injected_non_interactive(self):
        """TL-7: Missing trigger word is injected automatically in non-interactive mode."""
        from simple_config import check_and_inject_trigger_words  # noqa: PLC0415

        loras = {
            "test-trigger": {
                "trigger_words": ["ink sketch"],
                "compatible_models": ["sdxl"],
                "model_id": "test/model",
                "default_weight": 0.7,
                "description": "test",
            }
        }
        prompt = "A developer at a desk, warm light, no text"
        result = check_and_inject_trigger_words(prompt, "test-trigger", loras, interactive=False)
        assert "ink sketch" in result.lower(), "Trigger word should be injected into prompt"


# ---------------------------------------------------------------------------
# TL-8 — No duplicate injection
# ---------------------------------------------------------------------------


class TestTriggerWordNoDuplicates:
    def test_inject_twice_no_duplicates(self):
        """TL-8: Injecting the same trigger twice results in exactly one occurrence."""
        from simple_config import check_and_inject_trigger_words  # noqa: PLC0415

        loras = {
            "test-trigger": {
                "trigger_words": ["watercolor ink"],
                "compatible_models": ["sdxl"],
                "model_id": "test/model",
                "default_weight": 0.8,
                "description": "test",
            }
        }
        prompt = "A scenic mountain, no text"
        result1 = check_and_inject_trigger_words(prompt, "test-trigger", loras, interactive=False)
        result2 = check_and_inject_trigger_words(result1, "test-trigger", loras, interactive=False)
        # "watercolor ink" should appear exactly once
        count = result2.lower().count("watercolor ink")
        assert count == 1, f"Expected 1 occurrence of trigger word, got {count}: '{result2}'"


# ---------------------------------------------------------------------------
# TL-9 — lora add round-trip
# ---------------------------------------------------------------------------


class TestLoraAddRoundTrip:
    def test_lora_add_and_load_back(self, tmp_path):
        """TL-9: lora_add writes to temp loras.json; load_loras returns the entry."""
        from simple_config import lora_add  # noqa: PLC0415

        loras_path = tmp_path / "loras.json"
        entry = {
            "model_id": "test/test-lora-sdxl",
            "default_weight": 0.6,
            "trigger_words": ["test style"],
            "compatible_models": ["sdxl"],
            "guidance_delta": 0,
            "style_tokens": "",
            "description": "Test LoRA for round-trip validation",
        }
        lora_add("test-lora", entry, path=loras_path)
        loaded = load_loras(path=loras_path)
        assert "test-lora" in loaded
        assert loaded["test-lora"]["model_id"] == "test/test-lora-sdxl"
        assert loaded["test-lora"]["default_weight"] == 0.6


# ---------------------------------------------------------------------------
# TL-10 — lora remove
# ---------------------------------------------------------------------------


class TestLoraRemove:
    def test_lora_remove_deletes_entry(self, tmp_path):
        """TL-10: lora_remove removes the entry; subsequent load_loras does not contain it."""
        from simple_config import lora_add, lora_remove  # noqa: PLC0415

        loras_path = tmp_path / "loras.json"
        entry = {
            "model_id": "test/to-remove",
            "default_weight": 0.5,
            "trigger_words": [],
            "compatible_models": ["sdxl"],
            "guidance_delta": 0,
            "style_tokens": "",
            "description": "Will be removed",
        }
        lora_add("to-remove", entry, path=loras_path)
        assert "to-remove" in load_loras(path=loras_path)
        lora_remove("to-remove", path=loras_path)
        assert "to-remove" not in load_loras(path=loras_path)


# ---------------------------------------------------------------------------
# TL-11 — lora add: invalid models value raises ValueError
# ---------------------------------------------------------------------------


class TestLoraAddInvalidModels:
    def test_unknown_model_type_raises_value_error(self, tmp_path):
        """TL-11: lora_add with an unknown model type raises ValueError with helpful message."""
        from simple_config import lora_add  # noqa: PLC0415

        entry = {
            "model_id": "test/model",
            "default_weight": 0.7,
            "trigger_words": [],
            "compatible_models": ["unknown-model-type"],
            "guidance_delta": 0,
            "style_tokens": "",
            "description": "Test",
        }
        with pytest.raises(ValueError, match="Unknown model type"):
            lora_add("bad-model", entry, path=tmp_path / "loras.json")


# ---------------------------------------------------------------------------
# TL-12 — lora add: empty model_id raises ValueError; non-empty short ID accepted
# ---------------------------------------------------------------------------


class TestLoraAddModelIdValidation:
    def test_empty_model_id_raises_value_error(self, tmp_path):
        """TL-12: lora_add with empty model_id raises ValueError."""
        from simple_config import lora_add  # noqa: PLC0415

        entry = {
            "model_id": "",
            "default_weight": 0.7,
            "trigger_words": [],
            "compatible_models": ["sdxl"],
            "guidance_delta": 0,
            "style_tokens": "",
            "description": "Test",
        }
        with pytest.raises(ValueError, match="model_id"):
            lora_add("empty-id", entry, path=tmp_path / "loras.json")

    def test_short_non_empty_model_id_accepted(self, tmp_path):
        """TL-12: A short but non-empty model_id is accepted without error."""
        from simple_config import lora_add  # noqa: PLC0415

        entry = {
            "model_id": "a/b",
            "default_weight": 0.7,
            "trigger_words": [],
            "compatible_models": ["sdxl"],
            "guidance_delta": 0,
            "style_tokens": "",
            "description": "Short ID test",
        }
        # Should not raise
        lora_add("short-id", entry, path=tmp_path / "loras.json")
        loaded = load_loras(path=tmp_path / "loras.json")
        assert "short-id" in loaded


# ---------------------------------------------------------------------------
# TL-13 — lora add: duplicate name with overwrite=False raises KeyError
# ---------------------------------------------------------------------------


class TestLoraAddDuplicate:
    _ENTRY = {
        "model_id": "test/dup-lora",
        "default_weight": 0.7,
        "trigger_words": [],
        "compatible_models": ["sdxl"],
        "guidance_delta": 0,
        "style_tokens": "",
        "description": "Duplicate test",
    }

    def test_duplicate_name_raises_key_error(self, tmp_path):
        """TL-13: lora_add with an already-existing name raises KeyError when overwrite=False."""
        from simple_config import lora_add  # noqa: PLC0415

        loras_path = tmp_path / "loras.json"
        lora_add("dup-lora", self._ENTRY, path=loras_path)
        with pytest.raises(KeyError, match="dup-lora"):
            lora_add("dup-lora", self._ENTRY, path=loras_path, overwrite=False)

    def test_duplicate_name_overwrite_true_replaces_entry(self, tmp_path):
        """TL-13: lora_add with overwrite=True replaces the existing entry."""
        from simple_config import lora_add  # noqa: PLC0415

        loras_path = tmp_path / "loras.json"
        lora_add("dup-lora", self._ENTRY, path=loras_path)
        updated = {**self._ENTRY, "default_weight": 0.3}
        lora_add("dup-lora", updated, path=loras_path, overwrite=True)
        loaded = load_loras(path=loras_path)
        assert loaded["dup-lora"]["default_weight"] == 0.3


# ---------------------------------------------------------------------------
# TL-14 — Malformed loras.json raises json.JSONDecodeError
# ---------------------------------------------------------------------------


class TestMalformedJson:
    def test_load_registry_raises_on_corrupt_file(self, tmp_path):
        """TL-14: _load_registry raises json.JSONDecodeError when loras.json is corrupted."""
        from simple_config import _load_registry  # noqa: PLC0415

        bad_path = tmp_path / "loras.json"
        bad_path.write_text("{not valid json!!!}", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            _load_registry(path=bad_path)

    def test_load_loras_raises_on_corrupt_file(self, tmp_path):
        """TL-14: load_loras raises json.JSONDecodeError when loras.json is corrupted."""
        bad_path = tmp_path / "loras.json"
        bad_path.write_text("GARBAGE", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_loras(path=bad_path)


# ---------------------------------------------------------------------------
# TL-15 — Word boundary: trigger "ink" must not match "thinking"
# ---------------------------------------------------------------------------


class TestTriggerWordBoundary:
    def test_ink_not_matched_inside_thinking(self):
        """TL-15: Trigger word 'ink' must not falsely match inside 'thinking'."""
        from simple_config import check_and_inject_trigger_words  # noqa: PLC0415

        loras = {
            "test-ink": {
                "trigger_words": ["ink"],
                "compatible_models": ["sdxl"],
                "model_id": "test/model",
                "default_weight": 0.7,
                "description": "Boundary test",
            }
        }
        # "thinking" contains "ink" as a substring but NOT as a word
        prompt = "A developer thinking at a desk, blinking lights, no text"
        result = check_and_inject_trigger_words(prompt, "test-ink", loras, interactive=False)
        assert "ink" in result, "Trigger 'ink' should have been injected (was absent as a word)"

    def test_ink_present_as_word_not_reinjected(self):
        """TL-15: Trigger word 'ink' present as a standalone word — no injection."""
        from simple_config import check_and_inject_trigger_words  # noqa: PLC0415

        loras = {
            "test-ink": {
                "trigger_words": ["ink"],
                "compatible_models": ["sdxl"],
                "model_id": "test/model",
                "default_weight": 0.7,
                "description": "Boundary test",
            }
        }
        prompt = "A scene rendered in ink, no text"
        result = check_and_inject_trigger_words(prompt, "test-ink", loras, interactive=False)
        assert result == prompt, "Prompt should be unchanged when trigger word 'ink' is already a word"


# ---------------------------------------------------------------------------
# TL-16 — Temp file cleanup on write failure
# ---------------------------------------------------------------------------


class TestTempFileCleanup:
    def test_tmp_file_cleaned_up_on_write_failure(self, tmp_path, monkeypatch):
        """TL-16: .loras.json.tmp is removed if an error occurs during save."""
        from simple_config import _save_registry  # noqa: PLC0415

        target = tmp_path / "loras.json"
        tmp_file = tmp_path / ".loras.json.tmp"

        # Force the rename to fail by making it a dir that can't be replaced
        def _fail_replace(dst):
            raise OSError("simulated rename failure")

        # Write will succeed, replace will fail
        orig_replace = Path.replace

        def patched_replace(self, target_path):
            if self.name == ".loras.json.tmp":
                raise OSError("simulated rename failure")
            return orig_replace(self, target_path)

        monkeypatch.setattr(Path, "replace", patched_replace)

        with pytest.raises(OSError, match="simulated rename failure"):
            _save_registry({"version": 1, "loras": {}}, path=target)

        assert not tmp_file.exists(), ".loras.json.tmp should be cleaned up after failure"

