# Distilled Rules v2 — WORKING DRAFT (partial export, 2026-07-03)

Distilled from `training/library/coi_review_decisions_partial_2026-07-03.json`
(65 decisions of 156 graded COIs) joined against `training/graded_cois.json`.
**Alex is NOT done grading.** This draft exists so Prompt v2 assembly is fast
when the final export lands. Nothing here has been applied to
`coi_system_prompt.txt`, and `build_training_library.py` has NOT been run on
this export.

Verdict/problem context comes from the automated grader; "Alex" quotes are his
free-text notes verbatim (typos preserved where meaning matters).

---

## 1. Join summary

- 65 decided hashes, all 65 resolve cleanly against `graded_cois.json` (no unknown hashes).
- Decisions: **4 approve / 16 disagree / 44 skip / 1 note-without-decision** (`cb95b6a2` has a note but no decision saved — likely a UI miss; confirm with Alex).
- Notes: **24 entries carry notes** (4 approve, 16 disagree, 3 skip, 1 decision-less), 41 are bare skips.
- 41 of the 44 bare/near-bare skips are the Rolando's "Next Insurance renewal congrats" thread batch (see Section 5, noise).
- **91 of 156 hashes remain undecided** (full list in Section 7).

### Grading-artifact warning (affects the library builder)

Several "disagree" notes are NOT saying our verdict was wrong on the merits —
they say the grader showed the wrong artifact or insufficient context:

- **"I can only see delivered COI, cannot see what the request was"** — `b5214dc0`, `492ab96f`, `28d4217d`, `cb95b6a2`, `b5b0502d`, `a5b8ea2f`. These are *cannot-grade*, not *verdict-inverted*.
- **"What you're showing is what the CLIENT sent, not what we delivered"** — `927ae296`, `def0bbd7`, `75827b73`, `4deafa0d` (the graded PDF is the inbound sample/prior-broker COI, not our output).

`build_training_library.py` **inverts** a disagree on a correct/incorrect
verdict (`effective_verdict()`), so feeding these through unmodified will
mint false "effective-incorrect" training signal (e.g. `492ab96f` and
`28d4217d` are verdict=correct + disagree → would flip to incorrect purely
because Alex couldn't see the request). For questionable-verdict cases the
note-sentiment regex will likely land most of these in `needs_discussion`,
which is fine — but the correct/incorrect ones invert silently.
**Before the final build: re-tag cannot-grade disagrees as skip (or get Alex
to re-decide them), and exclude the sample-COI-artifact records or fix their
provenance in graded_cois.json.**

---

## 2. Candidate rules

Confidence legend: **explicit** = Alex states the rule as an instruction;
**inferred** = derived from his description of a case, needs his sign-off.
Destination legend: prompt rule / few-shot example / code-routing change /
registry data / library-builder hygiene.

### R1 — Prior-broker COI attached to a request = SOURCE MATERIAL only

**Rule:** When a client attaches an old COI issued by a *different
agent/agency* (their prior broker), that COI is never re-sent and never treated
as our deliverable. Extract the certificate holder name + address (and any
project data) from it, then issue a fresh COI on OUR current template. Our
Description-of-Operations wording supersedes the older, less sophisticated
wording on the attached cert.

- Confidence: **explicit** (multiple notes).
- Destination: **system prompt rule + few-shot example(s)**. See the contradiction flag in Section 6 — this collides with the current ABSOLUTE RULE routing.
- Supporting hashes:
  - `b93578b8` (ajf_roofing, holder Barron Development Corp, thread "another ---- barron development corp") — Alex: "the agent and agency is different thus this is an example coi that we need to use as help to make the coi we will deliver... we should have created a coi that included the cert holder info... this is an old coi with a less sophisticated wording thus our wording would supersede."
  - `927ae296` (absolute_air_solutions, holder AIO Realty & Property Management, request "Please send COI for the new management company for 9299 College Pkwy, I have attached the GL COI for your reference") — Alex: "the one you are showing is the one the client sent. this should have been handled by providing coi of the line i control the auto and copy the cert holder from the coi the insured is sending which is of the broker they currently have."
  - `e9dd589b` (ajf_roofing approve, holder Notowitz) — Alex confirms the workflow: "we are missing the first attachment that romy sent which included an old coi with the cert holder info which is where Katherin found the info for the cert holder."
  - `4deafa0d` (ajf_roofing, Denver CMC, thread "ajf roofing- coi & wc for burris & denver") — Alex, and this one extends the rule to BATCHES and ENDORSEMENTS: "the procedure would have been to look at the first coi sample and create a new one with our template and change the cert holder info and do the same for the other attached coi in request email and **send both cois to insured or requestor in one go**. also lets say... there were endorsements attached in the cois romy sent as samples then **we would use the templates we have for AJF with endorsements**."
  - `75827b73` (apogee_hvac, 3 Island Condominium, request: "I need an updated COI for 3 Island condominium as per the attached past form, adding a waiver of subrogation") — Alex: "this is the coi from the request... i made and sent janice a coi that copied the cert holder info from this one and had the description of ops text from the template."

Sub-rules packed inside R1 (each worth its own prompt line):
- **R1a (explicit):** multiple sample COIs in one request email → one fresh COI per sample, all delivered in a single reply (`4deafa0d`).
- **R1b (explicit):** if the samples include endorsement pages, attach our own endorsement templates for that client, never the prior broker's (`4deafa0d`).
- **R1c (explicit):** for clients where we control only some lines, the fresh COI covers OUR lines only (`927ae296`, ties into R10).

### R2 — Requestor-supplied SAMPLE COI (including as a photo) = same play

**Rule:** A sample/example COI supplied by the requestor (what the cert
"should look like"), including one sent as a **picture/photo**, is handled
exactly like R1: grab the holder info, use our template for everything else.
Additionally: if the sample shows a project name/address, carry those values
onto our COI; if the sample's DoO wording demands things **equivalent to or
less than** our template wording → issue; if it demands things we **don't
have** (endorsement-level asks) → funnel to Alejandro with notes AND tell the
client the endorsements are on the way.

- Confidence: **explicit** (`eb87397a` is the fullest statement; `def0bbd7` confirms the sample-COI pattern).
- Destination: **system prompt rule + top-priority few-shot example** (`eb87397a` — see walkthrough #1). The "equivalent-or-less" DoO comparison is the judgment call Alex wants to calibrate live before it's encoded (his note literally says to bring it up).
- Supporting hashes: `eb87397a` (ajf_roofing / Mercova Group), `def0bbd7` (central_comfort_ac / Paraiso Bay — "this is the coi they sent with request which is a sample coi from requestor to showcase what the coi should look like").
- Note the client-facing message on the funnel path is new: "endorsements are on the way" — different from the current locked ack ("Alejandro is reviewing the requirements and will get back to you shortly"). Needs Alex's sign-off as a reply-template variant.

### R3 — Our DoO wording supersedes older/less-sophisticated wording

**Rule:** When any source artifact (prior-broker COI, our own old-template
certs) carries weaker DoO language, the current template's wording wins.
Never copy old boilerplate forward.

- Confidence: **explicit**.
- Destination: **system prompt rule** (one line; mostly already implied by "always use current template"), and it justifies the template-era caveats in Section 4.
- Supporting hashes: `b93578b8`, `82f41dd8`, `6746cee9`, `d5fb0b80`, `e9dd589b` (all note DoO wording should be ours / would be improved by current template).

### R4 — Non-COI service requests → issue nothing, route to Alejandro

**Rule:** Requests that are not COI requests — policy cancellations,
cancellation letters, requests aimed at other carriers (e.g. StateFarm),
refund processing — must never produce a COI. Reply that "Alejandro will get
back to you" and route the thread to Alejandro. Alex notes clients currently
only send COI requests to this inbox, so this is graceful-degradation
handling, not an expected lane.

- Confidence: **explicit**.
- Destination: **system prompt rule**. The current taxonomy (`coi_*`, `question`, `thank_you`, `junk`) has no clean home for a legitimate non-COI *service* request — closest is `question`, but the required reply is the Alejandro hand-off. Either extend the `question` row's definition + template or add a label; that choice is Alex's/dev's, flag at prompt-integration time.
- Supporting hash: `41667af3` (ajf_roofing, thread "policies cancellation request effective: 01/07/2026" — request asks to cancel all StateFarm auto policies + process a refund; the grader paired it with an unrelated delivered COI). Alex: "if we get a request like that - alejandro will get back to you!... only down the line will I add endorsements as well."

### R5 — Alex's OWN TEAM as sender (@usi.com) → build on backend, ALWAYS route to Alejandro for approval

**Rule:** Senders on Alex's team — **@usi.com** addresses; named: **Andrea
Vargas, Katherin Molina, Christian Devilme** (plus Alex himself) — are
teammates, NOT clients. When a COI request arrives from/through them (usually
a forwarded client thread), the system should build the COI on the backend
but **always send it to Alejandro for approval first**; nothing goes to the
client or requestor without his sign-off. Alex calls this "one of the most
complex scenarios."

- Confidence: **explicit**.
- Destination: **CODE/ROUTING change first, prompt second.** This is a sender-identity gate, not a text-understanding problem: the pipeline needs a team-domain/allowlist check that forces the complex-review (draft-to-Alejandro) path regardless of classifier output. Also a data fix: `training/build_review.py` `TEAM_HINTS` is only `("alejandro bello", "jade harris", "laura rodriguez")` — it misses all three USI teammates and the @usi.com domain, which is part of why this case graded wrong. Update TEAM_HINTS *and* add the equivalent knowledge to the live pipeline (and the registry/config, wherever team identity should canonically live).
- Supporting hash: `c4314db2` (ajf_roofing / NV2A Dragados, thread "sdtoc | ajf coi"). Alex: "andrea vargas... works on my team same as katherin molina and christian devilme and other people with @usi EMAILS... the coi is correct - this is one of the most complex scenarios though for this you would create it on the backend and you will always send it to me and i will need to approve before you send out to client and requestor."

### R6 — Insured forwards a delivered COI to the requester and CCs us FYI → NOT a request

**Rule:** When the insured themselves sends an already-delivered COI onward to
the requester and merely CCs our inbox, take **no action** — it is not a
request. Value of the CC: if the requester bounces it back with revisions, we
can jump in fast. So: classify as monitor-only, stay quiet, watch the thread
for a revision request.

- Confidence: **explicit**.
- Destination: **system prompt rule + few-shot** (walkthrough #3). Maps closest to `junk`/`thank_you` behavior (no reply, no COI) but with the revision-watch rationale; the existing `coi_revision_request` lane covers the follow-up if a bounce arrives.
- Supporting hash: `fd77cf88` (central_comfort_ac / 500 Brickell + KW Property Management, thread "brickell west condominium association"). Alex: "this is actually not a request email but an email where the insured sends coi to requester and ccs me so if there are any revisions i can quickly jump in."

### R7 — G&D one-off: COI as proof of insurance for a newly purchased vehicle

**Rule (inferred):** A request for a COI proving auto coverage on a specific
newly purchased vehicle (so a dealer/lot will release it) is its own request
type: holder = the dealer (here GAF holder box read "PROOF OF INSURANCE"),
DoO carries the vehicle year/make/VIN + coverage effective date under the
commercial auto policy.

- Confidence: **inferred** — Alex describes the case ("a very specific case where the COI was issued for G&D Mechanical showing proof of insurance for a new vehicle they had purchased so they could take it off the lot") without prescribing future handling.
- Destination: **few-shot example** (probably complex-review lane) rather than a hard rule; confirm with Alex whether this should auto-issue or route to him.
- Supporting hash: `f4abacce` (gd_mechanical, DoO: "2017 RAM VIN: ZFBERFAB1H6E78926 has coverage under commercial auto policy effective 04/07/2026").

### R8 — VA-onboarding/training threads are noise — never training data

**Rule:** The "Test Entity Inc" COIs and their threads come from Alex
onboarding/training two virtual assistants. Exclude them from the training
library, benchmarks, and any few-shot mining — permanently.

- Confidence: **explicit**.
- Destination: **library-builder hygiene** (exclusion list), not prompt.
- Supporting hashes: `aeb41861`, `7330722f` (both ajf_roofing "AJF Roofing_Test Entity Inc.pdf", thread "ajf roofing coi - test entity inc."). Alex: "this is from when i was onboarding two virtual assistants and training them on how to do COIs."
- Undecided records that match the same pattern and should get the same treatment when Alex confirms: `6fe46263ce` (absolute_air "Test Entity Inc"), `575cc1e474` (central_comfort "Test Entity Inc"), `07dfc07db3` (emp3 "Test Entity Inc"), `a80aeca048` (gd_mechanical "Test Entity Inc"), `69653becd2`/`ef9c62fc18` (rolandos "Test Entity"). Don't pre-empt his grading; just don't be surprised.
- Related noise: the 41-skip Rolando's "Next Insurance — congrats, your business is covered" batch (insurer-generated certs, no request context). `build_training_library.py` already filters that thread via `JUNK_SUBJECT`/`JUNK_BODY`; his mass-skip confirms the filter is right.

### R9 — Multi-entity holder with a designated MAIN entity listed on top

**Rule (inferred, walkthrough pending):** When a requester specifies that the
certificate holder box must list multiple entities AND names which entity is
the MAIN one, the main entity is listed on top of the holder box, remaining
entities follow (spilling to DoO/additional pages per existing multi-entity
handling). Arose from a bounced-COI revision: our original COI had one entity;
the bounce-back supplied the full entity list (in a picture) + "Certificate
Holder needs to be listed as Sandy Lane Master Association" + "missing the 13
Additional Insured."

- Confidence: **inferred** — Alex explicitly wants to revisit this one together before it's encoded.
- Destination: **prompt (multi-entity holder section) + few-shot**, after the walkthrough (#2 below). Also exercises `coi_revision_request` + image-attachment extraction.
- Supporting hash: `1cfcc4b5` (apogee_hvac / 1 Homes South Beach 1 Hotel, thread "apogee hvac solutions coi").

### R10 — Absolute Air: we only control the auto line

**Rule:** For Absolute Air Solutions, our office controls ONLY the commercial
auto line; other lines (GL, WC...) sit with another broker. Any COI we issue
for them covers auto only; requests implicating other lines follow the
established "lines we don't control never block a cert" rule (issue ours,
don't withhold).

- Confidence: **explicit** ("FYI for absolute air i only control the auto").
- Destination: **registry data + prompt.** Cross-check result: `coi_client_registry.json` for `absolute_air_solutions` has aliases, address, trade, license, and two auto templates (symbol 789 / symbol 1) — the templates *embody* auto-only, but there is **no explicit controlled-lines field** anywhere in the registry for any client. If Prompt v2 leans on "which lines do we control" reasoning (it will, per PROJECT_BRIEF's uncontrolled-lines rule which cites Rolando's WC), that knowledge should become a registry field rather than prompt trivia.
- Supporting hashes: `492ab96f`, `927ae296`.

### R11 — Old-template disagrees are era-grading, not rules

See Section 4. Listed here only so the rule count is honest: these notes
produce **zero** Prompt v2 rules.

---

## 3. Examples Alex wants to walk through together

Alex flagged all three as "very good complex examples" — treat them as
top-priority Prompt v2 few-shot candidates AND walk through them with him
before encoding.

### 3.1 `eb87397afe10bc5e79de589d46e8269411e2065e` — picture-sample COI, DoO formatting variations

- **Record:** ajf_roofing, `AJF Roofing Inc_The Mercova Group, LLC.pdf`, thread "ajf roofing- coi & wc for mercova group", message 2026-01-30 era. Decision: **approve** (with a long note). Grader verdict: questionable.
- **Holder box (as graded):** `GAF / 1 Campus Drive / The Mercova Group, LLC / 8180 NW 36 Street, Suite 418 / Miami FL 33166` (stale GAF block stacked above the real holder — a known template-crop artifact).
- **Request:** Romy (AJF) — "Buen Dia Alejandro: Another Certificate to The Mercova Group, LLC 8180 NW 36 Street, Suite 418 Miami, FL..." with the sample COI attached **as a picture**, not a PDF.
- **Alex's note (verbatim, key parts):** "the client sent the request and the sample coi was a picture - we grab the cert holder info and put it in our coi. in this specific case the coi had a project name and project address section. i am not sure if our template does have for this but if it didnt then we would create them if yes just copy the values. regarding the wording about the project data on the description of ops box we would make sure that it is equivalent or less than what we have in the template and we could issue. if it has stuff we dont have or need to request by endorsement the funnel to me with notes and let client know endorsements on the way ... we need to run through a few of these specific examples as the formatting in the description of operations box might change on the incoming requests."
- **Correct system behavior, step by step:**
  1. Detect the image attachment as an insurance sample (today the fingerprinting focuses on PDFs; picture-COI detection is a capability gap to raise in the walkthrough).
  2. Extract holder name + address from the picture (and/or the body, which here repeats them).
  3. Extract project name/address from the sample; template has project-line handling (PROJECT_BRIEF rules), so copy the values.
  4. Compare the sample's DoO demands against our template wording: **equivalent-or-less → issue** on our template; **beyond ours → complex review**, draft + notes to Alejandro, client told endorsements are on the way.
  5. Never reuse the sample's own wording or layout (R1/R3).
- **Bucket:** `reference_coi_attached` (few-shot), classification `coi_complex_review_required` under today's ABSOLUTE RULE — but this is exactly the case Alex seems to want auto-issued when step 4 passes. That tension is Section 6 flag #1; resolve in the walkthrough.
- **Walkthrough agenda:** picture-COI extraction feasibility; where "equivalent or less" lives (rule text vs Alejandro judgment); the DoO formatting variations he warns about; the "endorsements on the way" reply template.

### 3.2 `1cfcc4b5ae58b77e589bf8c2228f2423ec037a9d` — Sandy Lane multi-entity holder, bounced-COI revision

- **Record:** apogee_hvac, `52491592_1 Homes South Beach 1 Hotel South Beach_01212026.pdf`, thread "apogee hvac solutions coi", 2026-01-21 era. Decision: **disagree**. Grader verdict: questionable.
- **Holder box (as graded):** `1 Homes South Beach 1 Hotel / South Beach / 102 24th Street` — i.e. our ORIGINAL single-entity COI.
- **Request (the bounce-back):** "I need this COI updated as soon as possible as per provided requirements. **Certificate Holder needs to be listed as Sandy Lane Master Association.** COI is also missing the **13 Additional Insured**." — with a **picture attachment listing all the entities** that belong in the holder box.
- **Alex's note (verbatim, key parts):** "another very specific example that I would like to revisit - big picture i sent a coi and it was bounced back and insured reached out that it was missing some stuff. from the requester email you can see the coi i originally made which only had one entity in the cert holder box. when you look at the picture attached there are all the entities that need to be in the cert holder box as well as the emails says the main entity to list on top - sandy lane."
- **Correct system behavior, step by step:**
  1. Recognize the thread as `coi_revision_request` (we sent a COI in this thread; the new email asks for changes).
  2. Extract the full entity list from the picture attachment (again: image extraction, not PDF).
  3. Honor the **designated MAIN entity**: Sandy Lane Master Association on top of the holder box; the other entities (the "13 Additional Insured") follow.
  4. Apply existing multi-entity mechanics: plural "Certificate Holders" boilerplate, box-capacity splits with address repeated per split.
  5. Realistically lands in complex review (13 entities + AI demands) — draft to Alejandro rather than auto-ship.
- **Bucket:** revision + multi-entity + image attachment; negative-example material for the original single-entity miss AND positive material for the revision flow.
- **Walkthrough agenda:** how the "main entity on top" instruction generalizes; whether 13 AIs on a bounce auto-routes to Alejandro; ordering rules for the remaining entities.

### 3.3 `fd77cf88659ada95562ac150092802d3af7107ec` — insured forwards delivered COI, CCs us FYI

- **Record:** central_comfort_ac, `Central Comfort AC COI.pdf`, thread "brickell west condominium association". Decision: **disagree** (with the grader's framing, not the COI). Grader verdict: questionable.
- **Holder box (as graded):** `500 Brickell Master Condominium Association; / 500 Brickell West Condo Association 500 East Condominium / Association / KW Property Management, LLC` (multi-entity).
- **"Request" text:** just Gina Ramos's (Central Comfort) signature block — because it isn't a request; it's the insured forwarding our delivered COI onward to the requester with our inbox in CC.
- **Alex's note (verbatim, key parts):** "the coi is correct. however i dont have the request email for the coi... this is actually not a request email but an email where the insured sends coi to requester and ccs me so if there are any revisions i can quickly jump in."
- **Correct system behavior, step by step:**
  1. Detect that the attached COI is one WE already issued (same insured/agency block, matches history DB) and that the sender is our own client forwarding it outward.
  2. Classify as **not a request → no action**: no reply, no COI generation. Closest existing labels are `thank_you`/`junk` (no-action lanes), but neither captures the semantics; candidate new behavior: monitor-only.
  3. Keep the thread hot: if the requester bounces it back with revision demands, the existing `coi_revision_request` lane picks it up with full thread context.
- **Bucket:** few-shot negative/no-action example — teaches the classifier that "COI attached + our client sending it" is not "reference COI attached → complex review" (today's ABSOLUTE RULE would wrongly wake Alejandro for every FYI CC).
- **Walkthrough agenda:** how to distinguish our-own-delivered-COI attachments from prior-broker/sample COIs (history DB lookup is the obvious hook); whether monitor-only needs its own classification label.

---

## 4. Template-era caveats — NOT rules for Prompt v2

A large share of the disagrees grade the OLD template era, not future
behavior. Alex repeatedly notes that at the time these were issued, the
client's template was missing: **license number in DoO**, **AI (additional
insured) wording**, **waiver-of-subrogation wording**, and used older/simpler
DoO text ("at this specific moment in time we only controlled the comp and
didnt have a template cert made with the right wording... and license
number"). The CURRENT templates already fix all of this — so these notes must
NOT be distilled into Prompt v2 rules, and these hashes must NOT become
negative examples that "teach" the classifier the old certs were behavioral
mistakes.

Era-caveat hashes (all carry some version of the missing
license/AI/waiver/old-DoO note):

| hash | client | decision | note gist |
|---|---|---|---|
| `82f41dd8` | ajf_roofing | disagree | good except old DoO wording; only controlled comp then; no license # |
| `492ab96f` | absolute_air | disagree | can't see request + old template missing license/AI/waiver (+ R10 FYI) |
| `28d4217d` | absolute_air | disagree | can't see request + old template missing license/AI/waiver |
| `cb95b6a2` | rolandos_hvac | (none) | same note as above, decision never saved |
| `b5b0502d` | central_comfort | disagree | can't see request + old template missing license/AI/waiver |
| `b5214dc0` | ajf_roofing | disagree | can't see request (pure cannot-grade) |
| `e9dd589b` | ajf_roofing | approve | agree, but DoO wording should be ours |
| `6746cee9` | central_comfort | approve | correct COI; DoO formatting was old-template |
| `d5fb0b80` | central_comfort | approve | correct; "old description of ops text but cert holder... is correct" |
| `a5b8ea2f` | central_comfort | disagree | can't see request/delivered pairing (cannot-grade) |

Overlap warning: most of these are ALSO the cannot-grade disagrees from
Section 1 — double reason to keep them away from the verdict-inversion logic.
The only durable content in them is R3 (our wording supersedes) and R10
(Absolute Air auto-only), already extracted above.

Also parked: `7f8f0882` (central_comfort, skip) — note cuts off mid-sentence
("this is a great exmaple but the request and deliverd"). Ask Alex to finish
the thought in the final pass.

---

## 5. What the final export changes / noise notes

- The 41 bare skips are overwhelmingly the Rolando's Next-Insurance renewal batch (auto-generated certs against a "no action required" insurer email — no request to learn from). Expect the final export to add real decisions mostly on the 91 undecided, which skew toward 305 Power (12), AJF (24), Central Comfort (16), Rolando's (21).
- Three undecided records are already-known era pieces (`1dc5e61eb` incorrect, `22a6c8f7d` incorrect, `bde0ba3bc` incorrect) — likely negative-example material once decided.

---

## 6. Contradictions / tensions with existing PROJECT rules — RESOLVED BY ALEX 2026-07-03 (items 1-3)

1. **R1/R2 vs the ABSOLUTE RULE — DECIDED: build-then-approve.** Clean
   prior-broker/sample-COI cases: the system BUILDS the COI automatically but
   routes it to Alejandro for APPROVAL instead of sending (same flow as
   @usi.com team requests). One-reply approval. Auto-send for proven-clean
   cases comes later, only when Alex explicitly flips it. Prompt v2 encodes
   this as a new outcome (auto-built draft -> approval), NOT as a relaxation
   to auto-issue. (Original tension preserved in git history.)
2. **Requirements docs / project fields — DECIDED: extended.** Requirements
   docs and sample COIs also supply PROJECT NAME + PROJECT ADDRESS when
   applicable. PROJECT_BRIEF rule amended 2026-07-03. Coverage requirements
   still NEVER modify the COI.
3. **Reply template drift — DECIDED: back burner.** "Endorsements are on the
   way" and "Alejandro will get back to you" are NOT approved wording; do not
   use in client-facing replies until Alex blesses exact text. Cases that
   would need them route to Alejandro without the new lines for now.
4. **Team identity gap (not a contradiction, a hole).** PROJECT_BRIEF/prompt
   have no concept of @usi.com teammates; `TEAM_HINTS` in
   `training/build_review.py` lists only "alejandro bello", "jade harris",
   "laura rodriguez". R5 makes team-sender detection load-bearing for routing
   — it must exist in the live pipeline, not just the review tooling.
5. **Minor:** R10 (Absolute Air auto-only) is *consistent* with the existing
   "lines we don't control never block a cert" rule, but the registry has no
   machine-readable controlled-lines field to hang either rule on.

---

## 7. Status counts and what remains

### Decisions (65 of 156)

| decision | count | with note |
|---|---|---|
| approve | 4 | 4 |
| disagree | 16 | 16 |
| skip | 44 | 3 |
| (note only, no decision) | 1 | 1 |
| **total decided** | **65** | **24** |

Undecided: **91**.

### Undecided hashes (short hash, grader verdict, filename)

**305_power_corp (12):** `71cfc6ae44` correct — City of South Miami · `c99847d590` correct — Bengoa Construction · `d81a8d47f0` correct — City of South Miami V2 · `78e062009b` correct — Rycon Construction · `a98358d385` correct — City of Miami · `54843fb79d` questionable — Lake Point Tower · `f5fe3fba54` questionable — Stratus · `73c45015e6` correct — Johnson Controls · `d20f2a65ea` correct — BelleTowers KW · `c3bc36c9f5` correct — City of Hallandale Beach · `fb2df53365` questionable — City of Homestead · `076c335396` questionable — Miami Dade County Building Dept

**absolute_air_solutions (5):** `09660cff35` correct — AIO Realty & Property Management · `6fe46263ce` questionable — Test Entity Inc (likely R8 noise) · `2abbf4c08a` correct — Absolute Air Solutions LLC CMC1249546 · `392b5c100a` correct — COI Template · `87eb2ef6e7` correct — Progressive COI

**ajf_roofing (24):** `093b31d417` correct — Palm Beach County · `8c818892d9` correct — ACORD Form 20250113 · `08a7ada42a` correct — Tribridge Residential · `3cfa88b15b` questionable — Camcon Group · `0a5ef21c4e` correct — GAF · `6b8e1d9083` correct — 3055 Burris Owner 8.23.24 · `cecbe4dd0e` correct — 3055 Burris Owner LLC · `9a8f218b94` questionable — Denver CMC Colorado Center · `0f8d8a222f` correct — 26-27 CNA 3055 Burris · `2ac897aa0e` questionable — 26-27 CNA Denver CMC · `34e94ff5c6` correct — 26-27 CNA Newmar Building · `335384739d` questionable — Biscayne Beach Miami Condo · `47c8666db5` correct — 2026 Miami Dade COI · `65c6ef070e` correct — 3055 Burris Owner LLC V2 · `20cc60f280` correct — 3055 Burris Owner LLC · `24fadcd33b` questionable — Denver CMC Colorado Center · `4bfd3b671e` questionable — Pembroke Pines · `d5fe5a8a87` correct — Premier Group With All Endorsements · `4ede7f19a2` correct — Alen Construction Group · `3729073e35` correct — NV2A with All Endorsements · `5a057c893e` correct — Lee Construction Group · `01b771e154` correct — Mutiny Hotel · `b1fb11e927` correct — COI 04-16-2026 · `1dc5e61ebe` incorrect — Dadeland Intermodel NV2A Updated COI

**apogee_hvac (3):** `deeaccf0b7` correct — PP_APOGEE_GL COI · `5314cf3c0f` correct — LaGreca Construction · `22a6c8f7de` incorrect — City of Fort Lauderdale

**central_comfort_ac (16):** `575cc1e474` correct — Test Entity Inc (likely R8 noise) · `0d2d18ea04` correct — ICON BAY · `5ceca3b253` correct — KW PROPERTY MANAGEMENT · `9ffede7686` questionable — Axis on Brickell II · `19ff37831d` correct — Waterview · `b0558f373b` correct — Riviera at Coral Lakes · `6850567d96` questionable — Icon Bay KW · `3442bac323` correct — Four Seasons Residences · `6dfb9151b8` correct — Searchkings · `e687487fc6` questionable — ASPCA · `f8cb4f9924` correct — COI Template · `170c3fac53` correct — COI 02-12-26 · `323dceccb3` correct — COI BH · `02120fd922` correct — COI 042426 · `29d60080bd` correct — COI 042426 · `3ef695b3ed` questionable — COI 2

**emp3_solutions (7):** `07dfc07db3` correct — Test Entity Inc (likely R8 noise) · `c62d239c8a` questionable — Ruiz Electric · `6260a6691a` questionable — Procontractors · `4b7724de2d` questionable — Polk County BoCC · `c6b9dffa7d` questionable — Tamarac Building Dept · `16ff8b2ded` questionable — Trent F Condominium · `bf5db1481b` correct — COI Template

**gd_mechanical (3):** `a80aeca048` questionable — Test Entity Inc (likely R8 noise) · `def0e9223f` questionable — Seminole County · `8b0d36044a` correct — COI Template

**rolandos_hvac (21):** `475aaac23b` questionable — City of Port St. Lucie · `69653becd2` questionable — Test Entity (likely R8 noise) · `ef9c62fc18` questionable — Test Entity (likely R8 noise) · `5ba7e65a2f` questionable — APC-ASBF LP · `f64b2f7ed4` questionable — Playland LLC · `2d4cb8e56d` correct — COI (39) · `ec2148617e` questionable — Charlotte County · `83d16111ad` questionable — Charlotte County · `2a3496ee08` questionable — Charlotte County Community Development · `6f7ec428db` questionable — Pasco County · `b319d3c3a3` correct — Marion County · `e20d0499ff` questionable — Atrium Development · `a213395cf3` questionable — City of Fort Myers Building Dept · `94c536cc26` questionable — Noontide Service · `c5ffbd7209` correct — City of Ocala · `dd1d2cc760` correct — Hernando County · `e859acb1a9` correct — Citrus Holdings · `635cfb7825` correct — Goodleap LLC · `a68c8e53a2` correct — Template · `bde0ba3bca` incorrect — City of Pinellas Park 04202026 · `a82173c078` correct — City of Seminole

### Checklist when the FINAL export lands

1. **Re-run the join** (final export × `graded_cois.json`) — confirm 0 unknown hashes and that every previously decided hash kept its decision (diff against this partial).
2. **Re-run the distillation on new notes** — extend/adjust Sections 2-4; especially watch the 91 currently undecided for new rule material (305 Power WC certs and the AJF endorsement certs are untapped).
3. **Sanitize before building:** re-tag the cannot-grade disagrees (Section 1) as skip/needs-discussion, resolve `cb95b6a2`'s missing decision, drop the R8 noise hashes, and fix/flag the four sample-COI-artifact records so `effective_verdict()` doesn't invert them.
4. **Run** `.venv/bin/python training/build_training_library.py --decisions <final export>` → review `TRAINING_LIBRARY.md` + `PROMPT_INTEGRATION_PLAN.md`; hand-write examples for the empty buckets (requirements-PDF, endorsements, specific-language, Spanish per SESSION_HANDOFF).
5. **Assemble Prompt v2:** mined examples + authored examples v2 + Alex's rules (this doc Sections 2-3 once walked through + PROJECT_BRIEF 2026-07-02 issuance rules), respecting the contradiction flags in Section 6 (Alex decides #1-#3 first).
6. **Benchmark gate (verified against current docs):** every prompt change must run `training/benchmark_classifier.py` and beat the prior score. Current documented bar (PROJECT_BRIEF/SESSION_HANDOFF, 26-case set): **≥20/26 classification, 15/15 holder name, 13/14 address**. The set has since grown to **36 cases** (benchmark_extra_cases.json); the current run in `training/benchmark_results.json` (2026-07-03, claude-sonnet-4-5) scores **31/36 classification_ok** (13/36 strict), 18/19 holder name, 15/17 holder address, 25/33 client — so the practical Prompt v2 gate is **beat 31/36 on the 36-case set with no extraction regressions**, plus pipeline harness 13/13. Note `benchmark_results.json` is currently modified-uncommitted in the repo; confirm that run is the intended baseline before gating on it.
7. **Update PROJECT_BRIEF** with whatever new permanent rules Alex ratifies (R1-R6, R10), and copy forward to the Cowork folder per the dual-location note in CLAUDE.md.

---

*Draft generated 2026-07-03 by Claude Code from the partial export. Working
draft only — supersede with the final-export version.*
