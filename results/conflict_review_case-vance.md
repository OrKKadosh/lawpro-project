# Conflict review -- case-vance

41 of 315 clusters had at least one field disagreement or a HITL-queue flag; everything else clustered and resolved cleanly and isn't listed below. Generated directly from `runs/candidate_timelines/case-vance.json` -- deterministic, no live judging, reproducible any time by re-running `python -m evalkit.report_readable`.

## `case-vance-cl003` -- vital signs
3 mentions of what looks like the same real event, documented independently in: 01_ems_and_ed p1, 01_ems_and_ed p3, 02_hospitalization p1. All place it on 2023-09-04.
- They disagree on who documented it: "Paramedic James Vance, NREMT-P" (01_ems_and_ed p1), "Dr. Elizabeth Foster, MD" (01_ems_and_ed p3), "J. Marsh RN" (02_hospitalization p1). Multiple equally-authoritative-ranked sources disagree on 'provider' (3 distinct values tied) -- no unambiguous resolution.
- They initially disagreed on concept ("vital signs" (01_ems_and_ed p1), "vital signs" (01_ems_and_ed p3), "vital signs check" (02_hospitalization p1)), but this resolved to "vital signs" -- Unambiguous: only one value comes from the most-authoritative source available for 'concept' among this cluster's members.
- They disagree on diagnosis or finding: "tachycardia, severe pain" (01_ems_and_ed p1), "tachycardia, tachypnea, pain 10/10" (01_ems_and_ed p3), "pain level 10" (02_hospitalization p1). Multiple equally-authoritative-ranked sources disagree on 'diagnosis_or_finding' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 6/9): SOURCE_CONFLICT.
Because of the unresolved disagreement above, and since this event isn't high-materiality, it was left out of the final timeline entirely rather than guessed.

## `case-vance-cl010` -- pain complaint
2 mentions of what looks like the same real event, documented independently in: 01_ems_and_ed p1. All place it on 2023-09-04.
- They disagree on body site: "neck, lower back" (01_ems_and_ed p1), "knee" (01_ems_and_ed p1). Multiple equally-authoritative-ranked sources disagree on 'body_site' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on diagnosis or finding: "severe neck and lower back pain" (01_ems_and_ed p1), "left knee pain" (01_ems_and_ed p1). Multiple equally-authoritative-ranked sources disagree on 'diagnosis_or_finding' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 9/9): SOURCE_CONFLICT.
It IS in the final timeline: "Left pain complaint."

## `case-vance-cl028` -- surgical consult/plan
1 mention of what looks like the same real event, documented independently in: 01_ems_and_ed p5. All place it on 2023-09-04.
- Flagged for human review (priority 3/9): UNCLEAR_PERFORMED_VS_PLANNED.
It IS in the final timeline: "Left humerus ORIF (open reduction internal fixation) (ordered), Dr. Myrtle Turner, MD, FACS."

## `case-vance-cl029` -- medication order
1 mention of what looks like the same real event, documented independently in: 01_ems_and_ed p5. All place it on 2023-09-04.
- Flagged for human review (priority 3/9): UNCLEAR_PERFORMED_VS_PLANNED.
It IS in the final timeline: "Initiate IV antibiotics (Ancef) and aggressive pain management (ordered), Dr. Elizabeth Foster, MD."

## `case-vance-cl030` -- imaging order
1 mention of what looks like the same real event, documented independently in: 01_ems_and_ed p5. All place it on 2023-09-04.
- Flagged for human review (priority 3/9): UNCLEAR_PERFORMED_VS_PLANNED.
It IS in the final timeline: "Obtain emergency X-rays of left arm, C-spine, and lumbar spine (ordered), Dr. Elizabeth Foster, MD."

## `case-vance-cl036` -- ambulation with physical therapy
2 mentions of what looks like the same real event, documented independently in: 02_hospitalization p1. All place it on 2023-09-05.
- They disagree on who documented it: "T. Kovac RN" (02_hospitalization p1), "J. Marsh RN" (02_hospitalization p1). Multiple equally-authoritative-ranked sources disagree on 'provider' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 3/9): SOURCE_CONFLICT.
Because of the unresolved disagreement above, and since this event isn't high-materiality, it was left out of the final timeline entirely rather than guessed.

## `case-vance-cl058` -- ORIF
2 mentions of what looks like the same real event, documented independently in: 02_hospitalization p5. All place it on 2023-09-07.
- They disagree on body site: "humerus" (02_hospitalization p5), "distal radius" (02_hospitalization p5). Multiple equally-authoritative-ranked sources disagree on 'body_site' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on diagnosis or finding: "open compound mid-shaft left humerus fracture" (02_hospitalization p5), "displaced spiral fracture of the left distal radius" (02_hospitalization p5). Multiple equally-authoritative-ranked sources disagree on 'diagnosis_or_finding' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on procedure: "ORIF with 8-hole dynamic compression plate and screws" (02_hospitalization p5), "ORIF with volar locking plate and screws" (02_hospitalization p5). Multiple equally-authoritative-ranked sources disagree on 'procedure' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 9/9): SOURCE_CONFLICT.
It IS in the final timeline: "Left ORIF, Dr. Myrtle Turner, MD, FACS."

## `case-vance-cl088` -- physical therapy referral
1 mention of what looks like the same real event, documented independently in: 04_ortho_followup p1. All place it on 2023-09-21.
- Flagged for human review (priority 3/9): UNCLEAR_PERFORMED_VS_PLANNED.
It IS in the final timeline: "Left shoulder, elbow, wrist, neck outpatient physical therapy 3x/week (ordered), Dr. Myrtle Turner."

## `case-vance-cl100` -- MRI order
1 mention of what looks like the same real event, documented independently in: 04_ortho_followup p4. All place it on 2023-12-14.
- Flagged for human review (priority 3/9): UNCLEAR_PERFORMED_VS_PLANNED.
It IS in the final timeline: "Left upper extremity and cervical spine MRI left upper extremity and C-spine (ordered), Dr. Myrtle Turner."

## `case-vance-cl103` -- restricted range of motion
2 mentions of what looks like the same real event, documented independently in: 04_ortho_followup p5. All place it on 2024-02-08.
- They disagree on body site: "forearm, shoulder" (04_ortho_followup p5), "cervical spine" (04_ortho_followup p5). Multiple equally-authoritative-ranked sources disagree on 'body_site' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on diagnosis or finding: "limited pronation/supination; restricted shoulder ROM" (04_ortho_followup p5), "moderately limited cervical ROM" (04_ortho_followup p5). Multiple equally-authoritative-ranked sources disagree on 'diagnosis_or_finding' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 6/9): SOURCE_CONFLICT.
Because of the unresolved disagreement above, and since this event isn't high-materiality, it was left out of the final timeline entirely rather than guessed.

## `case-vance-cl105` -- permanent disability
2 mentions of what looks like the same real event, documented independently in: 04_ortho_followup p6, 07_imaging_pharmacy p4. All place it on 2024-03-14.
- They initially disagreed on who documented it ("Dr. Myrtle Turner" (04_ortho_followup p6), "Dr. Myrtle Turner, MD, FACS" (07_imaging_pharmacy p4)), but this resolved to "Dr. Myrtle Turner, MD, FACS" -- Unambiguous: only one value comes from the most-authoritative source available for 'provider' among this cluster's members.
- They initially disagreed on concept ("permanent disability" (04_ortho_followup p6), "permanent functional impairment" (07_imaging_pharmacy p4)), but this resolved to "permanent disability" -- Unambiguous: only one value comes from the most-authoritative source available for 'concept' among this cluster's members.
- They initially disagreed on body site ("elbow, wrist" (04_ortho_followup p6), "left elbow, left forearm" (07_imaging_pharmacy p4)), but this resolved to "elbow, wrist" -- Unambiguous: only one value comes from the most-authoritative source available for 'body_site' among this cluster's members.
- They initially disagreed on diagnosis or finding ("15 degree elbow flexion/extension deficit, 20 degree wrist supination deficit" (04_ortho_followup p6), "15-degree flexion/extension deficit at left elbow; 20-degree loss of forearm supination" (07_imaging_pharmacy p4)), but this resolved to "15 degree elbow flexion/extension deficit, 20 degree wrist supination deficit" -- Unambiguous: only one value comes from the most-authoritative source available for 'diagnosis_or_finding' among this cluster's members.
It IS in the final timeline: "Left elbow, wrist 15 degree elbow flexion/extension deficit, 20 degree wrist supination deficit, Dr. Myrtle Turner, MD, FACS."

## `case-vance-cl106` -- diagnosis
2 mentions of what looks like the same real event, documented independently in: 04_ortho_followup p6, 07_imaging_pharmacy p4. All place it on 2024-03-14.
- They disagree on who documented it: "Dr. Myrtle Turner" (04_ortho_followup p6), "Dr. Myrtle Turner, MD, FACS" (07_imaging_pharmacy p4). Multiple equally-authoritative-ranked sources disagree on 'provider' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on concept: "permanent sensory deficit" (04_ortho_followup p6), "sensory deficit" (07_imaging_pharmacy p4). Multiple equally-authoritative-ranked sources disagree on 'concept' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on body site: "hand, radial aspect" (04_ortho_followup p6), "left forearm/radial nerve distribution" (07_imaging_pharmacy p4). Multiple equally-authoritative-ranked sources disagree on 'body_site' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on diagnosis or finding: "permanently blunted sensation" (04_ortho_followup p6), "permanently blunted radial sensory distribution due to traction injury" (07_imaging_pharmacy p4). Multiple equally-authoritative-ranked sources disagree on 'diagnosis_or_finding' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 9/9): SOURCE_CONFLICT.
It IS in the final timeline: "Sensation over the left radial aspect of the hand remains permanently blunted (provider disputed across sources -- see evidence)."

## `case-vance-cl115` -- physical therapy plan of care
1 mention of what looks like the same real event, documented independently in: 05_pt_lang_weimann p1. All place it on 2023-09-15.
- Flagged for human review (priority 3/9): UNCLEAR_PERFORMED_VS_PLANNED.
It IS in the final timeline: "Left arm, cervical spine therapeutic exercise, ROM, hot/cold pack therapy (planned), Robert Stewart, PT, DPT."

## `case-vance-cl125` -- physical therapy session
2 mentions of what looks like the same real event, documented independently in: 05_pt_lang_weimann p10. All place it on 2023-10-06.
- They disagree on procedure: "shoulder mobilization, passive elbow extension, moist heat" (05_pt_lang_weimann p10), "therapeutic exercise, manual therapy, moist heat, HEP review" (05_pt_lang_weimann p10). Multiple equally-authoritative-ranked sources disagree on 'procedure' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 3/9): SOURCE_CONFLICT.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-vance-cl126` -- therapeutic exercise
2 mentions of what looks like the same real event, documented independently in: 05_pt_lang_weimann p10, 08_billing_and_claims p8. All place it on 2023-10-06.
- They initially disagreed on procedure ("CPT 97110 therapeutic exercise" (05_pt_lang_weimann p10), "CPT 97110" (08_billing_and_claims p8)), but this resolved to "CPT 97110 therapeutic exercise" -- Unambiguous: only one value comes from the most-authoritative source available for 'procedure' among this cluster's members.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-vance-cl129` -- therapeutic exercise
2 mentions of what looks like the same real event, documented independently in: 05_pt_lang_weimann p11, 08_billing_and_claims p8. All place it on 2023-10-09.
- They initially disagreed on procedure ("CPT 97110 therapeutic exercise" (05_pt_lang_weimann p11), "CPT 97110" (08_billing_and_claims p8)), but this resolved to "CPT 97110 therapeutic exercise" -- Unambiguous: only one value comes from the most-authoritative source available for 'procedure' among this cluster's members.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-vance-cl132` -- therapeutic exercise
2 mentions of what looks like the same real event, documented independently in: 05_pt_lang_weimann p12, 08_billing_and_claims p8. All place it on 2023-10-11.
- They initially disagreed on procedure ("CPT 97110 therapeutic exercise" (05_pt_lang_weimann p12), "CPT 97110" (08_billing_and_claims p8)), but this resolved to "CPT 97110 therapeutic exercise" -- Unambiguous: only one value comes from the most-authoritative source available for 'procedure' among this cluster's members.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-vance-cl135` -- therapeutic exercise
2 mentions of what looks like the same real event, documented independently in: 05_pt_lang_weimann p13, 08_billing_and_claims p8. All place it on 2023-10-13.
- They initially disagreed on procedure ("CPT 97110 therapeutic exercise" (05_pt_lang_weimann p13), "CPT 97110" (08_billing_and_claims p8)), but this resolved to "CPT 97110 therapeutic exercise" -- Unambiguous: only one value comes from the most-authoritative source available for 'procedure' among this cluster's members.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-vance-cl152` -- therapy
3 mentions of what looks like the same real event, documented independently in: 05_pt_lang_weimann p19. All place it on 2023-10-27.
- They disagree on concept: "physical therapy session" (05_pt_lang_weimann p19), "manual therapy" (05_pt_lang_weimann p19), "physical therapy visit 18" (05_pt_lang_weimann p19). Multiple equally-authoritative-ranked sources disagree on 'concept' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on diagnosis or finding: "weather-related joint pain increase" (05_pt_lang_weimann p19), "joint pain" (05_pt_lang_weimann p19). Multiple equally-authoritative-ranked sources disagree on 'diagnosis_or_finding' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on procedure: "passive elbow stretching" (05_pt_lang_weimann p19), "CPT 97140 manual therapy - joint/soft tissue mobilization" (05_pt_lang_weimann p19), "therapeutic exercise, manual therapy - joint/soft tissue mobilization, passive elbow stretching" (05_pt_lang_weimann p19). Multiple equally-authoritative-ranked sources disagree on 'procedure' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 3/9): SOURCE_CONFLICT.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-vance-cl161` -- missed physical therapy sessions
1 mention of what looks like the same real event, documented independently in: 05_pt_lang_weimann p26.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Missed physical therapy sessions (cancelled), Robert Stewart, PT, DPT."

## `case-vance-cl163` -- therapy
2 mentions of what looks like the same real event, documented independently in: 05_pt_lang_weimann p28. All place it on 2023-11-29.
- They disagree on concept: "physical therapy visit 27" (05_pt_lang_weimann p28), "physical therapy session" (05_pt_lang_weimann p28). Multiple equally-authoritative-ranked sources disagree on 'concept' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on procedure: "therapeutic exercise, manual therapy, active mobilizations, therapy putty exercises, cervical heat pack" (05_pt_lang_weimann p28), "therapeutic exercise, manual therapy" (05_pt_lang_weimann p28). Multiple equally-authoritative-ranked sources disagree on 'procedure' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 3/9): SOURCE_CONFLICT.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-vance-cl191` -- therapy
2 mentions of what looks like the same real event, documented independently in: 06_pt_emory_sports p10. All place it on 2024-01-29.
- They disagree on concept: "physical therapy visit" (06_pt_emory_sports p10), "physical therapy session" (06_pt_emory_sports p10). Multiple equally-authoritative-ranked sources disagree on 'concept' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on body site: "upper extremity, cervical spine" (06_pt_emory_sports p10), "cervical spine" (06_pt_emory_sports p10). Multiple equally-authoritative-ranked sources disagree on 'body_site' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on diagnosis or finding: "cervical symptoms provoked during session" (06_pt_emory_sports p10), "cervical symptoms provoked, monitored and modified" (06_pt_emory_sports p10). Multiple equally-authoritative-ranked sources disagree on 'diagnosis_or_finding' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on procedure: "progressive resistance training, moist heat, therapeutic exercise, manual therapy" (06_pt_emory_sports p10), "therapeutic exercise, manual therapy, moist heat" (06_pt_emory_sports p10). Multiple equally-authoritative-ranked sources disagree on 'procedure' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 3/9): SOURCE_CONFLICT.
Because of the unresolved disagreement above, and since this event isn't high-materiality, it was left out of the final timeline entirely rather than guessed.

## `case-vance-cl202` -- physical therapy session
2 mentions of what looks like the same real event, documented independently in: 06_pt_emory_sports p19. All place it on 2024-02-19.
- They disagree on body site: "forearm, shoulder" (06_pt_emory_sports p19), "forearm/wrist" (06_pt_emory_sports p19). Multiple equally-authoritative-ranked sources disagree on 'body_site' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on procedure: "active wall climbs, forearm pronation strengthening, heat pack, therapeutic exercise, manual therapy" (06_pt_emory_sports p19), "therapeutic exercise, manual therapy, HEP review" (06_pt_emory_sports p19). Multiple equally-authoritative-ranked sources disagree on 'procedure' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 3/9): SOURCE_CONFLICT.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-vance-cl211` -- therapy
2 mentions of what looks like the same real event, documented independently in: 06_pt_emory_sports p28. All place it on 2024-03-11.
- They disagree on concept: "physical therapy session" (06_pt_emory_sports p28), "physical therapy visit 27" (06_pt_emory_sports p28). Multiple equally-authoritative-ranked sources disagree on 'concept' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on body site: "upper extremity, forearm" (06_pt_emory_sports p28), "upper extremity/forearm" (06_pt_emory_sports p28). Multiple equally-authoritative-ranked sources disagree on 'body_site' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on procedure: "therapeutic exercise, manual therapy, ergometer training" (06_pt_emory_sports p28), "therapeutic exercise, manual therapy, moist heat" (06_pt_emory_sports p28). Multiple equally-authoritative-ranked sources disagree on 'procedure' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 3/9): SOURCE_CONFLICT.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-vance-cl232` -- cervical disc bulge progression
1 mention of what looks like the same real event, documented independently in: 07_imaging_pharmacy p4. All place it on 2023-12-01.
- Flagged for human review (priority 3/9): CAUSATION_AMBIGUITY.
It IS in the final timeline: "Cervical spine C5-C6 progression of C5-C6 disc bulge from 4mm to 6mm with left neural foraminal stenosis, Dr. Myrtle Turner, MD, FACS."

## `case-vance-cl233` -- causation opinion
1 mention of what looks like the same real event, documented independently in: 07_imaging_pharmacy p4. All place it on 2024-04-02.
- Flagged for human review (priority 6/9): CAUSATION_AMBIGUITY.
It IS in the final timeline: "Cervical spine MVA exacerbated pre-existing cervical disc disease, Dr. Myrtle Turner, MD, FACS."

## `case-vance-cl237` -- Operating Room Services
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p1. All place it on 2023-09-04.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "Operating Room Services, CPT 27535, DR. ELIZABETH FOSTER, MD."

## `case-vance-cl239` -- Emergency Room visit
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p1. All place it on 2023-09-04.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "Emergency Room visit."

## `case-vance-cl240` -- Radiology/Diagnostic - CPT 70450
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p1. All place it on 2023-09-04.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Radiology/Diagnostic - CPT 70450."

## `case-vance-cl241` -- principal procedure
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p1. All place it on 2023-09-04.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "ICD-10-PCS codes OPS00ZZ/0PSG0ZZ (not narratively described), DR. ELIZABETH FOSTER, MD."

## `case-vance-cl244` -- X-ray
3 mentions of what looks like the same real event, documented independently in: 08_billing_and_claims p2. Dates mentioned: 2023-09-04, 2023-09-07, 2023-09-08.
- They disagree on the date: "2023-09-04" (08_billing_and_claims p2), "2023-09-07" (08_billing_and_claims p2), "2023-09-08" (08_billing_and_claims p2). Multiple equally-authoritative-ranked sources disagree on 'normalized_date' (3 distinct values tied) -- no unambiguous resolution.
- They disagree on procedure: "XR Knee 2 views follow-up" (08_billing_and_claims p2), "XR knee 3 views" (08_billing_and_claims p2), "XR knee 3 views" (08_billing_and_claims p2). Multiple equally-authoritative-ranked sources disagree on 'procedure' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 6/9): SOURCE_CONFLICT, AMBIGUOUS_DATE.
Because of the unresolved disagreement above, and since this event isn't high-materiality, it was left out of the final timeline entirely rather than guessed.

## `case-vance-cl249` -- cardiac monitoring
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p2. All place it on 2023-09-06.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Cardiac monitoring, CPT 93010."

## `case-vance-cl252` -- fracture repair
2 mentions of what looks like the same real event, documented independently in: 08_billing_and_claims p5. All place it on 2023-09-07.
- They disagree on diagnosis or finding: "S42.302A" (08_billing_and_claims p5), "S52.302A" (08_billing_and_claims p5). Multiple equally-authoritative-ranked sources disagree on 'diagnosis_or_finding' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on procedure: "CPT 24515 (billed procedure, left side)" (08_billing_and_claims p5), "CPT 25607 (billed procedure, left side)" (08_billing_and_claims p5). Multiple equally-authoritative-ranked sources disagree on 'procedure' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 9/9): SOURCE_CONFLICT.
It IS in the final timeline: "09/07/2023 11 24515 LT ... Dr. Myrtle Turner, MD, FACS, Dr. Myrtle Turner, MD, FACS."

## `case-vance-cl253` -- initial hospital inpatient consult/encounter
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p5. All place it on 2023-09-04.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "09/04/2023 11 99223 A ... Dr. Myrtle Turner, MD, FACS, Dr. Myrtle Turner, MD, FACS."

## `case-vance-cl261` -- emergency ambulance transport, ALS
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p4. All place it on 2023-09-04.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "A0427 (advanced life support ambulance), Paramedic James Vance, NREMT-P."

## `case-vance-cl262` -- ground mileage, ambulance transport
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p4. All place it on 2023-09-04.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "A0425 (ambulance mileage), Paramedic James Vance, NREMT-P."

## `case-vance-cl268` -- hot/cold pack therapy
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p8. All place it on 2023-09-18.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-vance-cl308` -- EMS/paramedic services
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p12. All place it on 2023-10-02.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "EMS/paramedic services, Paramedic James Vance, NREMT-P."

## `case-vance-cl309` -- emergency hospital services
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p13. All place it on 2023-11-12.
- Flagged for human review (priority 9/9): LOW_EXTRACTION_CONFIDENCE, HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "Emergency hospital services, Littel Inc Emergency Hospital."

## `case-vance-cl311` -- physician services (surgical, FACS)
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p14. All place it on 2024-04-18.
- Flagged for human review (priority 9/9): LOW_EXTRACTION_CONFIDENCE, HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "Physician services (surgical, FACS), Dr. Myrtle Turner, MD, FACS."

## `case-vance-cl312` -- physical therapy services
1 mention of what looks like the same real event, documented independently in: 08_billing_and_claims p15. All place it on 2024-01-15.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "CLM-99668711 - Robert Stewart, PT, DPT, billed 6,480.00, Robert Stewart, PT, DPT."
