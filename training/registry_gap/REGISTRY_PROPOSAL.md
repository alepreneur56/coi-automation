# Registry Gap Proposal — policies arrays for 5 clients

**Date:** 2026-07-02 · **Status: PROPOSAL — nothing has been written to `coi_client_registry.json`.**
Machine-readable version: `registry_gap_data.json` (same folder).

**What this is:** reconstructed `policies` arrays (305_power_corp schema) for the 5 clients missing them —
`emp3_solutions`, `gd_mechanical`, `absolute_air_solutions`, `ajf_roofing`, `apogee_hvac` — mined from
(1) the client COI templates in `templates/`, (2) delivered COIs indexed in `training/graded_cois.json`, and
(3) carrier policy documents / dec pages / finance notices in the email archive.

**Archive root** (`$ARCH` below):
`/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE`

> **Global caveat: the archive ends 2026-04-27. Today is 2026-07-02.** Anything that renewed, cancelled,
> or reinstated in May–June 2026 is invisible here. Every "current" claim below means "current per the
> latest evidence, dated ≤ 04/27/2026."

Confidence scale: **HIGH** = carrier-issued policy doc/dec page, or 3+ independent agreeing sources ·
**MEDIUM** = COI-only, or conflicting sources with a clear best candidate · **LOW** = inference.

---

## 1. emp3_solutions — COMPLETE, all policies current

All three policies 11/06/2025 → 11/06/2026. Current as of today.

```json
"policies": [
  {
    "line": "Commercial General Liability",
    "insurer_letter": "A",
    "policy_number": "SUB1579257",
    "eff_date": "11/06/2025",
    "exp_date": "11/06/2026",
    "addl_insured": true,
    "subr_wvd": true,
    "occur": true,
    "aggregate_basis": "PRO-JECT",
    "limits": {
      "each_occurrence": "1,000,000",
      "damage_to_rented_premises": "100,000",
      "med_exp": "5,000",
      "personal_adv_injury": "1,000,000",
      "general_aggregate": "2,000,000",
      "products_comp_op_agg": "2,000,000"
    }
  },
  {
    "line": "Commercial Auto",
    "insurer_letter": "B",
    "policy_number": "50019417101",
    "eff_date": "11/06/2025",
    "exp_date": "11/06/2026",
    "addl_insured": true,
    "subr_wvd": true,
    "auto_type": "Scheduled, Hired & Non-Owned Autos",
    "limits": { "combined_single_limit": "1,000,000" }
  },
  {
    "line": "Workers Compensation",
    "insurer_letter": "C",
    "policy_number": "WC307-0131466-2025A",
    "eff_date": "11/06/2025",
    "exp_date": "11/06/2026",
    "subr_wvd": true,
    "limits": {
      "el_each_accident": "1,000,000",
      "el_disease_ea_employee": "1,000,000",
      "el_disease_policy_limit": "1,000,000"
    }
  }
]
```

**Sources & confidence**

| Field | Confidence | Where to verify (≤1 min each) |
|---|---|---|
| GL number `SUB1579257` | **MEDIUM — conflict** | Template `templates/EMP_3_Solutions_Template.pdf`. But **all 7 delivered COIs (Jan–Feb 2026) print `SUB1579257-02`** — e.g. `$ARCH/Inbox/01001_Re_ COI Request/attachments/EMP 3 Solutions COI_Trent F Condominium.pdf` p1. No Trisura dec in archive. |
| GL dates 11/06/25–11/06/26 | HIGH | Template + all delivered COIs + IPFS notice `$ARCH/Inbox/00063_NOTICE OF INTENT TO CANCEL_301788.../attachments/NOTICE OF INTENT TO CANCEL_301788_EMP 3 SOLUTIONS .PDF` p2 (Trisura GL eff 11/06/25, 12-mo). |
| GL `damage_to_rented_premises` 100,000 | **MEDIUM — conflict** | Template says 100,000; **all 7 delivered COIs say 1,000,000**. One is wrong. |
| GL other limits | HIGH | Template p1; delivered COIs agree (1M/5K/1M/2M/2M). |
| Auto `50019417101` | HIGH | Template; all delivered COIs; **USI Paid Basis Report** `$ARCH/Inbox/00585_Paid Basis Report - PLEASE REVIEW/attachments/Paid Basis Report.pdf` p2 (Infinity CAU eff 11/06/25). |
| WC `WC307-0131466-2025A` | HIGH | Template; all delivered COIs; Paid Basis Report p2 (`WC30701314662`, LUBA WCO eff 11/06/25). |

**Open questions for Alex**
1. Is the in-force Trisura GL number `SUB1579257` or `SUB1579257-02`? (Suffix may be an endorsement rev.)
2. Damage-to-rented: 100K (current template) or 1M (every COI issued Jan–Feb)? Pull the Trisura dec.
3. The Jan IPFS intent-to-cancel (pay-by 01/30/26) was presumably paid — coverage kept getting certified through Feb — but no payment confirmation exists in the archive.

---

## 2. gd_mechanical — COMPLETE, but **AUTO IS EXPIRED**

GL / Umbrella / WC: 11/02/2025 → 11/02/2026, current. **Commercial Auto `50010517801` expired 05/03/2026** — two months ago.

```json
"policies": [
  {
    "line": "Commercial General Liability",
    "insurer_letter": "A",
    "policy_number": "10104588635",
    "eff_date": "11/02/2025",
    "exp_date": "11/02/2026",
    "addl_insured": true,
    "subr_wvd": true,
    "occur": true,
    "aggregate_basis": "POLICY",
    "limits": {
      "each_occurrence": "1,000,000",
      "damage_to_rented_premises": "100,000",
      "med_exp": "10,000",
      "personal_adv_injury": "1,000,000",
      "general_aggregate": "2,000,000",
      "products_comp_op_agg": "2,000,000"
    }
  },
  {
    "line": "Commercial Auto",
    "insurer_letter": "B",
    "policy_number": "50010517801",
    "eff_date": "05/03/2025",
    "exp_date": "05/03/2026",
    "addl_insured": true,
    "subr_wvd": true,
    "auto_type": "Scheduled, Hired & Non-Owned Autos",
    "limits": { "combined_single_limit": "1,000,000" }
  },
  {
    "line": "Umbrella Liability",
    "insurer_letter": "A",
    "policy_number": "10165492143",
    "eff_date": "11/02/2025",
    "exp_date": "11/02/2026",
    "occur": true,
    "limits": { "each_occurrence": "1,000,000", "aggregate": "1,000,000" }
  },
  {
    "line": "Workers Compensation",
    "insurer_letter": "C",
    "policy_number": "WC307-0131450-2025A",
    "eff_date": "11/02/2025",
    "exp_date": "11/02/2026",
    "subr_wvd": true,
    "limits": {
      "el_each_accident": "1,000,000",
      "el_disease_ea_employee": "1,000,000",
      "el_disease_policy_limit": "1,000,000"
    }
  }
]
```

**STALENESS — auto.** The renewal was still being marketed when the archive ends:
`Ref: G&D Mechanical Services - Commercial Auto Renewal` (Sent 04/07), `G&D Mechanical Services -
Commercial Auto Marketing` w/ `Marketing Summary.xlsx` (Inbox 04/13), `PRIORITY!!! G & D Mechanical
Services Co- Commercial...` (Inbox 04/21). **Whatever replaced 50010517801 on 05/03/2026 is not in the
archive.** The array above records the expired term as evidence; do not certify auto coverage from it.

**Sources & confidence**

| Field | Confidence | Where to verify |
|---|---|---|
| GL `10104588635` + limits | HIGH | Template `templates/G___D_Mechanical_Services_COI_Template.pdf`; delivered COIs (e.g. `$ARCH/Inbox/00076_G&D Mechanical COI - Test Entity Inc/attachments/G&D Mechanical_Test Entity Inc.pdf`); Paid Basis Report p2 (United Fire PKG eff 11/02/25). |
| Auto `50010517801` (expired term) | HIGH (historically) | Template; Ascendant endorsement threads `$ARCH/Inbox/00156`, `00183`, `00672`, `00846` all captioned "Policy#: 50010517801". |
| Umbrella `10165492143` 1M/1M | HIGH | Template; Paid Basis Report p2 (UNF UMC eff 11/02/25). |
| WC `WC307-0131450-2025A` | HIGH | Template; Paid Basis Report p2 (LUBA WCO eff 11/02/25). |

**Bonus find:** G&D also has a **United Fire Cyber policy `10187095536`** eff 11/02/25 (Paid Basis Report p2) — not on the COI template, listed in the JSON under `additional_policies_not_on_coi`.

**Open question for Alex:** what was bound for auto effective 05/03/2026 (carrier / number / dates / CSL)? Registry + template both need it before any COI with an auto line goes out for G&D.

---

## 3. absolute_air_solutions — COMPLETE (+1 off-template policy found)

Kemper/Infinity auto current but **renews 08/27/2026 (~8 weeks out)**. A second, Progressive auto policy exists that the registry doesn't know about.

```json
"policies": [
  {
    "line": "Commercial Auto",
    "insurer_letter": "A",
    "policy_number": "50026705601",
    "eff_date": "08/27/2025",
    "exp_date": "08/27/2026",
    "addl_insured": true,
    "subr_wvd": true,
    "auto_type": "Symbol 1 (Any Auto) on Symbol-1 template; Symbols 7/8/9 (Scheduled + Hired + Non-Owned) on Symbol-789 template",
    "limits": { "combined_single_limit": "1,000,000" }
  }
]
```

Off-template (JSON: `additional_policies_not_on_templates`) — **Progressive `872005650`**, 03/31/2026 → 03/31/2027,
CSL 1,000,000, one 2024 Chevrolet Express w/ GAP, ADDL **N** / SUBR **N**. Progressive issues its own COIs for it.

**Sources & confidence**

| Field | Confidence | Where to verify |
|---|---|---|
| `50026705601`, 08/27/25–08/27/26, CSL 1M | HIGH | Both templates (`Absolute_Air_Solutions_COI_Symbol_789.pdf`, `..._Symbol_1-_Copy.pdf`); delivered COIs (`$ARCH/Inbox/00920_Re_ New Vehicle COI/attachments/...CMC1249546.pdf`); Paid Basis Report p2 (Kemper CAU eff 08/27/25); thread subjects `Ref: Policy# 50026705601...` (Sent 02/17), `REF: Remove Vehicle - Policy# 50026705601` (Sent 04/09). |
| Progressive `872005650` | MEDIUM-HIGH | Only doc: `$ARCH/Sent Items/NEW_2026-04-09_170939_REF_ Remove Vehicle - Policy# 50026705601_11066148/attachments/Progressive COI - Absolute Air Solutions.pdf` p1; bind context in GAP-quote threads (Sent 03/18–03/31). |

**Template issue:** both templates print insurer letter **"B"** on the auto row while Infinity is INSURER **A**
(the only carrier on the cert). Proposed array uses A; fix the letter when the template is next touched.

**Open questions for Alex**
1. Confirm the Progressive policy number `872005650` and that the vehicle removed from 50026705601 (Apr 9) is the one Progressive now covers.
2. Should the Progressive policy get its own registry entry/template, or stay documented-only (Progressive self-serves its COIs)?
3. Diary: Infinity auto renews 08/27/2026.

---

## 4. ajf_roofing — COMPLETE, verified against carrier policy documents, all current

All four CNA policies 01/07/2026 → 01/07/2027. This is the strongest-sourced client: the full carrier policy
set is in the archive (`$ARCH/Inbox/00553_Policy Document(s) - AJF Roofing, Inc/attachments/`).

```json
"policies": [
  {
    "line": "Commercial General Liability",
    "insurer_letter": "A",
    "policy_number": "8035162052",
    "eff_date": "01/07/2026",
    "exp_date": "01/07/2027",
    "addl_insured": true,
    "subr_wvd": true,
    "occur": true,
    "aggregate_basis": "PRO-JECT",
    "deductible": "5,000 BI/PD per occurrence",
    "limits": {
      "each_occurrence": "1,000,000",
      "damage_to_rented_premises": "100,000",
      "med_exp": "15,000",
      "personal_adv_injury": "1,000,000",
      "general_aggregate": "2,000,000",
      "products_comp_op_agg": "2,000,000"
    }
  },
  {
    "line": "Commercial Auto",
    "insurer_letter": "A",
    "policy_number": "8035162049",
    "eff_date": "01/07/2026",
    "exp_date": "01/07/2027",
    "addl_insured": true,
    "subr_wvd": true,
    "auto_type": "Any Auto (symbol 1) + Hired + Non-Owned",
    "limits": { "combined_single_limit": "1,000,000" }
  },
  {
    "line": "Umbrella Liability",
    "insurer_letter": "B",
    "policy_number": "8035162066",
    "eff_date": "01/07/2026",
    "exp_date": "01/07/2027",
    "occur": true,
    "limits": { "each_occurrence": "3,000,000", "aggregate": "3,000,000" }
  },
  {
    "line": "Workers Compensation",
    "insurer_letter": "C",
    "policy_number": "8035490054",
    "eff_date": "01/07/2026",
    "exp_date": "01/07/2027",
    "subr_wvd": true,
    "limits": {
      "el_each_accident": "1,000,000",
      "el_disease_ea_employee": "1,000,000",
      "el_disease_policy_limit": "1,000,000"
    }
  }
]
```

**Sources & confidence** — all four lines **HIGH** (carrier docs):

| Line | Carrier doc (all under `$ARCH/Inbox/00553_Policy Document(s) - AJF Roofing, Inc/attachments/`) |
|---|---|
| GL | `2026-2027 GLI Policy.PDF` **p26** (dec: 1M occ / 100K rented / **15K med exp** / 1M P&A / 2M/2M, deductible endt CNA75119) · p100: underwriting co **National Fire Insurance of Hartford** |
| Auto | `2026-2027 CAU Policy.PDF` **p1** (`BUA 8035162049`, 01/07/26–01/07/27) · **p17** (dec: Covered Autos Liability **symbol 1**, $1,000,000; underwriting co National Fire Insurance Company of Hartford) |
| Umbrella | `2026-2027 UMB Policy.PDF` **p22** (dec: **The Continental Insurance Company**, CUE 8035162066, Each Incident 3,000,000 / Aggregate 3,000,000, SIR 10,000) · **p23** Schedule of Underlying: GL agg **Per Project: yes** |
| WC | `2026-2027 WCO Policy.PDF` **p18** (Information Page: **Valley Forge Insurance Company** NCCI 15032, 01/07/26–01/07/27, EL 1M/1M/1M) |

Same policy copies also at `$ARCH/Sent Items/NEW_2026-02-02_125701_FW_ RUSH Policy Copy - AJF ROOFING, INC 3047722917_9581604/attachments/`.

**Template fixes recommended (not blocking the registry)**
1. **Typo — auto policy number.** Template prints `9035162049`; carrier says `BUA 8035162049`. Archive-wide count: **8035162049 in 342 docs vs 9035162049 in 18** (the "NV2A / 2026 AJF COI" lineage the template inherited). The proposal uses 8035162049.
2. GL aggregate-basis checkbox is unmarked on the template; carrier's umbrella underlying schedule says **Per Project: yes** → mark PRO-JECT.
3. FYI the Feb "Policies Cancellation Request Effective 01/07/2026" traffic (`$ARCH/Inbox/00662-00665`) is the **old State Farm policies** being cancelled at CNA inception — not a problem with the current program.

**Open question for Alex:** none material. Optionally confirm with CNA that certs may show `8035162049` without the `BUA` prefix (that's how the delivered COIs print it).

---

## 5. apogee_hvac — data COMPLETE on paper, **IN-FORCE STATUS UNVERIFIED — highest-risk client**

> **Read this before trusting anything below.**
> 1. **LUBA WC was TERMINATED ~04/14/2026** (past-due payroll reports → non-payment). "APOGEE HVAC
>    SOLUTIONS LLC - TERMINATED POLICY" threads run 04/14–04/27; signed **no-loss letters** (04/22 and
>    04/27, both citing WC307-0131633) show reinstatement **in progress** when the archive ends. Outcome unknown.
> 2. **IPFS intent-to-cancel FLS-305556 (04/13/26):** the GL + BOTH excess policies cancel **05/01/2026**
>    unless $4,006.56 was paid (`$ARCH/Sent Items/NEW_2026-04-15_192701_.../attachments/NOTICE OF INTENT TO
>    CANCEL_305556_APOGEE HVAC SOLU.PDF` p1–2). Archive ends before the deadline. Outcome unknown.
> 3. The auto policy was **cancelled 02/01/2026 for non-payment** (`$ARCH/Inbox/00434`) and reappeared with
>    term 02/09/2026–02/09/2027. Non-payment is a pattern on this account.
>
> **As of today (07/02) none of Apogee's five policies should be presumed in force without checking.**

```json
"policies": [
  {
    "line": "Commercial General Liability",
    "insurer_letter": "A",
    "policy_number": "TSLBGL-0002210-00",
    "eff_date": "12/08/2025",
    "exp_date": "12/08/2026",
    "addl_insured": true,
    "subr_wvd": true,
    "occur": true,
    "aggregate_basis": "PRO-JECT",
    "deductible": "5,000 BI/PD per occurrence",
    "limits": {
      "each_occurrence": "1,000,000",
      "damage_to_rented_premises": "100,000",
      "med_exp": "Excluded",
      "personal_adv_injury": "1,000,000",
      "general_aggregate": "2,000,000",
      "products_comp_op_agg": "2,000,000"
    }
  },
  {
    "line": "Excess Liability (1st layer, follow-form)",
    "insurer_letter": "B",
    "policy_number": "07173314300",
    "eff_date": "12/08/2025",
    "exp_date": "12/08/2026",
    "occur": true,
    "limits": {
      "each_occurrence": "1,000,000",
      "aggregate": "1,000,000",
      "products_comp_op_agg": "1,000,000"
    }
  },
  {
    "line": "Excess Liability (2nd layer)",
    "insurer_letter": "C",
    "policy_number": "CXS4071612",
    "eff_date": "12/08/2025",
    "exp_date": "12/08/2026",
    "occur": true,
    "limits": { "each_occurrence": "4,000,000", "aggregate": "4,000,000" }
  },
  {
    "line": "Commercial Auto",
    "insurer_letter": "E",
    "policy_number": "50000190801",
    "eff_date": "02/09/2026",
    "exp_date": "02/09/2027",
    "addl_insured": true,
    "subr_wvd": true,
    "auto_type": "Owned Autos Only (per template; prior-agent COI showed Any Auto + Hired + Non-Owned)",
    "limits": { "combined_single_limit": "1,000,000" }
  },
  {
    "line": "Workers Compensation",
    "insurer_letter": "D",
    "policy_number": "WC307-0131633-2025A",
    "eff_date": "12/08/2025",
    "exp_date": "12/08/2026",
    "subr_wvd": true,
    "limits": {
      "el_each_accident": "1,000,000",
      "el_disease_ea_employee": "1,000,000",
      "el_disease_policy_limit": "1,000,000"
    }
  }
]
```

**Four discrepancies between this proposal and the current template** (all fed the 04/22 delivered COI that
the grader marked *incorrect*):

| # | Field | Template says | Evidence says | Proposal uses |
|---|---|---|---|---|
| 1 | WC policy number | `WC307-0131699-2025A` | **`WC307-0131633-2025A`** — LUBA-issued policy Information Page (`$ARCH/Sent Items/NEW_2026-04-23_133515_RE_ Ref_ Reliable Premium Management Introduction_11440324/attachments/25-26 WC - LUBA Apogee HVAC Solutions.pdf` **p14**); ALL of Alex's own Jan–Apr COIs; both no-loss letters; FHM termination + reinstatement notices; Lexington's Schedule of Underlying. `-0131699` traces only to the prior agent's 01/21 COI. | **0131633** (HIGH) |
| 2 | Insurer letters on Auto/WC rows | Auto=D, WC=E | On the template's own carrier list D=LUBA, E=Infinity. The auto policy (50000190801) is Infinity/Kemper; the WC is LUBA. Letters are swapped. | Auto=**E**, WC=**D** |
| 3 | Umbrella/Excess limits | 5,000,000 each occ + 5,000,000 agg | **Lexington 071733143-00 dec = 1M/1M/1M follow-form excess** (`$ARCH/Inbox/00186_FW_ Attached Policy for Apogee HVAC Solutions LLC (C_0717331/attachments/4069692.pdf` **p6**). Scottsdale CXS4071612 is the layer above at **4,000,000** (prior-agent COI `$ARCH/Inbox/00225_FW_ Apogee HVAC Solutions COI/attachments/52491592_1 Homes South Beach 1 Hotel South Beach_01212026.pdf`). Tower totals 5M; no single policy is 5M. | Two separate entries, 1M + 4M |
| 4 | GL med exp | 5,000 | **Excluded** per MS Transverse dec (`$ARCH/Sent Items/NEW_2026-01-30_192358_REF_ IMPORTANT - Cancellation_ Policy# IBL-P3VYDRW_9568068/attachments/GL Policy - Apogee HVAC Solutions LLC, TSLBGL-0002210-00.pdf` **p2**: "MEDICAL EXPENSE LIMIT $ Excluded"); prior-agent COI shows $0. | **Excluded** (HIGH) |

**Remaining confidence gaps**
- **Scottsdale CXS4071612 — MEDIUM.** No Scottsdale dec in archive. Existence + eff 12/08/25 confirmed by IPFS
  notice p2 ($8,048 premium) and USI Paid Basis Report p2; the 4M limit comes only from the prior agent's 01/21 COI.
- **Auto dates — MEDIUM.** 02/09/2026–02/09/2027 comes from the template + 04/22 COI; the policy number itself is
  solid (Kemper suspense thread `$ARCH/Inbox/00675`), but confirm the post-cancellation term and covered-auto symbol.

**Open questions for Alex (ordered by risk)**
1. Did Apogee pay IPFS by 05/01/2026? If not, GL + both excess layers died that day.
2. Was the LUBA WC reinstated after the 04/27 no-loss letter? (Check FHMConnect / Maria Simpson, msimpson@fhmic.com.)
3. Fix the template: WC number → 0131633, swap Auto/WC letters, split the excess tower (1M Lexington + 4M Scottsdale), med exp → 0/Excluded. Until then every Apogee COI issued repeats the 04/22 mistakes.
4. Confirm Scottsdale limits/attachment and the auto term.

---

## Suggested placement

Same as `305_power_corp`: each array goes under the client's default template object
(`clients[i].templates[0].policies`) in `coi_client_registry.json`. For `absolute_air_solutions` the two
templates share the one Infinity policy — put the same array on both, or on the default only (Alex's call).
The off-COI extras (G&D cyber, Absolute Air's Progressive unit) are in `registry_gap_data.json` under
`additional_policies_*` keys and are NOT part of the paste-able arrays.

## Verification shortlist (the five things most worth Alex's minute)

1. **Apogee in-force status** — IPFS payment (deadline 05/01) and LUBA WC reinstatement. Everything else about Apogee is moot if these lapsed.
2. **G&D auto renewal** — what replaced 50010517801 after 05/03/2026.
3. **Apogee WC number 0131633 vs template's 0131699** — carrier doc says 0131633; fix template before next issuance.
4. **AJF auto number 8035162049 vs template's 9035162049** — carrier doc wins; template typo.
5. **EMP3 GL** — `-02` suffix and 100K-vs-1M rented-premises limit (template vs every issued COI).
