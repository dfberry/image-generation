# Orchestration Log — Switch (Prompt/LLM Engineer)

**Date:** 2026-03-26T02:42:37Z  
**Agent:** Switch  
**Event:** Negative Prompt Documentation Update

## Assignment

Update prompts/examples.md with negative prompt guidance and integrate into prompt library.

## Execution Summary

✅ **COMPLETED**

### Activities

1. **Style Guide Expansion** — Enhanced style guide section with parameter guidance and negative prompt rationale
2. **Negative Prompt Baseline** — Documented default negative prompt and customization strategies
3. **Prompt Library Update** — Added negative prompt recommendations to all example prompts
4. **Parameter Table Update** — Aligned table with Niobe's performance recommendations

### Documentation Changes

**prompts/examples.md:**

1. **Style Guide Enhancement**
   - Added "Negative Prompt" subsection explaining artifact prevention (text, watermarks, deformities)
   - Documented default baseline and when to override
   - Added troubleshooting guidance for different artifact types

2. **Negative Prompt Strategy**
   - Default: "text, words, letters, watermark, signature, blurry"
   - Art quality focus: add "ugly, distorted, deformed, poorly drawn"
   - Photography focus: add "cartoon, illustration, fake, unrealistic"
   - Can be customized per-prompt with --negative-prompt flag

3. **Example Prompts Updated**
   - All 10 existing prompts now include suggested negative prompt overrides
   - Vacation prompts now include "no text" constraint (fixed from prior audit)
   - Standardized style anchors to "tropical magical realism" for consistency

4. **Parameter Recommendations**
   - Updated table with scheduler guidance (DPMSolverMultistep vs Euler)
   - Aligned --steps recommendations: quick draft (20), blog (28), best (40)
   - Refiner guidance: 7.0 for standard, 5.0 for softer fine details
   - Added note: "Negative prompt essential for all quality levels"

### Documentation Structure

```
prompts/examples.md
├── Style Guide (expanded)
│   ├── Tropical Magical Realism aesthetic
│   ├── Negative Prompt section (NEW)
│   │   ├── Default baseline
│   │   ├── Customization by use case
│   │   └── Troubleshooting
│   └── Parameter Effects
├── Example Prompts (10 total)
│   └── All now with negative_prompt suggestions
├── Parameter Recommendations Table (updated)
│   ├── Steps, guidance, refine per use case
│   └── Scheduler recommendation
└── CLI Examples (including --negative-prompt)
```

### Alignment with Team Decisions

- **Trinity Implementation:** Negative prompt CLI flag + default baseline now documented
- **Neo Testing:** Examples demonstrate negative prompt usage patterns
- **Morpheus Review:** Documentation reinforces architectural importance of negative prompts
- **Niobe Performance:** Parameter table reflects recommended scheduler + step counts

## Deliverable

📄 **File:** `prompts/examples.md` (updated)

### Key Updates

| Section | Change |
|---------|--------|
| Style Guide | +Negative Prompt subsection |
| Prompts | +negative_prompt recommendations, fixed "no text" constraint |
| Parameter Table | Updated steps (20/28/40), scheduler notes, refiner guidance |
| Examples | Now include --negative-prompt CLI usage |

---

**Status:** Documentation complete and merged. Reflects current Trinity implementation and team consensus.
