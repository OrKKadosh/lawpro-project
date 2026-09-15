---
name: timeline-check
description: Validate a generated timeline against the chronos schema before it is sent to /v1/summarize
---
# Timeline validation

Before calling `POST /v1/summarize/{A|B|C|D}` with any timeline:

1. Run `python -m chronos.timeline check <path-to-timeline.json>`.
2. If it fails, do not hand-patch the JSON to force it to pass. Fix the
   extraction prompt or post-processing logic that produced it, then
   regenerate.
3. If it passes, log the case id and timeline path to PROGRESS.md before
   proceeding to the summarizer call.
4. Never submit a timeline with extra/undocumented fields — the schema
   rejects them by design to catch exactly this.
