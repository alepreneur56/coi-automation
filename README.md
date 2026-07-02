# COI Automation — local runtime

Automated Certificate of Insurance (COI) processing for Alejandro Bello / USI
Insurance Services. Watches `admin@clientpolicyhelp.com` via Microsoft Graph,
classifies each incoming email with Claude, generates ACORD 25 PDFs with
PyMuPDF, and replies in-thread — CCing the producer.

**Architecture (since the 2026-05-24 pivot):** everything runs locally on the
Mac in a single Python process. No Railway, no Pipedream, no SendGrid.

```
Graph poll (60s) -> thread fetch -> attachment processing -> Claude classify
    -> coi_engine (PDF) -> Graph send (reply in-thread, CC producer)
```

## Files

| File | Role |
|---|---|
| `main.py` | Entry point — polling loop, `--check`, `--once`, `--dry-run` |
| `config.py` | Settings; secrets loaded from `.env` |
| `graph_client.py` | Microsoft Graph auth (client credentials) + mail I/O |
| `thread_fetch.py` | Conversation retrieval (conversationId + header walk) |
| `attachments.py` | PDF/image/HEIC/Word/Excel processing — all local |
| `classifier.py` | Claude call: system prompt + registry, prompt-cached |
| `pipeline.py` | Classification branching + PDF generation |
| `sender.py` | Outbound replies / review emails, TEST_MODE guard |
| `state.py` | Watermark + processed-ID state, JSONL logging |
| `coi_engine.py` | ACORD 25 PDF editor (PyMuPDF) — unchanged core |
| `coi_system_prompt.txt` | The parsing/classification prompt |
| `coi_client_registry.json` | The 8 clients, templates, policies |
| `templates/` | 9 client COI template PDFs |
| `app.py` | LEGACY — old Railway Flask service. Kept for reference only. |

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then fill in the four secrets
.venv/bin/python main.py --check   # verifies everything before first run
```

`.env` needs: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
(from the Azure app registration with application permissions Mail.ReadWrite +
Mail.Send, admin-consented) and `ANTHROPIC_API_KEY`.

## Running

```bash
./start.sh          # background loop (nohup)
./start.sh status
./start.sh logs     # tail today's JSONL log
./start.sh stop
```

For start-at-login + auto-restart, install the launchd job:

```bash
cp launchd/com.alepreneur.coi-automation.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.alepreneur.coi-automation.plist
```

## Safety

- `TEST_MODE=true` in `.env` (default) redirects every client-facing email to
  `TEST_REDIRECT_TO` and strips CCs. Flip to `false` only after end-to-end
  testing passes.
- On first run the watermark initializes to "now" — the inbox backlog is
  never processed.
- One failing message never wedges the loop; failures are logged to
  `logs/coi-YYYY-MM-DD.jsonl` and the loop moves on.
- Optional: installing LibreOffice enables full-fidelity Word→PDF conversion
  for .doc/.docx attachments (otherwise text is extracted from .docx directly).

## Templates

Filenames must match exactly what is in `coi_client_registry.json`:
- 305_Power_Corp_COI_Template.pdf
- Rolando_s_HVAC_COI_Template.pdf
- EMP_3_Solutions_Template.pdf
- Central_Comfort_Air_Conditioning_Inc_COI.pdf
- G___D_Mechanical_Services_COI_Template.pdf
- Absolute_Air_Solutions_COI_Symbol_789.pdf
- Absolute_Air_Solutions_COI_Symbol_1-_Copy.pdf
- AJF_Roofing_Inc_COI_Template.pdf
- Apogee_HVAC_Solutions_COI_Template.pdf
