# Conflict review -- case-davis

44 of 170 clusters had at least one field disagreement or a HITL-queue flag; everything else clustered and resolved cleanly and isn't listed below. Generated directly from `runs/candidate_timelines/case-davis.json` -- deterministic, no live judging, reproducible any time by re-running `python -m evalkit.report_readable`.

## `case-davis-cl006` -- vital signs
2 mentions of what looks like the same real event, documented independently in: 01_EMS_and_ED_Admit_2024-01-08 pp1, 01_EMS_and_ED_Admit_2024-01-08 pp3. All place it on 2024-01-08.
- They disagree on diagnosis or finding: "hypotension, tachycardia, severe pain" (01_EMS_and_ED_Admit_2024-01-08 pp1), "hypotension, tachycardia" (01_EMS_and_ED_Admit_2024-01-08 pp3). Multiple equally-authoritative-ranked sources disagree on 'diagnosis_or_finding' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 6/9): SOURCE_CONFLICT.
Because of the unresolved disagreement above, and since this event isn't high-materiality, it was left out of the final timeline entirely rather than guessed.

## `case-davis-cl017` -- specialist consult order
1 mention of what looks like the same real event, documented independently in: 01_EMS_and_ED_Admit_2024-01-08 pp4. All place it on 2024-01-08.
- Flagged for human review (priority 3/9): UNCLEAR_PERFORMED_VS_PLANNED.
It IS in the final timeline: "Immediate orthopedic trauma consultation (Dr. Marcus Vance) (ordered), Dr. Marcus Vance."

## `case-davis-cl019` -- surgical plan
1 mention of what looks like the same real event, documented independently in: 01_EMS_and_ED_Admit_2024-01-08 pp4. All place it on 2024-01-08.
- Flagged for human review (priority 3/9): UNCLEAR_PERFORMED_VS_PLANNED.
It IS in the final timeline: "Left arm emergent amputation (planned), Dr. David Cho, MD, FACEP."

## `case-davis-cl033` -- vital signs monitoring
2 mentions of what looks like the same real event, documented independently in: 02_Inpatient_Surgery_and_Ward_Stay p2. All place it on 2024-01-09.
- They disagree on who documented it: "J. Marsh RN" (02_Inpatient_Surgery_and_Ward_Stay p2), "R. Bell RN" (02_Inpatient_Surgery_and_Ward_Stay p2). Multiple equally-authoritative-ranked sources disagree on 'provider' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on diagnosis or finding: "pain level 10/10" (02_Inpatient_Surgery_and_Ward_Stay p2), "pain level 7/10" (02_Inpatient_Surgery_and_Ward_Stay p2). Multiple equally-authoritative-ranked sources disagree on 'diagnosis_or_finding' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 3/9): SOURCE_CONFLICT.
Because of the unresolved disagreement above, and since this event isn't high-materiality, it was left out of the final timeline entirely rather than guessed.

## `case-davis-cl084` -- planned surgery
1 mention of what looks like the same real event, documented independently in: 03_Ortho_Followups_and_Neuroma_Revision p2. All place it on 2024-11-12.
- Flagged for human review (priority 3/9): UNCLEAR_PERFORMED_VS_PLANNED.
It IS in the final timeline: "Left stump neuroma excision and deep muscle transposition (planned), Dr. Marcus Vance."

## `case-davis-cl100` -- plan of care
1 mention of what looks like the same real event, documented independently in: 04_Prosthetic_Fitting_and_Rehabilitation_Series pp3. All place it on 2025-01-12.
- Flagged for human review (priority 3/9): UNCLEAR_PERFORMED_VS_PLANNED.
It IS in the final timeline: "Left shoulder/arm myoelectric prosthesis training (planned), Sarah Jenkins, PT, DPT."

## `case-davis-cl121` -- patient-reported pain scores over course of treatment
1 mention of what looks like the same real event, documented independently in: 04_Prosthetic_Fitting_and_Rehabilitation_Series p18. All place it on 2024-01-08.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Patient-reported pain scores over course of treatment."

## `case-davis-cl132` -- principal procedure (ICD-10-PCS 0XJD0ZZ)
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp1. All place it on 2024-01-08.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "Principal procedure (ICD-10-PCS 0XJD0ZZ), Dr. David Cho, MD, FACEP."

## `case-davis-cl133` -- pharmacy charge, HCPCS J1650
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp1. All place it on 2024-01-08.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Pharmacy charge, HCPCS J1650."

## `case-davis-cl134` -- ICU admission/stay
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp1. All place it on 2024-01-08.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "ICU admission/stay."

## `case-davis-cl135` -- inpatient room and board
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp1. All place it on 2024-01-08.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Inpatient room and board."

## `case-davis-cl136` -- anesthesia service, CPT 01402
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp1. All place it on 2024-01-08.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Anesthesia service, CPT 01402."

## `case-davis-cl137` -- laboratory panel, CPT 80048
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp1. All place it on 2024-01-08.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Laboratory panel, CPT 80048."

## `case-davis-cl138` -- diagnosis codes S48.112A and S47.2XXA (ICD-10 codes, clinical meaning not narratively confirmed in this chunk)
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp1. All place it on 2024-01-08.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "Diagnosis codes S48.112A and S47.2XXA (ICD-10 codes, clinical meaning not narratively confirmed in this chunk), Dr. David Cho, MD, FACEP."

## `case-davis-cl139` -- major orthopedic instrument tray supply charge, suggests a second procedure/OR use on 01/09/2024
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp2. All place it on 2024-01-09.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Major orthopedic instrument tray supply charge, suggests a second procedure/OR use on 01/09/2024."

## `case-davis-cl140` -- wound culture, CPT 85610
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp2. All place it on 2024-01-11.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Wound (site unspecified) wound culture."

## `case-davis-cl141` -- wound culture, CPT 85610, second instance same day
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp2. All place it on 2024-01-11.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Wound (site unspecified) wound culture."

## `case-davis-cl142` -- rigid cervical collar application, billed under CPT 96365 (code mismatch with described item, no further clinical narrative given)
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp2. All place it on 2024-01-11.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Cervical spine rigid cervical collar application, billed under CPT 96365 (code mismatch with described item, no further clinical narrative given)."

## `case-davis-cl143` -- medication administration
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp2. All place it on 2024-01-12.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "01/12/2024, 0250, J1650, OXYCODONE 5MG TAB."

## `case-davis-cl144` -- procedure
2 mentions of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp2. Dates mentioned: 2024-01-12, 2024-01-14.
- They disagree on the date: "2024-01-12" (06_Comprehensive_Billing_and_Financial_Audit pp2), "2024-01-14" (06_Comprehensive_Billing_and_Financial_Audit pp2). Multiple equally-authoritative-ranked sources disagree on 'normalized_date' (2 distinct values tied) -- no unambiguous resolution.
- They disagree on concept: "pneumatic tourniquet used, suggesting another OR procedure on 01/12/2024" (06_Comprehensive_Billing_and_Financial_Audit pp2), "pneumatic tourniquet supply, suggesting another OR procedure on 01/14/2024" (06_Comprehensive_Billing_and_Financial_Audit pp2). Multiple equally-authoritative-ranked sources disagree on 'concept' (2 distinct values tied) -- no unambiguous resolution.
- Flagged for human review (priority 6/9): SOURCE_CONFLICT, AMBIGUOUS_DATE, LOW_EXTRACTION_CONFIDENCE.
Because of the unresolved disagreement above, and since this event isn't high-materiality, it was left out of the final timeline entirely rather than guessed.

## `case-davis-cl145` -- medication administration
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp2. All place it on 2024-01-14.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "01/14/2024, 0250, J8499, LISINOPRIL 10MG TAB."

## `case-davis-cl146` -- medication administration
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp2. All place it on 2024-01-14.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "01/14/2024, 0250, J8499, MORPHINE SULFATE 4MG INJ."

## `case-davis-cl147` -- complete blood count with differential, CPT 85025
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp2. All place it on 2024-01-14.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "CBC with differential."

## `case-davis-cl148` -- intraoperative C-arm fluoroscopy, suggesting an OR procedure on 01/15/2024
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp2. All place it on 2024-01-15.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Intraoperative C-arm fluoroscopy, suggesting an OR procedure on 01/15/2024."

## `case-davis-cl149` -- rigid cervical collar, discharge supply
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp2. All place it on 2024-01-15.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Cervical spine rigid cervical collar, discharge supply."

## `case-davis-cl150` -- operating room procedure, CPT 76000, no further clinical narrative provided
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp3. All place it on 2024-11-12.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "Operating room procedure, CPT 76000, no further clinical narrative provided, Dr. David Cho, MD, FACEP."

## `case-davis-cl151` -- principal procedure (ICD-10-PCS 0QSG04Z), no further clinical narrative given
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp3. All place it on 2024-11-12.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "Principal procedure (ICD-10-PCS 0QSG04Z), no further clinical narrative given, Dr. David Cho, MD, FACEP."

## `case-davis-cl152` -- anesthesia service, CPT 01402
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp3. All place it on 2024-11-12.
- Flagged for human review (priority 6/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Anesthesia service, CPT 01402."

## `case-davis-cl153` -- pharmacy charge, HCPCS J1650, specific medication not identified
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp3. All place it on 2024-11-12.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "Pharmacy charge, HCPCS J1650, specific medication not identified."

## `case-davis-cl154` -- diagnosis codes M96.5 (postprocedural scoliosis, per code, but not clinically confirmed in this chunk) and G54.6
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp3. All place it on 2024-11-12.
- Flagged for human review (priority 9/9): LOW_EXTRACTION_CONFIDENCE, HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "Diagnosis codes M96.5 (postprocedural scoliosis, per code, but not clinically confirmed in this chunk) and G54.6, Dr. David Cho, MD, FACEP."

## `case-davis-cl155` -- orthopedic procedure billed under CPT 24920, diagnosis S48.112A
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp4. All place it on 2024-01-08.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "24920, 01/08/2024, DX A, Referring Provider Dr. Marcus Vance, MD, FACS, Dr. Marcus Vance, MD, FACS."

## `case-davis-cl156` -- nerve-related procedure billed under CPT 64784, diagnosis M96.5
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp5. All place it on 2024-11-12.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "Peripheral nerve (per CPT code convention, not clinically confirmed in text) M96.5, Dr. Marcus Vance, MD, FACS."

## `case-davis-cl157` -- prosthetic/orthotic fitting, HCPCS L5611, diagnosis S48.112D (sequela of prior injury)
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp6. All place it on 2025-02-05.
- Flagged for human review (priority 6/9): HIGH_MATERIALITY_LOW_CONFIDENCE.
It IS in the final timeline: "Lower limb (per code convention, not narratively confirmed) S48.112D, Robert Chen, CPO, LPO."

## `case-davis-cl159` -- therapeutic exercise, CPT 97110
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp7. All place it on 2025-02-10.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "97110, 02/10/2025, 4 units, Sarah Jenkins, PT, Sarah Jenkins, PT, DPT."

## `case-davis-cl160` -- therapeutic exercise, CPT 97110
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp7. All place it on 2025-02-17.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-davis-cl161` -- self-care/home management training, CPT 97535
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp7. All place it on 2025-03-03.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-davis-cl162` -- self-care/home management training, CPT 97535
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp7. All place it on 2025-04-14.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-davis-cl163` -- neuromuscular reeducation, CPT 97112
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp7. All place it on 2025-06-02.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-davis-cl164` -- neuromuscular reeducation, CPT 97112
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp7. All place it on 2025-08-11.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-davis-cl165` -- community/work reintegration training, CPT 97537
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp7. All place it on 2025-10-06.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-davis-cl166` -- community/work reintegration training, CPT 97537
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp7. All place it on 2025-12-15.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-davis-cl167` -- community/work reintegration training, CPT 97537
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp7. All place it on 2026-03-09.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
This is a routine, repetitive-type event -- it was compressed out of the final timeline (grouped with similar routine visits, not because of the disagreement above).

## `case-davis-cl168` -- community/work reintegration training, CPT 97537
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp7. All place it on 2026-06-15.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "97537, 06/15/2026, 4 units, Sarah Jenkins, PT, Sarah Jenkins, PT, DPT."

## `case-davis-cl169` -- insurance EOB payment record for hospital claim, not itself a new clinical event
1 mention of what looks like the same real event, documented independently in: 06_Comprehensive_Billing_and_Financial_Audit pp8. All place it on 2024-02-15.
- Flagged for human review (priority 3/9): LOW_EXTRACTION_CONFIDENCE.
It IS in the final timeline: "CLM-50761454, Midwest Regional Medical Center, billed $145,230.50, paid 116,184.40, EFT issued 02/15/2024."
