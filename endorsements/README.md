# endorsements/ — blanket endorsement PDFs (A9)

One folder per `client_id` (matching `coi_client_registry.json`). Each folder
holds the client's endorsement PDFs, named exactly as the `pdf_filename`
values in `coi_endorsement_registry.json` (e.g. `ajf_roofing/ajf_gl_ai.pdf`).

How it works (`endorsements.py`, gated by `ENDORSEMENTS_ENABLED` in `.env`,
default off):

- When a COI request demands endorsement documentation (AI endorsement copy,
  waiver of subrogation, P&NC wording, notice of cancellation, per-project
  aggregate), the matching **blanket** endorsement PDF is attached to the
  outgoing delivery email — but only if the file exists here.
- **Blanket entry, PDF missing from this folder** → no attachment; a note goes
  to the producer instead. Drop the PDF in with the exact registry filename to
  activate it.
- **Scheduled entries are never attached** (e.g. Rolando's HVAC auto AI/WOS/
  P&NC — per-holder carrier change endorsements). They produce a producer flag
  that a carrier endorsement request is needed.

Status: folders scaffolded 2026-07-03; **no PDFs on file yet** — Alex is
supplying them. `.gitkeep` files only preserve the folder structure.

Hard rule: never place any GAF-related additional-insured artifact in
`ajf_roofing/` — the historical GAF-on-every-AJF-COI pattern was a mistake.
