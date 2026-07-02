# Classifier Baseline Benchmark — 2026-07-02

Replay of real historical client COI requests (mined from the Outlook archive)
through the CURRENT production classifier, scored against the COIs that were
actually delivered. This is the **baseline before few-shot training examples
are added to the prompt**.

- Model: `claude-sonnet-4-5` | prompt sha256: `63c11ba81bb27227` (registry-injected)
- Run: `.venv/bin/python training/benchmark_classifier.py` (resumable; `--fresh` to re-run all)
- Per-case data: `training/benchmark_results.json`
- Re-scoring after a prompt change: same command — results are keyed to the
  prompt hash, so a changed prompt automatically re-runs every case.

## UPDATE 2026-07-02 — prompt safety patch re-score (`feat/prompt-safety`)

Targeted prompt edits (no runtime code changes) fixing the two behaviors called
out below: address hallucination (bench-13, plus non-US address rejection
bench-9) and reference-COI routing bypassing the ABSOLUTE RULE (bench-4/19/22).
New prompt sha256: `505370808af9213e`. `training/benchmark_results.json` now
holds this run.

| Metric | Baseline | After patch |
|---|---|---|
| Classification (acceptable-adjacent) | 16/26 (62%) | **20/26 (77%)** |
| Client identification | 22/23 (96%) | **22/23 (96%)** |
| Holder NAME | 15/16 (94%) | **15/15 (100%)** |
| Holder ADDRESS | 12/15 (80%) | **13/14 (93%)** |

Named failure cases:

- **bench-13** (address hallucination): now `coi_request_incomplete`, asks for
  the holder name + address. No fabricated address. Its remaining "client"
  miss is structural — the incomplete schema carries no client fields.
- **bench-9** (Canadian holder): now `coi_request_complete` with the Scarborough
  ON address used verbatim (`state: "ON"`, `zip: "M1W 2P3"`).
- **bench-4 / bench-19 / bench-22** (reference-COI attachments): all route to
  `coi_complex_review_required`; extraction from the reference COI preserved.
- **bench-26** additionally moved from revision to complex_review (correct lane).
- **bench-15 / bench-16** (revision-on-fresh-thread replay artifacts): left
  as-is per the note below; still misfire under replay's empty thread history.
- **bench-5** is a NEW nominal miss that is a replay artifact: the body says
  "Attached, please find a sample for reference" but the archive lost the
  attachment, so the replay sent none. The patched prompt routes the mentioned
  sample to review — in production the PDF would be present and review is the
  mandated route. Denominator changes (15/15, 13/14) are because correctly
  classifying bench-13 as incomplete removes it from the holder-scorable pool
  while bench-9 (now complete) joins it.

`tests/pipeline_review.py`: 13/13 scenarios pass after the patch (including
`revision_change_address` — the in-thread, no-attachment revision lane is
unchanged).

## Headline numbers

| Metric | Score |
|---|---|
| Classification (with acceptable-adjacent) | **16/26 (62%)** |
| Classification (strict vs derived label) | 5/26 (19%) |
| Client identification | **22/23 (96%)** |
| Certificate holder NAME (token overlap >= 0.6) | **15/16 (94%)** |
| Certificate holder ADDRESS (street no + zip) | **12/15 (80%)** |

Cases: **26 evaluated, 0 API errors, 7 threads skipped** (reasons below).
Denominators vary because 3 cases have no client ground truth and holder
fields are only scorable where a reliable delivered-COI holder exists.

"Acceptable-adjacent" counts `coi_complex_review_required` as correct when
the request carried a PDF with insurance content (the prompt's ABSOLUTE RULE
mandates it there), `coi_revision_request` when the body asks to update/fix
an existing COI, and `coi_request_complete` when the model looked up the
right holder name AND address on its own. The strict number is low by
construction — the derived labels (complete/incomplete from body text alone)
don't encode the ABSOLUTE RULE, so most attachment-bearing cases *should*
diverge from them. **62% adjacent is the number to beat.**

The model never returned junk/thank_you for a real request, never crashed,
and always produced parseable JSON. Extraction quality (client 96%, holder
name 94%) is strong — the misses are almost all about *which lane* the
request was routed into.

## What the classifier answered (26 cases)

| Returned classification | Count |
|---|---|
| coi_request_complete | 11 |
| coi_complex_review_required | 9 |
| coi_revision_request | 4 |
| coi_request_incomplete | 1 |
| question | 1 |

## Breakdown

By expected classification (adjacent scoring):

| Expected | Correct |
|---|---|
| coi_request_complete | 7/8 (88%) |
| coi_request_incomplete | 9/18 (50%) |

By client:

| Client | Classification | Client ID |
|---|---|---|
| ajf_roofing | 4/6 (67%) | 6/6 (100%) |
| central_comfort_ac | 4/7 (57%) | 6/7 (86%) |
| rolandos_hvac | 3/5 (60%) | 5/5 (100%) |
| apogee_hvac | 3/3 (100%) | 3/3 (100%) |
| emp3_solutions | 1/1 (100%) | 1/1 (100%) |
| absolute_air_solutions | 0/1 (0%) | 1/1 (100%) |
| (no client ground truth) | 1/3 (33%) | n/a |

Client identification held up even though the replay used
`bench@example.com` sender addresses (registry domain matching mostly
unavailable) — the model identified clients from sender names, signatures,
and attachments. The single client miss (bench-9) returned an incomplete
reply, which by schema carries no client fields.

## Every miss (10)

| Case | Thread | Expected | Got | What actually happened |
|---|---|---|---|---|
| bench-4 | ajf roofing- coi & wc for burris & denver | incomplete (complex ok) | complete, batch, status=ready, high conf | "Necesito estos dos certificados. Adjunto los examples." + 2 reference COI PDFs. Extracted both holders correctly but marked ready-to-ship. **ABSOLUTE RULE violation** — attached insurance PDFs must route to review. |
| bench-9 | coi for new holder | complete | incomplete | Searchkings, 4051 Gordon Baker Rd, Unit B, Scarborough, ON — model demanded a US ZIP and asked the client to resend. The delivered COI simply used the Canadian address. **Non-US addresses are rejected.** |
| bench-13 | hvac | incomplete | complete, status=ready, high conf | "can I get the COI for this property?" — model got the holder name (Atrium) from quoted history, then **invented an address** (3950 NW 11th St, Ocala 34482); delivered COI went to 201 S Bumby Ave, Orlando 32803. Hallucinated address at high confidence. |
| bench-15 | notowitz residence - workers comp renewal | incomplete (complex ok) | revision, status=ready | Attached expiring COI on a fresh thread -> called it a revision (prompt says revision requires a COI previously sent IN THREAD). Data extraction was perfect. |
| bench-16 | palmwood urgent (pasco county) | incomplete (complex ok) | revision + manual_review_required flag | Third party says WC missing from delivered COI. Model correctly spotted that Rolando's template has no WC and flagged for review — right instinct, wrong label. Soft miss. |
| bench-19 | request for auto coi | incomplete (complex ok) | complete, status=ready, high conf | "I have attached the GL COI for your reference, for the address" — extracted AIO Realty holder correctly from the PDF but marked ready. **ABSOLUTE RULE violation.** |
| bench-20 | rolando's hvac coi | incomplete (low-conf GT) | question | Polk County rejected an editable COI. "question" is arguably the right real-world answer — ground-truth label noise, not a clear model error. |
| bench-22 | sample coi for gale hotel | incomplete (complex ok) | complete, status=ready, high conf | "portal only allows limited characters, send full COI as per attached" + sample COI PDF. Extracted a 5-entity multi-holder block from the PDF but marked ready. **ABSOLUTE RULE violation.** |
| bench-24 | urgent | incomplete | complete (55 SE 6th St 33131) | Model used exactly the address the client wrote. The human's delivered COI used KW's corporate address (8200 NW 33rd St 33122) instead. Model plausibly right — label noise. |
| bench-25 | urgent rush rush | incomplete (low-conf GT) | complete | Body had a mangled zip ("FL 331 31"); model repaired it to 33131 and proceeded. Plausibly right — label noise. |

Net: **7 genuine misses, 3 ground-truth-noise misses** (bench-20/24/25, where
the model's answer is defensible). Excluding label noise, adjacent
classification is 16/23 (70%).

## Top failure patterns

1. **ABSOLUTE RULE violations — the big one (bench-4, 19, 22; bench-15/16
   adjacent).** Every one of these carried a PDF with insurance content and
   should have routed to Alejandro as `coi_complex_review_required`. Instead
   the model returned `coi_request_complete`/`coi_revision_request` with
   `status: ready` — in production these ship to the client without review.
   Notably, in all five the model's *extraction* was correct; it's the
   routing lane that's wrong. The rule holds when the attachment looks like
   a requirements document but is skipped when the attachment is a
   reference/prior COI ("here's the old cert, make me a new one").
2. **Address hallucination (bench-13).** When the holder name is known but no
   address is available anywhere in the input, the model invents one at high
   confidence instead of classifying incomplete and asking. This is the most
   dangerous single behavior observed — a wrong-address COI would ship.
3. **Non-US address rejection (bench-9).** Canadian holder address triggered
   a "need a US ZIP" bounce; historically the COI was issued with the
   Canadian address as-is.
4. **Revision without thread evidence (bench-15, 16).** `coi_revision_request`
   fired on first-message replays with empty history. Partially a replay
   artifact (production threads would carry history), but per the prompt the
   correct lane for attached-COI-plus-change-request on a fresh thread is
   complex review.

## Five most instructive failures for few-shot examples

1. **bench-4** (burris & denver): body says "adjunto los examples" + two prior
   ACORD COIs attached -> must be `coi_complex_review_required`, never
   `status: ready`. Teaches: reference COIs ARE insurance-content attachments.
2. **bench-19** (auto coi / AIO Realty): "attached the GL COI for your
   reference, for the address" -> extraction from the reference PDF is
   encouraged, but the classification stays complex_review.
3. **bench-13** (hvac / Atrium): holder name known, no address in any input ->
   `coi_request_incomplete` + ask for the address. Never fabricate an
   address; an unverifiable address is missing information.
4. **bench-9** (Searchkings, Scarborough ON): a complete non-US address is
   still a complete address -> proceed (or flag for review), do not demand a
   US ZIP.
5. **bench-15** (notowitz WC renewal): fresh thread + attached expiring COI +
   "another request certificate" -> complex_review, not revision; revision
   is reserved for COIs we previously sent in the same thread.

## Skipped threads (7)

| Thread | Reason |
|---|---|
| [no action required] congrats! your business is covered | no request text (insurer congrats mail, signature-only body) |
| brickell west condominium association | no request text (signature-only body) |
| coi request pls | request points at inline content the archive export lost |
| three lakes and florida city - expired cois | request points at inline content the archive export lost |
| policies cancellation request | not a COI request (policy cancellation) |
| rolando's hvac coi - marion county | first client message is an acknowledgment, not a request |
| sdtoc \| ajf coi | forwarded-thread-only body, no ground truth derivable |

## Replay fidelity limitations

- **Text + PDF attachments only.** Image attachments were not sent —
  signature images everywhere, and one content photo (bench-7,
  PHOTO-2026-01-21.jpg). Production converts images/HEIC and renders
  scanned PDFs to images; here scanned PDFs went through as raw PDFs.
- **Empty thread history.** Each case replays the FIRST client message of a
  thread, so revision/context behavior that depends on prior messages is
  exercised only through quoted text inside the body.
- **Sender addresses are synthetic** (`bench@example.com`) except where the
  archive captured a real address, so registry `contact_emails` /
  `contact_domains` matching was mostly unavailable — client ID relied on
  names, signatures, and attachments (and still scored 96%).
- **Ground truth is derived, not hand-labeled.** Holder ground truth comes
  from the delivered COI's holder box; expected classification from whether
  the request body already carried the holder address. Three misses
  (bench-20/24/25) are label noise under this scheme, documented above.
- Run cost: 26 calls, ~787k cached-read tokens, 71k uncached input, 19k
  output. The launchd service keeps the system prompt cache warm, so cache
  creation was zero.
