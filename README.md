# COI Automation — USI Insurance Services

Automated Certificate of Insurance generation system for Alejandro Bello.
Handles COI requests via email and WhatsApp, processes them with Claude AI,
and returns finished PDFs.

## Project Structure

```
├── app.py                    # Flask server — main entry point
├── coi_engine.py             # PDF edit engine (PyMuPDF)
├── coi_system_prompt.txt     # Claude AI instructions
├── coi_client_registry.json  # Client registry (templates, aliases, policies)
├── templates/                # COI template PDFs (one per client)
├── output/                   # Generated COIs (temporary)
├── requirements.txt
├── Procfile
└── README.md
```

## Environment Variables (set in Railway)

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `SENDGRID_API_KEY` | SendGrid API key for email delivery |
| `FROM_EMAIL` | The email address COIs are sent from |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID for WhatsApp |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token |
| `TWILIO_WHATSAPP_NUMBER` | Your Twilio WhatsApp number |
| `TEMPLATES_DIR` | Path to templates folder (default: ./templates) |
| `OUTPUT_DIR` | Path to output folder (default: ./output) |

## Endpoints

- `GET /health` — health check
- `POST /email` — email webhook (JSON)
- `POST /whatsapp` — Twilio WhatsApp webhook
- `POST /test` — manual test without email/WhatsApp

## Templates Folder

Place all client COI template PDFs in the `templates/` folder.
Filenames must match exactly what is in `coi_client_registry.json`.

Current templates:
- 305_Power_Corp_COI_Template.pdf
- Rolando_s_HVAC_COI_Template.pdf
- EMP_3_Solutions_Template.pdf
- Central_Comfort_Air_Conditioning_Inc_COI.pdf
- G___D_Mechanical_Services_COI_Template.pdf
- Absolute_Air_Solutions_COI_Symbol_789.pdf
- Absolute_Air_Solutions_COI_Symbol_1-_Copy.pdf
- AJF_Roofing_Inc_COI_Template.pdf
- Apogee_HVAC_Solutions_COI_Template.pdf
