# COI Classifier Training Library (SYNTHETIC decisions — regenerate with Alex's real export)

Generated 2026-07-02T17:44:44 from `synthetic_decisions.json` by `training/build_training_library.py`.

Decisions: 34 total — 27 approve / 3 disagree / 4 skip / 0 unknown hashes. Effective verdicts: 18 correct, 7 incorrect, 4 questionable, 1 needs discussion.

## Coverage

| Bucket | Selected | Available |
|---|---|---|
| requirements_pdf_attached | 0 | 0 |
| reference_coi_attached | 2 | 2 |
| complex_endorsements | 0 | 0 |
| specific_language | 0 | 0 |
| spanish | 0 | 0 |
| vague_or_missing_info | 1 | 1 |
| body_only_request | 2 | 2 |
| **total** | **5** | **5** |

Available = effective-correct COIs whose thread carries a usable, faithfully modelable client request. Truncated holder crops, batch-shaped requests, and non-US addresses are excluded rather than guessed.

## requirements_pdf_attached (0 examples)

_No usable material in this bucket yet — see Coverage and Gaps._

## reference_coi_attached (2 examples)

### reference_coi_attached — example 1 (apogee_hvac, 2026-01-09 18:15:19)

- Subject: 3 Island Condominium COI - Apogee HVAC Solutions LLC
- From: Janice Lacayo
- Attachments: 3 Island Condominium Association, Inc.pdf (ACORD COI, insured: INSU); image001.png (image, likely signature graphic)
- Alex's note: this one is actually fine, the 3 island cert matched what they sent

Request body (cleaned):

```
Good afternoon Alejandro,
I need an updated COI for 3 Island condominium as per the attached past form, adding a waiver of subrogation.
Thank you in advance.
Best Regards,
Janice Lacayo
Office
640 S. Miami Avenue, Suite 201
Miami, FL 33130
Mailing Address
PO BOX 310305
Miami, FL
33231
Office (786) 294-0596
Direct (786) 740-6750
www.apogeehvac.com
```

Expected classifier output:

```json
{
  "classification": "coi_complex_review_required",
  "reply_text": "Janice,\n\nThanks for the request. Alejandro is reviewing the requirements and will get back to you shortly.\n\nRegards,",
  "original_request_summary": "Client requests a COI for APOGEE HVAC SOLUTIONS LLC with 3 Island Condominium Association, Inc as certificate holder.",
  "status": "ready",
  "client_id": "apogee_hvac",
  "client_canonical_name": "APOGEE HVAC SOLUTIONS LLC",
  "template_id": "apogee_hvac_full",
  "template_filename": "Apogee_HVAC_Solutions_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Sender and body context match APOGEE HVAC SOLUTIONS LLC in the registry.",
  "certificate_holder": {
    "name": "3 Island Condominium Association, Inc",
    "address_line_1": "3 Island Ave.",
    "address_line_2": null,
    "city": "Miami",
    "state": "FL",
    "zip": "33139"
  },
  "date_to_insert": "01/09/2026",
  "project_name": null,
  "project_address": null,
  "project_unit": null,
  "is_permit": false,
  "send_completed_coi_to": null,
  "flags": [],
  "edits_to_make": [
    {
      "field": "certificate_holder",
      "action": "replace",
      "old_value": "NAME\nADDRESS\nSTATE, CITY ZIP CODE",
      "new_value": "3 Island Condominium Association, Inc\n3 Island Ave.\nMiami, FL 33139"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "01/09/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address ( If Applicable)",
      "new_value": ""
    }
  ],
  "review_summary": "Client attached a prior COI as reference. A reference COI is insurance content, so the ABSOLUTE RULE applies even though the holder is fully extractable from it.",
  "coverage_analysis": {
    "required_coverages": [],
    "required_endorsements": [],
    "special_language": null,
    "notes": "Draft prepared from extracted holder info; Alejandro to verify against the attachment/body."
  }
}
```

**Teaching point:** A prior/reference COI attached to the request IS insurance content. Extract the holder from it, but the classification stays coi_complex_review_required. (Top benchmark failure: these were marked ready and would have shipped unreviewed.)

### reference_coi_attached — example 2 (apogee_hvac, 2026-01-09 18:09:05)

- Subject: LaGreca Construction Updated COI - Apogee HVAC Solutions LLC
- From: Janice Lacayo
- Attachments: PP_APOGEE_GL COI.pdf (ACORD COI, insured: INSU); image001.png (image, likely signature graphic)

Request body (cleaned):

```
Good afternoon Alejandro,
Hope you are doing well.
Please send me an updated COI for:
LaGreca Construction, LLC
12565 Orange Dr ' Suite 401C
Davie, FL 33330
And add Presidential Place Condominium Association, Inc. and LaGreca Construction, LLC are included as additional insured.
Thank you in advance.
Best Regards,
Janice Lacayo
Office
640 S. Miami Avenue, Suite 201
Miami, FL 33130
Mailing Address
PO BOX 310305
Miami, FL
33231
Office (786) 294-0596
Direct (786) 740-6750
www.apogeehvac.com
```

Expected classifier output:

```json
{
  "classification": "coi_complex_review_required",
  "reply_text": "Janice,\n\nThanks for the request. Alejandro is reviewing the requirements and will get back to you shortly.\n\nRegards,",
  "original_request_summary": "Client requests a COI for APOGEE HVAC SOLUTIONS LLC with LaGreca Construction, LLC as certificate holder.",
  "status": "ready",
  "client_id": "apogee_hvac",
  "client_canonical_name": "APOGEE HVAC SOLUTIONS LLC",
  "template_id": "apogee_hvac_full",
  "template_filename": "Apogee_HVAC_Solutions_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Sender and body context match APOGEE HVAC SOLUTIONS LLC in the registry.",
  "certificate_holder": {
    "name": "LaGreca Construction, LLC",
    "address_line_1": "12565 Orange Dr – Suite 401C",
    "address_line_2": null,
    "city": "Davie",
    "state": "FL",
    "zip": "33330"
  },
  "date_to_insert": "01/09/2026",
  "project_name": null,
  "project_address": null,
  "project_unit": null,
  "is_permit": false,
  "send_completed_coi_to": null,
  "flags": [],
  "edits_to_make": [
    {
      "field": "certificate_holder",
      "action": "replace",
      "old_value": "NAME\nADDRESS\nSTATE, CITY ZIP CODE",
      "new_value": "LaGreca Construction, LLC\n12565 Orange Dr – Suite 401C\nDavie, FL 33330"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "01/09/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address ( If Applicable)",
      "new_value": ""
    }
  ],
  "review_summary": "Client attached a prior COI as reference. A reference COI is insurance content, so the ABSOLUTE RULE applies even though the holder is fully extractable from it.",
  "coverage_analysis": {
    "required_coverages": [],
    "required_endorsements": [],
    "special_language": null,
    "notes": "Draft prepared from extracted holder info; Alejandro to verify against the attachment/body."
  }
}
```

**Teaching point:** A prior/reference COI attached to the request IS insurance content. Extract the holder from it, but the classification stays coi_complex_review_required. (Top benchmark failure: these were marked ready and would have shipped unreviewed.)

## complex_endorsements (0 examples)

_No usable material in this bucket yet — see Coverage and Gaps._

## specific_language (0 examples)

_No usable material in this bucket yet — see Coverage and Gaps._

## spanish (0 examples)

_No usable material in this bucket yet — see Coverage and Gaps._

## vague_or_missing_info (1 example)

### vague_or_missing_info — example 1 (ajf_roofing, 2026-01-15 18:08:18)

- Subject: FW: Three Lakes and Florida City - Expired COIs
- From: Guillermo Vidaurreta
- Attachments: image001.png (image, likely signature graphic); image002.png (image, likely signature graphic); image003.png (image, likely signature graphic); image004.png (image, likely signature graphic); image005.png (image, likely signature graphic); image006.png (image, likely signature graphic); image007.png (image, likely signature graphic); image009.png (image, likely signature graphic); image010.png (image, likely signature graphic); image011.png (image, likely signature graphic); image013.png (image, likely signature graphic)
- Historical resolution: GAF / 1 Campus Drive / Tribridge Residential Construction, LLC

Request body (cleaned):

```
Alejandro, Can you please provide COI as requested below. Thank you.
Guillermo Vidaurreta Commercial Project Manager & Estimator | AJF Roofing D : (786) 420-2012 O : (305) 456-8006 C: (305) 793-5153 7495 NW 7 th Street Suite #8, Miami, FL 33126 E: gvidaurreta@ajfroofingfl.com | Web: www.ajfroofingfl.com
```

Expected classifier output:

```json
{
  "classification": "coi_request_incomplete",
  "reply_text": "Guillermo,\n\nHappy to put this together for you. Please send the entity name and address of who is requesting the COI.\n\nRegards,",
  "original_request_summary": "Client asks AJF Roofing, Inc. for a COI but the request does not identify the certificate holder."
}
```

**Teaching point:** Holder information is missing from the request: look it up, and if the lookup cannot confirm a single match, ask. NEVER invent an address (the benchmark's most dangerous failure was a hallucinated address shipped at high confidence). (This request was historically resolved to the holder shown in historical_resolution.)

## body_only_request (2 examples)

### body_only_request — example 1 (rolandos_hvac, 2026-02-04 14:14:59)

- Subject: RE: COI TO Charlotte County
- From: Contractor Licensing
- Attachments: image002.png (image, likely signature graphic); image003.png (image, likely signature graphic); image004.jpg (image, likely signature graphic)
- Alex's note: county asked for this directly, came out right

Request body (cleaned):

```
Coi needs to be made out to Charlotte County Community Development 18400 Murdock Cir Port Charlotte FL 33948.
Respectfully,
Azeudee 'Dee' Carr
Contractor Licensing ,Sr Permit Technician2
Charlotte County CommunityDevelopment
941.743.1201
CharlotteCountyFL.gov
Delivering Exceptional Service
Help us get back to you faster ' please direct your emails to the appropriate inbox:
General Inquiries: BuildingConstruction@CharlotteCountyFL.gov
Contractor Licensing (COIs): ContractorLicensing@CharlotteCountyFL.gov
Elevation Certificates, Drainage As-Built Surveys: FloodInfo@CharlotteCountyFL.gov
Permitting (NOCs,SubcontractorChanges): OnlinePermitting@CharlotteCountyFL.gov
Resubmittals / Plan Changes: PermitResubmittal@CharlotteCountyFL.gov
Private Provider: PrivateProvider@CharlotteCountyFL.gov
Termite Certificates/Blower Door Reports: Inspections@CharlotteCountyfl.gov
How was your service? CLICK
HERE to let us know
```

Expected classifier output:

```json
{
  "classification": "coi_request_complete",
  "reply_text": null,
  "original_request_summary": "Client requests a COI for Rolando's HVAC LLC with Charlotte County Community Development as certificate holder.",
  "status": "ready",
  "client_id": "rolandos_hvac",
  "client_canonical_name": "Rolando's HVAC LLC",
  "template_id": "rolandos_hvac_gl_auto",
  "template_filename": "Rolando_s_HVAC_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Client is Rolando's HVAC LLC from the thread context; the sender is a third party requesting on our insured's behalf.",
  "certificate_holder": {
    "name": "Charlotte County Community Development",
    "address_line_1": "18400 Murdock Cir",
    "address_line_2": null,
    "city": "Port Charlotte",
    "state": "FL",
    "zip": "33948"
  },
  "date_to_insert": "02/04/2026",
  "project_name": null,
  "project_address": null,
  "project_unit": null,
  "is_permit": false,
  "send_completed_coi_to": null,
  "flags": [],
  "edits_to_make": [
    {
      "field": "certificate_holder",
      "action": "replace",
      "old_value": "NAME\nADDRESS\nSTATE, CITY ZIP CODE",
      "new_value": "Charlotte County Community Development\n18400 Murdock Cir\nPort Charlotte, FL 33948"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "02/04/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address ( If Applicable)",
      "new_value": ""
    }
  ]
}
```

**Teaching point:** A plain cert-holder request with a complete address in the body is coi_request_complete. Use the client's address verbatim, never verify or second-guess it.

### body_only_request — example 2 (central_comfort_ac, 2026-02-10 21:29:25)

- Subject: FW: Sample COI Needed
- From: Administration
- Attachments: Outlook-fmvs53fi.png (image, likely signature graphic); image001.jpg (image, likely signature graphic); image002.jpg (image, likely signature graphic); image003.jpg (image, likely signature graphic); image004.jpg (image, likely signature graphic); image005.jpg (image, likely signature graphic)

Request body (cleaned):

```
Good Afternoon Alejandro,
Can you please send me a certificate with the following:
The certificate holder on the Certificate of Liability Insurance should read:
The Riviera at Coral Lakes Condominium Association, Inc.
c/o Unlimited Property Management
13250 SW 135th Avenue
Miami, FL 33186
Cynthia Garrido
Central Comfort Air Conditioning
p:
305-598-7575
a:
12320
SW 129 th Ct., Miami, FL 33 186
w: e :
centralcomfortairconditioning.com
administration @centralcomfortac.com
```

Expected classifier output:

```json
{
  "classification": "coi_request_complete",
  "reply_text": null,
  "original_request_summary": "Client requests a COI for Central Comfort Air Conditioning with The Riviera at Coral Lakes Condominium Association, Inc. as certificate holder.",
  "status": "ready",
  "client_id": "central_comfort_ac",
  "client_canonical_name": "Central Comfort Air Conditioning",
  "template_id": "central_comfort_gl_wc",
  "template_filename": "Central_Comfort_Air_Conditioning_Inc_COI.pdf",
  "confidence": "high",
  "confidence_notes": "Sender and body context match Central Comfort Air Conditioning in the registry.",
  "certificate_holder": {
    "name": "The Riviera at Coral Lakes Condominium Association, Inc.",
    "address_line_1": "13250 SW 135th Avenue",
    "address_line_2": null,
    "city": "Miami",
    "state": "FL",
    "zip": "33186"
  },
  "date_to_insert": "02/10/2026",
  "project_name": null,
  "project_address": null,
  "project_unit": null,
  "is_permit": false,
  "send_completed_coi_to": null,
  "flags": [],
  "edits_to_make": [
    {
      "field": "certificate_holder",
      "action": "replace",
      "old_value": "NAME\nADDRESS LINE 1\nCITY, STATE ZIP CODE",
      "new_value": "The Riviera at Coral Lakes Condominium Association, Inc.\nc/o Unlimited Property Management\n13250 SW 135th Avenue\nMiami, FL 33186"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "02/10/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address ( If Applicable)",
      "new_value": ""
    }
  ],
  "certificate_holder_lines": [
    "The Riviera at Coral Lakes Condominium Association, Inc.",
    "c/o Unlimited Property Management",
    "13250 SW 135th Avenue",
    "Miami, FL 33186"
  ]
}
```

**Teaching point:** A plain cert-holder request with a complete address in the body is coi_request_complete. Use the client's address verbatim, never verify or second-guess it.

## Negative examples (5)

### negative 1 (central_comfort_ac, CentralComfort Waverly KW 04212026.pdf)

```
(no request text preserved in the archive)
```

- What went wrong: Alex: "the placeholder project line went out on the final cert, bad"; P1: placeholder 'Project name & Address (If Applicable)' left on the COI
- Correct behavior: Delete the 'Project name & Address (If Applicable)' placeholder line whenever no project is provided; it must never appear on a finished COI.

### negative 2 (ajf_roofing, ACORD Form 20250113-103038.pdf)

```
Alejandro, Can you please provide COI as requested below. Thank you.
Guillermo Vidaurreta Commercial Project Manager & Estimator | AJF Roofing D : (786) 420-2012 O : (305) 456-8006 C: (305) 793-5153 7495 NW 7 th Street Suite #8, Miami, FL 33126 E: gvidaurreta@ajfroofingfl.com | Web: www.ajfroofingfl.com
```

- What went wrong: Alex: "wrong holder, the request below was for the Florida City project not Tribridge"
- Correct behavior: Follow Alex's correction above; do not repeat this outcome.

### negative 3 (absolute_air_solutions, COI GL WC for 9299 college.pdf)

```
Good Afternoon,
Please send COI for the new management company for 9299 College Pkwy. I have attached the GL COI for your reference, for the address etc.
Please call, text, or email with any questions.
Kindest Regards,
MJ
Thank you,
Tina "MJ" Judkins
Absolute Air Solutions LLC
absoluteairsolutions@live.com
mj.absoairs@outlook.com
Office: 941-423-9908
Cell: 941-266-9061
```

- What went wrong: Alex: "yep, the date box was left blank on this one"; P4: no issue date in the date box
- Correct behavior: Always insert today's date in the date box. A COI must never go out without an issue date.

### negative 4 (ajf_roofing, AJF Roofing - Workers Comp. Exp. 01-01-26 - Notowitz.pdf)

```
Good morning, Alejandro Here another request certificate: Thank you.
Romy Koo Accounts Payable & Human Resources | AJF Roofing D: (786) 409-6988 C: (305) 456-8006 EXT 6988 7495 NW 7 th Street Suite #10, Miami, FL 33126 E: rkoo@ajfroofingfl.com | Web: www.ajfroofingfl.
```

- What went wrong: Alex: "no date on it, this went to the GC like that"; P4: no issue date in the date box
- Correct behavior: Always insert today's date in the date box. A COI must never go out without an issue date.

### negative 5 (central_comfort_ac, 24-25 COI - Paraiso Bay Condominium Association Inc..pdf)

```
Good Morning Alejando,
I wanted to see if you can please send over a certificate unfortunately, it is more than the said characters.
Cynthia Garrido
Central Comfort Air Conditioning
p:
305-598-7575
a:
12320
SW 129 th Ct., Miami, FL 33 186
w: e :
centralcomfortairconditioning.com
administration @centralcomfortac.com
```

- What went wrong: P4: no issue date in the date box
- Correct behavior: Always insert today's date in the date box. A COI must never go out without an issue date.

## Needs discussion (1)

- `e20d0499ff` rolandos_hvac (Rolando's HVAC COI_Atrium Development Group.pdf) — our verdict was questionable, Alex disagreed: "template changed around this time, need to ask Rolando about this address". Resolve with Alex before using.
