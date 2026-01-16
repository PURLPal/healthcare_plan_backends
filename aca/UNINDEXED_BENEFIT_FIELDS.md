# ACA Data Fields - Historical Reference

**Source:** CMS Benefits and Cost Sharing Public Use File (PUF)  
**Status:** ✅ FULLY DEPLOYED - All benefits now indexed (Jan 16, 2026)  
**See:** `BENEFITS_NOW_INDEXED.md` for current status  
**Total Fields Previously Unindexed:** 118 → **Now Indexed:** 234 benefit types

---

## ⚠️ DOCUMENT STATUS: HISTORICAL REFERENCE ONLY

This document originally listed fields that were NOT indexed. **As of January 16, 2026, ALL benefits are now fully loaded and searchable.**

For current status, see: `BENEFITS_NOW_INDEXED.md`

---

## Original Document (Pre-Deployment)

---

## Currently Indexed Fields

### Plan Attributes (Main Table)
1. Plan ID
2. State Code
3. Issuer ID
4. Issuer Name
5. Service Area ID
6. Plan Marketing Name
7. Plan Type
8. Metal Level
9. Is New Plan

### Plan Attributes (JSONB)
10. HIOS Product ID
11. Network ID
12. Formulary ID
13. Design Type
14. QHP Type
15. Plan Effective Date
16. Plan Expiration Date
17. Is HSA Eligible
18. National Network
19. URL for Enrollment
20. URL for Summary of Benefits
21. Plan Brochure URL
22. Individual Deductible (In-Network Tier 1)
23. Family Deductible (In-Network Tier 1)
24. Individual MOOP (In-Network Tier 1)
25. Family MOOP (In-Network Tier 1)

### Rate Data
26. Age-based premiums (0-64+)
27. Tobacco rates

**Total Currently Indexed: ~27 core fields**

---

## UNINDEXED FIELDS (60+ Available)

### Category 1: Cost-Sharing Details (Extended)

#### Deductibles (All Tiers)
1. **TEHBDedInnTier2Individual** - Tier 2 in-network individual deductible
2. **TEHBDedInnTier2FamilyPerGroup** - Tier 2 in-network family deductible
3. **TEHBDedOutOfNetIndividual** - Out-of-network individual deductible
4. **TEHBDedOutOfNetFamilyPerGroup** - Out-of-network family deductible
5. **TEHBDedCombInnOonIndividual** - Combined in/out individual deductible
6. **TEHBDedCombInnOonFamilyPerGroup** - Combined in/out family deductible

#### Out-of-Pocket Maximums (All Tiers)
7. **TEHBInnTier2IndividualMOOP** - Tier 2 in-network individual MOOP
8. **TEHBInnTier2FamilyPerGroupMOOP** - Tier 2 in-network family MOOP
9. **TEHBOutOfNetIndividualMOOP** - Out-of-network individual MOOP
10. **TEHBOutOfNetFamilyPerGroupMOOP** - Out-of-network family MOOP
11. **TEHBCombInnOonIndividualMOOP** - Combined in/out individual MOOP
12. **TEHBCombInnOonFamilyPerGroupMOOP** - Combined in/out family MOOP

---

### Category 2: Essential Health Benefits (EHB) - Detailed Cost Sharing

#### Primary Care
13. **PrimaryCarePhysicianToTreatAnInjuryOrIllness** - Primary care visit copay/coinsurance
14. **IsCovered_PrimaryCare** - Is primary care covered
15. **CopayInnTier1_PrimaryCare** - Copay amount in-network tier 1
16. **CopayInnTier2_PrimaryCare** - Copay amount in-network tier 2
17. **CoinsInnTier1_PrimaryCare** - Coinsurance % in-network tier 1
18. **CoinsInnTier2_PrimaryCare** - Coinsurance % in-network tier 2
19. **CopayOutOfNet_PrimaryCare** - Out-of-network copay

#### Specialist Visits
20. **SpecialistVisit** - Specialist visit cost sharing
21. **IsCovered_Specialist** - Is specialist covered
22. **CopayInnTier1_Specialist** - Copay in-network tier 1
23. **CopayInnTier2_Specialist** - Copay in-network tier 2
24. **CoinsInnTier1_Specialist** - Coinsurance in-network tier 1
25. **CoinsInnTier2_Specialist** - Coinsurance in-network tier 2

#### Emergency Services
26. **EmergencyRoomServices** - ER visit cost sharing
27. **IsCovered_EmergencyRoom** - Is ER covered
28. **CopayInnTier1_EmergencyRoom** - ER copay
29. **CoinsInnTier1_EmergencyRoom** - ER coinsurance

30. **UrgentCare** - Urgent care cost sharing
31. **IsCovered_UrgentCare** - Is urgent care covered
32. **CopayInnTier1_UrgentCare** - Urgent care copay

#### Hospitalization
33. **InpatientHospitalServices** - Hospital admission cost sharing
34. **IsCovered_Hospitalization** - Is hospitalization covered
35. **CopayInnTier1_Hospitalization** - Hospital copay per day/stay
36. **CoinsInnTier1_Hospitalization** - Hospital coinsurance %

37. **OutpatientFacility** - Outpatient facility cost sharing
38. **IsCovered_OutpatientFacility** - Is outpatient covered
39. **CopayInnTier1_OutpatientFacility** - Outpatient copay

#### Prescription Drugs
40. **GenericDrugs** - Generic drug copay/coinsurance
41. **IsCovered_GenericDrugs** - Are generics covered
42. **CopayInnTier1_GenericDrugs** - Generic drug copay

43. **PreferredBrandDrugs** - Preferred brand drug cost sharing
44. **IsCovered_PreferredBrandDrugs** - Are preferred brands covered
45. **CopayInnTier1_PreferredBrandDrugs** - Preferred brand copay

46. **NonPreferredBrandDrugs** - Non-preferred brand cost sharing
47. **IsCovered_NonPreferredBrandDrugs** - Are non-preferred brands covered
48. **CopayInnTier1_NonPreferredBrandDrugs** - Non-preferred brand copay

49. **SpecialtyDrugs** - Specialty drug cost sharing
50. **IsCovered_SpecialtyDrugs** - Are specialty drugs covered
51. **CoinsInnTier1_SpecialtyDrugs** - Specialty drug coinsurance %

#### Preventive Care
52. **RoutinePreventiveCare** - Preventive care cost sharing
53. **IsCovered_PreventiveCare** - Is preventive care covered (typically $0)
54. **CopayInnTier1_PreventiveCare** - Preventive care copay

---

### Category 3: Additional Services

#### Mental Health
55. **MentalHealthOutpatient** - Outpatient mental health cost sharing
56. **IsCovered_MentalHealthOutpatient** - Is outpatient mental health covered
57. **CopayInnTier1_MentalHealthOutpatient** - Mental health copay

58. **MentalHealthInpatient** - Inpatient mental health cost sharing
59. **IsCovered_MentalHealthInpatient** - Is inpatient mental health covered

#### Substance Abuse
60. **SubstanceAbuseOutpatient** - Outpatient substance abuse treatment
61. **IsCovered_SubstanceAbuseOutpatient** - Is outpatient SA covered
62. **CopayInnTier1_SubstanceAbuseOutpatient** - SA outpatient copay

63. **SubstanceAbuseInpatient** - Inpatient substance abuse treatment
64. **IsCovered_SubstanceAbuseInpatient** - Is inpatient SA covered

#### Maternity & Newborn Care
65. **PrenatalPostnatalCare** - Prenatal/postnatal care cost sharing
66. **IsCovered_PrenatalCare** - Is prenatal care covered
67. **CopayInnTier1_PrenatalCare** - Prenatal care copay

68. **DeliveryAndAllInpatientServicesForMaternityC are** - Delivery cost sharing
69. **IsCovered_Delivery** - Is delivery covered
70. **CoinsInnTier1_Delivery** - Delivery coinsurance

#### Imaging & Diagnostics
71. **DiagnosticTest** - Diagnostic test cost sharing (X-ray, blood work)
72. **IsCovered_DiagnosticTest** - Are diagnostic tests covered
73. **CopayInnTier1_DiagnosticTest** - Diagnostic test copay
74. **CoinsInnTier1_DiagnosticTest** - Diagnostic test coinsurance

75. **ImagingCTScan** - CT scan cost sharing
76. **IsCovered_ImagingCT** - Is CT scan covered
77. **CopayInnTier1_ImagingCT** - CT scan copay

78. **ImagingMRI** - MRI cost sharing
79. **IsCovered_ImagingMRI** - Is MRI covered
80. **CoinsInnTier1_ImagingMRI** - MRI coinsurance

#### Rehabilitation Services
81. **RehabilitativeOccupationalTherapy** - Rehab therapy cost sharing
82. **IsCovered_Rehabilitation** - Is rehab covered
83. **CopayInnTier1_Rehabilitation** - Rehab copay per visit

84. **HabilitativeOccupationalTherapy** - Habilitative therapy cost sharing
85. **IsCovered_Habilitation** - Is habilitation covered

#### Durable Medical Equipment
86. **DurableMedicalEquipment** - DME cost sharing
87. **IsCovered_DME** - Is DME covered
88. **CoinsInnTier1_DME** - DME coinsurance %

---

### Category 4: Additional Medical Services

#### Skilled Nursing
89. **SkilledNursingFacility** - Skilled nursing cost sharing
90. **IsCovered_SkilledNursing** - Is skilled nursing covered
91. **CopayInnTier1_SkilledNursing** - Skilled nursing copay per day

#### Home Health Care
92. **HomeHealthCareServices** - Home health cost sharing
93. **IsCovered_HomeHealth** - Is home health covered
94. **CoinsInnTier1_HomeHealth** - Home health coinsurance

#### Hospice
95. **HospiceService** - Hospice care cost sharing
96. **IsCovered_Hospice** - Is hospice covered

#### Vision (Adult)
97. **EyeExamForAdults** - Adult eye exam cost sharing
98. **IsCovered_AdultEyeExam** - Is adult eye exam covered
99. **CopayInnTier1_AdultEyeExam** - Eye exam copay

#### Dental (Child)
100. **ChildDentalCare** - Pediatric dental cost sharing
101. **IsCovered_ChildDental** - Is child dental covered

#### Chiropractic
102. **ChiropracticCare** - Chiropractic visit cost sharing
103. **IsCovered_Chiropractic** - Is chiropractic covered
104. **CopayInnTier1_Chiropractic** - Chiropractic copay

#### Acupuncture
105. **Acupuncture** - Acupuncture cost sharing
106. **IsCovered_Acupuncture** - Is acupuncture covered

#### Bariatric Surgery
107. **BariatricSurgery** - Bariatric surgery cost sharing
108. **IsCovered_BariatricSurgery** - Is bariatric surgery covered

---

### Category 5: Plan-Level Attributes

#### Network Information
109. **NetworkTier1ProviderName** - Tier 1 network name
110. **NetworkTier2ProviderName** - Tier 2 network name (if applicable)

#### Formulary Details
111. **FormularyIdNumber** - Detailed formulary identifier
112. **DrugTierStructure** - Number of drug tiers (3-tier, 4-tier, 5-tier)

#### Quality Ratings
113. **QualityRating** - Overall plan quality rating (1-5 stars)
114. **PatientSatisfactionRating** - Patient satisfaction score

#### Additional Plan Details
115. **ChildOnlyOffering** - Whether plan available for children only
116. **SpecialtyDrugMaximumCoinsurance** - Max coinsurance for specialty drugs
117. **BeginPrimaryCareDeductibleCoinsuranceAfterSetNumberOfVisits** - Deductible waiver for initial visits
118. **BeginPrimaryCareCoPayAfterSetNumberOfCopays** - Copay waiver for initial visits

---

## Why These Fields Aren't Loaded

**Documented Reasons (from DATA_SOURCES.md):**

1. **Large Data Volume**
   - Benefits file is significantly larger than other PUF files
   - ~100+ columns per plan
   - Millions of benefit-specific records

2. **Complex Structure**
   - Nested benefit categories
   - Multiple cost-sharing tiers (Tier 1, Tier 2, OON)
   - Boolean flags + cost-sharing amounts for each benefit

3. **Plan ID Format Mismatches**
   - Some benefit records use different plan ID variants
   - Requires additional normalization logic

---

## Business Value of Loading These Fields

### High Priority Benefits (Top 20 for User Experience)

1. **Primary Care Copay** - Most common user question
2. **Specialist Copay** - Second most common
3. **Emergency Room Cost** - Critical for comparison
4. **Generic Drug Copay** - Essential for Rx users
5. **Preferred Brand Drug Copay** - Essential for Rx users
6. **Urgent Care Copay** - Common usage
7. **Hospital Coinsurance** - Major expense planning
8. **Out-of-Network Deductible** - Important for comparison
9. **Out-of-Network MOOP** - Important for comparison
10. **Mental Health Copay** - Increasingly important
11. **CT/MRI Coinsurance** - High-cost procedures
12. **Preventive Care Coverage** - User reassurance
13. **Prenatal Care Copay** - Critical for families
14. **Delivery Cost Sharing** - Major expense
15. **Skilled Nursing Coverage** - Aging population
16. **Home Health Coverage** - Post-hospital care
17. **Rehab Therapy Copay** - Common need
18. **DME Coinsurance** - Chronic conditions
19. **Specialty Drug Coinsurance** - High-cost medications
20. **Chiropractic Coverage** - Common benefit question

### Medium Priority (Nice to Have)

- Tier 2 network costs
- Habilitation services
- Bariatric surgery coverage
- Acupuncture coverage
- Adult vision coverage
- Hospice coverage

### Lower Priority (Comprehensive Data)

- All permutations of in/out network tiers
- Detailed drug tier breakdowns
- Quality ratings (available elsewhere)
- Special program flags

---

## Implementation Recommendation

### Phase 1: Core Benefits (20 fields)
Load the top 20 most-queried benefits to provide immediate value for plan comparison.

### Phase 2: Extended Benefits (40 fields)
Add comprehensive coverage for all major service categories.

### Phase 3: Complete Dataset (60+ fields)
Full benefits table for advanced users and comprehensive plan details.

---

## Data Loading Challenges to Solve

1. **Plan ID Normalization**
   - Some benefit records use 14-character plan IDs
   - Some use 16-character with variants (-00, -01, etc.)
   - Need mapping logic to match benefits to plans

2. **Data Structure Design**
   - Store as JSONB in existing `benefits` table?
   - Create separate tables for each benefit category?
   - Hybrid approach: core fields + JSONB for extended?

3. **Query Performance**
   - Indexed benefit_name for fast lookups
   - Pre-compute common benefit queries?
   - Cache frequently accessed benefit combinations?

4. **Data Volume**
   - ~20,000 plans × 60+ benefits = 1.2M+ benefit records
   - Need efficient storage and retrieval
   - Consider compression or aggregation strategies

---

## Next Steps

1. **Download 2026 Benefits PUF** from CMS
2. **Analyze actual column names** in CSV (may differ from documentation)
3. **Build plan ID matching logic** to handle variants
4. **Prioritize top 20 benefits** for Phase 1 implementation
5. **Update `load_data.py`** to include benefits loading
6. **Test with sample data** before full load
7. **Update API** to return benefit details in plan responses

---

**Document Created:** January 15, 2026  
**Status:** Benefits table exists but not populated  
**Impact:** Full benefits data would enable comprehensive plan comparison
