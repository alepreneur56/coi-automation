# Clayton Mechanical — Onboarding Prep (Proposal Only)

Prepared 2026-07-03. No registry or template changes made — this is research + a draft skeleton for review only.

Source: Google Drive, folder `WORK FOLDER/OG Folder/Pushing Forward/0000000 WON/Clayton Mechanical/` and subfolders (`New COIS/Clayton_COIs_FULL_BATCH/`, `Finalist Presentation/`, `U Submit/`), plus two loose files at the "Other Desktop Files" root (`Clayton Mechanical Proposal.pdf`, `Clayton Mechanical - Excess Liability.PDF`). 6 files read in full (cap was 12). Machine-readable version of everything below: `training/clayton/clayton_data.json`.

---

## 1. What we know

### Entity

- **Trading name:** Clayton Mechanical
- **Legal name on policies/COIs:** Clayton Air and Heating, Inc
- **Relationship confirmed:** "CLAYTON AIR & HEATING INC DBA CLAYTON MECHANICAL" — explicit DBA, seen on the mod-history file title and matches the legal name printed on both bound COIs. Not two separate companies.
- **Address:** 2431 Aloma Ave, Suite 124, Winter Park, FL 32792
- **Trade:** HVAC Contractor
- **License number:** **CAC1817147** — printed directly on both bound ACORD COIs ("HVAC Contractor License Number: CAC1817147"). This is a hard data point, not an estimate.
- **Profile:** Family-owned, founded 2005 in the US (principals ran the business in Puerto Rico ~20 years before that). Founders David Clayton (COO) and Jose Mercado (CEO). ~$5M annual revenue, ~$229K field payroll, ~10 employees, 90% commercial / 10% residential, Orlando-based, statewide FL reach. No GL claims per internal account narrative (not independently verified against loss runs in this pass).
- Producer of record: Alejandro Bello, USI Insurance Services LLC/CL, 201 Alhambra Circle Suite 900, Coral Gables FL — same producer block used across the existing registry (matches `coi_client_registry.json` producer block, no changes needed there).

### Carriers, policy numbers, terms, limits (per line)

**Source of truth used:** two independently issued ACORD 25 COIs — `COI 070126.pdf` (issued 07/01/2026) and `Delta Hotels COI.pdf` (issued 06/30/2026), both from the `Clayton_COIs_FULL_BATCH` folder. They agree exactly on every policy number, carrier, and date, which is the strongest signal available that these are the actual bound terms (as opposed to draft quotes).

| Line | Carrier | Policy # | Term | Limits |
|---|---|---|---|---|
| Commercial General Liability | Westfield Insurance Company | CWP 530335F | 06/01/2026–06/01/2027 | $1M each occ / $500K premises damage / $5K med exp / $1M pers & adv injury / $2M gen'l agg / $2M products-comp/op agg |
| Commercial Auto | Infinity Assurance Insurance Company | CA945173MGA | 06/01/2026–06/01/2027 | $1M CSL, any auto |
| Excess Liability | National Union Fire Ins Co of Pittsburgh, PA (AIG), NAIC 19445 | 47329390 | 06/01/2026–06/01/2027 | $2M each occ / $2M aggregate, follows form over GL + Auto |
| Workers' Comp & Employers' Liability | Technology Insurance Company (AmTrust) | 13705262 | 06/01/2026–06/01/2027 | $1M each accident (disease limits not visible on extracted COI text) |

Boilerplate description-of-operations text on the bound COIs (verbatim):

> General Liability & Commercial Auto policies includes an automatic Additional Insured endorsement that provides Additional Insured status to the Certificate Holder as required by written contract. General Liability policy applies on a primary & non-contributory basis. A blanket Waiver of Subrogation applies for General Liability, Commercial Auto, and Employer's Liability policies. Umbrella Liability policy follows form. HVAC Contractor License Number: CAC1817147

### Staleness check vs. today (2026-07-03)

**All four lines are current** — clean 06/01/2026–06/01/2027 term, 32 days in, ~11 months of runway. No renewal urgency.

However, the June proposal packet in Drive (`Clayton Mechanical Proposal Signed.pdf`, print date 05/20/2026) tells a messier story and does **not** match the bound COIs cleanly:

- The Westfield GL declarations page inside that packet is explicitly marked **"NO COVERAGE BOUND"** with a quote validity window of 03/06/26–06/15/26 — i.e., that packet shows a quote, not confirmation of binding.
- The Kemper/Infinity auto quote in that packet was for eff. **3/5/2026–3/5/2027** — the bound COI shows the same policy number (CA945173MGA) but eff. **06/01/2026**, two-plus months later.
- The AIG excess quote in that packet (same submission #47329390) was for **$3,000,000/$3,000,000** limits, eff. **3/16/2026–3/16/2027** — the bound COI shows the same policy number but **$2,000,000/$2,000,000** limits and a 06/01/2026 eff. date.
- The AmTrust WC quote in that packet showed term **6/15/2026–6/15/2027** — the bound COI shows the same policy number (13705262) but eff. **06/01/2026**, two weeks earlier.

Every line shows the same pattern: quote packet has an earlier/different date or higher limit, bound COI shows 06/01/2026 uniformly and (for Excess) a lower limit. This is very likely just normal placement mechanics (carrier moved the actual inception to align all lines on one renewal date, excess got re-quoted at $2M once underlying was finalized) — but nothing in the reviewed files documents *why*, and it's the kind of gap that would cause an automation to certify wrong limits if it trusted the proposal packet instead of a real COI. Flagged as Q1 below.

### Book-of-business signal (important context, not something I was asked to act on)

This is not a simple one-off client. Drive contains:
- `COI LIST CMHQ 2026-2027 v.1 rev.2026.xlsx` — a master tracking sheet with dozens of certificate holders (hotels, HOAs, property managers, municipalities), each with distinct, often lengthy, custom additional-insured/waiver-of-subrogation language.
- `Clayton_COIs_FULL_BATCH 26-27.zip` and `Archive.zip` — batches of already-issued individual COIs for the current term.
- A `New COIS` folder actively organized by holder (sample PDFs: Delta Hotels, City of Pompano Beach, Pinar Center LLC, Springhill Suites, RPM Living, Simpson Property Group, CFI–Westgate Resorts, Castle Management, Winter Park Racquet Club).

Sample holder language, for scale of the customization problem:
- **Benderson Development Company LLC:** AI/WOS extended to "all of its related, affiliated or associated corporations, subsidiaries, entities, companies, trusts and/or partnerships, and their agents, employees, property managers, ground lessors, investment lessors, and tenants."
- **City of Orlando:** simple AI on GL + Auto, WOS on GL, "when required by written contract."
- **Courtyard @ Lake Buena Vista (Marriott):** AI extended to "Marriott International, Inc., Courtyard Management Corporation, NF III-CI Orlando C Op Co," primary/non-contributory, WOS on GL only.

This means a single fixed template (like the current 1-2 template clients in the registry) likely won't cover this account well — see Q7 below.

---

## 2. Draft registry entry skeleton

Matches the exact schema in `coi_client_registry.json` (see `rolandos_hvac` as the closest existing HVAC-trade example). Not inserted into the live registry — placeholder only, for review.

```json
{
  "client_id": "clayton_mechanical",
  "canonical_name": "Clayton Mechanical",
  "aliases": [
    "clayton",
    "clayton mechanical",
    "clayton air and heating",
    "clayton air & heating",
    "clayton hvac"
  ],
  "insured_address": "2431 Aloma Ave, Suite 124, Winter Park, FL 32792",
  "trade": "HVAC Contractor",
  "license_number": "CAC1817147",
  "templates": []
}
```

Notes on the skeleton:
- `templates: []` is intentionally empty — no PDF template exists yet for Clayton. Per instructions, no template file is being built in this pass.
- `legal_name` / `dba` isn't a field in the current schema (other clients don't carry it either) — worth deciding whether to add it given the DBA is material here, or just fold "Clayton Air and Heating, Inc" into `aliases`. Flagged as Q6.
- `contact_emails` / `contact_domains` (present on `rolandos_hvac`) intentionally omitted — no Clayton inbox/domain was found in the reviewed files. See Q3.

---

## 3. MISSING for template creation

1. **Which certificate-holder wording model do we use?** The sample holder language varies enormously (see book-of-business section above) — do we build one flexible template with an editable AI/WOS clause field per issuance (like other registry clients), or do we need holder-specific variants for the biggest/recurring holders (Benderson, Marriott properties, HOAs)?
2. **Excess Liability limit discrepancy** — bound COIs show $2M/$2M, the AIG quote packet shows $3M/$3M for the same submission/policy number. Which is actually correct/current? (Affects the `limits` block in the policies array.)
3. **What inbox/domain should trigger Clayton COI requests?** No Clayton-specific contact email or domain was found in any reviewed file (unlike `rolandos_hvac`, which has `leyva.lrolandoshvac@gmail.com` on file) — needed for `contact_emails`/`contact_domains` and for the classifier to route requests to this client.
4. **Do we need current declarations pages for all 4 lines, or are the two bound ACORD COIs sufficient?** The COIs give policy numbers/dates/limits but not full endorsement schedules (e.g., WC disease-per-employee and disease-policy-limit values weren't visible on the extracted COI text).
5. **Officer/member exclusion on WC** — the bound COI shows "ANY OFFICER/MEMBER PROPRIETOR/PARTNER/EXECUTIVE EXCLUDED?" checked Y but doesn't name who. Which principals (David Clayton, Jose Mercado, others) are excluded, for template accuracy if that ever needs to print?
6. **Legal name vs. DBA handling** — should the registry/template show "Clayton Mechanical," "Clayton Air and Heating, Inc," or both (as `rolandos_hvac`-style clients show trading name only)? Matters for how the INSURED block prints on generated COIs.
7. **Preferred boilerplate wording** — confirm the exact description-of-operations boilerplate to hard-code (the text pulled from the bound COIs above), and whether Alex wants the "Project name & Address (If Applicable)" placeholder line used by other clients (305 Power, Rolando's) added here too.
8. **Which coverage lines actually belong on the default cert** — all 4 (GL/Auto/Excess/WC), matching the pattern from 305 Power's default template, or does Clayton usually only need GL+Auto for most holders with Excess/WC pulled in only on request?
9. **Property/Inland Marine/Crime/Cyber lines** — the Westfield BOP quote also includes Commercial Property, Inland Marine, and Crime, and there's a separate Cyber line from UFG. Do any certificate holders ever ask for these on a COI, or is GL/Auto/Excess/WC the full universe needed?
10. **Source PDF for template build** — is there an existing signed/bound ACORD 25 (not just the two sample COIs found) that should be the base template to edit, or should the template be built fresh in the house style used for other clients?

## 4. Recommendation on readiness

**Not ready to build a template yet, but the underwriting/policy data is in unusually good shape for a new client.** Unlike a cold onboarding, Clayton already has a placed USI account, live bound COIs, and a well-organized certificate-holder tracking sheet — this is closer to "migrate an existing manual process into automation" than "onboard a brand-new client from scratch." The blocking gaps are narrow and mostly administrative: confirm the Excess Liability limit discrepancy (Q2), get a routing inbox/domain (Q3), and — the one that actually shapes template design — decide how to handle the wide variation in certificate-holder AI/WOS language (Q1) before building anything, since that decision determines whether this is a one-template client or a multi-template/variable-clause client.

Given the batch-COI volume already visible in Drive, this could become one of the higher-value automation targets once those three questions are answered — worth prioritizing the follow-up conversation with Alex over some of the lower-volume prospects.

## 5. Data quality flags (found in passing, not requested)

- `Clayton Mechanical - Account Narrative.docx` has a leftover reference to "Rolando's HVAC" in the Risk Management & Safety section, apparently cloned from the existing `rolandos_hvac` client narrative and never renamed. Doesn't affect the data above (I didn't use narrative claims for policy facts) but worth a quick fix if that doc is ever shared externally.
- Multiple conflicting versions of "Estimation Comparison - Clayton Mechanical" exist across folders (V3 x2, V4, and an unlabeled "Copy") with different renewal-carrier assumptions. Used V4 (most recently modified) as the closest match to the bound COIs; didn't reconcile the others.
