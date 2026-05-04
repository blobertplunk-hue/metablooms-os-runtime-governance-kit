# Video Classifier Heuristic Cartridge v1

## Meta
- **cartridge_id:** `video_classifier_heuristic_v1`
- **name:** Video Classifier Heuristic Cartridge v1
- **type:** routing_validation
- **purpose:** Estimate whether a YouTube video is likely to survive school embed filters in Google Sites and Canvas when direct YouTube access is blocked but some embeds are allowed.
- **execution_mode:** classify
- **status:** draft_active
- **primary_artifact:** `video_embed_likelihood_report`

---

## Why this exists

Some school environments block direct YouTube access but still allow a subset of embedded YouTube videos. In those environments, ordinary video search is not enough. The system needs a classifier that ranks candidates by likely embed survivability before lesson HTML is built.

This cartridge does **not** claim certainty. It is a probability tool. It is designed to:
1. improve the odds,
2. reject obvious bad candidates,
3. narrow testing harnesses,
4. hand off only the strongest candidates to the next stage.

---

## Operational principle

Treat YouTube videos as belonging to one of three classes:

### Class A — High-Likelihood Classroom Embed
Typical profile:
- child-facing or clearly classroom-safe
- simple explainer or read-aloud style
- short
- low controversy
- low moderation complexity
- not a live stream
- not a news segment
- not a press conference
- not breaking-news adjacent

### Class B — Uncertain / Requires Harness Test
Typical profile:
- official organization video
- educational but general-audience
- science/government explainer
- somewhat technical
- moderate runtime
- possible policy complexity
- unclear student-device survivability

### Class C — High-Risk / Reject by Default
Typical profile:
- news broadcast
- live stream or replay of live stream
- launch coverage
- press briefing
- mixed-content channel
- commentary/reupload
- sensational thumbnail/title
- current-events framing
- long runtime
- unclear ownership

---

## Inputs

### Required
- `topic`
- `target_audience`
- `delivery_context`

### Optional
- `candidate_videos`
- `school_constraints`
- `known_pass_examples`
- `known_fail_examples`

---

## Output artifact

`video_embed_likelihood_report`

Must include:
- candidate list
- heuristic feature table
- weighted scores
- class assignment
- approval / reject / test-first verdict
- confidence note
- recommended next step

---

## Delivery context assumptions

Default intended environment:
- student iPads
- Google Sites
- Canvas
- direct YouTube watch pages blocked
- some embedded YouTube videos allowed

---

## Hard rejection gates

Reject candidate immediately if any are true:

1. **Ownership ambiguous**
   - reupload
   - aggregator
   - clipped copy
   - unofficial mirror

2. **Broadcast/live profile**
   - live stream
   - launch coverage
   - event replay
   - press conference
   - TV segment

3. **Policy complexity too high**
   - current events framing
   - news-style packaging
   - heavy comments/culture-war bait feel
   - mixed audience signaling

4. **Runtime too long for elementary inquiry**
   - over 10 minutes by default unless there is strong evidence it still behaves like classroom-safe explainer content

5. **Sensational packaging**
   - fear language
   - hype language
   - dramatic all-caps headlines
   - clickbait phrasing

---

## Positive heuristic features

Each feature adds to likelihood score.

### H1 — Child-safe channel identity
Examples:
- read-aloud channel
- elementary educational channel
- museum/science kids content
- teacher-made kid explainer

Score:
- strong = +3
- moderate = +2
- weak = +1
- absent = 0

### H2 — Animation / visual explainer format
- heavily animated
- simple visual storytelling
- diagram-first
- less like a broadcast

Score:
- strong = +2
- moderate = +1
- absent = 0

### H3 — Short runtime
- 0–4 min = +3
- 4–6 min = +2
- 6–8 min = +1
- 8–10 min = 0
- over 10 min = -2

### H4 — Kid-facing title language
Signals:
- simple wording
- explanatory phrasing
- not breaking-news tone
- not “watch live,” “launch,” “coverage,” “breaking”

Score:
- strong = +2
- moderate = +1
- absent = 0

### H5 — Narrow concept focus
- one concept
- one question
- one visual story

Score:
- strong = +2
- moderate = +1
- absent = 0

### H6 — Low moderation complexity
Signals:
- evergreen
- non-political
- non-news
- non-debate
- non-commentary

Score:
- strong = +3
- moderate = +1
- absent = 0

### H7 — Similarity to known pass examples
Compare against videos already known to work in the district:
- read-aloud type
- child-safe formatting
- low complexity
- calm thumbnails/titles

Score:
- high similarity = +4
- moderate = +2
- low = 0

---

## Negative heuristic features

### N1 — Official but general-audience institutional video
Examples:
- NASA general mission brief
- agency explainer aimed at all ages

Score:
- mild risk = -1

### N2 — Science/government technical framing
- crewed mission overview
- operations-focused explainer
- technical mission graphics with general-audience tone

Score:
- moderate risk = -2

### N3 — Broadcast/news/event framing
- press tone
- newsroom style
- “launch day”
- “coverage”
- “live”
- “watch”

Score:
- strong risk = -4

### N4 — Long-form institutional media
- panel
- press event
- briefing
- mission special

Score:
- strong risk = -4

### N5 — Mixed-content channel
- educational sometimes, commentary sometimes
- unclear moderation posture

Score:
- moderate risk = -3

---

## Scoring model

Start at `0`.

Add positive and negative features.

### Final thresholds
- **8 or above** → `CLASS_A_HIGH_LIKELIHOOD`
- **4 to 7** → `CLASS_B_TEST_FIRST`
- **3 or below** → `CLASS_C_REJECT_DEFAULT`

---

## Confidence model

### High confidence
Use only when:
- multiple strong positive features
- no hard rejection gates triggered
- high similarity to known passing videos

### Medium confidence
Use when:
- candidate has mostly positive features
- some uncertainty remains

### Low confidence
Use when:
- sparse evidence
- mixed signals
- weak pass similarity

---

## Required output schema

```json
{
  "topic": "",
  "delivery_context": {
    "platforms": ["Google Sites", "Canvas"],
    "device": "student_iPad",
    "youtube_watch_pages_blocked": true,
    "embedded_youtube_partially_allowed": true
  },
  "known_pass_profile": [],
  "candidates": [
    {
      "title": "",
      "channel": "",
      "url": "",
      "features_positive": [],
      "features_negative": [],
      "hard_rejects": [],
      "score": 0,
      "class": "CLASS_A_HIGH_LIKELIHOOD | CLASS_B_TEST_FIRST | CLASS_C_REJECT_DEFAULT",
      "confidence": "high | medium | low",
      "verdict": "approve_for_harness | reject | reserve"
    }
  ],
  "recommended_next_step": ""
}
```

---

## Decision table

| Condition | Result |
|---|---|
| Any hard rejection gate triggered | Reject |
| Score >= 8 and no hard reject | Approve for harness |
| Score 4–7 and no hard reject | Test first |
| Score <= 3 | Reject default |
| No Class A candidates found | Hand off strongest Class B set to harness |
| No Class A or B candidates found | Fail closed and request alternate media strategy |

---

## Stage routing

### Stage VC0 — Context Lock
Input:
- topic
- student age
- platform constraints

Output:
- `video_classifier_context_packet`

### Stage VC1 — Candidate Intake
Input:
- search results / user candidates

Output:
- `video_candidates_unscored`

### Stage VC2 — Heuristic Classification
Input:
- candidate list
- known pass examples

Output:
- `video_embed_likelihood_report`

### Stage VC3 — Harness Recommendation
Input:
- scored candidates

Output:
- `video_harness_candidate_pack`

### Stage VC4 — Final Lesson Embed Set
Input:
- manually verified winners

Output:
- `video_embed_approved_set`

---

## Pass / fail validators

### Pass validators
- every candidate has title, channel, url
- every candidate has score
- every candidate has class
- every candidate has verdict
- no approved candidate triggers hard rejection

### Fail validators
- missing score field
- missing class field
- candidate approved despite hard reject
- narrative-only output without structured artifact
- claims of certainty instead of probability

---

## Candidate scoring template

```json
{
  "title": "",
  "channel": "",
  "url": "",
  "features_positive": [
    {"feature": "", "score": 0, "evidence": ""}
  ],
  "features_negative": [
    {"feature": "", "score": 0, "evidence": ""}
  ],
  "hard_rejects": [],
  "score": 0,
  "class": "",
  "confidence": "",
  "verdict": ""
}
```

---

## Final handoff packet format

```json
{
  "artifact": "video_embed_likelihood_report",
  "summary": "",
  "approved_for_harness": [],
  "reserve_candidates": [],
  "rejected_candidates": [],
  "known_pass_pattern": [],
  "recommended_next_step": "EXECUTE: VC3 — Harness Recommendation",
  "next_required_input": {
    "target_topic": "",
    "max_candidates": 3
  },
  "next_recommended_cartridge": "video_harness_builder_v1",
  "execution_ready": true
}
```

---

## Usage note for Artemis-like topics

For mission/space topics, prefer:
- animated explainers
- kid-facing concept videos
- short crew/story intros
- single-concept visuals

Avoid:
- launch coverage
- agency event videos
- long mission overview briefings
- press media packages

---

## Key governance rule

This cartridge is a **probability optimizer**, not a guarantee engine.

It may approve a candidate for **harness testing**.
It may not claim:
- guaranteed embed success
- district allowlist certainty
- verified classroom playback

Final approval requires real device/platform confirmation.

---

## Recommended companion cartridges
- `video_harness_builder_v1`
- `video_embed_survivability_logger_v1`
- `lesson_media_router_v1`
