# COI Classifier Training Library

Generated 2026-07-06T11:39:26 from `coi_review_decisions_retagged_2026-07-06.json` by `training/build_training_library.py`.

Decisions: 113 total — 32 approve / 9 disagree / 71 skip / 0 unknown hashes. Effective verdicts: 21 correct, 4 incorrect, 16 questionable, 0 needs discussion.

## Coverage

| Bucket | Selected | Available |
|---|---|---|
| requirements_pdf_attached | 0 | 0 |
| reference_coi_attached | 0 | 0 |
| complex_endorsements | 0 | 0 |
| specific_language | 0 | 0 |
| spanish | 0 | 0 |
| vague_or_missing_info | 1 | 1 |
| body_only_request | 1 | 1 |
| **total** | **2** | **2** |

Available = effective-correct COIs whose thread carries a usable, faithfully modelable client request. Truncated holder crops, batch-shaped requests, and non-US addresses are excluded rather than guessed.

## requirements_pdf_attached (0 examples)

_No usable material in this bucket yet — see Coverage and Gaps._

## reference_coi_attached (0 examples)

_No usable material in this bucket yet — see Coverage and Gaps._

## complex_endorsements (0 examples)

_No usable material in this bucket yet — see Coverage and Gaps._

## specific_language (0 examples)

_No usable material in this bucket yet — see Coverage and Gaps._

## spanish (0 examples)

_No usable material in this bucket yet — see Coverage and Gaps._

## vague_or_missing_info (1 example)

### vague_or_missing_info — example 1 (ajf_roofing, 2026-01-30 20:15:36)

- Subject: FW: SDTOC | AJF COI
- From: Janette Diaz
- Attachments: COI 2026.pdf (scanned PDF, image-only); image001.png (image, likely signature graphic); image002.png (image, likely signature graphic); image003.png (image, likely signature graphic); image004.png (image, likely signature graphic)
- Alex's note: andrea vargas fucking works on my team same as katherin molina and christian devilme and other people with @usi EMAILS....... the coi is correct - this is one of the most complex scenarios though for this you would create it on the backend and you will always send it to me and i will need to approve before you send out to client and requestor.
- Historical resolution: NV2A Dragados JV and Miami Dade / County / C/O: myCOI P.O. Box# 501970 8710

Request body (cleaned):

```
From: Sandra Lorie <slorie@nv2agroup.com>
Sent: Friday, January 30, 2026 11:45 AM
To: Marlene Torres <mtorres@ajfroofingfl.com>; Janette Diaz <jdiaz@ajfroofingfl.com>; Michael Roman <mroman@nv2agroup.com>
Subject: RE: SDTOC | AJF COI
Importance: High Hi Marlene! Thank you for talking with me, it was a pleasure 😊 @Janette Diaz I have confirmed with our accounting folks that we have been funded by the Owner through November 2025. The Textura hold for insurance has been removed in good faith while we iron out some minor details with the insurances. With the renewal of AJFs insurances, we received the attached renewal COI but are still missing some items that follow: General Liability · Please confirm aggregate limit applies on a per project basis on the certificate and/or by uploading additional documentation. · Primary and Non-Contributory endorsement. · A physical copy of the Waiver of Subrogation endorsement. · A physical copy of the Additional Insured forms for both ongoing and completed operations. Umbrella Excess Liability · Confirm on certificate that excess/umbrella follows form. Automobile Liability · Primary and Non-Contributory endorsement. · A physical copy of the Waiver of Subrogation endorsement. · A physical copy of additional insured endorsement. Workers Compensation · A physical copy of the Waiver of Subrogation endorsement must be submitted. Also, I was checking Textura and there seems to be a hold for the August Draw unrelated to insurance. @Michael Roman Can 
```

Expected classifier output:

```json
{
  "classification": "coi_request_incomplete",
  "reply_text": "Janette,\n\nHappy to put this together for you. I tried looking up the address for NV2A Dragados JV and Miami Dade but couldn't find a match. Please send the address the certificate holder wants on the COI.\n\nRegards,",
  "original_request_summary": "Client requests a COI for AJF Roofing, Inc. with NV2A Dragados JV and Miami Dade as certificate holder but provided no address, and lookup could not confirm one."
}
```

**Teaching point:** Holder information is missing from the request: look it up, and if the lookup cannot confirm a single match, ask. NEVER invent an address (the benchmark's most dangerous failure was a hallucinated address shipped at high confidence). (This request was historically resolved to the holder shown in historical_resolution.)

## body_only_request (1 example)

### body_only_request — example 1 (central_comfort_ac, 2026-02-10 21:29:25)

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

## Negative examples (4)

### negative 1 (apogee_hvac, 52491592_1 Homes South Beach 1 Hotel South Beach_01212026.pdf)

```
Hello Alejandro,
I need this COI updated as soon as possible as per provided requirements. Certificate Holder needs to be listed as Sandy Lane Master Association. COI is also missing the 13 Additional Insured.
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

- What went wrong: Alex: "this one is another very specifc example that I would like to revisit - big picutre i sent a coi and it was bounced back and insured reached out that it was missing some stuff. from the requester email you can see the coi i originally made which only had one entity in the cert holder box. when you look at the picture attached there are all the entities that need to be in the cert holder box as well as the emails says the main entity to list on top - sandy lane....."
- Correct behavior: Follow Alex's correction above; do not repeat this outcome.

### negative 2 (ajf_roofing, AJF Roofing - General Liability Exp. 01-07-26 - Barron.pdf)

```
Hello again Aqui otro Certificado'
Romy Koo Accounts Payable & Human Resources | AJF Roofing D: (786) 409-6988 C: (305) 456-8006 EXT 6988 7495 NW 7 th Street Suite #10, Miami, FL 33126 E: rkoo@ajfroofingfl.com | Web: www.ajfroofingfl.
```

- What went wrong: Alex: "so the client sent us an old coi from their prior broker with the cert holder info. I dont see here our reply but first thing is to notice that the agent and agency is different thus this is an example coi taht we need to use as help to make the coi we will devlier to client. Thus we should have created a coi that inlcuded the cert holder info. regarding the description of ops page this is an old coi with a less sophisticated wording thus our wording would supersede."
- Correct behavior: Follow Alex's correction above; do not repeat this outcome.

### negative 3 (ajf_roofing, AJF Roofing - Workers Comp. Exp. 01-01-26 - Notowitz.pdf)

```
Good morning, Alejandro Here another request certificate: Thank you.
Romy Koo Accounts Payable & Human Resources | AJF Roofing D: (786) 409-6988 C: (305) 456-8006 EXT 6988 7495 NW 7 th Street Suite #10, Miami, FL 33126 E: rkoo@ajfroofingfl.com | Web: www.ajfroofingfl.
```

- What went wrong: Alex: "I agree with the resutl except there should have been different wording on the description of operations. also we are missing the first attachment that romy sent which included an old coi with the cert holder info which is where Katherin found the info for the cert holder...."; P4: no issue date in the date box
- Correct behavior: Always insert today's date in the date box. A COI must never go out without an issue date.

### negative 4 (gd_mechanical, G & D Mechanical Services COI Template.pdf)

```
(no request text preserved in the archive)
```

- What went wrong: Alex: "this is a very specifc case where the COI was issued for G&D Mechanical showing proof of insurance for a new vehicle they had purchased so they could take it off the lot."
- Correct behavior: Follow Alex's correction above; do not repeat this outcome.

## Needs discussion (0)

_None._
