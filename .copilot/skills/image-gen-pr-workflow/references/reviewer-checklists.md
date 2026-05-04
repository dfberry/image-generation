# Reviewer Checklists

Detailed responsibilities for each PR reviewer.

## 🏗️ Morpheus (Lead)

Charter: `.squad/agents/morpheus/charter.md`

**Checks:**
- Architecture decisions and design patterns
- Security concerns (ReDoS, input validation, injection attacks)
- Code quality and style conventions
- Cross-cutting concerns (logging, error handling)
- Dependency choices and version management
- Performance implications
- Backward compatibility

**Common Issues:**
- Unvalidated user input (regex, file paths)
- Missing error handling or generic exceptions
- Inefficient algorithms or resource usage
- Security vulnerabilities (ReDoS, injection)
- Missing or inadequate logging

---

## 🎨 Niobe (Image Specialist)

Charter: `.squad/agents/niobe/charter.md`

**Checks:**
- OCR approach and accuracy
- Image quality preservation across transformations
- Color handling (RGBA, RGB, JPEG compatibility)
- Resolution, bounds, and aspect ratio
- Font rendering and fallback mechanisms
- Image format compatibility
- Memory efficiency with large images

**Common Issues:**
- JPEG save without quality parameter (degrades images)
- Double image loads (inefficient)
- Missing RGBA→RGB conversion for JPEG
- Missing font fallback (renders as boxes)
- Not preserving image metadata
- Inefficient image processing pipelines

---

## 💬 Switch (UX/Prompt Engineer)

Charter: `.squad/agents/switch/charter.md`

**Checks:**
- CLI flag naming and consistency
- Help text clarity and completeness
- Example quality in epilog
- Error message actionability
- Logging levels appropriateness
- User feedback and progress indicators
- Documentation alignment with implementation

**Common Issues:**
- Help text doesn't mention related flags
- Missing examples in epilog
- Generic error messages ("Error processing")
- Wrong logging levels (info as warning, debug as info)
- Inconsistent flag naming conventions
- Missing progress feedback for long operations

---

## 🧪 Neo (Tester)

Charter: `.squad/agents/neo/charter.md`

**Checks:**
- Test coverage completeness
- Edge case identification and coverage
- Assertion quality and specificity
- Mock realism and accuracy
- Missing test scenarios
- Test isolation and independence
- Performance test coverage

**Common Issues:**
- Weak assertions (`assert result is not None`)
- Missing edge cases (Unicode, case sensitivity, empty input)
- Unrealistic mocks that don't match production
- Tests that depend on execution order
- Missing negative test cases (invalid input)
- Missing performance/load tests
- Flaky tests with timing dependencies

---

## Spawning Pattern

```bash
# Spawn all reviewers in parallel for independent perspectives
task agent_type: general-purpose, name: morpheus-review, \
  prompt: "Review PR #{number} for architecture and security. Read .squad/agents/morpheus/charter.md first."

task agent_type: general-purpose, name: niobe-review, \
  prompt: "Review PR #{number} for image quality. Read .squad/agents/niobe/charter.md first."

task agent_type: general-purpose, name: switch-review, \
  prompt: "Review PR #{number} for UX/CLI. Read .squad/agents/switch/charter.md first."

task agent_type: general-purpose, name: neo-review, \
  prompt: "Review PR #{number} for test quality. Read .squad/agents/neo/charter.md first."
```

---

## Review Verdict Format

Each reviewer must provide:

1. **Verdict:** ✅ APPROVE or ⚠️ REQUEST CHANGES
2. **Findings:** Specific issues with file/line references
3. **Rationale:** Why each issue is blocking or non-blocking
4. **Suggestions:** How to fix (without fixing directly)

**Example:**
```
⚠️ REQUEST CHANGES

Findings:
1. `image-generation/redact_text.py:45` — No validation on user regex input (ReDoS risk)
2. `image-generation/redact_text.py:78` — JPEG save without quality parameter degrades image

Rationale:
- Finding 1 is a security vulnerability that could enable DoS attacks
- Finding 2 causes visible quality degradation in output images

Suggestions:
- Add regex complexity validation before compile()
- Add quality=95 parameter to JPEG save call
```

---

## Fix Cycle

**After REQUEST CHANGES:**

1. **DO NOT** ask the reviewer to fix their findings
2. **DO** spawn the appropriate dev agent to fix:
   - Morpheus/Niobe findings → Trinity (backend dev)
   - Switch findings → Trinity (UX implementation)
   - Neo findings → Neo (test implementation)
3. **DO** re-run only the reviewers who requested changes
4. **DO** verify all original concerns were addressed

**Re-review Pattern:**
```bash
# Only re-run reviewers who requested changes
task agent_type: general-purpose, name: morpheus-re-review, \
  prompt: "Re-review PR #{number} after fixes. Verify your original findings were addressed."
```
