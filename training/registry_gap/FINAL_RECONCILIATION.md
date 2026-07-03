# FINAL RECONCILIATION — all 8 clients, 4 sources

**Date:** 2026-07-02 · **Status: PROPOSAL — nothing written to `coi_client_registry.json` or `templates/`.**
Machine-readable version with full per-field provenance: `FINAL_RECONCILIATION.json` (same folder).

**Sources reconciled**, in precedence order (a conflict is never silently resolved — every one is shown):
1. **DRIVE** — `drive_extraction.json`, today's extraction of carrier policy docs in Google Drive (docs through June 2026)
2. **ARCHIVE** — `registry_gap_data.json` / `REGISTRY_PROPOSAL.md`, email-archive extraction (ends 2026-04-27)
3. Broker-issued COIs (cited inside both of the above)
4. **TEMPLATE** — what each PDF in `templates/` actually prints (fitz text+coordinate extraction, 2026-07-02)
5. **REGISTRY** — `coi_client_registry.json`

---

## (a) COVERAGE ALERTS — read these first

### CRITICAL

**A1. Rolando's HVAC — WC expired 03/23/2026, no replacement found.**
AmTrust/Technology Insurance `TWC4577701` (03/23/2025–03/23/2026, EL 1M/1M/1M) lapsed **101 days ago**. No successor WC document anywhere in the client's Drive tree.
*Evidence:* DRIVE `WC POLICY.pdf` Information Page (WC 99 00 01 B) + staleness flag "no replacement/renewal WC document found anywhere in the client folder tree."
*Silver lining:* WC is not in the registry and not on the template, so the automation can't accidentally certify it — but the client may be bare on WC.
→ **Confirm whether Rolando's has current WC. Decline any WC cert request until proof exists.**

**A2. Absolute Air — GL expired ~06/05/2026, WC expired 06/13/2026, Umbrella expired ~06/05/2026 — no renewals found.**
- WC: RetailFirst `520-51006`, dec page reads 06/13/2025–06/13/2026 (file title says 06-05 — the dec wins). Expired **19 days ago**.
- GL + Umbrella (Nationwide): dates from file titles only (dec pages would not extract — policy numbers/limits unknown, LOW confidence), both sitting in the OLD folder with **no 26-27 renewal anywhere** in the tree.
- The **only verifiably in-force coverage** today is the Infinity auto `50026705601` (through 08/27/2026).
*Evidence:* DRIVE `WC - Retail First- 06-05-25-26.pdf` Information Page; `GL - NW - 06-05-25-26.pdf` / `UMB - NW - 06-05-25-26.pdf` extraction failures + staleness flags.
→ **Ask the client: did GL/WC/Umbrella/Property/IM renew for 26-27, or is the account auto-only now?** (Registry/templates are auto-only, so the automation isn't exposed.)

**A3. 305 Power — GL + Excess expire 07/15/2026 (13 days), renewals QUOTED NOT BOUND.**
Clear Blue GL `BGFL9010651400` and Excess `BXFL9000890400` both end 07/15/2026. Drive has only **Obsidian Specialty quotes** (RT-Obsidian GL + XS Revised, 05/14/2026); the cost-comparison workbook (06/05/2026) still lists Clear Blue as "Current". Note the Obsidian GL quote carries a **$5,000 per-occurrence deductible** vs the current $0.
*Evidence:* DRIVE 305 Power found_docs + staleness flags.
→ **Confirm binding before 07/15. No COI dated on/after 07/15/2026 until new policy numbers are loaded.**

**A4. Rolando's HVAC — GL expires 07/15/2026 (13 days), renewal QUOTED NOT BOUND.**
Trisura `NRG-DBG-GL15062` ends 07/15/2026. Renewal quote `SUB1737578-01` exists in **two versions with very different premiums**: 06/10/2026 ($50,027.25) and 06/30/2026 V2 ($69,874.33, revised exposures). No binder in Drive.
*Evidence:* DRIVE `Trisura Renewal Quote.pdf` + `Renewal Quote V2.pdf`.
→ **Confirm which version binds and get the binder before 07/15.**

**A5. Apogee — GL + both excess layers may have died 05/01/2026 (IPFS non-payment).**
IPFS intent-to-cancel FLS-305556 (04/13/2026): MS Transverse GL + Lexington + Scottsdale cancel 05/01/2026 unless $4,006.56 paid. Archive ends 04/27; Drive (today) shows the policy docs but **no evidence of payment, cancellation, or reinstatement either way**.
*Evidence:* ARCHIVE Sent 2026-04-15 `NOTICE OF INTENT TO CANCEL_305556_APOGEE HVAC SOLU.PDF` p1-2; DRIVE cancellation folder holds only prior Thimble/Ascendant letters.
→ **Verify IPFS payment before issuing ANY Apogee GL/excess cert.**

**A6. Apogee — WC terminated ~04/14/2026, reinstatement outcome unknown.**
LUBA `WC307-0131633-2025A` terminated for past-due payroll reports/non-payment; two signed no-loss letters (04/22 and 04/27) show reinstatement in progress when the archive ends. Nothing in Drive confirms the outcome.
*Evidence:* ARCHIVE "TERMINATED POLICY" threads 04/14–04/27 + no-loss letters.
→ **Check FHMConnect / Maria Simpson (msimpson@fhmic.com). No Apogee WC cert until confirmed.**

**A7. G&D — two template lineages disagree on GL limits; the one that issued the 06/30/2026 COI is wrong.**
This repo's template prints **10,000 med exp / 100,000 rented premises — matching the UFG BOP dec**. The Drive-side "New Template with the New Auto policy" lineage (which produced the 06/30/2026 City of Winter Park COI) prints **5,000 / 1,000,000** — a 10x overstatement of rented-premises coverage.
*Evidence:* TEMPLATE fitz (10,000 at y=327; 100,000 at y=315) vs DRIVE UFG BOP dec pp.13-14 + Winter Park COI.
→ **Decide which template file is live; fix/retire the Drive copy.**

### WARNING

- **G&D auto renewal dec missing** — current term 05/03/2026–05/03/2027 rests solely on the 06/30/2026 broker COI; repo template still prints the **expired** 05/03/2025–05/03/2026 term (see template error T-GD1). Pull the Kemper 26-27 dec.
- **Apogee auto term conflict** — template + 04/22 COI say 02/09/2026–02/09/2027 (post-cancellation rewrite); Drive's renewal notice + the 03/23/2026 Miami Dade COI say 12/08/2025–12/08/2026 for the same number. Two broker COIs a month apart printed different terms. LOW confidence — needs the actual dec.
- **Absolute Air Progressive policy** — ARCHIVE has a Progressive-issued COI for `872005650` (03/31/2026–03/31/2027 → bound); DRIVE has only an unbound quote dated 03/24/2026. Sources disagree on binding status.
- **Renewal diary:** Absolute Air Infinity auto 08/27/2026 · 305 Power auto 08/29/2026 (Kemper replacement quote in play) · EMP3 all lines 11/06/2026 · G&D GL/UMB/WC 11/02/2026 · Central Comfort 12/26/2026.
- **EMP3** — Jan-2026 IPFS intent-to-cancel on the GL was presumably paid (COIs kept issuing) but payment is confirmed nowhere.

---

## (b) TEMPLATE ERRORS — printed value vs carrier document

All coordinates are fitz word positions on page 1. ADDL INSD column ≈ x=183.5, SUBR WVD ≈ x=201.5.
**24 findings, 12 CRITICAL.**

### EMP 3 Solutions (`EMP_3_Solutions_Template.pdf`)

| # | Field | Template prints | Carrier doc says | Severity |
|---|---|---|---|---|
| T-E1 | GL policy number | `SUB1579257` | **`NRG-DBG-GL17416`** (Trisura Common Policy Declarations, DRIVE `GL Novatae Policy.pdf`). All 7 delivered COIs print a third variant, `SUB1579257-02`. SUB1579257 appears **only** in broker files — it's the Novatae submission number. | **CRITICAL** |
| T-E2 | WC SUBR WVD | X (marked Y, x=201.5/y=483.7) | LUBA `WC307-0131466-2025A` full Schedule of Endorsements has **no waiver endorsement** (no WC 00 03 13) — DRIVE `WC LUBA POLICY.PDF` | **CRITICAL** |
| T-E3 | Description text | "…waiver … applies for General Liability, **Umbrella**, and **Employer's Liability**…" | EMP3 has **no umbrella policy at all**, and the EL waiver is unsupported (T-E2) | WARNING |

Verified OK: GL 100K rented / 5K med exp **match the carrier dec** — the 1,000,000 rented on all 7 delivered COIs was the wrong value (archive conflict resolved by the Drive dec). Auto and WC numbers/dates/limits all match.

### AJF Roofing (`AJF_Roofing_Inc_COI_Template.pdf`)

| # | Field | Template prints | Carrier doc says | Severity |
|---|---|---|---|---|
| T-A1 | Auto policy number | `9035162049` | **`BUA 8035162049`** — issued policy dec + umbrella Schedule of Underlying; 342 archive docs print 8035162049 vs 18 with the 9 (the inherited NV2A COI lineage) | **CRITICAL** |
| T-A2 | GEN'L AGG APPLIES PER | no box marked (no X in y=360-367 band) | **Per Project** (CNA74705XX item 11; umbrella underlying "Per Project: yes") → mark PRO-JECT | WARNING |
| T-A3 | Umbrella ADDL/SUBR | neither marked, but description text claims umbrella AI + waiver | CUE 8035162066 has blanket waiver (condition W) + follow-form AI — marks are supportable; grid and text are inconsistent | WARNING |

Verified OK: GL (incl. 15K med exp, $5K BI/PD ded, per-project), Umbrella 3M/3M, WC (incl. WC 00 03 13 blanket waiver — SUBR X is **supported**), auto CSL/dates/symbol — all match carrier docs from two independent sources.

### Apogee HVAC (`Apogee_HVAC_Solutions_COI_Template.pdf`) — worst template in the book

| # | Field | Template prints | Carrier doc says | Severity |
|---|---|---|---|---|
| T-P1 | WC policy number | `WC307-0131699-2025A` | **`WC307-0131633-2025A`** — LUBA Information Page (DRIVE p14 + ARCHIVE Sent 2026-04-23), all of Alex's own Jan–Apr COIs, both no-loss letters, FHM notices, Lexington's underlying schedule. `-0131699` traces only to the prior agent's 01/21 COI. This exact error made the 04/22 delivered COI grade "incorrect". | **CRITICAL** |
| T-P2 | Auto/WC insurer letters | Auto=**D**, WC=**E** | On the template's own carrier list D=LUBA, E=Infinity. Auto (50000190801) is Infinity→**E**; WC is LUBA→**D**. **Swapped.** | **CRITICAL** |
| T-P3 | Excess tower limits | Row B (Lexington `07173314300`): EACH OCC **5,000,000**; Row C (Scottsdale `CXS4071612`): AGG **5,000,000** | **Lexington = 1M/1M/1M** follow-form (DRIVE 1st-layer dec GLX 0003); **Scottsdale = 4M/4M** xs the Lexington (DRIVE 2nd-layer dec XLS-D-1 Item 4). Tower totals 5M; **no single 5M policy exists** — cert overstates Lexington 5x. | **CRITICAL** |
| T-P4 | GL MED EXP | `5,000` | **"MEDICAL EXPENSE LIMIT $ Excluded"** (CG 21 35) — MS Transverse dec (DRIVE + ARCHIVE p2); prior-agent COI printed $0 | **CRITICAL** |
| T-P5 | Umbrella ADDL/SUBR | both X (x=183.5/202.0, y=448.0) | Unverified on both excess layers (Lexington follow-form, Scottsdale wording never read) | WARNING |
| T-P6 | Auto ADDL/SUBR | both X (y=386.2) | No readable carrier doc shows auto AI/waiver; Miami Dade COI silent on auto | WARNING |
| T-P7 | Auto covered-autos box | OWNED AUTOS ONLY (x=43.1/y=410.4) | Unverified — prior-agent COI marked ANY AUTO + Hired + Non-Owned; dec is an unreadable scan | WARNING |

### G & D Mechanical (`G___D_Mechanical_Services_COI_Template.pdf`)

| # | Field | Template prints | Carrier doc says | Severity |
|---|---|---|---|---|
| T-GD1 | Auto dates | `05/03/2025 – 05/03/2026` — **EXPIRED** | Policy 50010517801 renewed **05/03/2026–05/03/2027** (06/30/2026 Winter Park COI; no renewal dec in Drive yet) | **CRITICAL** |
| T-GD2 | WC SUBR WVD | X (x=201.5/y=483.5) | LUBA `WC307-0131450-2025A` endorsement schedule read in full — **no waiver endorsement** (no WC 00 03 13) | **CRITICAL** |
| T-GD3 | Description text | waiver "for General Liability, Umbrella, Employer's , and Commercial Auto" (also stray space) | EL part unsupported (T-GD2); GL/UMB/Auto waiver claims rest on COI wording, endorsements unsighted | WARNING |

Verified OK: GL 10K med / 100K rented **match the BOP dec** (the Drive-lineage 5K/1M is the wrong one — alert A7). Umbrella 1M/1M matches dec. WC number/dates/limits match.

### Rolando's HVAC (`Rolando_s_HVAC_COI_Template.pdf`)

| # | Field | Template prints | Carrier doc says | Severity |
|---|---|---|---|---|
| T-R1 | Auto EXP date | `12/25/2026` | **`12/15/2026`** — Ascendant Business Auto Declarations Item One ("From 12/15/2025 to 12/15/2026") + 01/05/2026 Maitland COI | **CRITICAL** |
| T-R2 | Auto ADDL + SUBR | both X (x=183.5/201.5, y=386.2) + description claims auto AI & waiver | Ascendant `CA-74829-0` ML-002 form schedule has **no AI endorsement and no waiver endorsement**; the broker's own 01/05/2026 COI left both unmarked | **CRITICAL** |
| T-R3 | Auto insurer letter | `A` (= Trisura on this template) | Auto is **Ascendant = B**. Registry has the same wrong letter. | **CRITICAL** |
| T-R4 | Auto policy number | `CA-74829` | Dec prints `CA-74829-0` (suffix) | WARNING |
| T-R5 | Description typo | "General Liabilityand Commercial Auto" | cosmetic | WARNING |

Verified OK: GL — carrier, number (modulo the space: template "NRG-DBG-GL 15062" vs carrier "NRG-DBG-GL15062"), dates, all six limits, blanket AI + P&NC + CG 24 04 waiver.

### Absolute Air (both `Absolute_Air_Solutions_COI_Symbol_*.pdf`)

| # | Field | Template prints | Carrier doc says | Severity |
|---|---|---|---|---|
| T-AB1 | Auto insurer letter | `B` — but INSURER B is blank; Infinity is INSURER **A** (only carrier listed) | letter must be A | WARNING |
| T-AB2 | GL agg checkbox | stray X on POLICY box (x=43/y=363) with the whole GL section otherwise empty | no GL exists; band should be blank | WARNING |

Verified OK: auto number/dates/CSL and blanket AI + WOS (11/03/2025 endorsement) confirmed from the policy cover page + dec.

### 305 Power (`305_Power_Corp_COI_Template.pdf`)

| # | Field | Template prints | Carrier doc says | Severity |
|---|---|---|---|---|
| T-3P1 | INSURER A row | **two overlapping text objects**: "Clear Blue Insurance Company / 28860" AND "LUBA Casualty Ins Co / 12472" at identical coordinates (y=168.8) | INSURER A = Clear Blue only (LUBA is C, printed correctly at y=191.3) — leftover LUBA object never deleted; renders garbled on every cert | WARNING |
| T-3P2 | WC row letter + dates | **both `C` and `A`** overlapped at x=22.9/y=484.5; eff/exp dates printed **twice** (y=483.7 and y=485.2) | single "C", dates once — stale text objects under the corrected ones | WARNING |
| T-3P3 | Description text | waiver "applies for General Liability, **Umbrella**, and Employer's Liability" | Excess policy's forms schedule shows **no waiver endorsement** (DRIVE, read in full) | WARNING |

Verified OK: all four lines match carrier docs — GL 1M/300K/10K/1M/2M/2M, Auto $1M CSL + blanket AI/WOS, Excess 2M/2M, WC number/dates/EL limits.

### Central Comfort (`Central_Comfort_Air_Conditioning_Inc_COI.pdf`)

| # | Field | Template prints | Carrier doc says | Severity |
|---|---|---|---|---|
| T-C1 | Insured address | "12320 SW 129th Ct, Miami," + "Miami, FL 33186" (city duplicated; registry has the same duplication) | policy: "12320 SW 129th Ct, Miami FL 33186"; ACORD 35 shows **12310** — minor street-number discrepancy unresolved | WARNING |

Verified OK: everything else — GL all six limits, WC number/dates/EL 1M/1M/1M and **WC waiver X is supported** (WC 00 03 13 Blanket on the carrier schedule), Property row. Cleanest client in the book.

---

## (c) Proposed final `policies` arrays

Full arrays with per-field source + confidence are in `FINAL_RECONCILIATION.json` → `clients.<id>.policies`
(305_power_corp registry schema; insurer letters mapped against each template's carrier block). Summary of what changed vs. what each source believed:

| Client | Lines proposed | Key decisions (conflicts shown, not hidden) |
|---|---|---|
| 305_power_corp | GL, Auto, Excess, WC | **No changes** — registry fully verified against carrier docs. WC limits remain medium (bound policy is an unreadable scan). |
| rolandos_hvac | GL, Auto (**no WC — expired, none found**) | Auto: exp **12/15/2026** (registry says 12/25 — wrong), letter **B** (registry says A — wrong), number **CA-74829-0**, **addl_insured=false / subr_wvd=false** (no endorsements on the Ascendant form schedule — conflicts with template AND registry; carrier doc wins pending Alex). |
| emp3_solutions | GL, Auto, WC (new — registry had none) | GL number proposed as carrier's **NRG-DBG-GL17416** (template SUB1579257 / COIs SUB1579257-02 are the submission number — Alex must rule on what certs print). WC **subr_wvd=false** (no waiver on the LUBA schedule — conflicts with template). GL rented-premises **100,000** (dec) — resolves the archive's 100K-vs-1M conflict in the template's favor. |
| central_comfort_ac | GL, WC, Property (verified) | Add `subr_wvd: true` to WC (carrier-confirmed, registry omits it). Property "5,000" is a **deductible**, not a limit — annotate so the engine never presents it as coverage. |
| gd_mechanical | GL, Auto, Umbrella, WC (new — registry had none) | Auto dates **05/03/2026–05/03/2027** (COI-only, medium — get the renewal dec). WC **subr_wvd=false** (no waiver on the LUBA schedule — conflicts with template). GL limits per dec (10K med / 100K rented). |
| absolute_air_solutions | Auto only (new — registry had none) | Letter **A** (both templates print B — wrong). Progressive `872005650` documented separately (binding status: sources disagree). |
| ajf_roofing | GL, Auto, Umbrella, WC (new — registry had none) | Auto number **8035162049** (template's 9035162049 is a typo). All four lines carrier-doc verified twice over — ready to merge once the template is fixed. |
| apogee_hvac | GL, Excess x2, Auto, WC (new — registry had none) | Excess split into **two rows: Lexington 1M/1M/1M + Scottsdale 4M/4M** (never a single 5M). WC number **-0131633**. Letters Auto=**E** / WC=**D**. GL med exp **Excluded**. Auto dates **02/09/2026–02/09/2027 (LOW — conflicting sources)**, auto AI/WOS set **false (LOW — unverified, template says true)**. **Do not enable issuance until A5/A6 resolved.** |

---

## (d) Questions for Alex — each answerable in one line

**Blocking (answer before any related cert goes out):**
1. **305:** Are the Obsidian GL + Excess renewals bound for 07/15/2026? (Y/N + policy numbers)
2. **Rolando:** Is the Trisura GL renewal `SUB1737578-01` bound — and which version, 06/10 ($50,027) or 06/30 ($69,874)?
3. **Rolando:** Does Rolando's have any current WC after TWC4577701 expired 03/23/2026? (Y/N + carrier/number)
4. **Apogee:** Was the IPFS $4,006.56 paid by 05/01/2026 (GL + both excess layers alive)? (Y/N)
5. **Apogee:** Was the LUBA WC reinstated after the 04/27 no-loss letter? (Y/N — FHMConnect / msimpson@fhmic.com)
6. **Absolute:** Did GL / WC / Umbrella renew for 26-27, or is the account auto-only now?

**Rulings needed (fix templates/registry once answered):**
7. **EMP3:** Should certs print the carrier's `NRG-DBG-GL17416` or keep the broker `SUB1579257-02`?
8. **EMP3 + G&D:** Do the LUBA WC policies actually have waiver endorsements added after issuance? (Schedules show none, but templates mark Y.)
9. **Rolando:** Confirm the Ascendant auto truly has no blanket AI/waiver → certs must stop marking ADDL/SUBR on the auto line. (Y/N)
10. **Apogee:** What's the real auto term — 02/09/26–02/09/27 or 12/08/25–12/08/26 — and does the Infinity auto carry blanket AI/WOS? (Needs the dec — scanned PDF wants OCR.)
11. **G&D:** Which template is live — this repo's (10K med / 100K rented, dec-correct) or the Drive "New Template" (5K / 1M, wrong)?
12. **G&D:** Get the 26-27 Kemper auto renewal dec (05/03/26–05/03/27) — portal pull?
13. **Absolute:** Is Progressive `872005650` in force (archive COI says yes, Drive shows only a quote)?
14. **G&D vs Rolando:** Both registry entries (and both templates) print license **CAC1815707** — same qualifier, or copy-paste error?
15. **305:** Confirm WC EL disease limits from the bound LUBA policy (COI + quote only; policy scan unreadable).
16. **Central:** Insured street number — 12320 (template/registry/policy) or 12310 (ACORD 35)?

---

*Every value above carries its citation in `FINAL_RECONCILIATION.json`. Precedence applied: carrier doc (Drive) > carrier doc (archive) > broker COI > template > registry — and where sources disagree, the conflict is flagged LOW-confidence rather than picked.*
