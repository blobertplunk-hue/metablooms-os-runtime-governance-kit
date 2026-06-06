# TRACKER_RESEARCH_DIGEST_v1

Stage: TRACKER-0 INLINE PROJECT TRACKER RESEARCH AND DESIGN LOCK  
Status: design research complete; no implementation performed.

## Research questions

1. What ChatGPT UI surfaces can support an inline visual project tracker in April 2026?
2. What UX principles should govern progress/status trackers?
3. What accessibility constraints apply to progress/status indicators?
4. What project-status-reporting content belongs in a compact tracker?
5. What must remain artifact-governed rather than inferred from chat memory?

## Evidence digest

### ChatGPT UI capability evidence

- OpenAI Help Center release notes state that ChatGPT added interactive code blocks that allow writing/editing inline, previewing diagrams and mini apps directly in chat, and reviewing code in split-screen views. This supports a future richer prototype, but it does not guarantee a persistent custom widget injected into every response.
  - Source: OpenAI Help Center, ChatGPT Release Notes, February 19, 2026.
- OpenAI Help Center release notes state that ChatGPT Web and Android added exportable visuals from Code Blocks and more visual answers, including at-a-glance visuals. This supports visual response patterns, but inline Markdown remains the lowest-risk portable substrate.
  - Source: OpenAI Help Center, ChatGPT Release Notes, January 30 and February 27, 2026.
- OpenAI Help Center canvas documentation states that canvas is available on Web, Windows, and macOS and is coming soon to mobile platforms. Because the user's target usage is phone-first/Android, canvas cannot be treated as the default enforcement surface.
  - Source: OpenAI Help Center, Canvas FAQ.
- OpenAI Help Center release notes state that Projects can hold chats/files/sources and have project organization capabilities. Projects are useful context containers, but not a deterministic tracker state store without artifact receipts.
  - Source: OpenAI Help Center, ChatGPT Release Notes.

### UX/status tracker evidence

- Nielsen Norman Group's visibility-of-system-status heuristic supports keeping users informed through timely feedback. This maps directly to a tracker header at the start of every governed turn.
  - Source: Nielsen Norman Group heuristic summary.
- Project status report guidance from Atlassian emphasizes concise project progress, risks, blockers, health, and next steps. This maps directly to fields in the tracker block.
  - Source: Atlassian project status report guide.
- Material Design distinguishes determinate progress, where completion percentage is detectable, from indeterminate progress, where duration/completion cannot be specified. This supports the MetaBlooms rule: no progress percent without a known denominator.
  - Source: Material Design progress/activity guidance.

### Accessibility evidence

- W3C/WAI ARIA progress guidance states that range widgets communicate numeric constrained values and that `aria-valuenow` should be omitted when progress is unknown/indeterminate. This supports using textual status instead of fake percentages when the stage denominator is unknown.
  - Source: W3C WAI ARIA APG range-related properties.
- W3C WCAG technique ARIA25 states that progress changes should be conveyed through status text/live regions, because progressbar value changes alone may not be announced. For a chat-only tracker, the accessible equivalent is explicit text labels for status, stage, blocker, and next action.
  - Source: W3C WAI WCAG Technique ARIA25.

## Implications for MetaBlooms

1. The enforced default should be a Markdown/text tracker header, not canvas, custom widgets, or code previews.
2. A future HTML/canvas tracker may be useful, but it must be optional and artifact-derived.
3. The tracker must be generated from `TRACKER_STATE_v1`, receipts, handoff, and stage ledger, not chat memory.
4. Determinate progress is allowed only when `stage_index` and `stage_total` are both known and validated.
5. The tracker should expose blockers and next allowed action before tool execution so the user can interrupt or steer.
