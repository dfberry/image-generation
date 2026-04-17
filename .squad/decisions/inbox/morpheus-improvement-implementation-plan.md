# Image Generation Improvement Implementation Plan

**Prepared by:** Morpheus (Lead)  
**Date:** 2026-03-27  
**Requested by:** Dina Berry  
**Source:** M365 Copilot improvement analysis in `image-generation-improvements.md`

---

## Executive Summary

This plan analyzes the improvement suggestions against the current codebase and prioritizes implementation into 4 phases. Key finding: **Refiner is already implemented** (--refine flag). Focus areas: prompt improvements (no code), LoRA support (medium complexity), and ControlNet support (high complexity, optional).

---

## Current State Analysis

### ✅ Already Implemented

**SDXL Refiner** — FULLY IMPLEMENTED
- Flag: `--refine` (enabled base+refiner pipeline)
- Implementation: Lines 209-256 in generate.py
- Base generates latents (80% denoising), refiner completes (20%)
- Separate guidance control: `--guidance` (base), `--refiner-guidance` (refiner)
- Memory optimized: component sharing (text_encoder_2, vae), GPU cache management
- **Status:** Production-ready, tested, documented

### 🎯 Current Capabilities

**CLI Features:**
- Prompt control: `--prompt`, `--negative-prompt`
- Quality: `--steps`, `--guidance`, `--refiner-guidance`, `--refine`
- Composition: `--width`, `--height` (both default 1024)
- Reproducibility: `--seed`
- Scheduler: `--scheduler` (10 options)
- Batch: `--batch-file` (JSON input)
- Device: Auto-detection (CUDA/MPS/CPU), `--cpu` override

**Memory Management:**
- OOM detection (CUDA + MPS)
- Retry with reduced steps
- try/finally cleanup
- Inter-item batch flushing
- torch.compile dynamo cache reset

**Testing:**
- 53+ tests, ~2s runtime
- TDD workflow established
- CI workflow (Python 3.10/3.11)

**Style System:**
- Tropical magical-realism aesthetic
- Master prompt library: `prompts/examples.md`
- Canonical style anchor: "Latin American folk art style, magical realism illustration"
- 6-color palette (magenta, teal, emerald, gold, coral, amber)
- "no text" rule

---

## Improvement Analysis

### Category A: Prompt-Only Changes (No Code Required)

These improvements update `prompts/examples.md` only — no generate.py changes.

**A1. Layout-First Prompt Structure** 🟢 LOW EFFORT
- Current: Style-first prompts ("Latin American folk art...")
- Improved: Scene graph first → style → palette
- Example: "Two lighthouses (2) at dusk... [scene details]... Pen-and-ink line art... Limited 3-color palette only..."
- **Rationale:** SDXL responds better to layout → style → color order
- **Owner:** Switch (prompt engineering)
- **Risk:** None. Backward compatible — old prompts still work

**A2. Plain Color Names vs Hex Codes** 🟢 LOW EFFORT
- Current: prompts/examples.md includes hex codes (#B5179E, #118AB2, etc.)
- Improved: Use "deep magenta," "teal," "emerald green" instead
- Add constraint: "Limited palette only" or "Limited 3-color palette only"
- **Rationale:** SDXL's CLIP encoder ignores hex codes; named colors + "limited palette only" is stronger constraint
- **Owner:** Switch
- **Risk:** None. Improves color fidelity

**A3. Multi-Subject Separation** 🟢 LOW EFFORT
- Current: General compositional guidance
- Improved: Explicit counting + spatial placement
- Example: "Two lighthouses (2)" instead of "two lighthouses"
- Example: "Left lighthouse on left foreground, tall... Right lighthouse on right shore, smaller..."
- **Rationale:** Helps SDXL bind attributes correctly (prevents collapse to single subject)
- **Owner:** Switch
- **Risk:** None. Improves multi-subject consistency

**A4. Enhanced Negative Prompts** 🟢 LOW EFFORT
- Current: Generic negative prompt (11 terms, good baseline)
- Improved: Failure-mode-specific negatives
- Example: Add "single lighthouse, extra lighthouse" for multi-subject scenes
- Example: Add "monochrome, grayscale, black and white" for color palette scenes
- **Rationale:** SDXL training specifically responds to negative prompts; targeted negatives reduce known failure modes
- **Owner:** Switch
- **Risk:** None. Current default remains fallback

**A5. Update Style Guide** 🟢 LOW EFFORT
- Current: Style guide is good but doesn't include new SDXL-specific findings
- Improved: Add section on "SDXL-Specific Prompt Engineering"
  - Layout-first structure
  - Plain color names + "limited palette only"
  - Multi-subject counting and placement
  - Failure-mode-specific negative prompts
- **Owner:** Switch
- **Risk:** None. Documentation only

### Category B: Code Changes (New Features)

These require generate.py modifications and follow TDD workflow.

**B1. LoRA Support** 🟡 MEDIUM COMPLEXITY
- **What:** Load and apply LoRA weights to SDXL base pipeline
- **Why:** Style-specific LoRAs (e.g., "Aether Watercolor & Ink") dramatically improve aesthetic consistency
- **Example LoRA:** Aether Watercolor & Ink (CivitAI)
  - Trigger words: "watercolor ink sketch"
  - Suggested strength: 0.8
- **Implementation:**
  - Add CLI flag: `--lora PATH --lora-scale FLOAT`
  - Use `pipe.load_lora_weights(path)` before inference
  - Apply scale with `pipe.fuse_lora(lora_scale=scale)`
  - Support multiple LoRAs: `--lora path1 --lora-scale 0.8 --lora path2 --lora-scale 0.5`
- **Dependencies:** diffusers already supports LoRA (no new package needed)
- **Owner:** Trinity (implementation) + Neo (tests)
- **Risk:** Medium
  - VRAM impact: LoRAs add ~100-500MB depending on size
  - Compatibility: Must validate LoRA is SDXL-compatible (not SD 1.5)
  - Error handling: Invalid path, incompatible LoRA, OOM scenarios
- **Testing Requirements:**
  - Unit tests: load_lora_weights call, scale application, multiple LoRAs
  - Integration tests: end-to-end generation with LoRA
  - Error tests: missing file, wrong format, OOM with LoRA
- **Estimated Effort:** 2-3 days (design, implement, test, document)

**B2. Alternative SDXL Checkpoints** 🟡 MEDIUM COMPLEXITY
- **What:** Support loading different base SDXL models
- **Why:** Illustration-focused checkpoints (e.g., DreamShaper XL) follow stylization constraints better than base SDXL
- **Implementation:**
  - Add CLI flag: `--model PATH_OR_HF_REPO`
  - Default: "stabilityai/stable-diffusion-xl-base-1.0"
  - Modify `load_base()` to accept model_id parameter
- **Owner:** Trinity (implementation) + Neo (tests)
- **Risk:** Medium
  - Model size: Some checkpoints are 7GB+; download time and storage impact
  - Compatibility: Must be SDXL architecture (not SD 1.5)
  - Quality variance: Different checkpoints have different strengths/weaknesses
- **Testing Requirements:**
  - Unit tests: load_base with custom model_id
  - Integration tests: generation with alternative checkpoint
  - Error tests: invalid model_id, download failure
- **Estimated Effort:** 1-2 days

**B3. ControlNet Support** 🔴 HIGH COMPLEXITY
- **What:** Add ControlNet conditioning for guaranteed composition control
- **Why:** Ensures multi-subject count and placement when prompts alone fail
- **Example:** xinsir/controlnet-scribble-sdxl-1.0 (scribble/line conditioning)
- **Implementation:**
  - Add CLI flags: `--controlnet PATH --controlnet-image PATH --controlnet-scale FLOAT`
  - Use `StableDiffusionXLControlNetPipeline` instead of base pipeline
  - Load ControlNet model: `ControlNetModel.from_pretrained(path)`
  - Preprocess conditioning image if needed
  - Modify both base and refiner pipelines (if --refine used)
- **Dependencies:** diffusers supports ControlNet, but increases complexity
- **Owner:** Trinity (implementation) + Neo (tests)
- **Risk:** High
  - Architecture change: Different pipeline class, affects base+refiner integration
  - VRAM impact: ControlNet adds ~1-2GB depending on model
  - Preprocessing: May need additional image processing (edge detection, scribble extraction)
  - Complexity: Interaction between ControlNet conditioning and refiner stage
  - User workflow: User must provide conditioning image (scribble sketch)
- **Testing Requirements:**
  - Unit tests: ControlNet loading, conditioning image processing
  - Integration tests: base+ControlNet, base+refiner+ControlNet
  - Error tests: missing conditioning image, incompatible ControlNet, OOM
- **Estimated Effort:** 5-7 days (significant complexity)

---

## Prioritized Phases

### Phase 1: Prompt Improvements (Quick Wins)
**Duration:** 1-2 days  
**Owner:** Switch  
**Risk:** 🟢 None  
**Dependencies:** None

**Deliverables:**
1. Update `prompts/examples.md` with SDXL-specific prompt engineering section
2. Rewrite 5-10 existing prompts using layout-first structure
3. Replace hex codes with plain color names + "limited palette only"
4. Add multi-subject counting and spatial placement examples
5. Create failure-mode-specific negative prompt library
6. Document new prompt patterns

**Success Criteria:**
- Style guide updated with new SDXL patterns
- At least 5 example prompts demonstrating new structure
- Negative prompt library with 10+ failure-mode-specific variants

**Rationale:**
- Zero code changes, zero risk
- Immediate impact on image quality
- Establishes prompt patterns for Phase 2+ (when LoRA/ControlNet trigger words needed)
- User (Dina) can validate improvements without running code

---

### Phase 2: LoRA Support (High-Value Feature)
**Duration:** 3-4 days  
**Owner:** Trinity (code) + Neo (tests)  
**Risk:** 🟡 Medium  
**Dependencies:** Phase 1 (prompt patterns needed for LoRA trigger words)

**Deliverables:**
1. **CLI flags:** `--lora PATH --lora-scale FLOAT`
2. **Multi-LoRA support:** Allow multiple --lora flags
3. **Error handling:** Invalid path, incompatible LoRA, OOM scenarios
4. **Tests:** 15+ tests covering load, scale, multiple LoRAs, errors
5. **Documentation:** README update, example commands, LoRA recommendations
6. **Style guide update:** Add Aether Watercolor & Ink LoRA to recommended tools

**Implementation Steps:**
1. Neo designs test suite (TDD workflow)
2. Trinity implements:
   - Modify `load_base()` to accept lora_paths and lora_scales
   - Load LoRAs before inference: `pipe.load_lora_weights(path)`
   - Apply scales: `pipe.fuse_lora(lora_scale=scale)`
   - Error handling for invalid/missing LoRAs
3. All tests pass
4. Morpheus code review
5. Merge to main

**Success Criteria:**
- User can generate image with single LoRA: `python generate.py --prompt "..." --lora aether.safetensors --lora-scale 0.8`
- User can combine multiple LoRAs
- Clear error messages for invalid LoRAs
- No memory leaks or VRAM issues
- All 15+ tests pass

**Rationale:**
- High-value feature: dramatic style consistency improvement
- Medium complexity: diffusers already supports LoRA API
- Unlocks Phase 1 prompt patterns (trigger words like "watercolor ink sketch")
- Prepares groundwork for Phase 3 (alternative checkpoints may bundle LoRAs)

---

### Phase 3: Alternative Checkpoints (Optional Enhancement)
**Duration:** 2-3 days  
**Owner:** Trinity (code) + Neo (tests)  
**Risk:** 🟡 Medium  
**Dependencies:** Phase 2 (LoRA support often pairs with custom checkpoints)

**Deliverables:**
1. **CLI flag:** `--model PATH_OR_HF_REPO`
2. **Default:** "stabilityai/stable-diffusion-xl-base-1.0" (current)
3. **Tests:** 10+ tests covering custom models, errors
4. **Documentation:** Recommended SDXL checkpoints list, model selection guide

**Implementation Steps:**
1. Neo designs test suite
2. Trinity modifies `load_base(model_id)` to accept custom model_id
3. Test with 2-3 popular SDXL checkpoints (DreamShaper XL, etc.)
4. Document checkpoint recommendations in README
5. All tests pass
6. Morpheus review
7. Merge to main

**Success Criteria:**
- User can specify custom checkpoint: `python generate.py --prompt "..." --model dreamshaperXL.safetensors`
- Clear error for invalid checkpoints
- All tests pass

**Rationale:**
- Lower priority than LoRA (LoRA is easier and higher ROI)
- Some checkpoints pre-bundle illustration styles that may reduce need for LoRA
- Risk: quality variance between checkpoints requires testing/documentation

---

### Phase 4: ControlNet Support (Advanced, Optional)
**Duration:** 7-10 days  
**Owner:** Trinity (code) + Neo (tests)  
**Risk:** 🔴 High  
**Dependencies:** Phases 1-3 (prompts + LoRA should solve most composition issues first)

**Deliverables:**
1. **CLI flags:** `--controlnet PATH --controlnet-image PATH --controlnet-scale FLOAT`
2. **Pipeline refactor:** Use `StableDiffusionXLControlNetPipeline`
3. **Refiner compatibility:** Ensure base+refiner+ControlNet works
4. **Tests:** 20+ tests (base+ControlNet, refiner+ControlNet, errors)
5. **Documentation:** ControlNet guide, scribble sketch creation tutorial
6. **Example workflow:** Provide sample scribble images for common compositions

**Implementation Steps:**
1. Neo designs comprehensive test suite
2. Trinity implements:
   - New pipeline class usage
   - ControlNet model loading
   - Conditioning image preprocessing
   - Base+refiner+ControlNet integration (complex!)
   - Error handling (missing image, incompatible ControlNet, OOM)
3. All tests pass (20+)
4. Morpheus architecture review (high-risk change)
5. User validation with sample scribbles
6. Merge to main

**Success Criteria:**
- User can generate with ControlNet: `python generate.py --prompt "..." --controlnet scribble.safetensors --controlnet-image sketch.png`
- Base+refiner+ControlNet pipeline works
- Clear error messages
- No VRAM issues on typical GPUs
- All 20+ tests pass

**Rationale:**
- **Lowest priority** — only needed if Phases 1-2 don't solve composition issues
- Highest complexity and risk
- Adds significant VRAM overhead
- Requires user to create conditioning images (workflow friction)
- Recommendation: **Defer until Phases 1-2 validated** and composition issues persist

---

## Risk Assessment

### Phase 1: Prompt Improvements 🟢
**Risk Level:** None  
**Mitigation:** N/A (documentation only, no code changes)

### Phase 2: LoRA Support 🟡
**Risk Level:** Medium  
**Risks:**
1. **VRAM exhaustion** with large LoRAs
2. **Incompatible LoRAs** (SD 1.5 vs SDXL)
3. **Multiple LoRA conflicts** (weight interaction unpredictable)

**Mitigation:**
- Test LoRA loading in isolation before adding to main pipeline
- Add VRAM profiling in tests
- Document LoRA compatibility requirements
- Provide curated list of tested-compatible LoRAs
- Add `--lora-scale` warnings in docs (>1.0 can cause artifacts)

### Phase 3: Alternative Checkpoints 🟡
**Risk Level:** Medium  
**Risks:**
1. **Model size** (7GB+ downloads)
2. **Quality unpredictability** (some checkpoints may be worse)
3. **Licensing** (some checkpoints have restrictive licenses)

**Mitigation:**
- Document storage requirements clearly
- Provide curated checkpoint list with quality assessments
- Add license warnings in docs
- Test with 3-5 popular checkpoints before release
- Default remains stable base SDXL (no breaking changes)

### Phase 4: ControlNet Support 🔴
**Risk Level:** High  
**Risks:**
1. **Architecture change** (different pipeline class, affects all features)
2. **VRAM overhead** (~1-2GB additional)
3. **Refiner interaction** (unknown compatibility issues)
4. **User workflow friction** (requires conditioning image creation)
5. **Maintenance burden** (more code, more tests, more complexity)

**Mitigation:**
- **Defer until Phases 1-2 validated** — may not be needed
- Extensive testing on dev branch before merge
- Morpheus architectural review required
- User acceptance testing with Dina
- Document ControlNet as "advanced/optional" feature
- Consider feature flag to disable if issues arise
- Budget 2-3 days for refactoring/fixes after initial implementation

---

## Team Assignments

| Phase | Work Type | Owner | Supporting |
|-------|-----------|-------|------------|
| **Phase 1** | Prompt engineering | Switch | Neo (validation) |
| | Style guide update | Switch | — |
| | Negative prompt library | Switch | — |
| **Phase 2** | Test design | Neo | — |
| | LoRA implementation | Trinity | — |
| | Code review | Morpheus | — |
| | Quality validation | Neo | Switch (prompts) |
| **Phase 3** | Test design | Neo | — |
| | Checkpoint implementation | Trinity | — |
| | Code review | Morpheus | — |
| | Quality validation | Neo | Switch (prompts) |
| **Phase 4** | Test design | Neo | — |
| | ControlNet implementation | Trinity | — |
| | Architecture review | Morpheus | — |
| | Refiner integration | Trinity | — |
| | Quality validation | Neo | Switch (prompts) |

---

## Dependencies Between Phases

```
Phase 1 (Prompts)
    ↓
Phase 2 (LoRA) ← Requires Phase 1 prompt patterns for trigger words
    ↓
Phase 3 (Checkpoints) ← Optional; can run parallel to Phase 2
    ↓
Phase 4 (ControlNet) ← Requires Phases 1-2 validation; may not be needed
```

**Critical Path:**
- Phase 1 must complete before Phase 2 (LoRA trigger words need prompt structure)
- Phase 3 is optional and can run in parallel with Phase 2 if desired
- Phase 4 should NOT start until Phases 1-2 are validated in production

**Decision Gate:**
- After Phase 2 completes, assess: Do we still need ControlNet?
- If Phase 1 (prompts) + Phase 2 (LoRA) solve composition issues → Skip Phase 4
- If multi-subject issues persist → Proceed to Phase 4

---

## Governance (TDD Workflow)

Per Squad TDD directive (2026-03-23), all code changes follow:

1. **Create PR branch** (squad/{issue-number}-{slug})
2. **Write tests first** (Neo designs, RED state)
3. **Implement code** (Trinity implements, GREEN state)
4. **Code review** (Morpheus reviews)
5. **Team sign-off** (all tests pass, no regressions)
6. **Merge to main**

**No code merges without:**
- All tests passing (new + existing)
- Morpheus approval
- Documentation updates

---

## Recommended Immediate Actions

### For Dina (User)
1. **Start with Phase 1** — prompt improvements have zero risk and immediate impact
2. **Test refiner flag** — `--refine` is already implemented; try it on current prompts
3. **Validate Phase 1 results** — generate images with new prompt structure before committing to Phase 2

### For Squad
1. **Switch:** Begin Phase 1 immediately (1-2 day turnaround)
2. **Trinity + Neo:** Review LoRA API in diffusers, prepare for Phase 2
3. **Morpheus:** Monitor Phase 1 results; approve Phase 2 start after validation

---

## Out of Scope (Not Recommended)

These items from the improvement doc are **not recommended** for implementation:

1. **"Better negative prompts" in code** — This is a prompt pattern, not a code feature. Handled in Phase 1 (prompt library).
2. **Refiner implementation** — Already done! No work needed.
3. **ControlNet as first priority** — Too high-risk and high-complexity when simpler solutions (prompts, LoRA) will likely suffice.

---

## Success Metrics

### Phase 1
- [ ] Style guide updated with SDXL-specific patterns
- [ ] 5+ example prompts using new structure
- [ ] 10+ failure-mode-specific negative prompts documented
- [ ] Dina validates improved image quality

### Phase 2
- [ ] LoRA loading works with single and multiple LoRAs
- [ ] 15+ tests pass
- [ ] No VRAM leaks
- [ ] Dina generates images with Aether LoRA successfully
- [ ] Quality assessment: "Watercolor ink" aesthetic consistent

### Phase 3 (Optional)
- [ ] Custom checkpoint loading works
- [ ] 10+ tests pass
- [ ] 3-5 checkpoints tested and documented
- [ ] Quality comparison doc created

### Phase 4 (Conditional)
- [ ] ControlNet conditioning works
- [ ] Base+refiner+ControlNet pipeline stable
- [ ] 20+ tests pass
- [ ] User can generate from scribble sketch
- [ ] Dina validates composition control improvement

---

## Estimated Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1 | 1-2 days | Immediate | Day 2 |
| Phase 2 | 3-4 days | Day 3 | Day 6 |
| **Decision Gate** | 1 day | Day 7 | Day 7 |
| Phase 3 (Optional) | 2-3 days | Day 8 | Day 10 |
| Phase 4 (Conditional) | 7-10 days | Day 11 | Day 20 |

**Total Time (if all phases executed):** ~20 days  
**Recommended Path (Phases 1-2 only):** ~6 days

---

## Final Recommendation

**Start with Phase 1 (prompt improvements) immediately.** This has:
- Zero risk
- Zero code changes
- Immediate quality impact
- No resource costs

**Proceed to Phase 2 (LoRA) after Phase 1 validation.** This adds:
- High-value style consistency
- Medium complexity (manageable with TDD)
- Prepares for future enhancements

**Defer Phases 3-4 until Phase 2 is validated in production.** ControlNet may not be needed if prompts + LoRA solve composition issues.

---

**Prepared by:** Morpheus  
**Review Status:** Ready for team review  
**Next Action:** Dina approval → Switch begins Phase 1
