# A7 Design Brief — Requirements-Document Processing

**Date:** 2026-07-02
**Inputs:** `training/a7/requirements_catalog.json` (archive sweep, built by
`training/a7/catalog_requirements.py`), `training/a7/parsed_examples.json`
(13 hand-parsed ground-truth examples), `coi_client_registry.json`,
`training/corpus_index.json`, `sender.py`, `classifier.py`, `pipeline.py`,
`coi_system_prompt.txt`.

**Scope:** A7 = a requester sends an insurance-requirements document
(contract exhibit, vendor packet, bid spec, or sample COI) and the system
must (a) extract certificate-holder info and the required coverages /
limits / endorsements, (b) compare them against what the client actually
carries (A7a coverage matching, A7b limits mismatch), and (c) put that
comparison in front of Alex inside the existing complex-review email.
Today these requests already route to `coi_complex_review_required` and a
human does all of this by eye. A7 does not change WHO decides — it changes
how much pre-digested analysis the review email carries.

---

## 1. Corpus stats

The A3 miner's fingerprint regex found **3 `requirements_doc` attachment
records (2 unique documents)** across the whole archive. The A7 sweep
(`catalog_requirements.py`) walked **1,058 PDF attachments** in
Inbox / Sent Items / Deleted Items with broader keyword families, filename
hints, boilerplate suppression, and noise filters, and cataloged
**44 unique requirements-document candidates**:

| doc_type | count | note |
|---|---|---|
| sample_coi_with_requirements | 23 | requirements encoded as an annotated/filled sample cert, or a prior cert sent as "match this" |
| requirements_exhibit | 4 | prose requirements docs (Moriarty, MDSO RPQ, BrickellHouse, JCI checklist) |
| full_contract | 2 | requirements buried in a signed agreement (AJF master subcontract; a PEO client-services agreement) |
| vendor_packet | 1 | Bengoa vendor/sub setup sheet |
| unknown | 14 | 13 of these are scanned/image-only PDFs flagged `ocr_needed` (candidates by filename/thread only) |

Excluded as noise (counted in the catalog summary): 154 plain ACORD certs,
95 carrier policy documents/quotes, 19 carrier application forms, 14 of our
own issued certs that only exist in Sent Items, 4 legal filings, 130
scanned PDFs with no requirements signal.

**Per client:**

| client | docs | flavor |
|---|---|---|
| rolandos_hvac | 12 | mostly received sample/echoed certs with custom AI language (Charlotte County, Marion County, Progress Residential, Test Entity) |
| apogee_hvac | 7 | condo/property-management requirements (BrickellHouse, 1 Hotel South Beach, DUA, The Palace — 3 scanned) |
| ajf_roofing | 6 | big-GC / public-entity patterns (NV2A/SDTOC endorsement packets, Camcon sample, MDSO bid, own master subcontract) |
| central_comfort_ac | 3 | condo association samples (Paraiso Bay, Icon Bay) |
| unmatched | 16 | includes two 305 Power live-test threads (Stratus, Bengoa — client tokens absent from truncated folder names), JCI and Belle Tower live tests, landlord/tenant samples, RFP scans |
| emp3_solutions, gd_mechanical, absolute_air_solutions | 0 | no requirements docs in the archive for these three |

Takeaway: requirements docs are concentrated on the construction-facing
clients (AJF, Apogee, 305 Power) and property-management-facing ones
(Rolando's, Central Comfort). Volume is real but modest — roughly 2-4
genuinely new requirements documents per month across the book.

## 2. Concrete requirement patterns found

Five recurring document shapes (ground truth for each in
`parsed_examples.json`):

**P1 — Condo / property-management checklist** (`brickellhouse_requirements`,
`kw_belle_tower_vendor_packet`). Short prose or bullet list: GL $1M/occ
minimum, WC required *even if state-exempt*, AI + WOS expressed as "the
ACORD boxes must be checked," exact prescribed certificate-holder block,
sometimes dual holders (Association + property manager) and an ACORD form
edition requirement (2014/01 or 2016/03 only). This is the most common
pattern for the HVAC clients.

**P2 — GC subcontract insurance article** (`moriarty_subcontract_article8`,
`sals_ajf_master_subcontract`). ISO endorsement form numbers with editions
(CG 20 10 10/01 or 07/04 AND CG 20 37), per-project aggregate, tiered
umbrella limits by contract value ($5M over $500k / $2M under), completed
operations through the statute of repose, 30-day notice of cancellation,
conditional specialty lines (pollution $1M, professional $2M, equipment
floater), certs delivered to a compliance platform (CertSoft / Alliant
email) rather than a mailing address.

**P3 — Public-entity bid / JV project** (`mdso_rpq_addendum1`,
`nv2a_sdtoc_endorsement_packet`). Verbatim-prescribed holder block that
differs from the delivery address, carrier-quality gates (A.M. Best A- /
Class VII or FL Certificate of Authority), multi-entity AI (JV + County +
DTPW + Architects + Sub-consultants), specialty coverage (Riggers
Liability), and — critically — demands for **copies of the actual policy
endorsement forms attached to the cert** (the NV2A deliverable is 12 pages:
cert + CNA endorsement forms).

**P4 — Sample cert as the requirements** (`camcon_sample_subcontractor_certificate`,
`stratus_sample_cert_305power`, `hotel_south_beach_prior_cert`,
`calhoun_tenant_sample`). No prose at all: an annotated blank ACORD with
required limits pre-filled and margin notes, or a prior year's cert
forwarded as "match this." Requirements live in ACORD limit boxes,
checkbox positions, and the description-of-operations paragraph. This is
the **largest bucket (23 of 44)** and includes sub-limit requirements
(damage-to-rented $200k, med exp $10k) and open-ended AI clauses ("or any
other party requested").

**P5 — Vendor onboarding packet** (`bengoa_vendor_setup`,
`jci_subcontractor_checklist`). Insurance requirements embedded in a W-9 /
license / EHS packet; two-tier holder logic (account-level cert now,
per-project certs later with the GC added as AI on both); third-party cert
tracking platforms; limits above what clients carry (JCI: GL $2M/occ) with
explicit permission to stack umbrella to comply.

**Recurring requirement atoms** an extractor must capture: AI scope
(blanket-by-contract vs named entities vs multi-entity vs open-ended), WOS
per line, primary & non-contributory, notice-of-cancellation days (30/10
split), ISO form numbers + editions, ACORD form edition, endorsement
copies attached, carrier rating floor, per-project aggregate, claims-made
tail years, sub-limits, specialty lines (riggers / pollution /
professional / E&O / equipment floater), WC-even-if-exempt, umbrella
stacking, prescribed description-of-operations wording, and holder-vs-
delivery-address splits.

**Direction trap:** one cataloged contract is our own client (AJF) imposing
requirements on ITS subcontractor. A7 must detect "our client is the
requester" and not attempt issuance.

## 3. Registry: what it can answer vs what it lacks

`coi_client_registry.json` stores per-template `carriers`,
`lines_of_coverage`, `editable_fields` (incl. the description-of-operations
boilerplate, which encodes blanket AI + P&NC + WOS at a coarse level), and
— only sometimes — a `policies` array with per-line limits.

| client | `policies` array | lines with limits | A7b limits comparison possible? |
|---|---|---|---|
| 305_power_corp | yes | GL, Auto, Excess, WC | yes (full) |
| rolandos_hvac | yes | GL, Auto | partial — no WC/umbrella entries (they carry GL+Auto only, but the registry cannot distinguish "not carried" from "not recorded") |
| central_comfort_ac | yes | GL, WC, Property | partial — no Auto entry |
| **emp3_solutions** | **no** | — | **no** |
| **gd_mechanical** | **no** | — | **no** |
| **absolute_air_solutions** | **no** | — | **no** |
| **ajf_roofing** | **no** | — | **no** |
| **apogee_hvac** | **no** | — | **no** |

So **5 of 8 clients (emp3_solutions, gd_mechanical,
absolute_air_solutions, ajf_roofing, apogee_hvac) have no `policies`
arrays** — for them A7b can only render "insured carries: unknown". Worse,
the two clients with the heaviest requirements traffic (AJF, Apogee) are in
that group, and the 1 Hotel South Beach prior cert shows Apogee's real
excess ($4M/$4M) doesn't match anything recorded anywhere.

Registry-wide gaps regardless of client:
- no way to express "line not carried" vs "line not recorded";
- no endorsement form numbers actually on the policies (needed to answer
  "is CG 20 10 07/04 satisfied?");
- no carrier A.M. Best ratings (P3 gate);
- no deductibles / retention, no per-project-aggregate availability flag,
  no umbrella follow-form flag;
- no stored endorsement-form PDFs (needed for the NV2A "attach endorsement
  copies" demand).

## 4. Proposed pipeline design

Current flow: `main.py` loop -> `classifier.classify()` (ONE Claude call:
system prompt + registry, attachments as native `document`/`image` blocks)
-> `pipeline.decide_action()` -> `coi_engine.process_request()` draft ->
`sender.execute_action()` -> `build_complex_review_body()` review email to
Alex + acknowledgment to the client.

Two important existing facts:

1. **The extraction slot already exists.** `coi_system_prompt.txt` already
   instructs the model to emit `review_summary` + `coverage_analysis` on
   `coi_complex_review_required`, and `sender.build_complex_review_body()`
   already renders a `coverage_analysis` dict.
2. **Their schemas do not match.** The prompt's example schema uses
   `required_each_occurrence` / `client_each_occurrence` / `note` per
   coverage; the renderer reads `cov.get("required_limit")`,
   `cov.get("insured_limit")`, `cov.get("gap")` (sender.py lines ~197-205).
   A prompt-conformant model output renders with **blank limits** today.
   This must be fixed no matter what else A7 does.

### Proposed stages

**Stage 1 — classification (unchanged).** The absolute rule ("any attachment
with insurance language -> complex review") stays; it is conservative and
benchmarked. A7 hooks in *after* classification, in
`pipeline.decide_action()`, when `classification ==
"coi_complex_review_required"` and the email has PDF/image attachments.

**Stage 2 — dedicated extraction pass (new).** A second Claude call with a
new, small system prompt (`a7_extraction_prompt.txt`), input = ONLY the
requirements attachment(s) (same base64 document/image blocks the
classifier already builds — scanned PDFs are fine, the API reads them
visually, so `ocr_needed` matters for local tooling, not runtime) plus a
one-line context (client name, requester email). Output: strict JSON —

```json
{
  "certificate_holder": {"name": "...", "address": "...", "delivery_instructions": "..."},
  "additional_insured_entities": ["..."],
  "our_client_is_the_requester": false,
  "required_coverages": [
    {"line": "GL", "limits": {"each_occurrence": "2,000,000", "general_aggregate": "2,000,000"}, "conditional": false, "notes": "..."}
  ],
  "required_endorsements": [
    {"kind": "additional_insured", "lines": ["GL", "Auto"], "forms": ["CG 20 10 10/01", "CG 20 37 10/01"], "primary_noncontributory": true},
    {"kind": "waiver_of_subrogation", "lines": ["GL", "WC"]},
    {"kind": "notice_of_cancellation", "days": 30, "days_nonpayment": 10}
  ],
  "form_requirements": {"acord_edition": "2016/03", "endorsement_copies_required": true, "carrier_rating_min": "A- VII"},
  "special_language": ["verbatim sentences worth quoting"]
}
```

Deliberately NO registry in this prompt: cheaper, prevents the model from
doing the comparison itself, and makes the extraction directly evaluable
against `parsed_examples.json` (which uses the same limit-key vocabulary as
the registry `policies[].limits`).

**Stage 3 — deterministic comparison in Python (new module, e.g.
`coverage_compare.py`).** Pure function
`(extraction_json, client_registry_entry) -> coverage_analysis` producing
**exactly the dict shape `sender.build_complex_review_body()` renders**:

```python
{
  "required_coverages": [
    {"line": "Commercial General Liability",
     "required_limit": "$2,000,000 / occurrence",
     "insured_limit": "$1,000,000 / occurrence",
     "gap": True},
    ...
  ],
  "required_endorsements": ["Additional insured (GL, Auto) via CG 20 10 — covered by blanket endorsement [OK]", ...],
  "special_language": "...verbatim quotes...",
  "notes": "Registry has no policy limits for apogee_hvac — limits comparison not possible; forward to Alex with extraction only."
}
```

Logic: normalize dollar strings; map requirement line names to registry
lines (GL / Auto / Umbrella+Excess / WC; anything unmapped — riggers,
pollution, professional — is an automatic gap/flag); compare limit-by-limit
where the client has a `policies` array; match endorsement asks against the
template's known blanket AI / WOS / P&NC flags (`addl_insured`, `subr_wvd`,
description-of-operations text); clients without `policies` data get
`insured_limit: "unknown (no registry data)"` and `gap: true` with a note
(renderer is binary OK/GAP — see open question 3). One deterministic,
unit-testable place instead of trusting a one-shot LLM comparison.

**Stage 4 — delivery (unchanged).** The comparison dict feeds the existing
`decision["coverage_analysis"]` and flows through
`build_complex_review_body()` untouched. Client still gets only the
acknowledgment. Also align `coi_system_prompt.txt`'s coverage_analysis
schema with the renderer keys (or drop it from the classifier prompt
entirely once Stage 2 owns extraction — smaller classifier prompt, fewer
tokens).

Rollout: gated by the same two-harness rule as everything else — Stage 2
must pass the extraction benchmark and Stage 3 its unit tests before the
live loop uses them; TEST_MODE first, per-message logging of the Stage 2
JSON into the existing db for review.

## 5. Eval plan

- **Ground truth:** `training/a7/parsed_examples.json` (13 examples across
  all five patterns, hand-parsed from the source PDFs; each record has the
  source path so the harness can feed the original PDF to Stage 2).
- **Extraction benchmark** (`training/a7/benchmark_a7.py`, to be built like
  `training/benchmark_classifier.py`): run the Stage 2 prompt on each
  example's PDF; score per field: certificate-holder name (exact after
  normalization) and address (fuzzy), coverage-line recall/precision,
  limit values (exact string match per limit key), endorsement recall
  (kind+lines), NOC days, special-language capture (required verbatim
  sentences present as substrings). Report per-pattern (P1-P5) so
  weaknesses are visible (expect P4 sample-certs and scanned docs to be
  hardest).
- **Comparison unit tests** (no API): fixed registry fixtures + synthetic
  extractions covering: clean pass (Bengoa vs 305 Power), limits gap (JCI
  $2M GL vs $1M), unknown-client-data (Apogee), unmapped line (MDSO
  riggers), umbrella stacking case, sub-limit gap (Stratus $200k rented
  premises), our-client-is-requester (Sal's/AJF).
- **Acceptance gate before live wiring:** cert-holder correct on 13/13;
  no fabricated limits (precision on limit values > recall priority — a
  wrong number in Alex's review email is worse than a blank); zero
  regressions on the existing classifier benchmark.

## 6. Open questions for Alex (one-liners welcome)

1. **Registry data:** can you pull full `policies` arrays (limits, policy
   numbers, eff/exp) for emp3_solutions, gd_mechanical,
   absolute_air_solutions, ajf_roofing, apogee_hvac — same shape as 305
   Power's? Without them A7b renders "unknown" for the two busiest clients.
2. **Not carried vs not recorded:** OK to add an explicit
   `lines_not_carried` list per client so absence of a line is meaningful?
3. **Unknowns in the email:** binary OK/GAP only (unknown shown as GAP with
   a note), or should I extend `build_complex_review_body()` with a third
   [UNKNOWN] flag?
4. **Umbrella stacking:** requirement GL $2M/occ, client has GL $1M +
   umbrella $2M — report [OK] with a stacking note, or [GAP] and let you
   decide?
5. **Sub-limits:** compare damage-to-rented / med-exp too (real mismatches
   exist, e.g. Stratus wants $200k rented), or headline limits only?
6. **Endorsement copies demanded** (NV2A pattern): flag-only in the review
   email, or do you want to store each client's endorsement PDFs so the
   draft packet can include them automatically?
7. **Our client as requester** (AJF collecting subs' certs): should the
   system do_nothing + notify you, or draft a "requirements received"
   acknowledgment to the sub?
8. **Prompt schema fix:** fix the `coverage_analysis` key mismatch inside
   `coi_system_prompt.txt` now (pre-A7, it's a live rendering bug), or
   wait and remove it when Stage 2 lands?
9. **Images/screenshots:** requirements arriving as photos already route to
   complex review — should Stage 2 also run on image attachments from day
   one (same call, image blocks)?
