# Policy Inventory — all 9 clients (as of 2026-07-04)

**What this is:** per-client inventory of which POLICIES we actually hold, where the data comes from, and which periods are stale. Built read-only from four sources:

1. `coi_client_registry.json` (working tree) — `policies` arrays exist for **305 Power, Rolando's, Central Comfort, Clayton** only.
2. `coi_endorsement_registry.json` on branch `feat/a9-endorsements` (evidence annotations + Alex's 07/02–07/03 confirmations).
3. Google Drive Phase 1 manifests + `training/registry_gap/drive_extraction.json` (carrier policy docs actually in Drive, by filename/term — files not re-downloaded).
4. `training/registry_gap/FINAL_RECONCILIATION.{md,json}` and `training/clayton/clayton_data.json` (prior agents' per-field provenance).

**Source legend:** `registry` = in the live registry policies array · `policy doc` = carrier-issued policy/dec on file in Drive · `COI-derived` = only evidence is a broker-issued COI (no carrier doc) · `MISSING` = no usable document.
**Staleness flags** relative to **2026-07-04**, 60-day window (expiring on/before 2026-09-02).

---

## 1. 305 Power Corp — registry array: YES · policy docs: YES

| Line | Carrier | Policy # | Period | Source | Flag |
|---|---|---|---|---|---|
| GL | Clear Blue | BGFL9010651400 | 07/15/2025–07/15/2026 | registry + policy doc (`GL Policy.pdf`, read in full) | **EXPIRES IN 11 DAYS — renewal QUOTED (Obsidian), NOT BOUND** |
| Auto | Progressive Express | 862396417 | 08/29/2025–08/29/2026 | registry + policy doc (dec read; full `CA Policy.pdf` also on file) | **Expires in 56 days** (Kemper replacement quote in play) |
| Excess | Clear Blue | BXFL9000890400 | 07/15/2025–07/15/2026 | registry + policy doc (read in full) | **EXPIRES IN 11 DAYS — renewal NOT BOUND** |
| WC | LUBA | WC307-0132038-2026A | 04/11/2026–04/25/2027 | registry + policy doc **but the bound policy is an unreadable image scan** — limits rest on COI + quote 183678 | Current; get a readable copy |

Also on file (outdated): prior WC policy (Employers) — superseded.

## 2. Rolando's HVAC — registry array: YES · policy docs: YES

| Line | Carrier | Policy # | Period | Source | Flag |
|---|---|---|---|---|---|
| GL | Trisura | NRG-DBG-GL15062 | 07/15/2025–07/15/2026 | registry + policy doc (full Trisura policy, read) | **EXPIRES IN 11 DAYS — renewal quote SUB1737578-01 exists in two versions (06/10 $50,027 / 06/30 $69,874), NOT BOUND** |
| Auto | Ascendant | CA-74829-0 | 12/15/2025–**12/15/2026** | policy doc (full Ascendant policy) — registry says **12/25/2026 and "CA-74829", both wrong** vs the dec | Current, but **fix registry exp date + number** |
| WC | (Technology/AmTrust TWC4577701) | — | 03/23/2025–03/23/2026 | policy doc on file but **EXPIRED**; WC is now ANOTHER BROKER'S line (Alex 07/02) | Not ours — correct to exclude |

### Special check — Rolando's GL per-project aggregate
- **Blanket AI (CG 20 10_B), WOS (CG 24 04_B), P&NC (CG 20 01_B): carrier-verified** from the Trisura policy on file — solid.
- **Per-project aggregate: NOT verified.** The registry's Rolando's GL entry has **no `aggregate_basis` field at all** (305 and Clayton do). The reconciliation proposed `PRO-JECT` but its own provenance note says: *"TEMPLATE marks PRO-JECT (X at x=83/y=363); per-project aggregate not independently seen in the Trisura dec extraction — verify before relying on it."*
- **What's missing:** a designated-project general aggregate endorsement (CG 25 03 or Trisura equivalent) on the NRG-DBG-GL15062 forms schedule. The full policy IS on file in Drive — its forms schedule was read for AI/WOS/P&NC but no per-project aggregate form surfaced. Either the endorsement isn't there, or it needs a targeted re-read.
- **Action:** confirm against the Trisura forms schedule (or ask the carrier) before certifying per-project aggregate — and bake the answer into the 07/15 renewal binding, since the whole GL is about to be replaced anyway.

## 3. EMP 3 Solutions — registry array: **NO** · policy docs: YES

| Line | Carrier | Policy # | Period | Source | Flag |
|---|---|---|---|---|---|
| GL | Trisura (via Novatae) | NRG-DBG-GL17416 (carrier) — template/COIs print SUB1579257(-02), the **submission number** | 11/06/2025–11/06/2026 | policy doc (`GL Novatae Policy.pdf`) — **not in registry** | Alex ruling pending: what should certs print? |
| Auto | Infinity/Kemper | 50019417101 | 11/06/2025–11/06/2026 | policy doc (full policy + blanket-endorsement dec page) — **not in registry** | OK |
| WC | LUBA | WC307-0131466-2025A | 11/06/2025–11/06/2026 | policy doc (full policy incl. endorsement schedule) — **not in registry** | Schedule shows **NO waiver** though template marks SUBR WVD; Alex asking LUBA to add it |

## 4. Central Comfort Air Conditioning — registry array: YES · policy docs: YES (partly unreadable)

| Line | Carrier | Policy # | Period | Source | Flag |
|---|---|---|---|---|---|
| GL (UFG **BOP**) | United Fire & Casualty | 10176227110 | 12/26/2025–12/26/2026 | registry + policy doc on file **but the 47.8MB UFG PDF is an unreadable scan** — details corroborated via COI + proposal | Get a readable/OCR'd copy |
| WC | LUBA | WC307-0131650-2025A | 12/26/2025–12/26/2026 | registry + policy doc (fully readable, incl. WC 00 03 13 blanket waiver) | Clean |
| Property | United Fire & Casualty | 10176227110 | 12/26/2025–12/26/2026 | registry + same BOP | Registry's "5,000" is a **deductible, not a limit** |

Outdated on file: prior Phly GL PPK2659916-002 (cancelled eff 12/26/2025).

## 5. G&D Mechanical — registry array: **NO** · policy docs: MOSTLY (auto dec missing)

Note: the "GL" is a **UFG BOP-Pro** bundling GL + property, and a separate **UFG Cyber policy exists in Drive** (never extracted) — matches Alex's description of the BOP package.

| Line | Carrier | Policy # | Period | Source | Flag |
|---|---|---|---|---|---|
| GL (BOP) | United Fire Group | 10104588635 | 11/02/2025–11/02/2026 | policy doc (150-pp BOP, dec read visually — text layer garbled) — **not in registry** | OK |
| Umbrella | United Fire Group | 10165492143 | 11/02/2025–11/02/2026 | policy doc (79-pp, dec read visually) — **not in registry** | OK |
| WC | LUBA | WC307-0131450-2025A | 11/02/2025–11/02/2026 | policy doc (full, endorsement schedule read) — **not in registry** | **NO waiver on schedule** though template marks SUBR WVD |
| Auto | Infinity/Kemper | 50010517801 | 05/03/2026–05/03/2027 | **COI-derived only** — the only dec on file is the **EXPIRED** 05/03/2025–05/03/2026 term; current term rests on the 06/30/2026 Winter Park COI. (Unread 8.4MB `Kemper Commercial Auto.PDF` in Drive is likely the *old* term.) | **MISSING current-term dec — Alex to provide (already agreed 07/03)** |
| Cyber | United Fire Group | ? | ? (presumed 11/02 term) | policy doc exists in Drive (`UFG Cyber.PDF`) but **never read** | Extract when needed |

## 6. Absolute Air Solutions — registry array: **NO** · policy docs: YES (auto — the only line we control)

| Line | Carrier | Policy # | Period | Source | Flag |
|---|---|---|---|---|---|
| Auto (primary) | Infinity | 50026705601 | 08/27/2025–08/27/2026 | policy doc (dec w/ endorsements + full policy) — **not in registry** | **Expires in 54 days** — Alex plans to pitch the other lines at this renewal |
| Auto (secondary) | Progressive | 872005650 | 03/31/2026–03/31/2027? | **DISPUTED** — archive has a Progressive-issued COI (bound), Drive has only an unbound quote | Confirm binding status |
| GL / WC / Umbrella / Prop | (Nationwide / RetailFirst) | — | expired 06/05/2026 & 06/13/2026 | other broker's lines (Alex 07/02); expired docs on file are historical only | Not ours — correct to exclude |

## 7. AJF Roofing — registry array: **NO** · policy docs: YES (best-documented client)

| Line | Carrier | Policy # | Period | Source | Flag |
|---|---|---|---|---|---|
| GL | National Fire Ins. of Hartford (CNA) | 8035162052 | 01/07/2026–01/07/2027 | policy doc (full 26-27 policy; **per-project aggregate carrier-verified**, CNA74705XX item 11) — **not in registry** | Template auto # typo (9035162049) + unmarked PRO-JECT box already flagged |
| Auto | CNA | BUA 8035162049 | 01/07/2026–01/07/2027 | policy doc — **not in registry** | OK |
| Umbrella | Continental (CNA) | CUE 8035162066 | 01/07/2026–01/07/2027 | policy doc — **not in registry** | OK |
| WC | Valley Forge (CNA) | 8035490054 | 01/07/2026–01/07/2027 | policy doc — **not in registry** | OK |

Outdated on file: 24-25 Ironshore GL/UMB, Bridgfield WC, State Farm vehicle policies — all superseded.

## 8. Apogee HVAC Solutions — registry array: **NO** · policy docs: YES (auto dec unreadable)

Alex confirmed 07/02: fully reinstated, **all 5 lines in force through 12/08/2026** (resolves the IPFS/LUBA cancellation scares).

| Line | Carrier | Policy # | Period | Source | Flag |
|---|---|---|---|---|---|
| GL | MS Transverse | TSLBGL-0002210-00 | 12/08/2025–12/08/2026 | policy doc — **not in registry** | Med exp is **Excluded** (template wrongly prints 5,000) |
| Excess 1st layer | Lexington | 07173314300 | 12/08/2025–12/08/2026 | policy doc (1M/1M/1M follow-form) — **not in registry** | Template wrongly prints a 5M layer |
| Excess 2nd layer | Scottsdale | CXS4071612 | 12/08/2025–12/08/2026 | policy doc (4M/4M xs) — **not in registry** | — |
| Auto | Infinity/Kemper | 50000190801 | **CONFLICT: 02/09/2026–02/09/2027 vs 12/08/2025–12/08/2026** | dec on file is an **unreadable scan**; term rests on conflicting COIs/renewal notice | **Get a readable 26-term dec** |
| WC | LUBA | WC307-0131633-2025A | 12/08/2025–12/08/2026 | policy doc — **not in registry** | Template prints wrong number (-0131699) |

## 9. Clayton Mechanical — registry array: YES · policy docs: **NONE — all COI-derived**

Package is BOP-style GL + Auto + Umbrella + WC, all sharing one term. Registry array exists (added at 07/03 onboarding) but **every value traces to two broker COIs** (`COI 070126.pdf`, `Delta Hotels COI.pdf`); the only carrier paper in the proposal packet is a Westfield dec marked **NO COVERAGE BOUND** and quotes whose dates/limits disagree with the bound COIs (AIG excess quoted 3M, bound at 2M — unexplained).

| Line | Carrier | Policy # | Period | Source | Flag |
|---|---|---|---|---|---|
| GL | Westfield | CWP 530335F | 06/01/2026–06/01/2027 | registry, **COI-derived** | **No policy doc — request from Alex** |
| Auto | Infinity | CA945173MGA | 06/01/2026–06/01/2027 | registry, **COI-derived** | **No policy doc** |
| Umbrella | National Union (AIG) | 47329390 | 06/01/2026–06/01/2027 | registry, **COI-derived** (limit 2M vs 3M quoted — unexplained) | **No policy doc** |
| WC | Technology (AmTrust) | 13705262 | 06/01/2026–06/01/2027 | registry, **COI-derived** (quote showed a 6/15 term — bound COIs say 6/01) | **No policy doc** |

---

# Summary for Alex

## Policy documents you need to send / pull

1. **Clayton Mechanical — everything.** Zero carrier policy docs; all four lines are COI-derived. Send Westfield GL, Infinity auto, National Union umbrella, and AmTrust WC policies/decs (and clear up why the umbrella bound at 2M when AIG quoted 3M).
2. **G&D Mechanical — Kemper auto 26-27 renewal dec** (05/03/2026–05/03/2027, policy 50010517801). You already agreed to provide this 07/03; the only dec on file expired 05/03/2026.
3. **Apogee — readable Infinity auto dec** for 50000190801. The scan on file is unreadable and two of your own COIs printed different terms (02/09 vs 12/08).
4. **Readable copies (OCR or re-pull):** 305 Power LUBA WC (bound policy is an image scan), Central Comfort UFG BOP (47.8MB scan — GL details rest on COI/proposal only), G&D UFG Cyber (on file, never read).

## Periods expired or expiring within 60 days

| Client / line | Expires | Status |
|---|---|---|
| **305 Power GL + Excess** | **07/15/2026 (11 days)** | Obsidian quotes only — **NOT BOUND**. No COIs dated on/after 07/15 until bound numbers are loaded. |
| **Rolando's GL** | **07/15/2026 (11 days)** | Trisura renewal SUB1737578-01 quoted twice, **NOT BOUND** — binding meeting was set for "next week" as of 07/02. |
| Absolute Air Infinity auto | 08/27/2026 (54 days) | Renewal = Alex's pitch window for the other lines. |
| 305 Power Progressive auto | 08/29/2026 (56 days) | Kemper replacement quote in play. |
| Already expired, other broker (fine to ignore): Rolando's WC (03/23/2026), Absolute Air GL/UMB/Prop (06/05/2026) + WC (06/13/2026). Superseded old paper: AJF 24-25 lineage, Central Phly GL, G&D 25-26 auto dec, 305 prior WC. | | |

## Outdated/wrong data in the live registry

- **Rolando's auto:** registry exp **12/25/2026** and number **CA-74829** — dec says **12/15/2026** / **CA-74829-0**.
- **305 GL/Excess:** correct today, dead in 11 days — swap in bound renewal numbers before 07/15.
- **Missing `policies` arrays entirely:** EMP3, G&D, Absolute Air, AJF, Apogee (5 of 9) — fully reconciled proposals sit ready in `training/registry_gap/FINAL_RECONCILIATION.json`.

## Rolando's per-project aggregate (asked specifically)

Blanket AI, WOS, and P&NC on the GL are **carrier-verified** from the Trisura policy on file. **Per-project aggregate is NOT** — the only evidence is the template's own PRO-JECT checkbox; the reconciliation explicitly flagged it as "not independently seen in the Trisura dec extraction — verify before relying on it," and the registry entry has no `aggregate_basis` field. Need: CG 25 03 (or Trisura equivalent) sighted on the NRG-DBG-GL15062 forms schedule — or confirmed on the 07/15 renewal when it binds.
