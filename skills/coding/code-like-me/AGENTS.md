# code-like-me Maintenance Conventions

These conventions govern authoring and subsequent revisions of this skill's documents, including their Chinese
counterparts under `docs/coding/code-like-me/` in this repository.

- Organize content by topic or workflow; do not split it into blanket "recommended" and "absolutely forbidden" sections.
- Explain the expected code structure and reasoning first. State prohibitions against observed mistakes alongside the
  relevant guidance, including their conditions and exceptions.
- Use concise items, each expressing one main judgment. Integrate conditions and exceptions into the item rather than
  using a three-part "expected style / prohibited behavior / applicable boundaries" template.
- For recurring issues such as magic values, redundant checks, mechanical splitting, overengineering, and fallbacks
  that hide errors, place a **Do not** item immediately after the positive guidance. State ordinary rules and simple
  constraints directly; do not mechanically label every rule.
- Positive guidance describes the expected result; prohibitions address specific recurring mistakes. Do not attach a
  prohibition to every recommendation or keep adding prohibitions for hypothetical problems.
- Revise or merge feedback into the existing guidance for its topic. Avoid appending patches, duplicating rules, or
  creating a separate catalog of anti-patterns.
- Explain each issue in its own topic. Keep the final checklist brief rather than repeating detailed guidance.
- Preserve project priorities, interface contracts, and necessary safeguards. Do not turn conditional preferences into
  unconditional bans; use absolute wording only when there are no applicable exceptions.
- When both English and Chinese versions exist, update both in the same change to keep meaning, rule strength, scope,
  exceptions, and example behavior aligned. If the user explicitly requests staged review, update the requested version
  first, report pending synchronization, and synchronize the counterpart in the subsequent stage.
