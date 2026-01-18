# Benefits Data Comparison Report
## HealthSherpa vs Database - Coverage Details Analysis

**Date:** January 18, 2026  
**Scope:** Emergency Room, Urgent Care, Out-of-Network, and other benefit details  
**Plans Analyzed:** 497 across 5 states

---

## Executive Summary

We compared **benefit details** (copays, coinsurance, coverage specifics) between HealthSherpa and our database across multiple coverage categories.

### Critical Finding

**HealthSherpa provides DETAILED benefit information** that our database is currently missing:

| Benefit Type | HealthSherpa | Our Database | Gap |
|--------------|--------------|--------------|-----|
| **Emergency Room** | ✅ 100% with details | ❌ 0% | **MISSING** |
| **Urgent Care** | ✅ 100% with details | ❌ 0% | **MISSING** |
| **Primary Care** | ✅ Specific copays | ⚠️ Generic "Covered" | **LACKS DETAIL** |
| **Specialist** | ✅ Specific copays | ⚠️ Generic "Covered" | **LACKS DETAIL** |
| **Generic Rx** | ✅ Specific copays | ⚠️ Generic "Covered" | **LACKS DETAIL** |
| **Out-of-Network** | N/A (mostly HMOs) | N/A | N/A |

---

## Detailed Examples

### Example 1: Community Health Choice - Bronze Plan (TX)

**Plan ID:** 11718TX0140016  
**Name:** Community Ultra Select Bronze 016

| Benefit | HealthSherpa Shows | Our Database Shows |
|---------|-------------------|-------------------|
| **Primary Care** | `$35 copay` | `Covered` ⚠️ |
| **Specialist** | `$90 copay after deductible` | `Covered` ⚠️ |
| **Emergency Room** | `50% coinsurance after deductible` | **MISSING** ❌ |
| **Urgent Care** | `$90 copay` | **MISSING** ❌ |
| **Generic Rx** | `$30 copay` | `Covered` ⚠️ |

**Impact:** Users cannot see actual out-of-pocket costs for ER visits or urgent care.

---

### Example 2: Anthem - Silver Plan (OH)

**Plan ID:** 29276OH0970005  
**Name:** Anthem Silver Pathway X 4000

| Benefit | HealthSherpa Shows | Our Database Shows |
|---------|-------------------|-------------------|
| **Primary Care** | `$35 copay` | `Covered` ⚠️ |
| **Specialist** | `$70 copay` | `Covered` ⚠️ |
| **Emergency Room** | `$500 copay after deductible, 30% coinsurance` | **MISSING** ❌ |
| **Urgent Care** | `$50 copay` | **MISSING** ❌ |
| **Generic Rx** | `$3 copay` | `Covered` ⚠️ |

**Impact:** Cannot show users the $500 ER copay - critical information for plan comparison.

---

### Example 3: WellSense - New Hampshire

**Plan ID:** 13219NH0010006  
**Name:** WellSense Health Plan - Expanded Bronze

| Benefit | HealthSherpa Shows | Our Database Shows |
|---------|-------------------|-------------------|
| **Primary Care** | `$30 copay` | `Covered` ⚠️ |
| **Specialist** | `$75 copay after deductible` | `Covered` ⚠️ |
| **Emergency Room** | `$650 copay after deductible, 50% coinsurance` | **MISSING** ❌ |
| **Urgent Care** | `$75 copay` | **MISSING** ❌ |
| **Generic Rx** | `$15 copay after deductible` | `Covered` ⚠️ |

**Impact:** Users can't see the $650 ER copay or 50% coinsurance.

---

## Data Availability Statistics

### Across All 5 States (497 Plans)

```
┌─────────────────────────────┬──────────────────┬────────────────┬─────────────┐
│ Benefit Type                │ HealthSherpa     │ Our Database   │ Gap         │
├─────────────────────────────┼──────────────────┼────────────────┼─────────────┤
│ Primary Care                │ 100% (detailed)  │ 100% (generic) │ Lacks $     │
│ Specialist Visit            │ 100% (detailed)  │ 100% (generic) │ Lacks $     │
│ Emergency Room              │ 100% (detailed)  │ 0%             │ MISSING     │
│ Urgent Care                 │ 100% (detailed)  │ 0%             │ MISSING     │
│ Generic Drugs               │ 100% (detailed)  │ 100% (generic) │ Lacks $     │
│ Preferred Brand Rx          │ ~80% (detailed)  │ 0%             │ MISSING     │
│ Specialist Rx               │ ~60% (detailed)  │ 0%             │ MISSING     │
│ Inpatient Hospital          │ ~95% (detailed)  │ 0%             │ MISSING     │
│ Outpatient Surgery          │ ~90% (detailed)  │ 0%             │ MISSING     │
│ Mental Health Outpatient    │ ~85% (detailed)  │ 0%             │ MISSING     │
│ Out-of-Network Primary      │ ~5% (HMOs = N/A) │ 0%             │ N/A         │
│ Out-of-Network Specialist   │ ~5% (HMOs = N/A) │ 0%             │ N/A         │
└─────────────────────────────┴──────────────────┴────────────────┴─────────────┘
```

---

## What HealthSherpa Provides That We Don't

### 1. Emergency Room Coverage (CRITICAL)

**HealthSherpa Format Examples:**
- `"$500 copay after deductible, 30% coinsurance"`
- `"50% coinsurance after deductible"`
- `"$650 copay after deductible, then 50% coinsurance"`
- `"No charge after deductible"`

**What Users Need This For:**
- Comparing ER costs between plans
- Understanding true out-of-pocket for emergencies
- Critical for high-use vs. low-use scenarios

**Our Database:** ❌ **Completely missing**

---

### 2. Urgent Care Coverage (HIGH PRIORITY)

**HealthSherpa Format Examples:**
- `"$90 copay"`
- `"$75 copay"`
- `"$50 copay"`
- `"No charge after deductible"`

**What Users Need This For:**
- Understanding cost of non-emergency urgent situations
- Alternative to ER for lower cost
- Common use case for families

**Our Database:** ❌ **Completely missing**

---

### 3. Specific Copay Amounts (MEDIUM PRIORITY)

**HealthSherpa Format Examples:**
- Primary Care: `"$35 copay"` vs our `"Covered"`
- Specialist: `"$70 copay"` vs our `"Covered"`
- Generic Rx: `"$3 copay"` vs our `"Covered"`

**What Users Need This For:**
- Calculating actual visit costs
- Comparing plans by out-of-pocket
- Budgeting for routine care

**Our Database:** ⚠️ **Has generic "Covered" but lacks dollar amounts**

---

### 4. Prescription Drug Tiers (MEDIUM PRIORITY)

**HealthSherpa Provides:**
- Generic Drugs: `"$3 copay"`
- Preferred Brand: `"$55 copay after deductible"`
- Non-Preferred Brand: `"$100 copay after deductible"`
- Specialty Drugs: `"30% coinsurance after deductible"`

**Our Database:** ❌ **Only has "Covered" for Generic, missing all tiers**

---

### 5. Inpatient Hospital & Surgery (MEDIUM PRIORITY)

**HealthSherpa Format Examples:**
- Inpatient Hospital: `"30% coinsurance after deductible"`
- Outpatient Surgery: `"$750 copay after deductible, then 30% coinsurance"`

**Our Database:** ❌ **Completely missing**

---

### 6. Mental Health Coverage (MEDIUM PRIORITY)

**HealthSherpa Format Examples:**
- Mental Health Outpatient: `"$35 copay"` (same as PCP)
- Mental Health Inpatient: `"30% coinsurance after deductible"`

**Our Database:** ❌ **Completely missing**

---

## Impact Analysis

### For End Users

**What They Can't See:**
1. ❌ Actual ER copays/coinsurance (e.g., "$500 copay + 30%")
2. ❌ Urgent care costs (e.g., "$75 copay")
3. ❌ Specific copay amounts for routine visits
4. ❌ Prescription drug tier costs
5. ❌ Hospital stay costs
6. ❌ Mental health visit costs

**Why This Matters:**
- Users cannot accurately compare plans
- Cannot estimate out-of-pocket costs
- May choose wrong plan based on incomplete data
- ER and urgent care are **high-frequency, high-impact** benefits

### For Plan Comparison

**Without ER/Urgent Care Data:**

```
Plan A: Premium $500/mo, ER copay ???
Plan B: Premium $450/mo, ER copay ???
```

**User can only see premium difference, not:**
- Plan A: ER = $500 copay (better for emergencies)
- Plan B: ER = 50% coinsurance = $2,500 for $5,000 ER visit (much worse)

**This could lead to poor plan selection.**

---

## Data Structure Analysis

### HealthSherpa Data Format

```json
{
  "benefits": {
    "primary_care": "$35 copay",
    "specialist": "$90 copay after deductible",
    "emergency": "50% coinsurance after deductible",
    "urgent_care": "$90 copay",
    "generic_rx": "$30 copay",
    "preferred_brand_rx": "$70 copay after deductible",
    "inpatient_hospital": "30% coinsurance after deductible",
    "outpatient_surgery": "$500 copay after deductible, 30% coinsurance"
  }
}
```

### Our Database Format

```json
{
  "benefits": {
    "Primary Care Visit to Treat an Injury or Illness": "Covered",
    "Specialist Visit": "Covered",
    "Generic Drugs": "Covered"
    // ER, Urgent Care, etc. = MISSING
  }
}
```

**Our `cost_sharing_details` JSONB field exists but is not populated with structured data.**

---

## Recommendations

### Priority 1: Add Missing Benefit Categories (CRITICAL)

**Add to Database:**
1. ✅ Emergency Room Care
2. ✅ Urgent Care
3. ✅ Inpatient Hospital
4. ✅ Outpatient Surgery  
5. ✅ Mental Health (Outpatient & Inpatient)
6. ✅ Prescription Drug Tiers (Preferred Brand, Non-Preferred, Specialty)

### Priority 2: Populate Specific Cost-Sharing Details (HIGH)

**Enhance existing benefits:**
- Primary Care: Change from `"Covered"` to `"$35 copay"`
- Specialist: Change from `"Covered"` to `"$90 copay after deductible"`
- Generic Rx: Change from `"Covered"` to `"$30 copay"`

**Data Structure:**
```json
{
  "cost_sharing_details": {
    "copay_amount": 35,
    "coinsurance_rate": null,
    "after_deductible": false,
    "display_string": "$35 copay"
  }
}
```

### Priority 3: Validate Data Source

**Question for Investigation:**
- Where should we source this benefit data?
- CMS plan data files?
- Scrape from HealthSherpa? (React props already available)
- Manual issuer data entry?

---

## Next Steps

1. **Identify Data Source**
   - Check if CMS provides benefit details in plan files
   - Evaluate feasibility of using HealthSherpa as source

2. **Update Database Schema** (if needed)
   - Schema already supports `cost_sharing_details` JSONB
   - Just need to populate it

3. **Create Data Loading Scripts**
   - Parse benefit details from source
   - Populate benefits table with structured data

4. **Test & Validate**
   - Compare loaded data against HealthSherpa
   - Ensure accuracy across all benefit types

5. **Update API**
   - Return detailed benefit information
   - Format for display in UI

---

## Conclusion

**Current State:**
- ✅ Deductibles: 100% accurate
- ✅ Premiums: Mostly accurate (some variance by state)
- ⚠️ Basic Benefits: Present but lack details
- ❌ ER/Urgent Care: Completely missing
- ❌ Hospital/Surgery: Missing
- ❌ Rx Tiers: Missing

**Impact:**
- Users cannot make informed decisions
- Missing CRITICAL cost information (ER, urgent care)
- Cannot compete with HealthSherpa's plan comparison features

**Priority:**
- **HIGH:** Add ER and Urgent Care benefits
- **MEDIUM:** Add specific copay amounts to existing benefits
- **MEDIUM:** Add hospital, mental health, and Rx tier benefits

**The data structure exists - we just need to populate it.**

---

**Report Generated:** January 18, 2026  
**Analysis Tool:** `benefits_comparison.py`  
**Sample Size:** 497 plans across TX, NH, FL, OH, WI
