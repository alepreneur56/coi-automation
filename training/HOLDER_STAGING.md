# A10 Holder Staging — Alex's Curated Cert-Holder List

Source: `List of Cert Holders - IMPORTANT ONES HIGHLIGHTED IN YELLOW.xlsx`
(Google Drive, owner alepreneur56@gmail.com — exists in at least two Drive
folders; fileId `1YArjLC6PPkMrAQe6U43716SOp8LOvewl` used here).

Output: `training/holder_staging.json`

## STATUS: STAGED, NOT LOADED

Everything in `holder_staging.json` has `"verified": false`. **Nothing from
this file has been written to `data/coi_history.db`.** These rows only get
loaded into the live history DB after Alex reviews and approves them — that
is a separate, deliberate step (not part of this pass).

## Known limitation: highlight detection did not run

The task called for reading each row's cell fill (`cell.fill.start_color` via
openpyxl) to flag the yellow-highlighted "important" rows. That requires the
raw xlsx binary. The Drive download tool returns the file as a base64
string, but the encoded payload for this file is far larger than can be
reliably hand-transcribed into a local file in this environment without risk
of silent truncation/corruption — and a corrupted decode would have produced
either a decode error (safe) or, worse, a xlsx that opens but has scrambled
internals (unsafe, hard to detect). Rather than risk feeding openpyxl a
corrupted file and reporting wrong highlight data as fact, every row in this
pass is staged with `"highlighted": false` as a placeholder, not a real
determination.

**Every row's `highlighted` value should be treated as unknown, not as
"confirmed not highlighted."** A follow-up pass needs to fetch the actual
xlsx bytes through a path that doesn't route the binary through hand
transcription (e.g. a script with direct API/network access to Drive) and
re-run the fill-color check before this field can be trusted.

What *did* work reliably: the full row-level text (holder name, address,
notes/"Information 1" column) came through cleanly via Drive's
`read_file_content` tool, which returns the sheet as parsed text rather than
a binary blob — that's the source for every row parsed below.

## Counts

| | |
|---|---|
| Total rows in source (non-blank) | 71 |
| Parsed cleanly into `staged` | 70 |
| Routed to `needs_review` | 1 |
| Rows with `highlighted: true` | 0 (see limitation above — not yet determinable) |

## needs_review (1 row)

| Row # | Name | Address | Reason |
|---|---|---|---|
| 29 | Enzymedica | *(blank)* | Source row has no address at all — name only |

## 10 samples from `staged`

| Name | Address 1 | City | State | Zip |
|---|---|---|---|---|
| Advanced Radiology and Associates Mike Curry | 13731 Metropolis Avenue | Fort Myers | FL | 34287 |
| Advenir MOB @ Fort Myers LLC c/o Outlook Management Group LLC | S74W16853 Janesville Road | Muskego | WI | 53150 |
| Alamo Drafthouse Mercato | 9118 Strada PL #8205 | Naples | FL | 34108 |
| All Seasons Naples Oakland Management Corp., Attention: Accounting | 31731 Northwestern Hwy Suite 250 W | Farmington Hills | MI | 48334 |
| Alliant Property Management | 13831 Vector Ave | Fort Myers | FL | 33907 |
| Aso Corporation LLC | 300 Sarasota Center Blvd | Sarasota | FL | 34240 |
| Associates In Digestive Health | 2721 Del Prado Blvd, Ste 200 | Cape Coral | FL | 33904 |
| Ave Maria Master Association Attn: Contractor Compliance | 5076 Annunciation Circle #013 | Ave Maria | FL | 34142 |
| Ave Maria University Inc Thomas Minick | 5050 Ave Maria Blvd | Ava Maria | FL | 34142-9505 |
| Bethel Products LLC | 1732 SW 40th Terrace | Cape Coral | FL | 33914 |

Full 70-row set is in `holder_staging.json`. Two rows (15/16 and 39/40) are
near-duplicate holder names ("Charlotte County Community Development",
"Hendry County Building Department Attn: Contractor Licensing") with
identical addresses but different notes — left as separate entries since the
notes differ and de-duping is a judgment call for review, not this pass.

## Parsing approach

Each source row was `"<street/PO box> <City>, <ST> <ZIP>[-XXXX]"` with no
comma between street and city in most cases (Drive's CSV-ish export uses a
comma only before state). Parser:

1. Strip `, ST ZIP` off the end via regex.
2. Match the remaining text against a small closed list of known multi-word
   city names appearing in this file (Fort Myers, Cape Coral, Punta Gorda,
   North Port, Ave Maria, Ava Maria, Port Charlotte, Longboat Key, Bonita
   Springs, Miami Gardens, Farmington Hills) — checked longest-first so
   "Fort Myers" wins over a bare "Myers" match.
3. If no multi-word match, fall back to the single trailing Title-Case word
   as city.
4. Require the remaining street portion to contain a digit (street number or
   PO Box number) as a sanity check — guards against misparsing a holder
   name that leaked into the address column.

This is a closed-list heuristic scoped to this specific file's set of
cities, not a general US-address parser — it should not be reused as-is on a
different source list without checking for new multi-word cities.

## Next step (not done here)

1. Alex reviews `staged` (70) + `needs_review` (1, Enzymedica — needs an
   address) and corrects/confirms.
2. Re-run highlight detection against the real xlsx bytes to populate
   `highlighted` accurately.
3. Only then: load approved rows into `data/coi_history.db` via `db.py` /
   `record_coi()` (source="alex_list" or similar), which is what makes them
   show up in A10a address-autofill.

## Highlight detection — COMPLETED 2026-07-03 (follow-up pass)

The raw xlsx was materialized programmatically (byte-exact, 21,198 bytes) and yellow fills read via openpyxl. **7 holders are highlighted as IMPORTANT by Alex:**

1. Advenir MOB @ Fort Myers LLC c/o Outlook Management Group
2. All Seasons Naples / Oakland Management Corp.
3. Castle Management c/o VendorSmart
4. Jones Lang LaSalle Americas, Inc.
5. Jones Lang LaSalle Americas, Inc. + Gartner, Inc. (joint entry)
6. PR Mercato, LLC
7. ServiceChannel.com, Inc.

holder_staging.json updated: these 7 carry highlighted:true. NOTE for A3/A9: several of these rows carry rich SPECIFIC WORDING requirements in their 'Information' column (JLL/Gartner affiliates wording, ServiceChannel indemnitees clause, CG7288/CG7156/CG7160 form references, 30-day NOC) — prime real-world material for the specific-language and endorsement features.
