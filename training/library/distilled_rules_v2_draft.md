# Distilled Rules v2 — WORKING DRAFT (partial export, 2026-07-03)

Distilled from `training/library/coi_review_decisions_partial_2026-07-03.json`
(65 decisions of 156 graded COIs) joined against `training/graded_cois.json`,
**extended the same evening by batch 2**
(`coi_review_decisions_partial2_2026-07-03.json`, cumulative 113 entries — see
the "Batch 2" section). **Alex is NOT done grading** (44 undecided remain).
This draft exists so Prompt v2 assembly is fast when the final export lands.
Nothing here has been applied to `coi_system_prompt.txt`, and
`build_training_library.py` has NOT been run on these exports.

Verdict/problem context comes from the automated grader; "Alex" quotes are his
free-text notes verbatim (typos preserved where meaning matters).

## GLOBAL APPROVE CAVEAT — read before building anything from decisions

Every "approve" in BOTH exports is **"approve modulo old-template DoO
wording."** Alex marked many batch-2 approves without re-noting the
old-template Description-of-Operations issue each time, but every
approved/agreed record in these batches carries old-template DoO text (P3
warning, 0% template-sentence match). An approve endorses the
holder/content/handling decisions ONLY — it never endorses the old DoO text.
`build_training_library.py` (and any few-shot mining) must NOT treat approve
as blessing old DoO wording; the current templates' wording always supersedes
(R3, Section 4, and the batch-2 era-caveat extension).

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
- **CONFIRMED by Alex in batch 2:** `69653becd2`/`ef9c62fc18` (rolandos "Test Entity", the 2026-01-14 02:32 and 02:49 sends) are test sends from VA onboarding — move from "expected" to the confirmed exclusion list (first attempt's DoO missed the Test Entity AI wording; the second corrected it — neither is training data).
- Still-undecided records matching the same pattern: `6fe46263ce` (absolute_air "Test Entity Inc"), `575cc1e474` (central_comfort "Test Entity Inc"), `07dfc07db3` (emp3 "Test Entity Inc"), `a80aeca048` (gd_mechanical "Test Entity Inc"). Don't pre-empt his grading; just don't be surprised.
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

### Batch-2 additions (evening export 2026-07-03) — cases 3.4-3.9

### 3.4 `47c8666db5d727f071646f539151543a13c577b7` — AJF Miami-Dade: requirements-doc fulfillment gold example

- **Record:** ajf_roofing, `2026 Miami Dade COI - AJF.pdf`, **Sent Items** 2026-02-04 16:48:17. Decision: **approve**. Grader verdict: correct (P2 + P3 warns).
- **Holder box:** `Miami-Dade County / 111 NW 1st Street / Suite 2340 / Miami FL 33128` — government holder with full address.
- **DoO (as issued):** "This certificate is issued for insured operations usual to roofing. Lic#CC1331111. The Automobile Liability policy includes an automatic Additional Insured endorsement that provides Additional Insured status to Miami-Dade County, its officers, employees, agents, and instrumentalities when there is a written contract that requires such status... The General Liability, Umbrella Liability, Auto Liability and Employer's Liability policies provide a Blanket Waiver of Subrogation when required by written contract..."
- **Alex's note (verbatim, caps his):** "FLAG THIS ONE TO COME BACK TO AND EXPLAIN THIS IS A REQUIREMENTS DOC GOOD EXAMPLE"
- **Why it matters:** this is the model for how a REQUIREMENTS DOCUMENT drives the certificate — holder identity + full address, auto-liability AI endorsement language naming the county's officers/employees/agents/instrumentalities, and a blanket waiver spanning GL/Umbrella/Auto/EL. The empty requirements-PDF bucket in `PROMPT_INTEGRATION_PLAN.md` has been waiting for exactly this example.
- **Walkthrough agenda:** (1) have Alex narrate how the requirements doc maps to each DoO element; (2) settle the license discrepancy — the DoO reads **CC1331111** but the registry/grader expects **CCC1331111** (that's the P2 warn); whichever Alex confirms becomes a registry correction; (3) promote to few-shot only after this walkthrough (hold until then).

### 3.5 `deeaccf0b79f65bcec315df6c777cc01cf169e77` (+ `5314cf3c0f0e79b16e21121146c9083ef03e5f9b`) — LaGreca / Presidential Place: two-additional-insured holder-box construction

- **Record:** apogee_hvac, `PP_APOGEE_GL COI.pdf`, 2026-01-09 18:09:05. Decision: **disagree**. Grader verdict: correct — **the verdict is invalid: the PDF is third-party issued**, not team output (see batch-2 provenance era caveat).
- **Request (Janice Lacayo, Apogee):** "Please send me an updated COI for: LaGreca Construction, LLC / 12565 Orange Dr – Suite 401C / Davie, FL 33330. And add Presidential Place Condominium Association, Inc. and LaGreca Construction, LLC are included as additional insured."
- **Alex's note (verbatim):** "this coi was issued by someone else. flag this request as the way it should be created is as follows: in description of ops show that both are additional insured and in certain holder put condo name then on the next line la greca... then on the other lines below just hte address for la greca."
- **Correct construction (his dictation):** DoO states BOTH entities are additional insured; holder box = Presidential Place Condominium Association, Inc. on line 1, LaGreca Construction, LLC on line 2, then ONLY LaGreca's address below. The few-shot example must be built from this dictation, NOT from the graded PDF (third-party artifact).
- **Companion:** `5314cf3c0f` (`PP_APOGEE_LaGreca Construction, LLC.pdf`, 2026-01-12) — Alex: "same as prior request." Rides along with this walkthrough; no independent rules.
- **Walkthrough agenda:** does the condo-then-contractor stacking generalize to any request where two entities are AI and one (the contractor) is the certificate recipient, or is it per-request? Related to R9 (main-entity-on-top) but distinct — confirm the discriminator.

### 3.6 `c6b9dffa7df557f46682283ef34a9f0a5c2794fa` — Tamarac Building Department: originating request missing (join reused Ruiz Electric)

- **Record:** emp3_solutions, `EMP 3 Solutions COI_Tamarac Building Department.pdf`, 2026-02-26 14:56:38. Decision: **disagree**. Grader verdict: questionable (P9: holder not in request text).
- **Request excerpt shown to Alex:** Renier Portieles' "Ruiz Electric Corporation" request — the SAME byte-identical excerpt the join attached to all four EMP 3 records spanning Feb 2-26 (see the join-audit item in the batch-2 code/routing rules). The real Tamarac request was never surfaced.
- **Alex's note (verbatim):** "i dont see the reqeust for this coi...."
- **This is a cannot-grade, not a verdict inversion.** The disagree targets the missing request, not the certificate.
- **Walkthrough agenda:** after the join fix, locate the real originating request for the Tamarac cert (holder text also carries a `RYD Construction LLC / 1450 Madruga Ave Suite 204` block stacked above the Tamarac lines — figure out whether that's a real multi-holder or a template-crop artifact) — or confirm the cert was issued without an email request. Excluded from training until resolved.

### 3.7 `9ffede76860755505aed57d51c0a1b7cdf313003` — Central Comfort / Axis on Brickell: request email missing from the joined thread

- **Record:** central_comfort_ac, `Central Comfort AC COI_Axis on Brickell II Condominium Association, Inc..pdf`, 2026-01-23 18:02:35. Decision: **approve**. Grader verdict: questionable.
- **What the joined thread shows:** only Jade's "Received, will work on it right away!" reply to Gina Ramos plus Alex's forwarded "COI Requests Instructions" broadcast — Gina's actual request email is absent.
- **Alex's note (verbatim):** "i dont see the request email but the coi is correct - agree - would only change in that we now have new template with new description of operations box."
- **Artifact warning:** the graded holder text starts with leftover placeholder lines (`ABC Holder 2 / 3031 sw 11th street / Miami, FL 33135`) above the real Axis on Brickell entity stack — grading/extraction artifact, same family as the GAF template-crop blocks.
- **Walkthrough agenda:** recover Gina's actual request email before using this as a request→COI pair; until then it's an output-format reference only (multi-entity Axis stack), with the placeholder lines stripped.

### 3.8 `2a3496ee0894a9d40dc7dc28c2d616722c9fdcbd` — Charlotte County revision pair: timestamp inconsistency

- **Record:** rolandos_hvac, `Rolando's HVAC COI_Charlotte County Community Development.pdf`, message_date **2026-02-04 14:52:57**. Decision: **skip**, note "read 72".
- **The problem:** Alex (in the `2d4cb8e5` note) identifies this cert as the correct fulfillment of the Charlotte County revision request (holder changed to Charlotte County Community Development) — but the revision request is dated **2026-02-05 14:50:55**, i.e. the fulfillment email predates the request by ~24h. Likely a typo, timezone artifact, or join mis-pairing.
- **Second artifact in the same record:** the holder box carries a `Main Street Renewal and Amherst Group Properties, LLC / c/o VendorShield...` block stacked above the Charlotte County lines — the same cross-client carryover text that Jade's known-error cert contained. Confirm what the actual delivered PDF's holder box says.
- **Tooling note (applies to all "read N" notes):** Alex's cross-references like "read 72" are review-UI positions and do NOT match export key order (this note sits at position 77/113). Resolve "read N" references by thread/content match, never by index.
- **Walkthrough agenda:** confirm real request→fulfillment ordering with Alex; only then store the Charlotte County revision pair as a few-shot.

### 3.9 `09660cff352bcce1b8e821f9233a0d072c6302fd` — Absolute Air / AIO Realty: is auto-only AI+waiver right, or should GL show too?

- **Record:** absolute_air_solutions, `Absolute Air Solutions_AIO Realty & Property Management..pdf`, 2026-01-12 20:21:16. Decision: **skip**. Grader verdict: correct.
- **DoO (as issued):** "Additional Insured and waiver of subrogation applies to commercial auto policy per blanket additional insured and blanket waiver of subrogation endorsement."
- **Alex's note (verbatim):** "i cannot see gl attachd coi..... withohut that i cannot verify if one or the other is right..."
- **The open question:** AI + waiver of subrogation on the commercial auto policy only — correct (R10: we control only auto for Absolute Air, GL sits with another broker), or should the GL COI the client attached have driven something more? Cannot be answered without the GL attachment in hand — which the join didn't surface (full-attachment-set join fix, batch-2 code/routing rules).
- **Walkthrough agenda:** pull the original email's GL attachment, then have Alex rule. Also feeds the uncontrolled-lines open question (#1 in the NEW open questions).

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

- The 41 bare skips are overwhelmingly the Rolando's Next-Insurance renewal batch (auto-generated certs against a "no action required" insurer email — no request to learn from). ~~Expect the final export to add real decisions mostly on the 91 undecided, which skew toward 305 Power (12), AJF (24), Central Comfort (16), Rolando's (21).~~ **Batch-2 update:** 44 undecided remain, now skewing toward 305 Power (12, untouched), AJF (12), Rolando's (8); most of the rest are template files and Test Entity noise — see Section 7.
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

### NEW open questions for Alex (batch 2, 2026-07-03 evening — items 1-3 above stay resolved)

1. **Uncontrolled-lines behavior is now three-way:** PROJECT_BRIEF (2026-07-02)
   says issue our lines and never withhold (silently), the Central Comfort note
   (`6850567d96`) says just skip the auto portion, and the Rolando's WC note
   (`6f7ec428db`) says auto-reply that the other broker will send the COI with
   the missing lines — Alex needs to pick one behavior (or make it a
   per-account registry setting), and the referral reply is new client-facing
   wording that resolved contradiction #3 currently back-burners.
2. **Limits-shortfall routing (ASPCA note, `e687487fc6`):** "create and send to
   ME, not the insured, with the non-compliance list" vs PROJECT_BRIEF "lines
   we don't control never block a cert — do not withhold, do not bounce" — Alex
   must define the boundary: does hold-for-Alejandro apply only when limits on
   lines WE control fall short, or also when the request demands lines/coverages
   another broker holds (which the brief says to issue-and-send without)?
3. **Missing holder address:** Alex's new notes say "I would have asked for the
   address" (Fort Myers `a213395cf3`, Central Comfort 02-12-26 `170c3fac53`),
   but the established PROJECT_BRIEF rule says look it up first via Sunbiz and
   only ask if lookup fails — confirm the resolution order (holder-address DB,
   then registry lookup, then ask requester) and whether the bot sends the
   ask-back or the case routes to Alejandro.

---

## Batch 2 — evening export 2026-07-03

Source: `coi_review_decisions_partial2_2026-07-03.json` — cumulative 113
entries (48 new/changed since the morning export). Every rule below was
verified against the per-record context; two candidate hashes arrived
corrupted from the extractor and were corrected against the canonical export
(`0d2d18ea…d118fa2a4d`, `170c3fac…bd827c02d9c`). Duplicates of existing
rules/lanes are omitted (already covered: ack-only replies → thank_you lane;
emp3 new template → current-template era; Test Entity confirmations → folded
into R8 above). Confidence legend as in Section 2. Rules whose behavior is
**BLOCKED** on a NEW open question are marked; do not encode until Alex rules.

### New prompt rules

- **B1. Match each COI to the specific request it answers** *(explicit —
  `5ba7e65a2f`)*: when a client has multiple open COI requests, answer each one
  individually; never grade or fulfil one COI against a different request. (The
  APC-ASBF, LP cert answers Lorena Leyva's 2026-01-28 20:07:10 request.
  Historically mostly a review-join failure, but a valid live rule for
  multi-request threads.)
- **B2. Entity vs job-site address** *(inferred — `5ba7e65a2f`)*: when a
  request contains both a corporate entity (name + address) and a separate
  job-site/project address, the entity is the certificate holder and the
  job-site address goes in the DoO box as the project address. (Generalized
  from the explicit OONTIDE/Lake Emma correction; get Alex's nod at
  prompt-integration time.)
- **B3. Identify the insured per request, not per bucket** *(inferred —
  `5ba7e65a2f`)*: the classifier must identify the insured/client from request
  content and sender (e.g. sender domain), never inherit it from the thread,
  batch, or bucket the message arrived under — mixed-insured batches occur in
  practice (the dsegre mix-up).
- **B4. Mine the full thread history** *(explicit — `475aaac23b`)*: extract
  certificate-holder details from the whole thread, not only the newest
  message/attachments; a reply claiming a missing attachment is not a blocker
  when the needed info is quoted in the thread text (Port St. Lucie: the
  correct holder was already in the thread).
- **B5. Never falsify or inflate coverage** *(explicit — `e687487fc6`)*: the
  certificate always shows the client's ACTUAL policy limits, even when the
  requester asks for higher limits or coverages the policies don't carry. Not
  written anywhere in PROJECT_BRIEF today — make it an explicit hard rule.
- **B6. Extract demanded limits and enumerate shortfalls** *(explicit —
  `e687487fc6`)*: the classifier must extract the limits/coverages a request
  demands, compare against the client's actual limits, and enumerate every
  shortfall (the non-compliance list) whenever the request can't be fully
  satisfied. Feeds the route-to-Alejandro payload (B-C1).
- **B7. QR code = third-party provenance** *(explicit — `2d4cb8e56d`)*: "we
  never put qr code on COIs" — a QR code on a certificate identifies it as
  another carrier/agency's output, never a team deliverable. Usable as a
  provenance heuristic when classifying attachments.
- **B8. DoO cross-client validation check** *(inferred — `2d4cb8e56d`,
  `ec2148617e`)*: the DoO on a generated COI must reference the CURRENT
  request's holder/client; flag any COI whose DoO names entities from a
  different client or request (cross-client carryover — Jade's demonstrated
  human error). Cheap engine/pipeline assertion.
- **B9. Two-AI + contractor-recipient holder construction** *(explicit —
  `deeaccf0b7`, `5314cf3c0f`)*: when a request adds two entities as additional
  insured and one (the contractor) is the certificate recipient: DoO states
  BOTH are additional insured; holder box shows condo/association name on
  line 1, contractor name on line 2, then only the contractor's address.
  (Dictated for the LaGreca case; generalization is walkthrough 3.5's
  question.)
- **B10. Revision specifics live in ANY attachment type** *(explicit —
  `093b31d417`)*: when a COI is bounced back or a revision requested, the
  specifics may be in the email body, an attached PDF, or an attached
  photo/image (portal error screenshot); check all attachment types before
  deciding what to change or concluding the request is unspecific. (General
  statement of R2's photo-sample and R9/3.2's picture-list cases.)
- **B11. BLOCKED — uncontrolled-lines referral reply** *(explicit —
  `6f7ec428db`; NEW open question #1)*: when asked for lines the registry says
  we don't control, reply that we do not control those policies and the broker
  who does will send the COI with the missing lines — do NOT attempt a COI
  showing those lines. Implies a new classifier category + auto-reply route.
  Three behaviors now exist for uncontrolled lines and the wording is
  back-burnered — route these to Alejandro until Alex rules.
- **B12. BLOCKED — missing-holder-address resolution order** *(explicit —
  `a213395cf3`, `170c3fac53`; NEW open question #3)*: when the holder's mailing
  address is missing, resolve before issuing — proposed order: holder-address
  DB, then state-registry lookup (Sunbiz), then ask the requester. Ordering and
  who asks (bot vs Alejandro) pending Alex; government departments aren't on
  Sunbiz, so the tiers likely coexist.

### New code/routing changes

- **B-C1. Limits-shortfall routing** *(explicit — `e687487fc6`)*: when a
  generated COI does not meet all requested limits/requirements, do NOT send
  to the requester — route to Alejandro with the itemized non-compliance list
  so he can take it to the client (accept as-is vs buy additional coverage).
  Boundary with PROJECT_BRIEF's "lines we don't control never block a cert"
  needs his call — NEW open question #2.
- **B-C2. Certificate-holder address database** *(explicit — `a213395cf3`)*:
  build it and have the pipeline consult it before any lookup/ask-back; known
  holders resolve automatically. (Alex explicitly names the database and the
  pain — digging through old COIs.) Seed entry in the account facts below.
- **B-C3. Flatten COI PDFs before sending** *(explicit — `f64b2f7ed4`,
  `b319d3c3a3`)*: COIs must be non-editable on delivery; `coi_engine.py` needs
  a flatten output mode. If a recipient bounces a COI solely because the file
  is editable, re-emit the identical COI flattened and resend — no content
  changes, not a new request (branch remains for legacy editable certs in the
  wild).
- **B-C4. NDR bounce handling** *(explicit — `635cfb7825`, `b319d3c3a3`)*:
  a bounced send is not complete — notify the client contact on the thread,
  ask for/confirm the correct recipient address, then resend. Reply wording
  should come from Alex's real Laritza email (few-shot below); until blessed,
  route bounces to Alejandro per resolved contradiction #3.

### New account-specific facts

- **central_comfort_ac controlled lines** *(explicit — `6850567d96`)*: we do
  not control all lines — auto is with State Farm and the State Farm agent
  delivers auto certificates. For this account, skip the auto-coverage portion
  of any request: issue the COI for the lines we control only. Alex scoped
  this to "this account" — do NOT generalize (see NEW open question #1).
  Record controlled vs uncontrolled lines in `coi_client_registry.json` (the
  controlled_lines field contradiction #5 already calls for).
- **dsegre@ajfroofingfl.com → AJF Roofing** *(explicit — `5ba7e65a2f`)*:
  requests from this address are for insured AJF Roofing, not Rolando's HVAC,
  even when they surface in another client's thread/bucket; the 2026-01-27
  21:09:15 request is a simple COI for AJF Roofing.
- **Laritza — Rolando's HVAC point of contact** *(inferred — `635cfb7825`,
  `b319d3c3a3`)*: for COI requests and delivery-address questions.
- **Holder-address DB seed** *(inferred — `a213395cf3`)*: City of Fort Myers
  Building Department = 1825 Hendry St #101, Fort Myers, FL 33901 (recurring
  holder for rolandos_hvac permitting work). Address comes from the approved
  record's holder_text, not Alex's note verbatim — verify against the PDF when
  seeding.
- **central_comfort_ac property-manager bundles** *(inferred — `0d2d18ea04`,
  `5ceca3b253`)*: requests via property managers (e.g. KW Property Management)
  often bundle multiple condo associations in one ask; expect splits per
  name+address pair. Registry note, not a hard rule.

### New few-shot candidates

All subject to the GLOBAL APPROVE CAVEAT / era caveats (old-DoO wording never
copied into examples; substitute current-template DoO where noted).

1. **Amendment (add project info to DoO):** the 2026-02-11 18:50:20 "AJF
   ROOFING- BURRIS" Romy reply paired with the original approved 2026-02-10
   AJF COIs *(inferred — `cecbe4dd0e`, `9a8f218b94`)*.
2. **Entity + job-site address:** Office - Rolandoshvac 2026-02-12 18:22:24 →
   holder OONTIDE SERVICE CORPORATION USA INC., 1603 Capitol Ave. Ste 310
   A465, Cheyenne, WY 82001; 2255 Lake Emma Rd, Lake Mary, FL 32746 as project
   address in DoO *(explicit — `5ba7e65a2f`)*.
3. **Simple single-holder request:** dsegre@ajfroofingfl.com 2026-01-27
   21:09:15 (AJF Roofing) *(inferred — `5ba7e65a2f`)*. The same note also
   calls "Lorena Leyva 2026-01-15 15:42:17 COI" a simple request — retrievable
   as a second simple example.
4. **Mine-the-thread-history:** the "Re: COI for the City of Port St Lucie -
   sample coi 5" thread (Alejandro Bello 2026-01-12 22:49:01 forward, incl.
   the "there no file in this email" reply) *(inferred — `475aaac23b`)*. Swap
   in current-template DoO before use.
5. **Clean simple-request pair:** Renier Portieles' Ruiz Electric request
   paired with the approved EMP 3 COI, new-template DoO substituted *(inferred
   — `c62d239c8a`)*.
6. **CONDITIONAL — EMP 3 holder-change trio:** Procontractors, Polk County
   BOCC, Trent F Condominium *(inferred — `6260a6691a`, `4b7724de2d`,
   `16ff8b2ded`)* — ONLY after the join fix verifies each record's real
   originating request (all three carry P9 + the mis-joined shared excerpt).
7. **Limits-shortfall exemplar:** Central Comfort / ASPCA — accurate
   non-inflated COI + route-to-Alejandro escalation with itemized shortfalls
   *(inferred — `e687487fc6`)*. Finalize after NEW open question #2.
8. **Charlotte County initial request (positive):** the 2026-02-02 17:41:32
   "Re: COI TO Charlotte County" delivery — NOT the 17:35:18 wrong-DoO version
   *(explicit — `2d4cb8e56d`, `83d16111ad`)*.
9. **HOLD — Charlotte County revision pair:** revision request (holder →
   Charlotte County Community Development) fulfilled by `2a3496ee08`
   *(explicit — `2d4cb8e56d`, `2a3496ee08`)*. Hold until the timestamp
   inconsistency is resolved (walkthrough 3.8).
10. **DoO-construction exemplar:** Atrium Development Group COI (rolandos,
    2026-02-23), amended to add waiver-of-subrogation and Auto wording before
    use as the gold example *(inferred — `e20d0499ff`)*.
11. **Uncontrolled-line referral:** Beth-Ann Reed / Palmwood Construction WC
    follow-up receiving the broker-referral response (not a COI regeneration)
    *(inferred — `6f7ec428db`)*. BLOCKED on NEW open question #1.
12. **Split-into-separate-COIs:** KW Property Management / ICON BAY thread
    (Central Comfort), incl. the ask-back for a missing holder address
    *(inferred — `0d2d18ea04`, `5ceca3b253`)*. Pair with the corrected split
    OUTPUT, not the raw graded PDF — its holder box contains leftover
    placeholder text ("ABC Holder 2 / 3031 sw 11th street").
13. **Multi-entity single-address formatting:** Four Seasons Residences cert
    (Central Comfort — seven entities stacked in the holder box, one address)
    *(inferred — `3442bac323`)*.
14. **Output-format only:** Central Comfort COI 02-12-26 multi-entity holder
    box (partnership + trusts stacked, license + project address in DoO)
    *(inferred — `170c3fac53`)*. Re-extract holder text from the PDF first
    (OCR garbage on the last entity); no request email exists ("I CANNOT SEE
    SAMPLE") so it cannot be a request→COI pair.
15. **Revision-specifics-in-an-image:** AJF Roofing / City of North Miami
    bounce-back thread (vague email text; image002 contains the rejection
    error naming the missing DoO info) *(explicit — `093b31d417`)*. Classifier
    training ONLY — the delivered PDF never fixed the missing DoO info (era
    caveat), so it is NOT a correct-output exemplar.
16. **Two-AI holder construction:** LaGreca Construction / Presidential Place
    Condominium, built from Alex's dictated construction — NOT from the
    delivered PDF, which was third-party issued *(explicit — `deeaccf0b7`,
    `5314cf3c0f`)*. See walkthrough 3.5.
17. **Vehicle proof-of-insurance (canonical):** Absolute Air Solutions vehicle
    COI (holder "Proof of Insurance", DoO = business name + license CMC1249546
    + 2024 Chevrolet Express VIN + Kemper carrier) *(inferred — `2abbf4c08a`)*.
    Structure only, not boilerplate wording. Refines R7 — see refinements.
18. **HOLD — requirements-doc fulfillment:** AJF Miami-Dade COI *(explicit —
    `47c8666db5`)*. Promote only after walkthrough 3.4.
19. **Bounce-notification tone template:** Alex's real email to Laritza ("the
    email bounced back... resend me where to send it to") *(inferred —
    `635cfb7825`, `b319d3c3a3`)*. Client-facing wording — needs Alex's
    blessing before the pipeline sends it (contradiction #3 posture).

### New era caveats

- **Batch-2 old-DoO extension** *(explicit)*: ALL approves/agrees in this
  batch carry old-template DoO wording (P3, 0% template match); the decisions
  grade holder/content handling only and never endorse the old DoO text. Zero
  future rules derive from old-DoO observations. Extends the Section 4 table
  with: `5ba7e65a2f`, `475aaac23b`, `c62d239c8a`, `6260a6691a`, `4b7724de2d`,
  `16ff8b2ded`, `e687487fc6`, `9ffede7686`, `e20d0499ff`, `a213395cf3`,
  `f64b2f7ed4`, `6850567d96`, `b319d3c3a3`, `0d2d18ea04`, `5ceca3b253`,
  `3442bac323`, `2abbf4c08a`, `47c8666db5`, `170c3fac53`, `093b31d417`.
  (Consolidates ~10 per-record era-caveat candidates into one hash-list
  extension.)
- **Provenance — third-party PDFs graded as ours** *(explicit)*: `COI
  (39).pdf` (Charlotte County, 2026-02-02 17:21:52) is the EXPIRING CARRIER's
  cert, and the Apogee/LaGreca PDFs were issued by someone else — none are
  team output. Exclude as team deliverables and **invalidate the "correct"
  machine verdict on `2d4cb8e56d`**. Adds `2d4cb8e56d`, `deeaccf0b7`,
  `5314cf3c0f` to the Section 1 "what you're showing is what the CLIENT sent"
  artifact list.
- **Jade's known human error — negative example only** *(explicit —
  `2d4cb8e56d`, `ec2148617e`)*: the 2026-02-02 17:35:18 Charlotte County
  delivery has the correct holder but a DoO carried over from Main Street
  Renewal/Amherst (another client). Treat only as a negative example (feeds
  B8).

### Refinements to R1-R10 (and PROJECT_BRIEF / draft sections)

- **→ `coi_revision_request` lane (classifier taxonomy):** *(explicit —
  `cecbe4dd0e`, `9a8f218b94`)* when a requester replies to an already-issued
  COI with additional project information, treat it as an AMENDMENT of the
  same certificate: reissue with the project info added to the DoO box,
  changing nothing else. Delivery still follows build-then-approve (resolved
  contradiction #1) — no conflict.
- **→ R3 / current-template DoO standard:** *(explicit — `e20d0499ff`)* DoO
  content standard confirmed and extended: include the insured's license
  number, project name, and project address; and when we control lines beyond
  GL, include the corresponding wording (waiver of subrogation, Auto
  liability) rather than GL additional-insured language only. Largely embodied
  in the new templates; keep one prompt line so generation never regresses.
- **→ R7 (vehicle proof-of-insurance):** *(explicit — `2abbf4c08a`)* Alex's
  note upgrades R7 from inferred one-off to an explicit general rule "for this
  kind of cois": holder box reads "Proof of Insurance" unless the
  request/requirements specify a holder; DoO includes vehicle details
  (year/make/model, VIN, carrier) alongside business name and license number.
  Resolves R7's open question — a defined request type, not a one-off;
  auto-issue vs route still per current posture. The Absolute Air record is
  the cleaner exemplar vs R7's `f4abacce` (keep both or prefer the new one).
- **→ R10 / contradiction #5 (controlled-lines registry field):** *(explicit —
  `e20d0499ff`, `6f7ec428db`)* rolandos_hvac: we control General Liability and
  Auto (waiver-of-subrogation wording available on controlled lines) but NOT
  Workers Compensation. Extends the controlled_lines field from absolute_air
  to rolandos; PROJECT_BRIEF already cites Rolando's WC as another broker's
  line.
- **→ R1 (Romy as AJF requester):** *(inferred — `cecbe4dd0e`, `9a8f218b94`)*
  Romy is also a known FOLLOW-UP contact on AJF certificate requests (3055
  Burris Owner, LLC project); replies from Romy with project details are
  legitimate amendment requests.
- **→ PROJECT_BRIEF batch-split rule:** *(explicit — `0d2d18ea04`,
  `5ceca3b253`)* when a request asks for multiple holder names EACH WITH ITS
  OWN ADDRESS on a single COI, issue separate COIs — one per name+address pair
  — **even if the requester explicitly asked for one combined certificate**
  (adds the override-the-literal-ask clause).
- **→ PROJECT_BRIEF multi-holder plural/box-capacity rules:** *(explicit —
  `3442bac323`, `170c3fac53`)* the complement: multiple related entities
  sharing ONE address (holder + additional-insured list at the same location)
  → stack all names in the holder box with the single address on ONE COI — do
  not split. Makes the shared-vs-distinct-address discriminator explicit.
- **→ A6b forwarded-thread parsing:** B4 (mine the full thread) extends the
  existing forwarded-thread work *(explicit — `475aaac23b`)*.
- **→ Walkthrough 3.3 our-own-COI detection hook:** *(inferred —
  `2d4cb8e56d`)* before treating any COI PDF found in a thread as team-issued,
  run a provenance check (sending address, producer box, QR-code presence — B7)
  — in both the training-data joiner and any pipeline step reading COIs from
  inbound email. The `COI (39).pdf` mis-join (expiring-carrier cert graded as
  team output) proves the failure mode.
- **→ Walkthrough 3.1/3.2 image-extraction gap:** *(inferred — `093b31d417`)*
  concrete code task: `attachments.py` / `pipeline.py` must download inline
  and attached images (image002-style embedded screenshots) and pass them into
  classification context; photo-only revision specifics are otherwise
  invisible.
- **→ Section 1 grading-artifact warning / library-builder hygiene:**
  *(explicit — `6260a6691a`, `4b7724de2d`, `c6b9dffa7d`, `16ff8b2ded`,
  `323dceccb3`, `02120fd922`, `29d60080bd`, `09660cff35`, `9ffede7686`,
  `6f7ec428db`, `170c3fac53`)* audit and fix the review-export join
  (`join_batch2.py` / export pipeline): all four EMP 3 records spanning Feb
  2-26 share a byte-identical "Ruiz Electric" request excerpt with uniform P9
  warnings (the join reuses one email across attachments — verified against
  the per-record context). Also: attach the FULL COI attachment set (all
  pages/GL sections) per record, and auto-tag records whose originating
  request can't be found as **"no-request"** so they're excluded from
  grading/training instead of wasting Alex's time. Bounce-containing threads
  (`635cfb7825`) should be annotated as non-clean sends. Tooling: resolve
  Alex's "read N" cross-references by thread/content match, never index (see
  walkthrough 3.8).

---

## 7. Status counts and what remains

### Decisions — cumulative after batch 2 (2026-07-03 evening)

| decision | count |
|---|---|
| approve | 32 |
| disagree | 24 |
| skip | 56 |
| (note only, no decision) | 1 (`cb95b6a2`, unchanged) |
| **total entries** | **113** (48 new/changed vs the morning export) |

Undecided: **44 of 156**. Note: Alex intentionally skipped ALL Section-2
template-quality entries in this pass — the remaining skips are deliberate
deferrals, not accidents. The `COI Template` records among the undecided
(`392b5c100a`, `f8cb4f9924`, `bf5db1481b`, `8b0d36044a`, `a68c8e53a2`,
`cb95b6a2`) are template files, not deliveries, and four Test Entity records
remain undecided (expected R8 noise).

<details><summary>Superseded batch-1 counts (65 decided: 4 approve / 16 disagree / 44 skip / 1 note-only; 91 undecided)</summary>
Kept for the diff trail only — the batch-2 export is cumulative and every
batch-1 decision carried forward unchanged.
</details>

### Undecided hashes after batch 2 (short hash, grader verdict, filename)

**305_power_corp (12 — the whole client remains untouched):** `71cfc6ae44` correct — City of South Miami · `c99847d590` correct — Bengoa Construction · `d81a8d47f0` correct — City of South Miami V2 · `78e062009b` correct — Rycon Construction · `a98358d385` correct — City of Miami · `54843fb79d` questionable — Lake Point Tower · `f5fe3fba54` questionable — Stratus · `73c45015e6` correct — Johnson Controls · `d20f2a65ea` correct — BelleTowers KW · `c3bc36c9f5` correct — City of Hallandale Beach · `fb2df53365` questionable — City of Homestead · `076c335396` questionable — Miami Dade County Building Dept

**absolute_air_solutions (3):** `6fe46263ce` questionable — Test Entity Inc (likely R8 noise) · `392b5c100a` correct — COI Template · `87eb2ef6e7` correct — Progressive COI

**ajf_roofing (12):** `08a7ada42a` correct — Tribridge Residential · `3cfa88b15b` questionable — Camcon Group · `0a5ef21c4e` correct — GAF · `20cc60f280` correct — 3055 Burris Owner LLC · `24fadcd33b` questionable — Denver CMC Colorado Center · `d5fe5a8a87` correct — Premier Group With All Endorsements · `4ede7f19a2` correct — Alen Construction Group · `3729073e35` correct — NV2A with All Endorsements · `5a057c893e` correct — Lee Construction Group · `01b771e154` correct — Mutiny Hotel · `b1fb11e927` correct — COI 04-16-2026 · `1dc5e61ebe` incorrect — Dadeland Intermodel NV2A Updated COI

**apogee_hvac (1):** `22a6c8f7de` incorrect — City of Fort Lauderdale

**central_comfort_ac (3):** `575cc1e474` correct — Test Entity Inc (likely R8 noise) · `f8cb4f9924` correct — COI Template · `3ef695b3ed` questionable — COI 2

**emp3_solutions (2):** `07dfc07db3` correct — Test Entity Inc (likely R8 noise) · `bf5db1481b` correct — COI Template

**gd_mechanical (3):** `a80aeca048` questionable — Test Entity Inc (likely R8 noise) · `def0e9223f` questionable — Seminole County · `8b0d36044a` correct — COI Template

**rolandos_hvac (8):** `94c536cc26` questionable — Noontide Service · `c5ffbd7209` correct — City of Ocala · `dd1d2cc760` correct — Hernando County · `e859acb1a9` correct — Citrus Holdings · `cb95b6a28a` incorrect — COI Template GL & CA (the note-without-decision) · `a68c8e53a2` correct — Template · `bde0ba3bca` incorrect — City of Pinellas Park 04202026 · `a82173c078` correct — City of Seminole

### Checklist when the FINAL export lands

1. **Re-run the join** (final export × `graded_cois.json`) — confirm 0 unknown hashes and that every previously decided hash kept its decision (diff against this partial).
2. **Re-run the distillation on new notes** — extend/adjust Sections 2-4; especially watch the 91 currently undecided for new rule material (305 Power WC certs and the AJF endorsement certs are untapped).
3. **Sanitize before building:** re-tag the cannot-grade disagrees (Section 1) as skip/needs-discussion, resolve `cb95b6a2`'s missing decision, drop the R8 noise hashes, and fix/flag the four sample-COI-artifact records so `effective_verdict()` doesn't invert them.
   **Batch-2 additions to the re-tag list:**
   - `c6b9dffa7d` (disagree, verdict=questionable) — pure cannot-grade: "i dont see the reqeust for this coi...." Re-tag as no-request/needs-discussion, not verdict-inverted.
   - `6f7ec428db` (disagree, verdict=questionable) — partial cannot-grade: "this COI is correct but i am not seeing the request for it only its delivery." The disagree carries the uncontrolled-lines referral rule (B11), NOT a verdict inversion.
   - **Silent-inversion hazards — verdict=correct + disagree where the disagree does NOT mean the COI verdict was wrong:** `2d4cb8e56d` (disagree = provenance: the PDF is the expiring carrier's cert — exclude, don't invert), `deeaccf0b7` (disagree = third-party PDF + construction dictation — exclude, don't invert), `635cfb7825` (disagree = the send bounced, COI itself fine — annotate non-clean send), `093b31d417` (disagree = image-extraction lesson; note literally says "disregard..." — era caveat, new template already covers it).
   - **No-request records to auto-tag and exclude:** `323dceccb3`, `02120fd922`, `29d60080bd` (all "no request can be seen on the emails associated..."), plus `9ffede7686` and `170c3fac53` (approved but no request visible — output-format reference only) and `09660cff35` (skip, GL attachment missing — walkthrough 3.9).
4. **Run** `.venv/bin/python training/build_training_library.py --decisions <final export>` → review `TRAINING_LIBRARY.md` + `PROMPT_INTEGRATION_PLAN.md`; hand-write examples for the empty buckets (requirements-PDF, endorsements, specific-language, Spanish per SESSION_HANDOFF).
5. **Assemble Prompt v2:** mined examples + authored examples v2 + Alex's rules (this doc Sections 2-3 + the Batch 2 section, once walked through + PROJECT_BRIEF 2026-07-02 issuance rules), respecting Section 6: original contradictions #1-#3 are RESOLVED, but the three NEW open questions (uncontrolled lines, shortfall boundary, address-resolution order) block B11, B12, B-C1 and few-shots 7/11 until Alex rules.
6. **Benchmark gate (verified against current docs):** every prompt change must run `training/benchmark_classifier.py` and beat the prior score. Current documented bar (PROJECT_BRIEF/SESSION_HANDOFF, 26-case set): **≥20/26 classification, 15/15 holder name, 13/14 address**. The set has since grown to **36 cases** (benchmark_extra_cases.json); the current run in `training/benchmark_results.json` (2026-07-03, claude-sonnet-4-5) scores **31/36 classification_ok** (13/36 strict), 18/19 holder name, 15/17 holder address, 25/33 client — so the practical Prompt v2 gate is **beat 31/36 on the 36-case set with no extraction regressions**, plus pipeline harness 13/13. Note `benchmark_results.json` is currently modified-uncommitted in the repo; confirm that run is the intended baseline before gating on it.
7. **Update PROJECT_BRIEF** with whatever new permanent rules Alex ratifies (R1-R6, R10), and copy forward to the Cowork folder per the dual-location note in CLAUDE.md.

---

*Draft generated 2026-07-03 by Claude Code from the partial export; extended
the same evening with the verified batch-2 findings
(`coi_review_decisions_partial2_2026-07-03.json`). Working draft only —
supersede with the final-export version.*
