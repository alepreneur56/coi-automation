> UPDATE 2026-07-03: Alex confirmed (07-02 evening) Apogee was fully reinstated — all 5 lines in force through 12/08/2026. The 'in-force unverified' caveats below predate that confirmation. Rolando's WC and Absolute Air GL/WC/Umbrella are other brokers' lines.

# Endorsement Inventory (A9 scaffold) — PROPOSAL ONLY

Generated 2026-07-03. Nothing in this file or `endorsement_inventory.json` has been written to `coi_client_registry.json`, `templates/`, or `coi_system_prompt.txt`. This is source material for a future auto-issue rule.

**Sources:**
- Email archive: `Documents/Migrated_From_TestAccount_2026-05-03/.../IPM_SUBTREE` — 8 standalone endorsement PDFs found by filename search, plus the AJF "with All Endorsements" COI bundles which embed full endorsement text (CNA forms). Text-extracted with fitz, capped at 80 files.
- `training/registry_gap/FINAL_RECONCILIATION.json` (2026-07-02) — per-client carrier-doc-verified extractions; primary source for form numbers where the archive didn't surface a standalone endorsement PDF.

**A note on "Morata":** the task brief pointed at a "Morata Blanket AI/WOS/P&NC COI Template folder" as a source. No such client or folder exists. "Morata Plumbing" appears in the archive only as a labeled **TEST ENTITY** (`Inbox/00075_Morata Plumbing COI - Test Entity Inc`, `Inbox/00209_...SCL Stage Notification`) — not one of the 8 real clients. Not used as a source. See open questions.

---

## Top summary — what an auto-issue rule needs

Proposed rule shape: **issue directly (no human review) when every endorsement a certificate holder is demanding is already confirmed `blanket: true` in this file for the relevant coverage line(s), on a policy that is currently in force.** Two gates, not one — blanket status alone isn't enough if the underlying policy's in-force status is itself in doubt (see Apogee).

| Client | Safe to auto-issue on? | Why / why not |
|---|---|---|
| **AJF Roofing** | Yes, strongest client | GL, Auto, WC all form-verified blanket AI + WOS + P&NC directly from CNA endorsement text (read in full from archive PDF). Umbrella AI is follow-form/medium. All 4 policies confirmed in force by two independent carrier-doc sources. |
| **305 Power Corp** | Mostly yes | GL, Auto, WC all blanket AI/WOS (GL & Auto high confidence; WC medium — scanned policy). Excess is follow-form for AI but **has no waiver-of-subrogation endorsement despite template boilerplate claiming one** — do not auto-issue certs claiming excess/umbrella waiver until fixed. GL+Excess expire 07/15/2026, renewal not yet bound — re-check before that date. |
| **EMP3 Solutions** | Mostly yes | GL fully form-verified blanket (CG 20 10/20 01/24 04, exact form numbers). Auto blanket AI+WOS confirmed via policy-change notice. **WC waiver is marked on the template but the carrier's endorsement schedule shows none** — exclude WC waiver claims from auto-issue until resolved. No umbrella exists; template boilerplate referencing umbrella waiver is stale. |
| **Central Comfort AC** | Conditionally yes | WC waiver is form-verified (WC 00 03 13, high confidence). GL AI/P&NC/waiver rest on COI/template wording only — underlying policy is an unreadable scan, so no endorsement form was directly sighted. "Cleanest client in the book" per reconciliation, but GL endorsement claims are medium-confidence, not high. |
| **Rolando's HVAC** | No — auto only, and only for scheduled parties | GL is fully blanket-confirmed (CG 20 10_B / CG 20 01_B / CG 24 04_B). **Auto AI/WOS/P&NC is SCHEDULED, not blanket** — archive contains three standalone Florida policy-change endorsements (Designated Insured, PNC, WOS) each naming ONE certificate holder at a time (Cottages at Brandon LP; a second copy for Test Entity Inc). A new certificate holder likely needs a new change endorsement before auto can be certified with AI/WOS. **WC has no current policy at all** (expired 03/23/2026, no replacement found) — cannot issue WC certs. |
| **G&D Mechanical** | No | WC waiver marked on template but not in the carrier's endorsement schedule (same unresolved pattern as EMP3). Auto policy's CURRENT term has no renewal declarations page in Drive at all — AI/WOS unverified for the in-force policy. GL/Umbrella AI/WOS rest on COI wording only, not a sighted endorsement form. Two conflicting template lineages exist. |
| **Absolute Air Solutions** | No, except the one confirmed line | Only the Infinity auto policy is verifiably in force (blanket AI + WOS, high confidence, policy-change doc). GL, Umbrella, and WC have all expired with no renewals found anywhere. A second Progressive auto policy exists with NO AI/waiver and disputed binding status. |
| **Apogee HVAC** | No — highest-risk client in the book | GL and WC endorsement forms are well-documented on paper (CG 20 10/20 37/20 01/24 53 for GL; WC 00 03 13 for WC) but **in-force status of GL, both excess layers, and WC is unverified** — an IPFS non-payment cancellation notice (GL+excess, threatened 05/01/2026) and a WC termination (~04/14/2026) both have unknown outcomes. Excess AI/waiver never verified at the form level. Auto AI/waiver completely unknown (scanned dec). Do not auto-issue anything for this client until in-force status is confirmed. |

**Pattern worth flagging to Alex:** three separate clients (EMP3, G&D, Apogee — and possibly 305's WC) have a template that marks WC "SUBR WVD" (waiver of subrogation) even though the LUBA/carrier endorsement schedule shows no WC 00 03 13 on file. This looks like a systemic template assumption ("LUBA WC always has a blanket waiver") that isn't universally true. Worth a one-time audit across all LUBA WC policies before trusting that mark anywhere.

---

## Per-client tables

### 305 Power Corp

| Line | Form # | Title | Kind | Blanket? | Confidence |
|---|---|---|---|---|---|
| GL | FCG 1029 (Clear Blue) | AI by Written Contract (automatic) | blanket_ai | Yes | high |
| GL | CG 24 04 | Waiver of Subrogation (Blanket) | waiver_subrog | Yes | high |
| GL | (unspecified, boilerplate) | Primary & Non-Contributory | primary_noncontrib | Yes | medium |
| Auto | (unspecified, Progressive) | Blanket Additional Insured | blanket_ai | Yes | high |
| Auto | (unspecified, Progressive) | Blanket Waiver of Subrogation | waiver_subrog | Yes | high |
| Excess | n/a (CX 00 01 Sec I.1.d) | AI follow-form | blanket_ai | Yes | medium |
| WC | (unspecified, LUBA) | Blanket Waiver of Subrogation | waiver_subrog | Yes | medium |

**Gaps:** Excess has no waiver-of-subrogation endorsement despite template claiming one for "Umbrella" (active template bug). Auto AI/WOS only confirmed via a policy dec, no standalone endorsement PDF located.

**Open questions:**
1. Is the Obsidian GL/Excess renewal bound before 07/15/2026, and does it preserve the same FCG 1029/CG 24 04 blanket forms?

---

### Rolando's HVAC

| Line | Form # | Title | Kind | Blanket? | Confidence |
|---|---|---|---|---|---|
| GL | CG 20 10_B | AI - Owners, Lessees or Contractors | blanket_ai | Yes | high |
| GL | CG 20 01_B | Primary and Noncontributory | primary_noncontrib | Yes | high |
| GL | CG 24 04_B | Waiver of Subrogation | waiver_subrog | Yes | high |
| Auto | n/a (CA 20 48 02 99 sighted, but per-holder) | Designated Insured / PNC / WOS change endorsements | other | **No — scheduled, not blanket** | high |

**Gaps:** WC has no current policy (expired 03/23/2026, no replacement found in Drive) — no endorsement evidence applies.

**Open questions:**
1. Does Ascendant require a brand-new Florida policy-change endorsement (like the two sighted for Cottages at Brandon LP and Test Entity Inc) every time a new certificate holder needs auto AI/WOS/PNC — i.e., is auto genuinely never blanket for this client?
2. Has Rolando's HVAC replaced the lapsed WC policy since 03/23/2026?

---

### EMP3 Solutions

| Line | Form # | Title | Kind | Blanket? | Confidence |
|---|---|---|---|---|---|
| GL | CG 20 10 04 13 | AI - Owners, Lessees or Contractors (blanket wording) | blanket_ai | Yes | high |
| GL | CG 20 01 04 13 | Primary and Noncontributory | primary_noncontrib | Yes | high |
| GL | CG 24 04 05 09 | Waiver of Subrogation (Blanket) | waiver_subrog | Yes | high |
| Auto | (unspecified, Infinity/Kemper) | Blanket Additional Insureds | blanket_ai | Yes | high |
| Auto | (unspecified, Infinity/Kemper) | Blanket Waiver of Subrogations | waiver_subrog | Yes | high |
| WC | n/a — no WC 00 03 13 found | No waiver endorsement on schedule | other | No | medium |

**Gaps:** WC waiver marked on template but not present on carrier's endorsement schedule. No umbrella policy exists (template boilerplate referencing it is stale).

**Open questions:**
1. Was a WC waiver endorsement added to the LUBA policy after 2026-01-07 (the last-modified date on the policy PDF), or is the template's SUBR mark simply wrong?

---

### Central Comfort AC

| Line | Form # | Title | Kind | Blanket? | Confidence |
|---|---|---|---|---|---|
| GL | BP 71 74 08 15 (UFG BOP-Pro) | Primary and Non-Contributory | primary_noncontrib | Yes | medium |
| GL | (unspecified, COI-sourced) | Automatic AI by written contract | blanket_ai | Yes | medium |
| GL | (unspecified, COI-sourced) | Blanket Waiver of Subrogation | waiver_subrog | Yes | medium |
| WC | WC 00 03 13 | Waiver of Our Right to Recover From Others (Blanket) | waiver_subrog | Yes | high |

**Gaps:** GL AI/waiver form numbers never directly sighted — underlying UFG policy PDF is an unreadable 47.8MB scan. Reconciliation calls this "the cleanest client in the book" overall, but that's about limits/dates agreement, not endorsement-form verification.

**Open questions:**
1. Can the UFG BOP be OCR'd to confirm the actual GL AI/waiver form numbers, or is 3-agreeing-docs corroboration considered sufficient to auto-issue on?

---

### G&D Mechanical

| Line | Form # | Title | Kind | Blanket? | Confidence |
|---|---|---|---|---|---|
| GL | (unspecified, COI wording only) | AI / P&NC / Blanket Waiver | blanket_ai | Yes (asserted) | medium |
| Auto | (unspecified, COI block only) | AI / Waiver (current term unverified) | blanket_ai | **Unknown** | low |
| Umbrella | n/a — follow-form | No standalone endorsement cited | other | **Unknown** | medium |
| WC | n/a — no WC 00 03 13 found | No waiver endorsement on schedule | other | No | high |

**Gaps:** Auto renewal declarations page missing entirely for the current term. WC waiver marked but unsupported (same pattern as EMP3). GL/Umbrella AI/WOS not verified at endorsement-form level. Two conflicting template lineages in circulation.

**Open questions:**
1. Which template file is actually live for the automation — this repo's, or the Drive-side "New Template with the New Auto policy" copy with the wrong GL limits?
2. Can the 26-27 Kemper/Infinity auto renewal declarations be pulled to confirm AI/WOS on the current term?

---

### Absolute Air Solutions

| Line | Form # | Title | Kind | Blanket? | Confidence |
|---|---|---|---|---|---|
| Auto (Infinity, primary) | (unspecified) | Blanket AI | blanket_ai | Yes | high |
| Auto (Infinity, primary) | (unspecified) | Blanket WOS | waiver_subrog | Yes | high |
| Auto (Progressive, secondary, 872005650) | n/a | No AI / no waiver (ADDL N / SUBR N) | other | No | medium |

**Gaps:** GL and WC have both lapsed with no renewals found — no endorsement evidence applies because no current policy exists to certify.

**Open questions:**
1. Did GL, Umbrella, Property, and WC genuinely lapse for this client, or does a 26-27 renewal exist somewhere not yet found (e.g. a different carrier/portal)?
2. Is the Progressive secondary auto policy (872005650) actually bound, and does it cover the vehicle removed from the Infinity policy?

---

### AJF Roofing

| Line | Form # | Title | Kind | Blanket? | Confidence |
|---|---|---|---|---|---|
| GL | CNA75079XX (3-22) | Blanket AI - Owners, Lessees or Contractors w/ Products-Completed Ops | blanket_ai | Yes | high |
| GL | CNA75079XX (3-22) §VI | Primary and Noncontributory | primary_noncontrib | Yes | high |
| GL | CNA74705XX (1-15) Item 25 | Waiver of Subrogation - Blanket | waiver_subrog | Yes | high |
| Auto | CNA63359XX (04-2012) | Blanket AI (written-contract clause) | blanket_ai | Yes | high |
| Auto | CNA63359XX (04-2012) | Primary and non-contributory | primary_noncontrib | Yes | high |
| Auto | CNA63359XX (04-2012) | Blanket waiver of subrogation | waiver_subrog | Yes | high |
| Umbrella | n/a — condition W, follow-form | Blanket waiver; AI unverified at umbrella layer | waiver_subrog | Yes | medium |
| WC | WC 00 03 13 (04-1984) | Waiver of Our Right to Recover From Others | waiver_subrog | Yes | high |

**Gaps:** Umbrella AI status rests on follow-form inference only, not a sighted standalone endorsement.

**Open questions:** none — strongest-documented client in the book; the full CNA endorsement text was read directly from an archive PDF (`AJF COI NV2A with All Endorsements.pdf`).

---

### Apogee HVAC

| Line | Form # | Title | Kind | Blanket? | Confidence |
|---|---|---|---|---|---|
| GL | CG 20 10 / CG 20 37 | AI - Owners, Lessees or Contractors | blanket_ai | Yes (on paper) | high |
| GL | CG 20 01 | Primary and Noncontributory | primary_noncontrib | Yes (on paper) | high |
| GL | CG 24 53 | Waiver of Subrogation (automatic) | waiver_subrog | Yes (on paper) | high |
| Excess (1st layer, Lexington) | n/a — follow-form only | AI/waiver unverified | other | Unknown | low |
| Excess (2nd layer, Scottsdale) | n/a | AI/waiver wording never verified | other | Unknown | low |
| Auto | n/a — unreadable scan | AI/waiver status unknown | other | Unknown | low |
| WC | WC 00 03 13 | Waiver of Our Right to Recover From Others | waiver_subrog | Yes (on paper) | high |

**Gaps:** In-force status of GL, both excess layers, and WC is unverified (non-payment cancellation/termination events with unknown outcomes). Excess AI/waiver never confirmed at form level. Auto AI/waiver completely unknown.

**Open questions:**
1. Was the $4,006.56 IPFS payment made before the 05/01/2026 GL/excess cancellation deadline — is GL still in force?
2. Was the WC policy (terminated ~04/14/2026) reinstated — check FHMConnect / Maria Simpson (msimpson@fhmic.com)?
3. Can the actual Infinity auto declarations page be pulled (needs OCR/portal) to resolve the auto term and AI/waiver questions in one shot?

---

## Cross-client open questions

1. Is "Morata Plumbing" (labeled TEST ENTITY in the archive) meant to become a 9th real client, or was the task brief's reference to it a mix-up with one of the 8 existing clients?
2. Should the systemic WC-waiver-marked-but-unsupported pattern (EMP3, G&D, possibly others) be fixed at the template level, or does it need a per-client carrier callback first?
3. For Rolando's HVAC auto: can Ascendant confirm whether AI/WOS/PNC can ever be blanket, or is a new change endorsement genuinely required per certificate holder?

**Totals:** 43 endorsement-evidence entries across 8 clients (34 confirmed blanket=true, 4 confirmed blanket=false, 5 unknown/unverified pending in-force or form confirmation). 19 per-client gap notes. 12 open questions (9 per-client + 3 cross-client).
