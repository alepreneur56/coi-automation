# Wording Discrepancy Mining Report

Evidence-gathering only — no judgment calls made. Each hit below is a COI where the Description of Operations Additional-Insured sentence names a capitalized entity that does not appear in the Certificate Holder box (e.g. a property-management company, an 'and its affiliates' style open grant, or an entity the holder box doesn't list at all).

- Corpus scanned: **156** graded COIs (`training/graded_cois.json`)
- Total discrepancy hits: **21**
  - HIGH: 0   MEDIUM: 15   LOW: 6

Severity is a rough triage signal, not a verdict:
- **HIGH** — open-ended 'and its affiliates'/'its affiliates' grant, a named property-management/realty company, or an empty holder box with nothing to cross-check against.
- **MEDIUM** — a specific named corporate entity (has an LLC/Inc/Corp/Association-type suffix) that isn't anywhere in the holder box.
- **LOW** — a capitalized multi-word phrase flagged as a possible entity name but without a corporate suffix; more likely to be a false positive (worth a quick human glance, not a str8-to-top item).

---

## 1. [MEDIUM] PP_APOGEE_LaGreca Construction, LLC.pdf

- **Client:** apogee_hvac
- **Message date:** 2026-01-12 20:58:04
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Inbox/00041_Re_ LaGreca Construction Updated COI - Apogee HVAC Solutions/attachments/PP_APOGEE_LaGreca Construction, LLC.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Presidential Place Condominium, Association, Inc
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Presidential Place Condominium Association, Inc. and LaGreca Construction, LLC are included as Presidential Place Condominium Association, Inc. and LaGreca Construction, LLC are included as additional insured.
```

**Holder box:**
```
LaGreca Construction, LLC
12565 Orange Dr – Suite 401C
Davie, FL 33330
```

---

## 2. [MEDIUM] AJF Roofing_Test Entity Inc.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-01-14 02:27:07
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Inbox/00080_AJF Roofing COI - Test Entity Inc/attachments/AJF Roofing_Test Entity Inc.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 GAF, its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
GAF
1 Campus Drive
Test Entity Inc
12354 SW 57th Ave
Miami FL 33135
```

---

## 3. [MEDIUM] AJF Roofing_Test Entity Inc.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-01-14 02:40:03
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Inbox/00073_Re_ AJF Roofing COI - Test Entity Inc/attachments/AJF Roofing_Test Entity Inc.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 GAF, its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
GAF
1 Campus Drive
Test Entity Inc
12354 SW 57th Ave
Miami FL 33135
```

---

## 4. [MEDIUM] AJF Roofing Inc_Camcon Group LLC.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-01-21 20:41:56
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Inbox/00241_AJF ROOFING/attachments/AJF Roofing Inc_Camcon Group LLC.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 Camcon Group LLC, its respective officers, employees and agents are named as additional insured, on a primary and non-contributory basis, with regard to Business Auto and to General Liability, including products and completed operations.
```

**Holder box:**
```
GAF
1 Campus Drive
Camcon Group LLC 
5000 SW 75th Ave 
Suite 300B 
Miami, FL 33155
```

---

## 5. [MEDIUM] AJF Roofing Inc_GAF.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-01-21 20:41:56
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Inbox/00241_AJF ROOFING/attachments/AJF Roofing Inc_GAF.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 GAF, its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
GAF
1 Campus Drive
GAF
1 CAMPUS DRIVE
PARSIPPANY, NJ 07054
```

---

## 6. [MEDIUM] AJF Roofing Inc_3055 Burris Owner, LLC.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-02-10 22:56:55
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Inbox/00725_Re_ Certificates--3055 BURRIS OWNER & DENVER/attachments/AJF Roofing Inc_3055 Burris Owner, LLC.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 3055 Burris Owner, LLC, its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
GAF
1 Campus Drive
3055 Burris Owner, LLC
3055 B
i R
d
```

---

## 7. [MEDIUM] AJF Roofing Inc_Denver CMC Group, Inc. Colorado Center Tower 1.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-02-10 22:56:55
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Inbox/00725_Re_ Certificates--3055 BURRIS OWNER & DENVER/attachments/AJF Roofing Inc_Denver CMC Group, Inc. Colorado Center Tower 1.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 Denver CMC Group, Inc. Colorado Center Tower 1, its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
GAF
1 Campus Drive
Denver CMC Group, Inc. Colorado Center Tower 1
2000 S Colorado Boulevard
Suite 10500
```

---

## 8. [MEDIUM] 26-27 CNA Cert  AJF Roofing Inc - 3055 Burris.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-01-27 20:01:30
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Sent Items/NEW_2026-01-27_200130_RE__9458404/attachments/26-27 CNA Cert  AJF Roofing Inc - 3055 Burris.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 3055 BURRIS OWNER LLC, its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
3055 BURRIS OWNER LLC
3055 BURRIS ROAD
```

---

## 9. [MEDIUM] 26-27 CNA Cert  AJF Roofing Inc - Denver CMC.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-01-27 20:04:01
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Sent Items/NEW_2026-01-27_200401_RE_ AJF ROOFING- COI & WC for BURRIS & DENVER_9459396/attachments/26-27 CNA Cert  AJF Roofing Inc - Denver CMC.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 Denver CMC Group, Inc., its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
Denver CMC Group, Inc.
Colorado Center, Tower 1
2000 S Colorado Blvd Ste 10500
```

---

## 10. [MEDIUM] 26-27 CNA Cert  AJF Roofing Inc - Newmar Building.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-01-27 21:22:28
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Sent Items/NEW_2026-01-27_212228_RE_ COI - Newmar Building LLC_9463556/attachments/26-27 CNA Cert  AJF Roofing Inc - Newmar Building.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 Newmar Building LLC, its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
NEWMAR BUILDING LLC
1856 N. Nob Hill Road, #144
```

---

## 11. [MEDIUM] AJF Roofing Inc COI_Biscayne Beach Miami Condominium Association, Inc..pdf

- **Client:** ajf_roofing
- **Message date:** 2026-02-03 12:48:37
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Sent Items/NEW_2026-02-03_124837_Re_ REQUESTING CERTIFICATION_9634340/attachments/AJF Roofing Inc COI_Biscayne Beach Miami Condominium Association, Inc..pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 Biscayne Beach Miami Condominium Association, Inc., its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
GAF
1 Campus Drive
Biscayne Beach Miami Condominium Association, Inc.
2900 NE 7th Ave, Suite 201
Miami, FL 33137
```

---

## 12. [MEDIUM] AJF Roofing Inc_3055 Burris Owner LLC V2.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-02-11 18:52:50
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Sent Items/NEW_2026-02-11_185250_RE_ AJF ROOFING-  BURRIS_9921060/attachments/AJF Roofing Inc_3055 Burris Owner LLC V2.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor Project IOV Burris Davie, Industrial Center AJF Roofing Inc, GC LIC#, Solar LIC#
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor Project: IOV Burris Davie Industrial Center AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 3055 Burris Owner, LLC, its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
GAF
1 Campus Drive
3055 Burris Owner, LLC
3055 B
i R
d
```

---

## 13. [MEDIUM] AJF Roofing Inc_3055 Burris Owner, LLC.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-02-11 19:20:40
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Sent Items/NEW_2026-02-11_192040_RE_ AGAIN _)_9923460/attachments/AJF Roofing Inc_3055 Burris Owner, LLC.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#, IOV BURRIS INDUSTRAIL CENTER
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 Project: IOV BURRIS INDUSTRAIL CENTER -X623 3055 Burris Owner, LLC, its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
GAF
1 Campus Drive
3055 Burris Owner, LLC
3055 B
i R
d
```

---

## 14. [MEDIUM] AJF Roofing Inc_Denver CMC Group, Inc. Colorado Center Tower 1.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-02-11 19:20:40
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Sent Items/NEW_2026-02-11_192040_RE_ AGAIN _)_9923460/attachments/AJF Roofing Inc_Denver CMC Group, Inc. Colorado Center Tower 1.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#, IOV BURRIS INDUSTRAIL CENTER
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 Project: IOV BURRIS INDUSTRAIL CENTER -X623 Denver CMC Group, Inc. Colorado Center Tower 1, its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
GAF
1 Campus Drive
Denver CMC Group, Inc. Colorado Center Tower 1
2000 S Colorado Boulevard
Suite 10500
```

---

## 15. [MEDIUM] AJF Roofing Inc COI_Pembroke Pines.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-02-17 15:27:59
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Sent Items/NEW_2026-02-17_152759_Re_ Request certificate_10008260/attachments/AJF Roofing Inc COI_Pembroke Pines.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Roofing Contractor AJF Roofing Inc, GC LIC#, Solar LIC#
- **Why flagged:** named corporate entity not found anywhere in the holder box

**DoO sentence:**
```
Roofing Contractor AJF Roofing Inc., License #CCC-1331111, GC LIC# CGC1530450, Solar LIC# CVC5714 Pembroke Pines, its respective officers, employees and agents are listed as additional insured respect to General Liablity.
```

**Holder box:**
```
GAF
1 Campus Drive
Pembroke Pines
601 City Center Way
2nd Floor
Pembroke Pines, FL 33025
```

---

## 16. [LOW] 3 Island Condominium Association, Inc.pdf

- **Client:** apogee_hvac
- **Message date:** 2026-01-09 18:15:19
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Inbox/00013_3 Island Condominium COI - Apogee HVAC Solutions LLC/attachments/3 Island Condominium Association, Inc.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** CERTIFICATE HOLDER IS NAMED AS ADDITIONAL
- **Why flagged:** capitalized multi-word phrase not found in the holder box (may be a false positive)

**DoO sentence:**
```
CERTIFICATE HOLDER IS NAMED AS ADDITIONAL INSURED.
```

**Holder box:**
```
3 Island Condominium Association, Inc
 3 Island Ave.
Miami, FL 33139
```

---

## 17. [LOW] 24-25 COI - Paraiso Bay Condominium Association Inc..pdf

- **Client:** central_comfort_ac
- **Message date:** 2026-01-26 13:17:29
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Inbox/00283_URGENT RUSH RUSH - TECH ON THE WAY/attachments/24-25 COI - Paraiso Bay Condominium Association Inc..pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** DESCRIPTION OF OPERATIONS LOCATIONS VEHICLES ACORD
- **Why flagged:** capitalized multi-word phrase not found in the holder box (may be a false positive)

**DoO sentence:**
```
DESCRIPTION OF OPERATIONS / LOCATIONS / VEHICLES (ACORD 101, Additional Remarks Schedule, may be attached if more space is required) Paraiso Bay Condominium Association Inc. and Paraiso Bay Master Association are included as additional insureds with respect to General Liability on a primary and non-contributory basis when required by written contract.
```

**Holder box:**
```
CERTIFICATE HOLDER
Paraiso Bay Condominium Association Inc.
Paraiso Bay Master Association
650 NE 32nd Street
Miami, FL 33137
```

---

## 18. [LOW] Rolando's HVAC COI_Atrium Development Group.pdf

- **Client:** rolandos_hvac
- **Message date:** 2026-02-23 21:35:32
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Inbox/00931_Re_ HVAC/attachments/Rolando's HVAC COI_Atrium Development Group.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Ocala Industrial, St Ocala FL
- **Why flagged:** capitalized multi-word phrase not found in the holder box (may be a false positive)

**DoO sentence:**
```
Rolando’s HVAC - CAC1820272 Project: Ocala Industrial 3950 NW 11th St, Ocala, FL 34482, USA Atrium Development Group Atrium Management Company are Additional Insured on primary and noncontributory basis under the General Liability coverage for work performed by the Named Insured.
```

**Holder box:**
```
Main Street Renewal and Amherst Group Properties, LLC
c/o VendorShield
PO Box 1576
Hicksville NY 11802 1576
Atrium Development Group
Atrium Management Company
201 S Bumby Ave
Orlando FL 32803
```

---

## 19. [LOW] 2026 Miami Dade COI - AJF.pdf

- **Client:** ajf_roofing
- **Message date:** 2026-02-04 16:48:17
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Sent Items/NEW_2026-02-04_164817_RE_ Request for Certificate of Insurance_9703620/attachments/2026 Miami Dade COI - AJF.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Lic#CC1331111 The Automobile
- **Why flagged:** capitalized multi-word phrase not found in the holder box (may be a false positive)

**DoO sentence:**
```
Lic#CC1331111 The Automobile Liability policy includes an automatic Additional Insured endorsement that provides Additional Insured status to Miami-Dade County, its officers, employees, agents, and instrumentalities when there is a written contract that requires such status, and only with regard to work performed by or onbehalf of the named insured.
```

**Holder box:**
```
Miami-Dade County
111 NW 1st Street
Suite 2340
Miami FL 33128
```

---

## 20. [LOW] Rolando's HVAC COI City of Fort Myers Building Dept.pdf

- **Client:** rolandos_hvac
- **Message date:** 2026-02-06 20:34:27
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Sent Items/NEW_2026-02-06_203427_RE_ COI - Fort Myers_9775652/attachments/Rolando's HVAC COI City of Fort Myers Building Dept.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** Willard St Fort Myers FL
- **Why flagged:** capitalized multi-word phrase not found in the holder box (may be a false positive)

**DoO sentence:**
```
HVAC Contractor License: CAC1820272 Project Location: 3416 Willard St, Fort Myers, FL 33916 City of Fort Myers are Additional Insured on primary and noncontributory basis under the General Liability coverage fo work performed by the Named Insured.
```

**Holder box:**
```
City of Fort Myers Building Department
1825 Hendry St #101, 
Fort Myers, FL 33901
```

---

## 21. [LOW] 1 - Rolando's HVAC Template.pdf

- **Client:** rolandos_hvac
- **Message date:** 2026-04-11 16:55:08
- **Path:** `/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/Microsoft Outlook Copy/Extracted/IPM_SUBTREE/Sent Items/NEW_2026-04-11_165508_RE_ Chiller Medic_11138340/attachments/1 - Rolando's HVAC Template.pdf`
- **DoO extraction source:** fitz (fresh)
- **Entities named in DoO but absent from holder box:** DBA Rolando's HVAC HVAC
- **Why flagged:** capitalized multi-word phrase not found in the holder box (may be a false positive)

**DoO sentence:**
```
LLC DBA Rolando's HVAC HVAC Contractor License: CAC1820272 Certificate Holder is listed as additional insured as required by written contract.
```

**Holder box:**
```
Motili Inc. 
abc inc
bcd llc
juan llc
1900 W
St
t S it
1533
```

---
