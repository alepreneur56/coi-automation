# Prompt Integration Plan — few-shot training examples

How the 2 positive examples and 4 negative examples in
`training/library/training_examples.json` should be inserted into
`coi_system_prompt.txt`. This plan does NOT modify the prompt; apply it as a
separate, reviewed edit. Empty buckets this run: requirements_pdf_attached, reference_coi_attached, complex_endorsements, specific_language, spanish.

## Where

Insert ONE new top-level section into `coi_system_prompt.txt`:

- Anchor by SECTION HEADINGS, not line numbers — the prompt is actively
  edited and line numbers drift.
- Place the new section immediately AFTER the `## RULES` section and BEFORE
  `## MULTI-ENTITY CERTIFICATE HOLDER HANDLING`.
- Rationale: at that point every rule the examples exercise has already
  been defined (ABSOLUTE RULE, STEP 0 precedence, ADDRESS LOOKUP, OUTPUT
  FORMAT, RULES), and the examples land before the long PDF-engine
  reference sections. The existing worked examples (ABSOLUTE RULE examples
  1-3, OUTPUT FORMAT examples A-E) stay where they are — the new section
  complements them with real traffic.

## Section skeleton

```markdown
---

## TRAINING EXAMPLES FROM REAL REQUESTS

The following are real historical client requests (bodies cleaned, holder
data verified against the COIs actually delivered and reviewed by
Alejandro). Match their patterns. Dates in these examples are historical;
always use TODAY'S DATE from your input.

### <bucket name in human form, e.g. "Requests with a reference COI attached">

**Example — <client>, <date>**
Subject: ...
Attachments: ...
Body:
<request_context.body>

Correct output:
<expected_output JSON block, verbatim from training_examples.json>

Why: <teaching_point>

### Mistakes to never repeat

These historical requests were mishandled. Never reproduce these outcomes.

- <request one-liner> -> what went wrong: ... -> correct behavior: ...
```

## Framing rules for the edit

1. Copy `expected_output` blocks VERBATIM from training_examples.json —
   they follow the OUTPUT FORMAT schema exactly (including reply_text
   templates and edits_to_make). Do not paraphrase the JSON.
2. Keep bucket order: requirements_pdf_attached, reference_coi_attached, complex_endorsements, specific_language, spanish, vague_or_missing_info, body_only_request.
   Attachment buckets come first — they target the benchmark's top failure
   (ABSOLUTE RULE violations on reference COIs marked ready-to-ship).
3. Negative examples go in as the terse "Mistakes to never repeat" list
   (request one-liner -> what went wrong -> correct behavior), not as full
   JSON.
4. Do not include Alex's raw notes, file hashes, or historical_resolution
   fields in the prompt — they are provenance, kept in
   training_examples.json only.
5. Token budget: 2 examples plus negatives is roughly 4-6k tokens.
   The system prompt is cached (the launchd service keeps it warm), so the
   cost impact is one cache write per deploy. If trimming is needed, drop
   to 2 per bucket starting from body_only_request — per
   BENCHMARK_REPORT.md that is the lane the classifier already handles
   best (88% on coi_request_complete).
6. After integrating, re-run
   `.venv/bin/python training/benchmark_classifier.py` — results are keyed
   to the prompt hash, so all 26 cases re-run automatically. The number to
   beat is 16/26 (62%) adjacent classification; watch specifically for the
   five ABSOLUTE RULE misses (bench-4, 15, 16, 19, 22) flipping to
   coi_complex_review_required.

## Regenerating this library

```
.venv/bin/python training/build_training_library.py \
    --decisions <path to Alex's coi_review_decisions.json>
```

All three outputs are overwritten in place (idempotent, deterministic).
