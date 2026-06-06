# STAAR ADAPTIVE ENGINE — STANDARD OPERATING PROCEDURE
## Invariants, Architecture, and Ground-Up Build Guide for Any TEKS

**Version:** v32 | **Author:** Reverse-engineered from staar_engine_v32_chooser_fixed.html  
**Purpose:** Any LLM can follow this document to build a correct, complete, STAAR-aligned adaptive practice engine for any TEKS standard from scratch.

---

## PART 1 — WHAT THIS IS

A STAAR Engine is a single self-contained HTML file that:
- Generates unlimited practice questions covering every item format STAAR has ever used for one TEKS
- Adapts question selection based on the student's error patterns
- Matches the exact visual and interaction conventions of the Cambium STAAR platform
- Runs on any device with no server, no login, no external dependencies

---

## PART 2 — NON-NEGOTIABLE INVARIANTS

These rules apply to every STAAR Engine regardless of TEKS. Violating any of them produces a broken or misleading engine.

### INVARIANT 1 — STAAR FORMAT PARITY
Every item format that has appeared on released STAAR tests for the target TEKS MUST be represented in the engine. You must read all released items before writing any generator code. Do not guess what STAAR asks. Read the items.

**How to find released items:** Search "STAAR released test [grade] [subject] [year]" on tea.texas.gov or use a lead4ward IQ Analysis document. Collect every item for the target TEKS going back to 2015.

### INVARIANT 2 — CAMBIUM UI CONVENTION
- **Single-answer questions** (MC): choices show a **circle (○)** before each option
- **Two-answer questions** (multiselect): choices show a **square (□)** before each option
- There is **no "Next Question" / "Skip" button**. Students cannot skip. Auto-advance fires after correct answer only.
- The directions line must say "Select one answer." for MC and "Select TWO answers." for multiselect — exactly matching STAAR wording.

### INVARIANT 3 — SPARSE NUMBER MANDATE
STAAR consistently uses numbers with one or more zero places (e.g., 15,090; 40,280; 90,241). A generator that only produces dense numbers (all places nonzero) trains students on the easy case. All number generators must produce sparse numbers at least 40% of the time.

**Sparse number definition:** A 5-digit number where at least one of the four lower places (thousands, hundreds, tens, ones) is zero.

### INVARIANT 4 — VALIDATOR INDEPENDENCE
Every generated item must pass a `validateItem()` check before being shown to a student. The validator must:
- Confirm the correct number of choices (4 for MC, 4–5 for multiselect)
- Confirm the correct number of correct answers (1 for MC, 2 for multiselect)
- Confirm declared answers match marked choices
- Confirm drag-drop answers exist in the answer bank and sum to the target number

**CRITICAL:** The drag-drop validator MUST validate against the item's own declared answers, not a hardcoded expected string. Hardcoding kills every non-matching item silently.

### INVARIANT 5 — NO DEAD FAMILIES
A family listed in the family registry MUST have a working generator. A family whose generator always returns null is a dead family. Dead families cause silent fallback to the simplest item type, producing a narrower question mix than intended without any error signal.

**Test for dead families:** After building, run `runtimeCoverageAudit()` and confirm every family has `familyExposure > 0` after 15 items. Add this check to the teacher panel.

### INVARIANT 6 — DIRECTION COVERAGE
For every representation transformation, both directions must exist as separate item formats:
- Standard form → expanded form ✓
- Expanded form → standard form ✓
- Standard form → expanded notation ✓
- **Expanded notation → standard form ✓** (commonly missed — STAAR 2015 Q1, 2018 Q21)

If STAAR has used both directions, the engine must train both.

### INVARIANT 7 — SYMBOLIC VALIDATOR SCOPE
The symbolic validator (`symbolicValidateItem`) must only validate what it can actually verify. For expression-comparison items (multiselect), do NOT use `safeEvalArithmetic` to determine which choices are "symbolically correct" — complex grouped expressions like `"1,000 + 5,000 + 90"` can fail eval even when mathematically valid. Instead: trust the generator's declared `correctAnswers` and verify that at least one declared answer evaluates to `targetNumber`.

### INVARIANT 8 — ANTI-STARVATION WINDOW
Every question family must appear at least once per `ANTI_STARVATION_WINDOW` items (default: 8). Implement this as a recency check, not a modulo counter. Modulo counters create predictable cycles and cause slot collisions when two modulos align on the same item number.

### INVARIANT 9 — NO LEGACY BYPASS
The adaptive template chooser (`chooseAdaptiveTemplate`) must route ALL item selection through the family router. Any branch that maps error patterns directly to 2–3 legacy templates bypasses 80%+ of the family system and must be removed.

### INVARIANT 10 — ITEM FAMILY COMPLETENESS BEFORE WEIGHTING
Define ALL item families and write ALL generators before writing ANY weighting logic. Weighting a family before its generator exists produces dead weight — a family that appears in probability calculations but never actually generates items.

---

## PART 3 — ARCHITECTURE (what goes in the file, in order)

```
1. HTML shell + CSS
2. Global state variables
3. Student model (mastery, streak, error pattern counters, telemetry)
4. Utility functions (randInt, shuffle, unique, formatNumber, etc.)
5. Number generators (sparse, full, place-part extractors)
6. String builders (makeExpandedFormString, makeExpandedNotationString)
7. Item generators — one function per family
8. Validators (validateItem, symbolicValidateItem)
9. Family registry (COMPOSE_REPRESENTATION_FAMILIES array)
10. Family weights (FAMILY_WEIGHTS object)
11. Misconception-to-family map (MISCONCEPTION_TO_FAMILY)
12. Family chooser (chooseComposeFamilyWeighted) — 5-step pipeline
13. Item renderer (renderItem)
14. Answer submission logic (submitAnswer)
15. Mastery loop + endgame (enterMasteryMode, finishFinalCheck, triggerWin)
16. Adaptive template router (chooseAdaptiveTemplate — always returns "__compose_family_router__")
17. Boot + coverage audit
```

---

## PART 4 — GROUND-UP BUILD PROCESS FOR ANY TEKS

### STEP 0 — READ THE RELEASED ITEMS FIRST
Do not write a single line of code until you have inventoried every released STAAR item for the target TEKS. For each item, record:
- Year and question number
- Item type (MC, multiselect, drag-drop, grid-in)
- The exact format/phrasing of the stem
- The correct answer
- The distractor structure (what makes each wrong answer plausible)
- The misconception each distractor targets

This inventory becomes your family list. You are not inventing families — you are reading them off of real tests.

### STEP 1 — IDENTIFY ITEM FAMILIES
Group the released items into families by what they are testing and how they present it. Each distinct (stimulus type × question direction × response mode) combination is a separate family.

**Example for TEKS 3.2A:**
| Family | Stimulus | Direction | Response |
|---|---|---|---|
| expanded_form_to_standard | Expanded form expression (scrambled) | → standard number | MC |
| standard_to_expanded_form | Standard number | → expanded form | MC |
| standard_to_expanded_notation | Standard number | → notation (d×p) | MC |
| notation_to_standard | Notation expression (d×p) | → standard number | MC |
| unit_language_to_standard | Word-unit description | → standard number | MC |
| unit_overflow_compose | Overflowing unit counts | → standard number | MC |
| place_label_mapping | Number + coefficient slots | → place name labels | Drag-drop |
| partial_plausible_multiselect | Standard number | → which 2 of 5 are equivalent | Multiselect |
| regrouped_correct | Standard number | → which is a valid non-canonical form | MC or MS |
| regrouped_near_miss | Standard number | → which split is valid (near-miss traps) | MC |
| truth_judgment | Standard number | → which statement is true (or NOT true) | MC |
| error_analysis | Wrong student expression | → what error was made | MC |
| notation_discrimination | Standard number | → which uses expanded notation (not form) | MC |

### STEP 2 — DEFINE MISCONCEPTION TAXONOMY
Identify 2–4 core misconceptions that cut across all families. Every family targets at least one misconception. This drives adaptive routing.

**Example for 3.2A:**
- `unit_to_digit_confusion` — treats a coefficient as a digit (70 hundreds → 70,___ instead of 7,000+___)
- `place_value_misalignment` — maps coefficient to wrong place (shifts left or right)
- `partial_decomposition_acceptance` — accepts an incomplete decomposition as correct

### STEP 3 — BUILD UTILITY LAYER FIRST
Before any generators, build:
- `randInt(min, max)`
- `shuffle(arr)` — Fisher-Yates, returns new array
- `unique(arr)` — deduplicates
- `formatNumber(n)` — locale string with commas
- `nonzeroPlaceParts(n)` — returns `[{digit, place, value}, ...]` for each nonzero place
- `makeSparseNumber()` — guarantees at least one zero place
- `makeExpandedFormString(n)` — "10,000 + 200 + 30"
- `makeExpandedNotationString(n)` — "(1 × 10,000) + (2 × 100) + (3 × 10)"

**Test each utility function before building generators.**

### STEP 4 — BUILD ONE GENERATOR PER FAMILY
Each generator is a function that:
1. Generates a number (use `makeSparseNumber()` ~50% of the time)
2. Constructs the correct answer
3. Constructs 3 wrong answers (for MC) or 3–4 traps + 2 correct (for multiselect)
4. Calls `unique()` on all choices and returns null if fewer than required unique choices exist
5. Returns a complete item object

**Item object schema (required fields):**
```javascript
{
  id: string,              // unique: templateId + Date.now() + random
  templateId: string,      // matches composeMC allowlist
  family: string,          // matches COMPOSE_REPRESENTATION_FAMILIES
  itemType: "multiple_choice" | "multiselect" | "drag_and_drop",
  skill: string,
  pattern: string,         // misconception key
  stem_en: string,
  stem_es: string,
  directions_en: string,   // "Select one answer." or "Select TWO answers."
  directions_es: string,
  visual: { type: "equation", text: string },
  answerKey: {
    mode: "single_select" | "multi_select_exact" | "ordered_text_list",
    correctAnswers: string[]
  },
  meta: { correctValue?: number, targetNumber?: number, notationExpr?: string },
  choices: [{ text: string, correct: boolean }]
}
```

**Generator return contract:**
- Return the complete item object on success
- Return `null` if uniqueness checks fail or inputs are degenerate
- Never throw — return null on edge cases

### STEP 5 — BUILD VALIDATORS
Build `validateItem(item)` before wiring up the chooser. The router loop calls this after every generation attempt and discards FAIL items. Without it, bad items reach students.

```
validateItem checks:
✓ Correct choice count (4 for MC, 4-5 for multiselect, 3 answers for drag-drop)
✓ Correct answer count (1 for MC, 2 for multiselect)
✓ Declared answers match marked choices
✓ templateId is in the composeMC allowlist
✓ Drag-drop: answers in bank, coefficients × declared places = targetNumber
✓ Symbolic spot-check for expression items (at least one correct eval to target)
```

### STEP 6 — BUILD THE FAMILY REGISTRY AND WEIGHTS
```javascript
const COMPOSE_REPRESENTATION_FAMILIES = [ /* all family names */ ];

const FAMILY_WEIGHTS = {
  // Higher = more frequent
  // Families targeting STAAR-confirmed trap types: weight 8-10
  // Families covering every STAAR format: weight 6-8
  // Supplementary families: weight 4-6
};

const MISCONCEPTION_TO_FAMILY = {
  misconception_key: ["family1", "family2", ...],
  ...
};
```

### STEP 7 — BUILD THE CHOOSER (5-step pipeline)
```
Step 1: Anti-starvation — force any family not seen in last N items
Step 2: Misconception priority — restrict pool if any error count ≥ 2
Step 3: Domination prevention — exclude families with > 1.5× average exposure
Step 4: Dedup — exclude the last chosen family
Step 5: Weighted sample from remaining pool
```

After every pick: update `familyExposure[chosen]++` and `familyLastSeen[chosen] = currentIndex`.

### STEP 8 — BUILD THE RENDERER
The renderer (`renderItem`) must:
- Set `data-shape="circle"` on all MC choice buttons
- Set `data-shape="square"` on all multiselect choice buttons
- Clear prior state (selected, feedback, visual visibility)
- Show answer bank for drag-drop items

### STEP 9 — BUILD SUBMIT + ADAPTIVE ROUTING
- On correct: update student model, advance mastery, auto-advance after delay
- On wrong: show structure support, increment pattern error counter, do NOT auto-advance
- `chooseAdaptiveTemplate()` must always return `"__compose_family_router__"` — no legacy bypass

### STEP 10 — ADD TEACHER PANEL + COVERAGE AUDIT
The teacher panel must show:
- Per-family exposure counts (so you can see dead families at a glance)
- STAAR trap family coverage (warns if any critical family is at zero after N items)
- Student model state
- Last item raw JSON

`runtimeCoverageAudit()` runs at boot and logs any family with zero coverage.

---

## PART 5 — DISTRACTOR DESIGN RULES

For every family, each wrong answer must target a specific, real misconception. Distractors must be:

1. **Plausible** — a student with a specific misconception would choose it
2. **Exclusive** — it must not evaluate to the correct answer
3. **Distinct** — all 4 choices must be unique strings and unique values

**Distractor patterns by family type:**

| Family type | Required distractor types |
|---|---|
| Standard → expanded form | Wrong place (digit instead of value), truncated (missing last place), notation instead of form |
| Expanded form → standard | Off by one place (shift), concatenation of digits, partial sum |
| Unit overflow | Concatenation of coefficients, digit-only (ignores multiplier), shifted place |
| Notation → standard | Off by one place unit, missing last place, last digit as ones not value |
| Multiselect equivalence | Missing one place, last place shifted, extra place added |
| Truth judgment / NOT | Swap tens↔ones, wrong digit for a place, drop one place |
| Error analysis | Blame wrong place, correct opposite diagnosis, "it's fine" |

---

## PART 6 — COMMON FAILURE MODES (and how to prevent them)

| Failure | Symptom | Prevention |
|---|---|---|
| Hardcoded validator | Drag-drop always fails, falls back to MC | Never hardcode expected answers in validator |
| Dead family | One family never appears despite being in registry | Check for generator body before adding to registry |
| Legacy bypass | Only 2–3 question types appear | `chooseAdaptiveTemplate` must always return `"__compose_family_router__"` |
| Modulo starvation | Families only appear every Nth question, many turns with nothing | Use anti-starvation window, not modulo |
| Dense-only numbers | Students never practice sparse-place items | `makeSparseNumber()` used ≥40% of the time |
| Symbolic validator over-reach | Valid expressions fail validation | Use declared answers as truth source, not arithmetic re-eval |
| Missing direction | Kids see notation → standard on STAAR but never practiced it | Both directions required for every transformation family |
| Regrouped-correct multiselect only | STAAR had it as MC in 2016 | Build both MC and multiselect variants |
| Skip button present | Kids skip hard items | No skip button. Auto-advance on correct only. |
| Wrong selector shape | Kids don't know how many answers to select | MC = circles, multiselect = squares (matches Cambium) |

---

## PART 7 — CHECKLIST BEFORE SHIPPING

Run through this before giving the file to students:

```
□ Every released STAAR item format (back to 2015) has a generator
□ makeSparseNumber() is used ≥40% of the time in all generators
□ No generator returns null for all inputs (test each one manually)
□ validateItem() rejects items with wrong choice counts
□ Drag-drop validator uses item's own declared answers, not hardcoded string
□ chooseAdaptiveTemplate() always returns "__compose_family_router__"
□ No Next Question / Skip button
□ MC choices have data-shape="circle"
□ Multiselect choices have data-shape="square"
□ Both directions covered for every transformation (standard→X AND X→standard)
□ runtimeCoverageAudit() shows 0 missing families at boot
□ Teacher panel shows per-family exposure counts
□ Bilingual (EN + ES) for all stems and directions
□ Brace balance in JS (open count === close count)
□ File loads and generates first item within 1 second on mobile
```

---

## PART 8 — HOW TO ADAPT THIS TO ANY TEKS

### Phase 1: Research (before any code)
1. Pull all released STAAR items for the target TEKS (2015–present)
2. Build the item inventory table (year, format, stem, correct answer, distractor analysis)
3. Identify item families from the inventory
4. Identify 2–4 core misconceptions
5. Map each family to the misconceptions it targets

### Phase 2: Design
6. Define the family registry (names, weights, misconception mapping)
7. Define the number/value generator appropriate to the TEKS domain
8. Define the distractor patterns for each family
9. Define the visual support (what the structure hint shows)

### Phase 3: Build (in strict order)
10. Utility layer
11. Domain-specific generators (e.g., fraction builders, coordinate generators)
12. Item generators — one per family
13. Validators
14. Family registry, weights, misconception map
15. Chooser
16. Renderer + submit logic
17. Mastery loop
18. Teacher panel + coverage audit

### Phase 4: Audit
19. Run the audit: every released item format covered? Both directions? Sparse inputs?
20. Play 20 questions and check teacher panel — every family appeared?
21. Fix any dead families, broken validators, or missing directions
22. Ship

---

## PART 9 — DOMAIN TEMPLATES FOR OTHER TEKS

### For fraction standards (e.g., 3.3A, 4.3A)
Number generator: fraction generator — `{numerator, denominator, value}`. Families: identify fraction on number line, equivalent fractions, compare fractions, compose from unit fractions. Misconception map: numerator-denominator confusion, benchmark confusion, part-whole vs part-group.

### For multiplication/division (e.g., 3.4A, 3.4K)
Number generator: factor pair generator. Families: array model, area model, equation completion, fact family, word problem structure. Misconception map: addition confusion, skip-count error, partial product.

### For geometry (e.g., 3.6A)
Stimulus generator: shape attribute list. Families: classify by attribute, identify by name, sort into categories, explain why not. Misconception map: prototype fixation (only equilateral triangles are triangles), orientation confusion.

### For data/graphs (e.g., 3.8A)
Stimulus generator: dataset generator with deliberate near-miss values. Families: read single bar, compare two bars, find total, find difference, what changed. Misconception map: read label vs value, axis scale confusion, off-by-one bar reading.

---

*This SOP was reverse-engineered from staar_engine_v32_chooser_fixed.html, which implements TEKS 3.2A place value. The architecture, invariants, and failure modes documented here apply universally.*

---

## PART 10 — LIVING INVARIANTS (JiT-style — added as bugs are found)

These invariants were discovered during live testing and coding sessions. Each one corresponds to a real bug that shipped. Following the JiT testing principle from Meta Research: every bug found creates a new invariant and a "catching check" to prevent regression.

### INVARIANT L-1 — No valid representation as distractor for representation-discrimination items
**Bug found:** `standard_to_expanded_notation` used `expandedForm` as `wrong2`. Expanded form is a valid alternate representation of the same number. Students selecting it are not making a conceptual error — they just picked the other valid form. This is a test design error, not a student error.
**Rule:** On any item that asks students to select the correct FORM of representation (notation vs form, etc.), all distractors must be **broken versions of the target form**, never a different valid form.
**Catching check:** After any distractor change to a notation item: verify no choice text evaluates to the correct value via a non-notation arithmetic path. Specifically: `safeEvalArithmetic(choice) === correctValue` must be false for all wrong choices.

### INVARIANT L-2 — Challenge Zone gate requires ALL format stamps + minimum item count
**Bug found:** Student reached 100 without seeing all question types because the gate only checked score ≥ 90 and `allFormatsSeenForChallengeZone()`, but the anti-starvation window alone was not strong enough to guarantee all 9 formats appeared before score reached 90.
**Rule:** Challenge Zone requires: score ≥ 90 AND all 9 STAAR format stamps seen AND minimum 12 items attempted. The chooser must additionally force unseen-format families every 3rd item when score ≥ 40.
**Catching check:** Simulate 12 items with score climbing fast — verify `allFormatsSeenForChallengeZone()` is false if any stamp family has never been chosen.

### INVARIANT L-3 — Win screen must deliver a real emotional moment
**Bug found:** Student reached 100, got a generic overlay with "🎉 You did it!" and two buttons. No personalized stats, no real celebration energy. Students who earned mastery deserve a moment proportional to the achievement.
**Rule:** The win screen must include: a bold championship title (randomly selected from 4+ options), personalized first-try accuracy stat, total questions stat, confirmation that all STAAR format types were practiced, and multiple celebration burst waves. The screen must feel materially different from the "almost" overlay.
**Catching check:** `triggerWin()` must call `spawnCelebrationBurst()` at least 3 times with staggered timeouts, and must populate at least 3 distinct personalized stat elements before showing the overlay.

### INVARIANT L-4 — Drag-drop items must use native mobile-friendly interaction
**Bug found:** The drag-drop place-label item rendered as a text input where students had to type "ten thousands, hundreds, ones" — completely unworkable on mobile under time pressure.
**Rule:** Any item with `itemType === "drag_and_drop"` must render as inline `<select>` dropdowns embedded in the expression. No text input for place-label items. On mobile, native `<select>` opens the OS picker, which is fast and accessible.
**Catching check:** `renderItem()` for drag_and_drop items must not call `inputWrap.style.display = "block"` or create any `<input type="text">` element.

### INVARIANT L-5 — Notation distractors must use × syntax, not + syntax
**Rule:** Distractors for expanded notation items must look like notation — they must use `(digit × place)` format, not `value + value` format. Mixing the two in a choice list allows visual pattern-matching instead of conceptual understanding.
**Catching check:** Every choice in a notation item must either contain `×` (correct notation format) or be clearly wrong notation — no plain addition expressions as choices.

### INVARIANT L-6 — showMasteryOverlay must not clobber pre-populated content
**Bug found:** `triggerWin()` populated win stats directly into DOM elements, then called `showMasteryOverlay("", "")` which overwrote title/message with empty strings.
**Rule:** `showMasteryOverlay(title, message)` must only set elements when `title`/`message` are non-empty strings. When the caller populates content directly before calling `showMasteryOverlay`, the function is just a visibility trigger.
**Catching check:** `showMasteryOverlay("", "")` must leave existing `textContent` of `masteryTitle` and `masteryMessage` unchanged.

---

## PART 11 — JiT TESTING PROTOCOL FOR THIS ENGINE

Inspired by Meta's Just-in-Time testing research: tests are generated at change time, targeted at the specific diff, designed to fail on the broken version and pass on the fixed version.

**For every generator change:**
1. Identify the specific distractor or answer rule being changed
2. State the old broken behavior as a falsifiable condition
3. Add a comment in the code stating what the new behavior must NOT do
4. After patching, verify the breaking condition is gone using `python3 -c` spot checks

**For every new family:**
Run the 7-item SUBSYSTEM_VALIDATOR_MATRIX checklist (from SUBSYSTEM_VALIDATOR_MATRIX_v1.json):
generator_exists → chooser_surface_exists → validator_support_exists → label_helper_support_exists → coverage_signal_exists → clue_mapping → persistence_review

**For every mastery system change:**
Run the 5-item mastery_loop checklist: mode_transition_check → overlay_reachability_check → progress_state_check → continue_challenge_path_check → syntax_check

**Telemetry targets for future improvement:**
- Track which families produce the most wrong-answer-on-first-try events → weight those families higher in Practice Zone
- Track which specific distractors are most chosen → these reveal real student misconceptions worth surfacing in the structure hint
- Track time-to-submit per family → families that take longest may need clearer stem writing
- Track Challenge Zone fail rate per family → families with high Challenge Zone fail rate need easier Practice Zone variants as scaffolding


### INVARIANT L-7 — Scaffold support must be task-specific and number-aware, never echo
**Bug found:** The "Structure support" box showed `80,409` as the hint for "What is 80,409 in expanded form?" — identical to the stem. A student who doesn't know the answer gets zero help from seeing the question number repeated.
**Rule:** Every scaffold must include at minimum: (1) what the question is asking the student to DO, (2) a place-value digit chip row built from the item's actual number, (3) a show-your-work model for that specific question family. Never echo the number from the stem as the entire hint content.
**Catching check:** `buildScaffoldTier1(item)` must return HTML containing at least one `×` or `+` operator or a structured digit breakdown — never just `formatNumber(n)` as the sole content.

### INVARIANT L-8 — Scaffold must be hidden until first wrong answer, not always visible
**Bug found:** The visual/hint panel was visible by default, meaning students saw the hint before even attempting the question — removing challenge and reward structure.
**Rule:** Scaffold starts at `scaffoldTier = 0` (hidden) on every new item. Tier 1 reveals on first wrong answer or if student taps "Need a hint?" voluntarily. Tier 2 reveals on second wrong answer. The button label must say "Need a hint?" not "Think with structure" — the latter implies students should always use it.
**Catching check:** `renderItem()` must set `scaffoldTier = 0` and call `visual.style.display = "none"` before rendering each new item.

### INVARIANT L-9 — Scaffold must advance by tier on wrong answers, not just show the same content
**Rule:** First wrong → Tier 1 (conceptual + show-your-work model). Second wrong → Tier 2 (step-by-step with actual numbers from the item). The tier advances automatically so students get more help the more they struggle, without being shown the answer.
**Catching check:** `submitAnswer()` wrong-answer path must call `scaffoldTier = Math.min(2, scaffoldTier + 1)` followed by `renderScaffold(currentItem, scaffoldTier)`.

### INVARIANT L-10 — Removing a block that contains utility functions kills the whole engine
**Bug class found:** When replacing a large block that starts with `promptEngine` and ends with `getPrompt`, the replacement accidentally excluded `t()`, `randInt()`, `formatNumber()`, `shuffle()`, `unique()`, `normalize()` — utilities defined between those two anchors. Engine fails silently on first item generation.
**Rule:** Before any str_replace on a block longer than 20 lines: grep for all function definitions inside that block. Every function found must appear in the replacement. After patching: grep for all functions that were in the original block and verify each is still present.
**Catching check:** After any large block replacement, run `grep -n "^function " file.html` and compare count before vs after. A drop means utilities were lost.

### SHOW-YOUR-WORK SYSTEM — Design principles
Based on IES/WWC practice guide and CRA (Concrete-Representational-Abstract) framework:
1. **Hidden until needed.** Students should attempt first. The hint button says "Need a hint?" — not "Look here." This preserves productive struggle, which research shows is necessary for learning (not struggle that causes frustration, but the kind that requires effort).
2. **Three-tier structure.** Tier 1 = conceptual (what is this question TYPE asking you to do?) + representational (digit chips showing place structure). Tier 2 = procedural (the actual arithmetic step with the real numbers from this item). Never give the answer — show the next move.
3. **STAAR scratch area modeling.** The show-your-work section explicitly says "✏️ Show your work (like STAAR scratch area):" — this connects the hint to the test-taking skill. Students see what thinking-on-paper looks like for this family.
4. **Family-aware.** Different question types need different cognitive support. Notation items need a reminder that notation uses `×`, not `+`. Overflow items need the multiplication model. Multiselect items need the "check each choice" strategy. Generic hints don't transfer.
5. **Bilingual.** All scaffold content is translated. ELL students benefit more from scaffolding than native speakers — this is one of the most evidence-supported interventions for emergent bilinguals.

### INVARIANT L-11 — Never use JavaScript .sort() on formatted-number expression arrays
**Bug found:** The regrouped_equivalent generator used `.sort().join(" + ")` to build expression strings like `regroupedCorrect`, `wrongMissing`, `canonicalForm`. JavaScript `.sort()` on strings is **lexicographic**, not numeric. `"9,000"` sorts after `"300"` (because `"9" > "3"`) but before `"90,000"` (because `"9," < "90"`). This made `"70,000 + 9,000 + 300"` and `"300 + 70,000 + 9,000"` appear to be different strings even though they represent the same expression. Both ended up in `raw[]` as distinct entries. One got `correct: true`, the other got `correct: false`. Students who selected the mathematically correct answer were marked wrong.

**Rule:** All expression strings built from arrays of formatted numbers MUST use `joinExpr()` — which sorts numerically descending (largest place first) before joining. Never use `[...parts].sort().join(" + ")` directly. The only safe pattern is `joinExpr([...parts])`.

**The fix:** Added `sortExprParts(arr)` (numeric-descending sort) and `joinExpr(arr)` (sort + join) helper functions. All 8 call sites in the regrouped_equivalent and regrouped_near_miss generators were updated to use `joinExpr()`.

**Catching check:** `grep 'sort().join(" + ")'` in the HTML must return zero results. Any hit is a violation.

**Why it also affects dedup:** When `canonicalForm` and `wrongMissing` represent the same value but in different string order, `unique()` keeps both, making `raw.length === 5` appear to succeed when it shouldn't — or making a correct answer appear as a wrong choice. After the fix, both use the same normalized order, `unique()` correctly deduplicates them, `raw.length < 4` triggers `return null`, and the generator retries with a different number.

### INVARIANT L-12 — Never disable ALL buttons during answer advancement
**Bug found:** `advanceToNextItem()` used `querySelectorAll("button.choice, button")` to disable buttons during the 900ms transition delay. The `, button` part grabbed every button on the page — including the win overlay's "Keep Playing" button. The win overlay appeared but was completely dead because its button was disabled before it rendered.

**Rule:** Button-disable sweeps during item transitions MUST scope to `button.choice` only. Overlay buttons, language toggle, read-aloud, and teacher panel buttons must never be included in transition disabling.

**Catching check:** `grep 'querySelectorAll.*button.choice.*button'` must return zero results. The correct pattern is `querySelectorAll("button.choice")`.

### INVARIANT L-13 — evaluateChoiceText must cover every templateId that uses it
**Bug found:** `evaluateChoiceText()` handled `compose_from_units_mc_v1` but not `mc_v2`. The `unit_language_to_standard` family uses `mc_v2` exclusively. So `symbolicValidateItem` called `evaluateChoiceText`, got `false` for every choice (the function returned `false` as default), and every item from `unit_language_to_standard` failed the exclusivity check. The Word Units stamp never lit because no `unit_language_to_standard` item ever survived validation.

**Rule:** Every templateId that generates items of a specific type must have a matching case in `evaluateChoiceText()`, OR the templateId must use a different validator path that handles its choice type correctly. Never add a new templateId to `symbolicValidateItem`'s dispatch without confirming `evaluateChoiceText` handles it.

**Catching check:** For every templateId in `compose_from_units_mc_*` family: verify `evaluateChoiceText` has a case for it. The function must not fall through to `return false` for any active templateId.

### INVARIANT L-14 — wrongMissing in the regrouped MC path must never equal canonicalForm
**Bug found (second instance, same session):** The MC path used `wrongMissing = joinExpr(others + [splitPart.value])`. Since `others` = all parts except the split part, adding `splitPart.value` back reconstructs the original canonical decomposition. `wrongMissing` was **always** identical to `canonicalForm` — a mathematically correct expression being treated as a wrong answer. Every student who selected the canonical form got marked wrong.

**Why it persisted after the joinExpr fix:** The previous fix (L-11) ensured expression strings are consistently ordered, which fixed the false-dedup issue in the multiselect path. But the MC path structurally always produced canonicalForm as wrongMissing — a design error, not just an ordering bug.

**Rule:** In any regrouped decomposition MC item, every wrong-answer choice must evaluate arithmetically to a value ≠ targetNumber. `others + [splitPart.value]` always rebuilds the target number — it is never a valid distractor. Replace with partial-regroup distractors: `others + [splitA]` (missing splitB, sum < target) and `others + [splitB]` (missing splitA, sum < target). Build a 5-candidate pool and take first 4 unique.

**Additional safety check:** After building `raw`, verify all wrong choices evaluate to ≠ rNumber: `wrongChoices.some(c => safeEvalArithmetic(c) === rNumber)` → return null if any match.

**Catching check:** In the MC path of `released_regrouped_equivalent_decomposition`, grep for `formatNumber(splitPart.value)` — must return zero results. Any use of splitPart.value as a standalone term in the distractor pool is suspect.

### INVARIANT L-15 — All wrong choices in any expression-based item must be verified against the target number
**Bug found (audit):** `released_regrouped_near_miss_decomposition` had `wrong3 = ps.map(p => formatNumber(p.value)).join(" + ")` — unordered canonical form. Same bug class as L-11. Wrong3 and `correct` (which uses `joinExpr`) had the same values in different string orders. `unique()` kept both. `wrong3` appeared as a wrong answer in the choices but evaluated to the correct answer. 376 out of 500 simulated items had a correct answer marked wrong.

**Rule:** Every expression-based generator must: (1) use `joinExpr()` for ALL expression strings, (2) include a safety eval check after building `raw`: `if (raw.some(c => c !== correctAnswer && safeEvalArithmetic(c) === targetNumber)) return null`. This is the catching check that blocks any correct answer from appearing as a wrong choice.

**Catching check:** For every family that generates expression-string choices: after building `raw`, run the safety eval. It is not enough to use `joinExpr` consistently — near-miss arithmetic can accidentally produce the correct total. The eval check is the final gate.

---

# APPENDIX A — 3.2A RESEARCH ANNEX
## 2025–2026 STAAR Grade 3 Math: TEKS 3.2A Evidence Report
**Research date:** 2026-04-19
**Sources:** TEA Spring 2025 answer key (verified), TEA Spring 2025 rationale PDF (verified), ESC Region 13 2025-2026 blueprint breakdown PDF (verified), TEA STAAR redesign item type guidance (ESC Region 13, verified), 2024 STAAR Grade 3 Math answer key (Scribd, verified), TEA HB 3906 redesign documentation.

---

## A1 — TEKS 3.2A Standard (Unchanged)

TEKS 3.2A: *Compose and decompose numbers up to 100,000 as a sum of so many ten thousands, so many thousands, so many hundreds, so many tens, and so many ones using objects, pictorial models, and numbers, including expanded notation as appropriate.*

**Status:** Standard text is UNCHANGED for 2025-2026. The skill tested is identical to prior years.

**What changed:** Not the standard. The assessment format, point structure, and item type mix changed under HB 3906 (effective 2022-23). Those changes are now mature and stable for 2025-2026.

---

## A2 — 2025-2026 Blueprint Facts (Verified from ESC Region 13 PDF)

**Grade 3 Math totals:**
- 30 questions, 37 total points
- Reporting Category 1 (Numerical Representations and Relationships): **4 standards, 10 questions**
- 1-point questions: 23 (76.7%) — multiple choice AND non-multiple choice
- 2-point questions: 7 (23.3%) — non-multiple choice only
- 75% MC cap is met: ~76.7% are 1-point (but not all 1-point are MC)

**3.2A position:** RC1, Readiness Standard. Blueprint weight is not published per-SE, but RC1 holds 10 of 30 questions total. 3.2A is a Readiness standard, meaning it receives greater emphasis and appears on every test.

**Evidence floor for 3.2A:** At minimum 1-2 items per test form, possibly 2-3 given it is the anchor Readiness SE of RC1.

---

## A3 — Released Item Evidence (2023–2025, Verified)

The STAAR answer key uses an internal numbering format: `3.X.Y.Z` where X=RC, Y=standard cluster, Z=SE. TEKS 3.2A maps to `3.1.2.A` in this system.

### Spring 2025 — 3.2A Items Confirmed

| Item | Type | Points | Status |
|------|------|--------|--------|
| 1 | **Multiselect** | 2 | Readiness, RC1 — verified TEKS 3.1.2.A |
| 24 | **Multiple Choice** | 1 | Readiness, RC1 — verified TEKS 3.1.2.A |

**Item 1 rationale (verified from TEA PDF):** "Which expressions are equivalent to 15,090?" — 5 choices, select 2 correct. Correct answers: `15,000 + 90` and `10,000 + 5,000 + 90`. Distractors target ten-thousands/thousands confusion (place misalignment) and tens/hundreds confusion. This is a **multiselect** item worth 2 points, scored with partial credit possible.

**Item 24 rationale (verified from TEA PDF):** "70 hundreds, 1 ten, 15 ones — what is Evie's sum?" Answer: 7,025. Distractors: 70,025 (hundreds→thousands confusion), 70,115 (no place value conversion), 7,015 (1 ten absorbed into 15 ones). This is a **unit overflow compose** item — a student is given unit counts that don't fit canonical digit values and must convert/compose correctly.

### Spring 2024 — 3.2A Items Confirmed

| Item | Type | Points | Status |
|------|------|--------|--------|
| 30 | **Drag and Drop** | 2 | Readiness, RC1 — verified TEKS 3.1.2.A |

**Item 30 rationale:** Place value label mapping — drag "ten thousands," "hundreds," "tens" to correct positions. 2-point item. This is the exact item type the engine's `teacher_forensic_place_label_mapping` / `decomposition_dragdrop_v1` family was built to address.

### Observed 3.2A Item Type Distribution (2023–2025)

| Year | Item Types Observed on 3.2A Items |
|------|----------------------------------|
| 2023 | Multiple Choice (confirmed); Multiselect (inferred from redesign launch) |
| 2024 | Multiple Choice, **Drag and Drop** (2-point, verified) |
| 2025 | **Multiselect** (2-point, verified), Multiple Choice (1-point, verified) |

**Pattern:** Every year since 2022-23 has included at least one non-MC item for 3.2A. The item types rotate — drag-and-drop in 2024, multiselect in 2025.

---

## A4 — Item Types Available for 3.2A on STAAR Grade 3 Math (Verified)

Per TEA item type guidance and confirmed released items:

| Item Type | Available Gr 3 Math | Seen on 3.2A | Points | Notes |
|-----------|-------------------|--------------|--------|-------|
| Multiple Choice | ✅ YES | ✅ YES (every year) | 1 | Baseline, always present |
| Multiselect | ✅ YES | ✅ YES (2025 confirmed) | 2 | Select 2 correct from 5 options |
| Inline Choice (dropdown) | ✅ YES | ⚠️ INFERRED | 1-2 | Not confirmed on 3.2A specifically, confirmed on other RC1 standards |
| Drag and Drop | ✅ YES | ✅ YES (2024 confirmed) | 2 | Place label mapping confirmed |
| Hot Spot | ✅ YES | ⚠️ INFERRED | 1-2 | Confirmed on geometry (RC3); plausible for 3.2A place value diagrams |
| Equation Editor | ✅ YES | ⚠️ INFERRED | 1-2 | Confirmed on other math RCs; plausible for standard-form entry |
| Match Table Grid | ❌ NOT Gr 3-5 | ❌ NO | — | Grade 6-8 and EOC only per TEA guidance |
| Short Constructed Response | ✅ YES (any) | ⚠️ INFERRED | 2 | No confirmed 3.2A SCR in released items yet |
| Extended Constructed Response | ❌ RLA only | ❌ NO | — | Not on math |
| Graphing | ✅ YES (math) | ❌ UNLIKELY | — | No plausible 3.2A graphing format identified |
| Number Line | ✅ YES (math) | ❌ UNLIKELY | — | 3.2A does not naturally lend to number line placement |

**Confirmed for 3.2A:** Multiple Choice, Multiselect, Drag and Drop.
**Inferred / plausible:** Inline Choice, Hot Spot, Equation Editor, Short Constructed Response.
**Ruled out:** Match Table Grid (grade band restriction), ECR (RLA only), Graphing, Number Line.

---

## A5 — Engine Coverage Matrix vs. Released Evidence

| Engine Family | 3.2A Format Covered | Released Item Evidence | Status |
|--------------|--------------------|-----------------------|--------|
| unit_language_to_standard | Word-unit → standard MC | Yes — Item 24, 2025 (unit overflow variant) | ✅ Verified |
| expanded_form_to_standard | Expanded form → standard MC | Yes — historical pre-2023 items | ✅ Verified |
| standard_to_expanded_form | Standard → expanded form MC | Yes — historical | ✅ Verified |
| standard_to_expanded_notation | Standard → notation MC | Yes — historical | ✅ Verified |
| released_unit_overflow_compose | Unit overflow (70 hundreds, etc.) MC | Yes — Item 24, 2025 directly | ✅ Verified |
| released_equivalent_expression_multiselect | Multiselect equivalent expressions | Yes — Item 1, 2025 directly | ✅ Verified |
| teacher_forensic_place_label_mapping (drag-drop) | Drag-drop place labels | Yes — Item 30, 2024 directly | ✅ Verified |
| released_regrouped_equivalent_decomposition | Regrouped equivalent (MC + MS) | Pre-2023 released items | ✅ Verified (historical) |
| released_regrouped_near_miss_decomposition | Near-miss MC | Pre-2023 released items | ✅ Verified (historical) |
| released_error_analysis_compose | Error analysis MC | Pre-2023 released items | ✅ Verified (historical) |
| released_truth_judgment_compose | Truth/NOT judgment MC | Pre-2023 released items | ✅ Verified (historical) |
| released_cross_representation_mismatch | Cross-rep mismatch MC | Inferred from standard | ⚠️ Inferred |
| released_select_correct_notation | Select notation (dual direction) | Historical + inferred | ⚠️ Inferred |
| released_expanded_notation_discrimination | Notation vs. form discrimination | Historical + inferred | ⚠️ Inferred |
| missing_part_compose | Missing part MC | Historical | ✅ Verified (historical) |
| digit_value_compose | Digit value MC | Historical | ✅ Verified (historical) |
| equivalence_compose | Equivalent expression multiselect | Similar to Item 1, 2025 | ✅ Verified (parallel) |
| teacher_forensic_partial_plausible_multiselect | Partial plausible trap MS | Pre-2023 trap items | ✅ Verified (historical) |

**NOT YET IMPLEMENTED — Gap families identified from research:**

| Missing Format | Item Type | Evidence | Priority |
|---------------|-----------|----------|----------|
| Inline Choice (dropdown select) | Inline Choice | Confirmed on 3.2B, 3.1.2 items in released tests; inferred for 3.2A | **HIGH** |
| Text Entry / Equation Editor | Equation Editor | Confirmed on other RC math items; plausible for 3.2A standard-form entry | MEDIUM |
| Hot Spot (select place position) | Hot Spot | Confirmed on geometry; plausible for 3.2A place chart | LOW |

---

## A6 — Misconception Map (Verified from TEA Rationale PDFs)

TEA publishes explicit misconception rationales for every released item. The following are confirmed from the 2025 rationale PDF for 3.2A items.

**From Item 1 (2025, Multiselect 15,090):**
| Distractor | Misconception | TEA Language |
|-----------|--------------|-------------|
| 1,000 + 5,000 + 900 | ten-thousands digit read as 1 thousand; tens digit read as 9 hundreds | "misinterpreted the digit in the ten-thousands place as 1 thousand and the digit in the tens place as 9 hundreds" |
| 1,000 + 5,000 + 90 | ten-thousands digit read as 1 thousand only | "misinterpreted the digit in the ten-thousands place as 1 thousand" |
| 15,000 + 900 | tens digit read as 9 hundreds | "misinterpreted the digit in the tens place as 9 hundreds" |

**From Item 24 (2025, MC unit overflow 7,025):**
| Distractor | Misconception | TEA Language |
|-----------|--------------|-------------|
| 70,025 | hundreds → thousands confusion (70 hundreds = 70 thousands) | "confused 70 hundreds with 70 thousands and multiplied 70 by 1,000" |
| 70,115 | no conversion, digits placed in order given | "did not consider the place values of the given numbers and placed the digits in the order they were given" |
| 7,015 | 15 ones decomposed as 1 ten + 5 ones, absorbed 1 ten from problem | "understood that '15 ones' represents 15 and determined that the 1 in 15 represents the '1 ten' in the problem" |

**Confirmed misconception taxonomy (verified cross-reference with engine families):**

| Misconception | Verified in TEA Rationales | Engine Family Targeting It |
|--------------|--------------------------|--------------------------|
| place_value_misalignment (tens↔hundreds, etc.) | ✅ Yes — Items 1, 24 (2025) | unit_language_to_standard, released_truth_judgment, released_cross_representation |
| unit_to_digit_confusion (70 hundreds → 70 thousands) | ✅ Yes — Item 24 (2025) | released_unit_overflow_compose |
| partial_decomposition_acceptance (missing a place) | ✅ Yes — Item 1 (2025) | equivalence_compose, regrouped families |
| digit_concatenation (ignoring place, stringing digits) | ✅ Yes — Item 24 (2025 "70,115") | unit_language_to_standard (concat distractor) |

---

## A7 — 2025-2026 SOP Update Checklist (Action Items)

Items confirmed needed based on this research:

**CONFIRMED GAPS (implement):**
- [ ] `inline_choice_place_value` family — Inline Choice item where student selects correct place value term or expression from dropdown. Confirmed available for Gr 3 math, confirmed on nearby 3.2 standards, not yet in engine. High priority.
- [ ] `equation_editor_standard_form` family — Student enters standard form of a number given expanded form or unit description. Confirmed available for Gr 3 math. Medium priority.

**PROCESS ADDITIONS (add to SOP):**
- [ ] Research provenance section — each family should have: evidence source, year verified, item type confirmed, release date. Template:
  ```
  Family: [name]
  Evidence: [TEA item year + item position]
  Item type: [MC / Multiselect / Drag-drop / etc.]
  Last verified: [date]
  Status: [Verified / Inferred / Deprecated]
  ```
- [ ] TEA update trigger — when TEA releases a new test (typically each spring), the SOP must be re-seeded with the new answer key and any new 3.2A items cross-referenced against the family coverage matrix.
- [ ] Partial credit flag — multiselect and drag-drop items award 2 points with possible partial credit. Engine should track whether student got both correct answers in a multiselect vs. only one, since TEA awards 1 point for partial credit on 2-point items.
- [ ] Grade-3-only guardrail — Match Table Grid, ECR, and Number Line are NOT available on Grade 3 Math per TEA guidance. These must never be added to the engine as a 3.2A family.

**CONFIRMED CORRECT (no change needed):**
- ✅ Multiple Choice coverage — strong, verified
- ✅ Multiselect coverage — verified against 2025 Item 1 exactly
- ✅ Drag and Drop coverage — verified against 2024 Item 30 exactly
- ✅ Unit overflow family — verified against 2025 Item 24 exactly
- ✅ Misconception map — all 3 pattern names (`place_value_misalignment`, `unit_to_digit_confusion`, `partial_decomposition_acceptance`) match verified TEA rationale language

---

## A8 — Scoring Structure Note (2025-2026)

The engine currently scores all items as pass/fail (correct/incorrect). Real STAAR 2-point items allow partial credit:
- **Multiselect (2-point):** 2 pts for both correct, 1 pt for one correct, 0 for neither
- **Drag and Drop (2-point):** 2 pts for all slots correct, 1 pt for partial, 0 for none
- **Inline Choice (2-point):** Same partial credit structure

The engine does not need to replicate this scoring exactly for practice purposes, but the **student model** should distinguish between "got both" and "got one" in multiselect items for accurate misconception routing. Currently `updateStudentModel` receives a boolean correct/incorrect — consider adding `partialCredit: boolean` field to the telemetry push.

---

## A9 — Source of Truth Registry

| Source | What It Governs | Last Verified | URL |
|--------|----------------|---------------|-----|
| TEA Spring 2025 Gr 3 Math Answer Key | Item types by TEKS, 2025 | 2026-04-19 | tea.texas.gov/…/2025-staar-math-3-answer-key.pdf |
| TEA Spring 2025 Gr 3 Math Rationales | Misconception language, distractors | 2026-04-19 | tea.texas.gov/…/2025-staar-math-3-rationale.pdf |
| ESC Region 13 Blueprint 2025-2026 | Question counts, point structure | 2026-04-19 | esc13.net/assets/…/r13-staar-math-blueprint-2025-2026.pdf |
| ESC Region 13 Item Type Guidance | Item type availability by grade/subject | 2026-04-19 | blog.esc13.net/new-staar-item-types/ |
| TEA STAAR Released Test Questions page | All released forms and sample questions | 2026-04-19 | tea.texas.gov/…/staar-released-test-questions |

