# A9 — Endorsement Documentation Attachments (design)

Built 2026-07-03 on `feat/a9-endorsements`. Everything is behind
`ENDORSEMENTS_ENABLED` in `.env` (default **false** — the live loop's behavior
is bit-for-bit unchanged until Alex flips it).

## What it does

When a COI request (or its attached requirements document) demands endorsement
documentation — Additional Insured endorsement copy, Waiver of Subrogation,
Primary & Non-Contributory wording, notice of cancellation, per-project/
per-location aggregate — the system:

1. **Detects** the demanded endorsement types (`endorsements.py`, pure Python,
   keyword/form-number based, no API calls).
2. **Looks up** what the client actually has on file
   (`coi_endorsement_registry.json`).
3. **Acts** per entry:
   - `blanket` + PDF present in `endorsements/<client_id>/` → **attach** to the
     delivery email (or to the review email in the complex lane).
   - `blanket` but PDF not on file yet → producer note ("drop the PDF in").
   - `scheduled` → **never attached**; a flag says a carrier endorsement
     request is needed (surfaces in the complex-review email body, or in a
     separate internal "Endorsement attention needed" email to
     `PRODUCER_CC_EMAIL` on direct sends).
   - `none` / `unverified` / nothing on file → producer note.

## Data model — why a sibling registry

`coi_endorsement_registry.json`, NOT an `endorsements` array inside
`coi_client_registry.json`. Reason: the client registry is injected verbatim
into **every** classifier API call (`classifier.load_system_prompt()`). ~50
endorsement entries with evidence notes would add thousands of tokens per call
and risk perturbing classification behavior. The endorsement registry is only
read locally by `endorsements.py`.

Entry shape: `endorsement_id`, `type` (5 canonical types), `line`
(GL/Auto/WC/Umbrella/Excess), `status` (`blanket|scheduled|none|unverified`),
`form_number`, `form_title`, `pdf_filename`, `confidence`, `notes`. Data was
lifted from `training/endorsements/endorsement_inventory.json` (the overnight
A9 inventory, incl. the 07-02/07-03 reinstatement confirmations).

## Detection coverage

Types: `additional_insured`, `waiver_of_subrogation`,
`primary_noncontributory`, `notice_of_cancellation`, `per_project_aggregate`.

Sources scanned: `coverage_analysis.required_endorsements` /
`special_language` / `notes`, `review_summary`, and locally-extracted text of
attached requirements docs (PyMuPDF for text PDFs; Word/Excel text reuses
`attachments.py`'s extraction). A plain cert-holder request carries none of
these fields → zero demands → the bread-and-butter path is untouched.

Form families recognized: CG 20 10/37/33/38 (AI-GL), CG 20 01 (PNC-GL),
CG 24 04 / 24 53 (WOS-GL), CG 25 03/04 (per-project agg), CA 20 48 (AI-Auto),
CA 04 44 (WOS-Auto), WC 00 03 13 / WC 04 03 06 (WOS-WC). Line inference from
phrase context commits only when exactly one coverage line is named nearby;
otherwise the demand is line-agnostic (matches all lines of that type — safe
direction: extra blanket proof attached, scheduled still always skipped).

## Hard rules encoded

- **AJF/GAF:** nothing GAF-related exists in any endorsement entry, path, or
  detection rule; the registry and folder README document the prohibition.
  `tests/endorsements_review.py` asserts no endorsement entry and no AJF plan
  output ever references GAF.
- **Rolando's HVAC auto AI/WOS/P&NC = `scheduled`:** the attach logic skips
  scheduled entries unconditionally (even if a PDF file exists on disk) and
  emits a `scheduled_endorsement_carrier_request_needed` flag. The actual
  carrier-request process is a hook only — to be designed with Alex.

## Wiring

- `config.py`: `ENDORSEMENTS_ENABLED` (default false), `ENDORSEMENTS_DIR`.
- `pipeline.decide_action(ai_result, attachments_result=None)` — new optional
  arg (all existing positional callers unaffected); when the flag is on and a
  PDF-producing classification fires, the decision dict gains
  `endorsement_pdf_paths` / `endorsement_flags` / `endorsement_notes` /
  `endorsement_demands`, plus an `endorsements_planned` log event.
- `main.py` passes `attachments_result` through.
- `sender.py`: `send_pdf` attaches the PDFs (one extra cover-note line, EN/ES)
  and sends the internal producer note when flags/notes exist; complex review
  gets an "Endorsement documentation (A9)" section + PDFs on the review email.
  TEST_MODE redirect logic untouched (flag off → zero code paths change; flag
  on → the client email still redirects; the producer note is internal, like
  the review email, and goes to Alex either way).

## Stubbed / not done yet

- **No endorsement PDFs on file.** `endorsements/<client_id>/` folders are
  scaffolded with a README; every blanket demand currently lands in the
  producer-note bucket until Alex drops in PDFs named per `pdf_filename`.
- **Rolando carrier-request process** — flag hook only.
- Clayton Mechanical has an empty inventory (onboarded today, no carrier docs
  reviewed yet).
- `notice_of_cancellation` and `per_project_aggregate` are detected but no
  client has a registry entry for them → they always produce producer notes.
  (ACORD 25 standard cancellation language may make NOC attachment moot —
  ask Alex.)

## Testing

- `tests/endorsements_review.py` — 38 offline checks (detection, attach
  matrix, Rolando scheduled-skip, AJF no-GAF, pipeline/sender wiring,
  flag-off inertness). No API calls.
- `tests/engine_review.py` — 33/33 OK, 0 WARN (unchanged).
- `tests/zip_review.py` + `tests/spanish_review.py` — still green (they import
  the modified pipeline/sender).
- `tests/pipeline_review.py` NOT run (live Anthropic calls) — should be run
  once before enabling the flag.

## Open questions for Alex

1. **PDFs:** can you pull the actual endorsement PDFs? Strongest candidates:
   AJF (the "COI NV2A with All Endorsements" bundle has everything) and
   Rolando's GL ("GL Blanket AI, PNCB, WOS End.pdf", a scan). Naming
   convention is in `endorsements/README.md`.
2. **Rolando auto flow:** when a scheduled endorsement is demanded, what
   should the producer email say / trigger — draft the Ascendant change-
   endorsement request automatically, or just alert you?
3. **LUBA WC waiver pattern** (EMP3 `unverified`, G&D `none`, 305 `medium`):
   audit before any WC waiver endorsement is ever attached for these clients?
4. **Follow-form entries** (305 excess AI, AJF umbrella WOS): there is no
   standalone PDF to attach — attach the underlying form + an explanation, or
   leave as producer notes?
5. **305 excess WOS template bug** (template claims umbrella waiver, forms
   schedule has none) — fix the template, or get the endorsement added?
6. Should the delivery email list which endorsements are attached by name,
   or is the current one-line mention enough?
