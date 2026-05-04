# TRACKER_MOBILE_REFLOW_POLICY_v1

The inline project tracker is phone-first. It is a status message, not a decorative box.

Policy:
- Render as compact stacked lines.
- Do not use box borders, pipe tables, fixed-width cell padding, or right-side border characters.
- Keep each line at or below 64 characters before ChatGPT wrapping.
- Prefer abbreviated stage names and concise action labels.
- Preserve explicit text labels for status, stage, evidence, blocker, next action, and stop rule.
- Reject fake percentages or determinate bars when the stage denominator is unknown.

Evidence basis:
- User mobile screenshots of TRACKER-4 show broken wrapped box geometry.
- W3C WCAG reflow guidance requires content to remain usable at narrow widths without loss of information/functionality or two-dimensional scrolling.
- ARIA/progress guidance supports explicit status text and avoiding determinate numeric progress when progress is unknown.
