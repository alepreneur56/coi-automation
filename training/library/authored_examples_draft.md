# Authored Draft Examples — the 4 empty buckets

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL** — every example below is authored, not mined. None of this enters `coi_system_prompt.txt` until Alex approves each example.

Generated 2026-07-02T19:21:57 by hand-authoring against: `training/BENCHMARK_REPORT.md`, `training/a7/requirements_catalog.json`, `training/a7/parsed_examples.json`, `training/a7/A7_DESIGN_BRIEF.md`, `coi_client_registry.json`, and the OUTPUT FORMAT / template rules in `coi_system_prompt.txt` (including the 2026-07-02 safety patch: anti-fabrication, non-US addresses, reference-COI routing).

Request bodies are adapted from real request excerpts and real requirements-document patterns; third parties are lightly anonymized; the 8 real clients, registry data, and template placeholder strings are exact (note: `edits_to_make` old_value strings follow the registry's `editable_fields` verbatim, so Apogee/AJF use `(If Applicable)` while the other templates use `( If Applicable)`).

## Coverage

| Bucket | Authored (draft) |
|---|---|
| requirements_pdf_attached | 4 |
| complex_endorsements | 3 |
| specific_language | 3 |
| spanish | 4 |
| **total** | **14** |

## requirements_pdf_attached (4 authored examples)

A requirements document (checklist, bid addendum, vendor packet, annotated sample cert) is attached. Always `coi_complex_review_required` with `status: "ready"` and a filled `coverage_analysis` using the prompt's schema keys (`required_each_occurrence` / `client_each_occurrence` / `gap` / `note`).

### requirements_pdf_attached — authored example 1 (apogee_hvac, 2026-02-10 16:42:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: Brickell Harbour Condominium COI - Apogee HVAC Solutions
- From: Janice Lacayo
- Attachments: Insurance Requirements for Contractors.pdf (insurance requirements document: GL $1M minimum, WC required even if state-exempt, AI + waiver checkbox instructions, prescribed certificate holder block); image001.png (image, likely signature graphic)
- Grounded in: training/a7/parsed_examples.json: brickellhouse_requirements (Apogee, real thread 2026-02-10) — P1 condo/property-management checklist; association lightly renamed.

Request body (authored):

```
Good afternoon Alejandro,
Please see the attached insurance requirements for Brickell Harbour Condominium. They will not give us building access until the certificate is on file with the Management Office. Please let me know if you need anything else.
Thank you in advance.
Best Regards,
Janice Lacayo
Office
640 S. Miami Avenue, Suite 201
Miami, FL 33130
Office (786) 294-0596
Direct (786) 740-6750
www.apogeehvac.com
```

Expected classifier output:

```json
{
  "classification": "coi_complex_review_required",
  "reply_text": "Janice,\n\nThanks for the request. Alejandro is reviewing the requirements and will get back to you shortly.\n\nRegards,",
  "original_request_summary": "Client requests a COI for APOGEE HVAC SOLUTIONS LLC with Brickell Harbour Condominium Association, Inc. as certificate holder per an attached insurance requirements document.",
  "status": "ready",
  "client_id": "apogee_hvac",
  "client_canonical_name": "APOGEE HVAC SOLUTIONS LLC",
  "template_id": "apogee_hvac_full",
  "template_filename": "Apogee_HVAC_Solutions_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Sender and body context match APOGEE HVAC SOLUTIONS LLC in the registry.",
  "certificate_holder": {
    "name": "Brickell Harbour Condominium Association, Inc.",
    "address_line_1": "1301 Brickell Bay Drive",
    "address_line_2": null,
    "city": "Miami",
    "state": "FL",
    "zip": "33131"
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
      "old_value": "NAME\nADDRESS\nSTATE, CITY ZIP CODE",
      "new_value": "Brickell Harbour Condominium Association, Inc.\n1301 Brickell Bay Drive\nMiami, FL 33131"
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
      "old_value": "Project name & Address (If Applicable)",
      "new_value": ""
    }
  ],
  "review_summary": "Attached condo requirements document: GL $1,000,000 minimum, WC required even if state-exempt, and the ACORD AI and waiver boxes must be checked for the holder. A requirements PDF always routes to Alejandro before issuance.",
  "coverage_analysis": {
    "required_coverages": [
      {
        "line": "Commercial General Liability",
        "required_each_occurrence": "1,000,000",
        "client_each_occurrence": null,
        "gap": true,
        "note": "Registry records no policy limits for APOGEE HVAC SOLUTIONS LLC, so the $1,000,000 minimum cannot be confirmed. Template carries GL. Alejandro to verify."
      },
      {
        "line": "Workers Compensation",
        "required_each_occurrence": null,
        "client_each_occurrence": null,
        "gap": false,
        "note": "Required even if the company is state-exempt; no dollar minimum stated. Template carries WC."
      }
    ],
    "required_endorsements": [
      "Additional insured (GL) for the certificate holder with the ACORD ADDL INSD box checked",
      "Waiver of subrogation (GL and WC) for the certificate holder with the ACORD SUBR WVD box checked"
    ],
    "special_language": null,
    "notes": "Certificate must be on file with the Management Office before work starts. The holder block is prescribed verbatim in the document; the draft uses it exactly."
  }
}
```

**Teaching point:** The condo/property-management checklist is the most common requirements PDF for the HVAC clients. A requirements PDF attached means coi_complex_review_required with status ready so Alejandro gets a reviewable draft. When the registry records no limits for the client, client_each_occurrence stays null and the gap is flagged with a note. Never fabricate limits.

### requirements_pdf_attached — authored example 2 (ajf_roofing, 2026-02-04 15:10:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: Request for Certificate of Insurance
- From: Romy Koo
- Attachments: MDSO Project RPQ PDC-W25014 Property and Evidence Warehouse Roof Replacement. Addendum No. 1.pdf (public bid addendum with insurance requirements: statutory WC, GL and Auto limits, prescribed certificate holder block, A.M. Best carrier gate, conditional Riggers Liability)
- Grounded in: training/a7/parsed_examples.json: mdso_rpq_addendum1 (AJF, real thread 2026-02-04) — P3 public-entity bid; prescribed holder block, holder-vs-delivery split, conditional Riggers Liability, A.M. Best gate.

Request body (authored):

```
Good morning Alejandro,
We are bidding the County warehouse roof project. The insurance requirements are in the attached addendum, the certificate holder section is on page 3. They need the certificate before the award. Thank you.
Romy Koo Accounts Payable & Human Resources | AJF Roofing D: (786) 409-6988 C: (305) 456-8006 EXT 6988 7495 NW 7 th Street Suite #10, Miami, FL 33126 E: rkoo@ajfroofingfl.com | Web: www.ajfroofingfl.
```

Expected classifier output:

```json
{
  "classification": "coi_complex_review_required",
  "reply_text": "Romy,\n\nThanks for the request. Alejandro is reviewing the requirements and will get back to you shortly.\n\nRegards,",
  "original_request_summary": "Client requests a COI for AJF Roofing, Inc. for a Miami-Dade County bid, with the certificate holder block prescribed in an attached RPQ addendum.",
  "status": "ready",
  "client_id": "ajf_roofing",
  "client_canonical_name": "AJF Roofing, Inc.",
  "template_id": "ajf_roofing_full",
  "template_filename": "AJF_Roofing_Inc_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Sender and signature match AJF Roofing, Inc. in the registry.",
  "certificate_holder": {
    "name": "MIAMI-DADE COUNTY",
    "address_line_1": "111 NW 1st Street",
    "address_line_2": "Suite 2340",
    "city": "Miami",
    "state": "FL",
    "zip": "33128"
  },
  "date_to_insert": "02/04/2026",
  "project_name": "PDC-W25014 Property and Evidence Warehouse Roof Replacement",
  "project_address": null,
  "project_unit": null,
  "is_permit": false,
  "send_completed_coi_to": null,
  "flags": [],
  "edits_to_make": [
    {
      "field": "certificate_holder",
      "action": "replace",
      "old_value": "NAME \nADDRESS\nSTATE, CITY ZIP CODE",
      "new_value": "MIAMI-DADE COUNTY\n111 NW 1st Street\nSuite 2340\nMiami, FL 33128"
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
      "old_value": "Project name & Address (If Applicable)",
      "new_value": "PDC-W25014 Property and Evidence Warehouse Roof Replacement"
    }
  ],
  "review_summary": "Public bid addendum prescribes the certificate holder block verbatim, gates carriers on A.M. Best rating, and conditionally requires Riggers Liability, a line AJF does not carry. Needs Alejandro's review before anything ships.",
  "coverage_analysis": {
    "required_coverages": [
      {
        "line": "Commercial General Liability",
        "required_each_occurrence": "1,000,000",
        "client_each_occurrence": null,
        "gap": true,
        "note": "General aggregate $2,000,000 also required; policy must NOT exclude Products and Completed Operations. Registry records no limits for AJF Roofing, Inc. Alejandro to verify."
      },
      {
        "line": "Commercial Auto",
        "required_each_occurrence": "1,000,000",
        "client_each_occurrence": null,
        "gap": true,
        "note": "Combined single limit, all owned, non-owned and hired vehicles. Registry records no limits for AJF Roofing, Inc."
      },
      {
        "line": "Workers Compensation",
        "required_each_occurrence": null,
        "client_each_occurrence": null,
        "gap": false,
        "note": "Statutory limits per Florida Statute 440 for all employees; template carries WC."
      },
      {
        "line": "Riggers Liability",
        "required_each_occurrence": "1,000,000",
        "client_each_occurrence": null,
        "gap": true,
        "note": "Conditional, required for any rigging/lifting/moving work. AJF's template has no Riggers Liability line, a specialty coverage none of the eight clients carry."
      }
    ],
    "required_endorsements": [
      "Miami-Dade County as additional insured on the CGL"
    ],
    "special_language": "Carrier must be rated at least A- (management) and Class VII (financial) in A.M. Best, or hold a valid Florida Certificate of Authority, subject to County Risk Management approval.",
    "notes": "The holder block is prescribed verbatim (CERTIFICATE HOLDER MUST READ) but the certificate is FURNISHED to a different address: MDSO Facilities Management Office, 9105 NW 25th Street, Doral, FL 33172. Holder and delivery address differ."
  }
}
```

**Teaching point:** Public-entity bid pattern: the holder block is prescribed verbatim and differs from the delivery address; a specialty line the client does not carry (Riggers) is an automatic gap; the carrier-rating gate is surfaced in special_language. Classification is complex review with a full draft, never coi_request_complete.

### requirements_pdf_attached — authored example 3 (rolandos_hvac, 2026-03-12 14:05:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: COI for Jenson Controls
- From: Hany Montero
- Attachments: Checklist Subcontractor US (Fire and Security).pdf (vendor onboarding checklist with insurance requirements: GL $2,000,000 per occurrence, Auto $1,000,000 CSL, WC $500,000, certificate holder and additional insured block, umbrella stacking permitted)
- Grounded in: training/a7/parsed_examples.json: jci_subcontractor_checklist — P5 vendor packet with GL $2M/occ (the A7b limits-gap case) applied to Rolando's (registry GL $1M/occ, GL+Auto only, no WC); GC lightly renamed.

Request body (authored):

```
Good morning Alejandro, we are getting set up as a subcontractor for Jenson Controls and they sent the attached insurance checklist. Can you send the certificate they need? Let me know if you need any additional information. Thank you! Hany Montero
Team Lead | Rolando's H.V.A.C LLC .
Air Conditioning Contractor
License Number: CAC1820272
5117 W Rio Vista, Tampa, Florida 33634
Office: (813) 373-6804 | (813) 856-1188
```

Expected classifier output:

```json
{
  "classification": "coi_complex_review_required",
  "reply_text": "Hany,\n\nThanks for the request. Alejandro is reviewing the requirements and will get back to you shortly.\n\nRegards,",
  "original_request_summary": "Client requests a COI for Rolando's HVAC LLC with Jenson Controls, Inc. as certificate holder per an attached vendor onboarding insurance checklist.",
  "status": "ready",
  "client_id": "rolandos_hvac",
  "client_canonical_name": "Rolando's HVAC LLC",
  "template_id": "rolandos_hvac_gl_auto",
  "template_filename": "Rolando_s_HVAC_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Sender and signature match Rolando's HVAC LLC in the registry.",
  "certificate_holder": {
    "name": "Jenson Controls, Inc.",
    "address_line_1": "5700 N Industrial Ave",
    "address_line_2": null,
    "city": "Milwaukee",
    "state": "WI",
    "zip": "53209"
  },
  "date_to_insert": "03/12/2026",
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
      "new_value": "Jenson Controls, Inc.\n5700 N Industrial Ave\nMilwaukee, WI 53209"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "03/12/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address ( If Applicable)",
      "new_value": ""
    }
  ],
  "review_summary": "Vendor checklist requires GL $2,000,000 per occurrence against Rolando's recorded $1,000,000, and requires WC, a line missing from Rolando's GL+Auto template. Two real gaps for Alejandro.",
  "coverage_analysis": {
    "required_coverages": [
      {
        "line": "Commercial General Liability",
        "required_each_occurrence": "2,000,000",
        "client_each_occurrence": "1,000,000",
        "gap": true,
        "note": "Rolando's GL is $1,000,000 each occurrence; the checklist requires $2,000,000 and allows umbrella to supplement, but Rolando's template carries no umbrella. Whether stacking could apply is Alejandro's call."
      },
      {
        "line": "Commercial Auto",
        "required_each_occurrence": "1,000,000",
        "client_each_occurrence": "1,000,000",
        "gap": false,
        "note": "Combined single limit matches the requirement."
      },
      {
        "line": "Workers Compensation",
        "required_each_occurrence": "500,000",
        "client_each_occurrence": null,
        "gap": true,
        "note": "Rolando's template has no Workers Compensation line (GL + Auto only)."
      }
    ],
    "required_endorsements": [
      "Jenson Controls, Inc. additional insured on GL and Auto"
    ],
    "special_language": null,
    "notes": "Vendor onboarding packet; certificates are tracked on a third-party compliance platform with expiry reminders. Non-owned auto coverage additionally required when personal vehicles are used for work."
  }
}
```

**Teaching point:** The limits-gap case: a required limit above what the registry records ($2M vs $1M GL) is a computable gap, and a required line missing from the template (WC on Rolando's) is an automatic gap. The comparison goes in coverage_analysis for Alejandro; the template is never modified and nothing ships without his review.

### requirements_pdf_attached — authored example 4 (central_comfort_ac, 2026-03-25 18:30:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: FW: Vendor Packet - Belle Harbour
- From: Cynthia Garrido
- Attachments: Vendor Set Up Package.pdf (vendor packet with insurance requirements: GL/WC/Umbrella minimums, annotated sample COI page, dual certificate holder, ACORD 25 edition requirement); image001.jpg (image, likely signature graphic)
- Grounded in: training/a7/parsed_examples.json: kw_belle_tower_vendor_packet (dual holder, ACORD edition, AI on umbrella) + stratus_sample_cert_305power (damage-to-rented $200k sub-limit lesson), applied to Central Comfort's real condo-association traffic; parties lightly renamed.

Request body (authored):

```
Good Afternoon Alejandro,
The property manager for Belle Harbour sent the attached vendor package. They need the certificate on file before our maintenance visit next week. Can you please send it with what they ask for?
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
  "classification": "coi_complex_review_required",
  "reply_text": "Cynthia,\n\nThanks for the request. Alejandro is reviewing the requirements and will get back to you shortly.\n\nRegards,",
  "original_request_summary": "Client requests a COI for Central Comfort Air Conditioning with Belle Harbour Condominium Association, Inc. and its property manager as dual certificate holders per an attached vendor packet.",
  "status": "ready",
  "client_id": "central_comfort_ac",
  "client_canonical_name": "Central Comfort Air Conditioning",
  "template_id": "central_comfort_gl_wc",
  "template_filename": "Central_Comfort_Air_Conditioning_Inc_COI.pdf",
  "confidence": "high",
  "confidence_notes": "Sender and signature match Central Comfort Air Conditioning in the registry.",
  "certificate_holder": {
    "name": "Belle Harbour Condominium Association, Inc.",
    "address_line_1": "9200 Collins Avenue",
    "address_line_2": null,
    "city": "Miami Beach",
    "state": "FL",
    "zip": "33154"
  },
  "date_to_insert": "03/25/2026",
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
      "new_value": "Belle Harbour Condominium Association, Inc.\n9200 Collins Avenue\nMiami Beach, FL 33154"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "03/25/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address ( If Applicable)",
      "new_value": ""
    }
  ],
  "review_summary": "Vendor packet demands a dual holder block (Association + property manager), AI on primary AND excess/umbrella, a $200,000 damage-to-rented sub-limit above Central Comfort's $100,000, and a specific ACORD 25 edition.",
  "coverage_analysis": {
    "required_coverages": [
      {
        "line": "Commercial General Liability",
        "required_each_occurrence": "1,000,000",
        "client_each_occurrence": "1,000,000",
        "gap": false,
        "note": "Meets the $1,000,000 each-occurrence minimum."
      },
      {
        "line": "GL - Damage to Rented Premises",
        "required_each_occurrence": "200,000",
        "client_each_occurrence": "100,000",
        "gap": true,
        "note": "Sample cert shows $200,000 damage-to-rented-premises; Central Comfort's GL box is $100,000. Sub-limit gap."
      },
      {
        "line": "Workers Compensation",
        "required_each_occurrence": "500,000",
        "client_each_occurrence": "1,000,000",
        "gap": false,
        "note": "Required even if state-exempt; Central Comfort carries $1,000,000 employers liability."
      },
      {
        "line": "Umbrella/Excess Liability",
        "required_each_occurrence": "1,000,000",
        "client_each_occurrence": null,
        "gap": true,
        "note": "Central Comfort's template has no Umbrella/Excess line; the packet requires AI on primary AND excess/umbrella policies."
      }
    ],
    "required_endorsements": [
      "Association and property manager additional insured on all liability policies (primary and excess/umbrella), primary and non-contributory",
      "Waiver of subrogation in favor of Association and property manager on all liability and WC policies",
      "Certificate must be on ACORD 25 (2016/03) or (2014/01); other editions rejected"
    ],
    "special_language": "Vendor shall cause the Association and its property manager to be included as additional insureds on a primary and non-contributory basis on all of its commercial general liability insurance policies (both primary and excess/umbrella).",
    "notes": "Dual certificate holder: both the Association and the property manager go in the holder box; the address is the Association's management office. Insured name must exactly match the W-9."
  },
  "certificate_holder_lines": [
    "Belle Harbour Condominium Association, Inc.",
    "Keystone Property Management & Consulting, LLC",
    "9200 Collins Avenue",
    "Miami Beach, FL 33154"
  ]
}
```

**Teaching point:** Property-management vendor packets hide three traps: a dual-entity holder block (use certificate_holder_lines), sub-limit deltas that count as gaps (damage-to-rented $200k vs $100k), and an ACORD edition requirement. All of it goes to coverage_analysis; the classification is complex review.

## complex_endorsements (3 authored examples)

Endorsement demands (ISO form codes with editions, notice-of-cancellation days, endorsement-copies-attached, AI/WOS box demands) arrive in plain body text with no requirements attachment. Still `coi_complex_review_required`.

### complex_endorsements — authored example 1 (ajf_roofing, 2026-01-30 16:20:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: COI for Marlowe Construction - endorsement requirements
- From: Guillermo Vidaurreta
- Attachments: image001.png (image, likely signature graphic)
- Grounded in: training/a7/parsed_examples.json: moriarty_subcontract_article8 + camcon_sample_subcontractor_certificate — CG 20 10 / CG 20 37 with editions, P&NC, 30/10 notice of cancellation, expressed as body text with no attachment; GC fictional.

Request body (authored):

```
Alejandro, good morning. For the new project the GC needs the COI made out to:
Marlowe Construction Group, LLC
8300 NW 53rd Street, Suite 350
Doral, FL 33166
Per their subcontract we must show additional insured on forms CG 20 10 10/01 and CG 20 37 10/01 or equivalent, primary and non-contributory, waiver of subrogation, and 30 days notice of cancellation (10 days for non-payment). Can you confirm the cert will show all of this? Thank you.
Guillermo Vidaurreta Commercial Project Manager & Estimator | AJF Roofing D : (786) 420-2012 O : (305) 456-8006 C: (305) 793-5153 7495 NW 7 th Street Suite #8, Miami, FL 33126 E: gvidaurreta@ajfroofingfl.com | Web: www.ajfroofingfl.com
```

Expected classifier output:

```json
{
  "classification": "coi_complex_review_required",
  "reply_text": "Guillermo,\n\nThanks for the request. Alejandro is reviewing the requirements and will get back to you shortly.\n\nRegards,",
  "original_request_summary": "Client requests a COI for AJF Roofing, Inc. with Marlowe Construction Group, LLC as certificate holder and names specific ISO endorsement forms and cancellation-notice terms in the body.",
  "status": "ready",
  "client_id": "ajf_roofing",
  "client_canonical_name": "AJF Roofing, Inc.",
  "template_id": "ajf_roofing_full",
  "template_filename": "AJF_Roofing_Inc_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Sender and signature match AJF Roofing, Inc. in the registry.",
  "certificate_holder": {
    "name": "Marlowe Construction Group, LLC",
    "address_line_1": "8300 NW 53rd Street",
    "address_line_2": "Suite 350",
    "city": "Doral",
    "state": "FL",
    "zip": "33166"
  },
  "date_to_insert": "01/30/2026",
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
      "old_value": "NAME \nADDRESS\nSTATE, CITY ZIP CODE",
      "new_value": "Marlowe Construction Group, LLC\n8300 NW 53rd Street\nSuite 350\nDoral, FL 33166"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "01/30/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address (If Applicable)",
      "new_value": ""
    }
  ],
  "review_summary": "Body text names ISO endorsement forms with editions (CG 20 10 10/01 and CG 20 37 10/01), primary and non-contributory, waiver, and a 30/10 notice-of-cancellation demand, and asks us to confirm compliance. Only Alejandro can answer that.",
  "coverage_analysis": {
    "required_coverages": [],
    "required_endorsements": [
      "Additional insured via CG 20 10 10/01 AND CG 20 37 10/01 or equivalent (ongoing and completed operations)",
      "Primary and non-contributory for additional insureds",
      "Waiver of subrogation",
      "30 days notice of cancellation, 10 days for non-payment"
    ],
    "special_language": null,
    "notes": "The registry does not record which ISO endorsement forms are on AJF's policies, so CG 20 10 10/01 / CG 20 37 10/01 compliance cannot be confirmed. Notice-of-cancellation days are a policy feature a certificate cannot create. The sender explicitly asks for confirmation; that answer must come from Alejandro."
  }
}
```

**Teaching point:** Endorsement form numbers with editions in plain body text, with no attachment at all, still route to coi_complex_review_required. The classifier never confirms form editions, P&NC, or notice-of-cancellation days; it extracts the demands verbatim into coverage_analysis and lets Alejandro answer.

### complex_endorsements — authored example 2 (rolandos_hvac, 2026-01-14 15:45:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: Rolando's HVAC COI - Ashford Landing
- From: Lisandra Leyva
- Attachments: (none)
- Grounded in: training/a7/parsed_examples.json: rolandos_test_entity_packet (10-page deliverable = cert + endorsement pages) + nv2a_sdtoc_endorsement_packet (endorsement copies demanded); holder fictional.

Request body (authored):

```
Good afternoon Alejandro,
The management company for Ashford Landing needs a certificate with the holder below, and they also require copies of the actual GL endorsement pages (blanket additional insured, primary and non-contributory, and waiver of subrogation) attached behind the certificate.
Ashford Landing Apartments LLC
4520 Marion Oaks Blvd
Ocala, FL 34473
Thank you,
Lisandra
Rolando's HVAC LLC
```

Expected classifier output:

```json
{
  "classification": "coi_complex_review_required",
  "reply_text": "Lisandra,\n\nThanks for the request. Alejandro is reviewing the requirements and will get back to you shortly.\n\nRegards,",
  "original_request_summary": "Client requests a COI for Rolando's HVAC LLC with Ashford Landing Apartments LLC as certificate holder plus copies of the GL endorsement pages attached behind the certificate.",
  "status": "ready",
  "client_id": "rolandos_hvac",
  "client_canonical_name": "Rolando's HVAC LLC",
  "template_id": "rolandos_hvac_gl_auto",
  "template_filename": "Rolando_s_HVAC_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Sender matches Rolando's HVAC LLC contact in the registry.",
  "certificate_holder": {
    "name": "Ashford Landing Apartments LLC",
    "address_line_1": "4520 Marion Oaks Blvd",
    "address_line_2": null,
    "city": "Ocala",
    "state": "FL",
    "zip": "34473"
  },
  "date_to_insert": "01/14/2026",
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
      "new_value": "Ashford Landing Apartments LLC\n4520 Marion Oaks Blvd\nOcala, FL 34473"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "01/14/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address ( If Applicable)",
      "new_value": ""
    }
  ],
  "review_summary": "Requester demands copies of the actual GL endorsement pages (blanket AI, P&NC, waiver) behind the certificate. Endorsement pages live outside the COI template, so the automation cannot assemble this packet.",
  "coverage_analysis": {
    "required_coverages": [],
    "required_endorsements": [
      "Copies of the GL Blanket Additional Insured, Primary & Non-Contributory, and Waiver of Subrogation endorsement pages attached behind the certificate"
    ],
    "special_language": null,
    "notes": "Endorsement pages are separate policy documents that do not exist inside the COI template PDF; the draft cannot include them. Alejandro must pull the endorsement forms and assemble the full packet."
  }
}
```

**Teaching point:** An endorsement-copies-attached demand is a recurring GC/property-manager ask that a flat template can never satisfy. Detect it, route to complex review, and flag it explicitly. Never claim the copies are attached and never ship the bare cert as if the demand were met.

### complex_endorsements — authored example 3 (305_power_corp, 2026-04-16 17:55:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: Dorada Construction - vendor setup COI
- From: Yisel Fonseca
- Attachments: (none)
- Grounded in: training/a7/parsed_examples.json: bengoa_vendor_setup — GC vendor-setup demands (AI + WOS boxes on all coverages, GL P&NC) that map almost 1:1 onto 305 Power's template boilerplate; GC lightly renamed.

Request body (authored):

```
Good morning Alejandro,
Dorada Construction is setting us up as a vendor and needs the COI to show:
Certificate Holder and Additional Insured: Dorada Construction Group, Inc, 2311 Taft Street, Hollywood, FL 33020
GL must be primary and non-contributory, waiver of subrogation in favor of the certificate holder on GL, Auto and WC, and the additional insured and waiver boxes checked on all coverages.
They asked for it before Friday. Thank you,
Yisel Fonseca
305 Power Corp
```

Expected classifier output:

```json
{
  "classification": "coi_complex_review_required",
  "reply_text": "Yisel,\n\nThanks for the request. Alejandro is reviewing the requirements and will get back to you shortly.\n\nRegards,",
  "original_request_summary": "Client requests a COI for 305 Power Corp with Dorada Construction Group, Inc as certificate holder and additional insured, with P&NC and waiver demands spelled out in the body.",
  "status": "ready",
  "client_id": "305_power_corp",
  "client_canonical_name": "305 Power Corp",
  "template_id": "305_power_full",
  "template_filename": "305_Power_Corp_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Sender signature matches 305 Power Corp in the registry.",
  "certificate_holder": {
    "name": "Dorada Construction Group, Inc",
    "address_line_1": "2311 Taft Street",
    "address_line_2": null,
    "city": "Hollywood",
    "state": "FL",
    "zip": "33020"
  },
  "date_to_insert": "04/16/2026",
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
      "old_value": "Bengoa Construction, Inc\n2200 N. Dixie Hwy.\nHollywood, FL 33020",
      "new_value": "Dorada Construction Group, Inc\n2311 Taft Street\nHollywood, FL 33020"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "04/14/2026",
      "new_value": "04/16/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address ( If Applicable)",
      "new_value": ""
    }
  ],
  "review_summary": "Vendor-setup demands in the body: holder as additional insured, GL primary and non-contributory, waivers on GL, Auto and WC, AI and WOS boxes checked. Likely satisfied by 305 Power's blanket endorsements, but that call is Alejandro's.",
  "coverage_analysis": {
    "required_coverages": [],
    "required_endorsements": [
      "Dorada Construction Group, Inc additional insured (GL and Auto) as certificate holder",
      "GL primary and non-contributory",
      "Waiver of subrogation in favor of the certificate holder on GL, Auto and WC",
      "AI and WOS boxes checked on all required coverages"
    ],
    "special_language": null,
    "notes": "305 Power's template already shows blanket AI by written contract, GL primary and non-contributory, and waivers on GL, Auto and WC (registry policies show addl_insured and subr_wvd), so this likely passes as-is. Explicit endorsement demands still require Alejandro's confirmation before shipping."
  }
}
```

**Teaching point:** Even when body-text endorsement demands appear to map 1:1 onto the template's blanket boilerplate (the classic GC vendor-setup pattern), explicit AI/WOS/P&NC demands route to complex review. The analysis may say 'likely compliant', but the ship/no-ship decision belongs to Alejandro.

## specific_language (3 authored examples)

The requester prescribes exact wording: a must-read holder block or verbatim description-of-operations language. `coi_complex_review_required` with the wording captured verbatim in `special_language`.

### specific_language — authored example 1 (ajf_roofing, 2026-02-17 14:20:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: URGENT COI - certificate holder must read exactly
- From: Janette Diaz
- Attachments: image001.png (image, likely signature graphic)
- Grounded in: training/a7/parsed_examples.json: mdso_rpq_addendum1 ('CERTIFICATE HOLDER MUST READ') + camcon_sample_subcontractor_certificate ('its officers, employees and agents' AI phrasing) — the officers/agents/architects holder-wording pattern in body text.

Request body (authored):

```
Good morning Alejandro,
For the school project the certificate holder must read exactly as follows:
The School Board of Miami-Dade County, Florida, its officers, agents and architects
1450 NE 2nd Avenue
Miami, FL 33132
Please make sure it shows exactly like that, they rejected the last sub's cert over the wording. Thank you.
Janette Diaz | AJF Roofing 7495 NW 7 th Street Suite #8, Miami, FL 33126
```

Expected classifier output:

```json
{
  "classification": "coi_complex_review_required",
  "reply_text": "Janette,\n\nThanks for the request. Alejandro is reviewing the requirements and will get back to you shortly.\n\nRegards,",
  "original_request_summary": "Client requests a COI for AJF Roofing, Inc. where the certificate holder block must read exactly as prescribed, including officers, agents and architects wording.",
  "status": "ready",
  "client_id": "ajf_roofing",
  "client_canonical_name": "AJF Roofing, Inc.",
  "template_id": "ajf_roofing_full",
  "template_filename": "AJF_Roofing_Inc_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Sender and signature match AJF Roofing, Inc. in the registry.",
  "certificate_holder": {
    "name": "The School Board of Miami-Dade County, Florida, its officers, agents and architects",
    "address_line_1": "1450 NE 2nd Avenue",
    "address_line_2": null,
    "city": "Miami",
    "state": "FL",
    "zip": "33132"
  },
  "date_to_insert": "02/17/2026",
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
      "old_value": "NAME \nADDRESS\nSTATE, CITY ZIP CODE",
      "new_value": "The School Board of Miami-Dade County, Florida, its officers, agents and architects\n1450 NE 2nd Avenue\nMiami, FL 33132"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "02/17/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address (If Applicable)",
      "new_value": ""
    }
  ],
  "review_summary": "The holder box wording is prescribed verbatim and includes non-entity language (its officers, agents and architects). A prior sub's cert was rejected over wording, so Alejandro must confirm the exact block before issuance.",
  "coverage_analysis": {
    "required_coverages": [],
    "required_endorsements": [],
    "special_language": "The School Board of Miami-Dade County, Florida, its officers, agents and architects",
    "notes": "Draft carries the prescribed holder wording character for character. Do not normalize, trim, or 'fix' the phrase; the requester rejects certificates over wording."
  }
}
```

**Teaching point:** 'Must read exactly' plus officers/agents/architects holder phrasing is the specific-language pattern: complex review, with the demanded wording quoted verbatim in special_language and reproduced character for character in the draft. Never paraphrase or shorten a prescribed holder block.

### specific_language — authored example 2 (rolandos_hvac, 2026-02-24 16:10:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: COI needed - Meridian Residential
- From: Dana Whitfield
- Attachments: (none)
- Grounded in: training/a7/requirements_catalog.json: rolandos custom-AI-language sample certs (Progress Residential et al.) + rolandos_test_entity_packet's named-entity AI wording ('Main Street Renewal and Amherst Group Properties...'); operator lightly renamed.

Request body (authored):

```
Good afternoon,
We manage single family rental homes that Rolando's HVAC services. Please issue an updated certificate with the holder below. The description of operations must include the following language: "Meridian Residential, LLC and its affiliates and subsidiaries are Additional Insured on a primary and noncontributory basis under the General Liability coverage for work performed by the Named Insured."
Meridian Residential, LLC
5001 Plaza on the Lake, Suite 200
Austin, TX 78746
Thank you,
Dana Whitfield
Vendor Compliance | Meridian Residential
```

Expected classifier output:

```json
{
  "classification": "coi_complex_review_required",
  "reply_text": "Dana,\n\nThanks for the request. Alejandro is reviewing the requirements and will get back to you shortly.\n\nRegards,",
  "original_request_summary": "Third party requests a COI for Rolando's HVAC LLC with Meridian Residential, LLC as certificate holder and prescribes exact additional-insured wording for the description of operations.",
  "status": "ready",
  "client_id": "rolandos_hvac",
  "client_canonical_name": "Rolando's HVAC LLC",
  "template_id": "rolandos_hvac_gl_auto",
  "template_filename": "Rolando_s_HVAC_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Client is Rolando's HVAC LLC from the body context; the sender is a third party requesting on our insured's behalf.",
  "certificate_holder": {
    "name": "Meridian Residential, LLC",
    "address_line_1": "5001 Plaza on the Lake",
    "address_line_2": "Suite 200",
    "city": "Austin",
    "state": "TX",
    "zip": "78746"
  },
  "date_to_insert": "02/24/2026",
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
      "new_value": "Meridian Residential, LLC\n5001 Plaza on the Lake\nSuite 200\nAustin, TX 78746"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "02/24/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address ( If Applicable)",
      "new_value": ""
    }
  ],
  "review_summary": "Requester prescribes custom named-entity AI wording (entity plus open-ended affiliates and subsidiaries) for the description of operations. That differs from the template's blanket by-written-contract boilerplate, which the system never rewords.",
  "coverage_analysis": {
    "required_coverages": [],
    "required_endorsements": [
      "Meridian Residential, LLC and its affiliates and subsidiaries additional insured (GL), primary and non-contributory"
    ],
    "special_language": "Meridian Residential, LLC and its affiliates and subsidiaries are Additional Insured on a primary and noncontributory basis under the General Liability coverage for work performed by the Named Insured.",
    "notes": "Prescribed description-of-operations wording names entities beyond the certificate holder and is open-ended (affiliates and subsidiaries). The template boilerplate must not be altered without Alejandro."
  }
}
```

**Teaching point:** Prescribed description-of-operations wording, especially custom named-entity AI with open-ended affiliates, is specific_language: complex review, wording captured verbatim in special_language, and the template boilerplate left untouched. Third-party sender does not change the insured client, which comes from context.

### specific_language — authored example 3 (central_comfort_ac, 2026-03-05 19:15:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: COI - Palm Grove Towers
- From: Cynthia Garrido
- Attachments: image001.jpg (image, likely signature graphic)
- Grounded in: training/a7/requirements_catalog.json: central_comfort condo-association samples (Paraiso Bay, Icon Bay) + P1 checklist pattern; association and manager fictional.

Request body (authored):

```
Good Morning Alejandro,
Palm Grove Towers is asking that the certificate include this exact wording in the description: "Palm Grove Towers Condominium Association, Inc., its Board of Directors, officers and managing agent are named as Additional Insured on a primary and non-contributory basis and a Waiver of Subrogation applies in their favor."
The holder is:
Palm Grove Towers Condominium Association, Inc.
c/o Horizon Management Group
701 Brickell Key Blvd
Miami, FL 33131
Thank you!
Cynthia Garrido
Central Comfort Air Conditioning
p:
305-598-7575
```

Expected classifier output:

```json
{
  "classification": "coi_complex_review_required",
  "reply_text": "Cynthia,\n\nThanks for the request. Alejandro is reviewing the requirements and will get back to you shortly.\n\nRegards,",
  "original_request_summary": "Client requests a COI for Central Comfort Air Conditioning with Palm Grove Towers Condominium Association, Inc. as certificate holder and prescribes exact additional-insured wording for the description.",
  "status": "ready",
  "client_id": "central_comfort_ac",
  "client_canonical_name": "Central Comfort Air Conditioning",
  "template_id": "central_comfort_gl_wc",
  "template_filename": "Central_Comfort_Air_Conditioning_Inc_COI.pdf",
  "confidence": "high",
  "confidence_notes": "Sender and body context match Central Comfort Air Conditioning in the registry.",
  "certificate_holder": {
    "name": "Palm Grove Towers Condominium Association, Inc.",
    "address_line_1": "701 Brickell Key Blvd",
    "address_line_2": null,
    "city": "Miami",
    "state": "FL",
    "zip": "33131"
  },
  "date_to_insert": "03/05/2026",
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
      "new_value": "Palm Grove Towers Condominium Association, Inc.\n701 Brickell Key Blvd\nMiami, FL 33131"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "03/05/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address ( If Applicable)",
      "new_value": ""
    }
  ],
  "review_summary": "Association prescribes exact description wording extending AI and waiver to its Board of Directors, officers and managing agent, entities beyond the certificate holder that the template's blanket language does not name.",
  "coverage_analysis": {
    "required_coverages": [],
    "required_endorsements": [
      "Association, its Board of Directors, officers and managing agent additional insured (GL), primary and non-contributory",
      "Waiver of subrogation in favor of the same parties"
    ],
    "special_language": "Palm Grove Towers Condominium Association, Inc., its Board of Directors, officers and managing agent are named as Additional Insured on a primary and non-contributory basis and a Waiver of Subrogation applies in their favor.",
    "notes": "Holder block includes a c/o management-company line; the full block is preserved in certificate_holder_lines. The demanded wording covers parties beyond the certificate holder; only Alejandro can approve inserting it."
  },
  "certificate_holder_lines": [
    "Palm Grove Towers Condominium Association, Inc.",
    "c/o Horizon Management Group",
    "701 Brickell Key Blvd",
    "Miami, FL 33131"
  ]
}
```

**Teaching point:** 'Include this exact wording' is specific_language even when it resembles the template boilerplate: the demanded text names parties beyond the certificate holder (board, officers, managing agent), so it routes to complex review with the wording quoted verbatim. The c/o line stays in the holder block.

## spanish (4 authored examples)

Spanish-language requests exercising the locked-in reply rules: name-comma opener, `envíame` never `mándame`, `certificate holder` and `ZIP code` stay English, `Saludos,` closer, no dashes anywhere.

### spanish — authored example 1 (rolandos_hvac, 2026-02-18 13:40:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: COI para Grove Isle
- From: Rolando Leyva
- Attachments: (none)
- Grounded in: Registry Spanish aliases (hvac de rolando) + benchmark Spanish traffic; the plain body-only-complete pattern rendered in Spanish; holder fictional.

Request body (authored):

```
Alejandro, buenas tardes. Necesito un certificado para este holder:
Grove Isle Property Management LLC
2951 S Bayshore Drive
Miami, FL 33133
Es para un trabajo de mantenimiento, no hay proyecto. Gracias.
Rolando Leyva
Rolando's HVAC
```

Expected classifier output:

```json
{
  "classification": "coi_request_complete",
  "reply_text": null,
  "original_request_summary": "Client requests a COI for Rolando's HVAC LLC with Grove Isle Property Management LLC as certificate holder, request sent in Spanish.",
  "status": "ready",
  "client_id": "rolandos_hvac",
  "client_canonical_name": "Rolando's HVAC LLC",
  "template_id": "rolandos_hvac_gl_auto",
  "template_filename": "Rolando_s_HVAC_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Sender and signature match Rolando's HVAC LLC in the registry.",
  "certificate_holder": {
    "name": "Grove Isle Property Management LLC",
    "address_line_1": "2951 S Bayshore Drive",
    "address_line_2": null,
    "city": "Miami",
    "state": "FL",
    "zip": "33133"
  },
  "date_to_insert": "02/18/2026",
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
      "new_value": "Grove Isle Property Management LLC\n2951 S Bayshore Drive\nMiami, FL 33133"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "02/18/2026"
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

**Teaching point:** A complete Spanish request behaves exactly like English: coi_request_complete, no reply needed, address used verbatim. The JSON stays in English (original_request_summary included, per the prompt rules). Language only changes client-facing reply text, which here is null.

### spanish — authored example 2 (emp3_solutions, 2026-03-03 15:25:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: COI urgente
- From: Mariela Paz
- Attachments: (none)
- Grounded in: BENCHMARK_REPORT.md bench-13 (address hallucination, the most dangerous failure) rendered as a Spanish request against the prompt's Spanish lookup-failed template; holder fictional.

Request body (authored):

```
Buenas tardes Alejandro,
Necesito un COI para EMP 3 lo antes posible. El certificado va a nombre de Coastal Ridge Builders. ¿Me lo puedes enviar hoy?
Gracias,
Mariela Paz
EMP 3 Solutions
```

Expected classifier output:

```json
{
  "classification": "coi_request_incomplete",
  "reply_text": "Mariela,\n\nCon gusto preparo el COI. Intenté buscar la dirección de Coastal Ridge Builders pero no la encontré. Por favor envíame la dirección que el certificate holder quiere en el COI.\n\nSaludos,",
  "original_request_summary": "Client requests a COI for EMP 3 Solutions, Inc with Coastal Ridge Builders as certificate holder but provided no address, and lookup could not confirm one."
}
```

**Teaching point:** The Spanish reply rules, locked in: name-comma opener, envíame (never mándame), certificate holder stays in English inside the Spanish sentence, closes with Saludos, and no dashes anywhere. And the anti-fabrication rule: a generic holder name with no address and no certain lookup means ask, never invent an address.

### spanish — authored example 3 (ajf_roofing, 2026-01-13 16:35:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: COI para Barros Owner - AJF
- From: Romy Koo
- Attachments: AJF Roofing - Barros Owner 8.23.24.pdf (ACORD COI, insured: AJF Roofing, Inc.; certificate holder: Barros Development Owner, LLC)
- Grounded in: BENCHMARK_REPORT.md bench-4 ('Sorry Alejandro Necesito estos dos certificados. Adjunto los examples.' + 2 prior ACORD COIs, an ABSOLUTE RULE violation at high confidence), reduced to a single certificate; holder fictional.

Request body (authored):

```
Sorry Alejandro Necesito este certificado para el GC de abajo. Adjunto el example. Gracias
Romy Koo Accounts Payable & Human Resources | AJF Roofing D: (786) 409-6988 C: (305) 456-8006 EXT 6988 7495 NW 7 th Street Suite #10, Miami, FL 33126 E: rkoo@ajfroofingfl.com | Web: www.ajfroofingfl.
```

Expected classifier output:

```json
{
  "classification": "coi_complex_review_required",
  "reply_text": "Romy,\n\nGracias por el envío. Alejandro está revisando los requisitos y te responderá pronto.\n\nSaludos,",
  "original_request_summary": "Client requests a COI for AJF Roofing, Inc. with Barros Development Owner, LLC as certificate holder, sending a prior COI as reference, request in Spanish.",
  "status": "ready",
  "client_id": "ajf_roofing",
  "client_canonical_name": "AJF Roofing, Inc.",
  "template_id": "ajf_roofing_full",
  "template_filename": "AJF_Roofing_Inc_COI_Template.pdf",
  "confidence": "high",
  "confidence_notes": "Sender and signature match AJF Roofing, Inc. in the registry.",
  "certificate_holder": {
    "name": "Barros Development Owner, LLC",
    "address_line_1": "3055 NE 1st Avenue",
    "address_line_2": null,
    "city": "Miami",
    "state": "FL",
    "zip": "33137"
  },
  "date_to_insert": "01/13/2026",
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
      "old_value": "NAME \nADDRESS\nSTATE, CITY ZIP CODE",
      "new_value": "Barros Development Owner, LLC\n3055 NE 1st Avenue\nMiami, FL 33137"
    },
    {
      "field": "date",
      "action": "replace",
      "old_value": "MM/DD/YYYY",
      "new_value": "01/13/2026"
    },
    {
      "field": "description_of_operations",
      "action": "replace",
      "old_value": "Project name & Address (If Applicable)",
      "new_value": ""
    }
  ],
  "review_summary": "Client attached a prior COI as reference. A reference COI is insurance content, so the ABSOLUTE RULE applies even though the holder is fully extractable from it. Request is in Spanish, so the acknowledgment is in Spanish.",
  "coverage_analysis": {
    "required_coverages": [],
    "required_endorsements": [],
    "special_language": null,
    "notes": "Draft prepared from the holder extracted off the reference cert; Alejandro to verify against the attachment/body."
  }
}
```

**Teaching point:** The top benchmark failure, in Spanish: a reference COI attached to a Spanish request still routes to coi_complex_review_required (never coi_request_complete), with the holder extracted from the attachment for the draft. The acknowledgment follows the Spanish rules: name-comma opener, Gracias por el envío body, Saludos closer, no dashes.

### spanish — authored example 4 (central_comfort_ac, 2026-03-18 14:50:00)

**DRAFT — AUTHORED, NOT MINED — NEEDS ALEX APPROVAL**

- Subject: Certificado para Marina Bay
- From: Yanet Soto
- Attachments: (none)
- Grounded in: coi_system_prompt.txt Spanish missing-ZIP template + BENCHMARK_REPORT.md bench-25 (mangled/absent ZIP pattern); holder fictional.

Request body (authored):

```
Buenos días Alejandro,
¿Me puedes enviar un certificado para el holder de abajo?
Marina Bay Yacht Club
1801 SE 17th Street
Fort Lauderdale, FL
Lo necesitan hoy si es posible. Gracias.
Yanet Soto
Central Comfort Air Conditioning
```

Expected classifier output:

```json
{
  "classification": "coi_request_incomplete",
  "reply_text": "Yanet,\n\nCon gusto preparo el COI. Solo necesito el ZIP code de Marina Bay Yacht Club en 1801 SE 17th Street, Fort Lauderdale, FL y te lo envío.\n\nSaludos,",
  "original_request_summary": "Client requests a COI for Central Comfort Air Conditioning with Marina Bay Yacht Club as certificate holder but the address is missing its ZIP code."
}
```

**Teaching point:** A missing ZIP is missing information in any language: never guess it (Miami alone has 50+ ZIPs). The Spanish missing-ZIP template keeps ZIP code in English, opens with the name and a comma, ends with Saludos, and contains no dashes.
