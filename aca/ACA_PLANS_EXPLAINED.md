# ACA Plans Explained: Age-Based Pricing, Plan IDs, and Benefits

**Last Updated:** January 14, 2026

---

## 1. Do ACA Plans Have Different Offerings Based on Age?

### Short Answer: Yes and No

**The Plan Itself:** The same (coverage is identical regardless of age)  
**The Premium:** Different (price varies by age)

### How ACA Age-Based Pricing Works

ACA plans have **identical coverage** for all ages, but **premiums vary by age**. This is fundamentally different from Medicare.

#### Same Coverage, Different Price

**A 25-year-old and a 60-year-old buying the same plan get:**
- ✅ Same benefits
- ✅ Same deductible
- ✅ Same copays
- ✅ Same network
- ✅ Same covered services
- ❌ Different monthly premiums

#### Age Rating Rules

The ACA allows **age rating** with strict limits:

**3:1 Ratio Rule:**
- Maximum premium ratio between oldest (64) and youngest (21) adults is 3:1
- A 64-year-old can pay at most 3x what a 21-year-old pays
- This protects older adults from excessive premiums

**Age Bands:**

Premium increases gradually with age:

```
Age 21: $250/month  (baseline)
Age 25: $260/month  (1.04x)
Age 30: $280/month  (1.12x)
Age 35: $302/month  (1.21x)
Age 40: $340/month  (1.36x)
Age 45: $385/month  (1.54x)
Age 50: $480/month  (1.92x)
Age 55: $570/month  (2.28x)
Age 60: $685/month  (2.74x)
Age 64: $750/month  (3.00x - maximum ratio)
```

**Age 0-20:** All children under 21 pay the same rate (usually lowest)

**Age 65+:** Rare in ACA marketplace (most have Medicare)

#### Additional Rating Factors

Beyond age, premiums also vary by:

1. **Geographic Rating Area**
   - Same plan costs different amounts in different counties
   - Urban areas often more expensive than rural
   - Example: Miami vs. Jacksonville in Florida

2. **Tobacco Use**
   - Smokers can be charged up to 50% more
   - Example: Age 40 non-smoker: $340/month
   - Example: Age 40 smoker: $510/month (1.5x)

3. **Household Size**
   - Family coverage vs. individual
   - Different rates for couples, families with children

### The Rate Table Structure

In the CMS rate PUF file, each plan has a complete rate table:

**Example: Plan 13887FL0010001-00**

| Age | Individual Rate | Tobacco Rate |
|-----|----------------|--------------|
| 0-20 | $200 | N/A |
| 21 | $250 | $375 |
| 22 | $253 | $380 |
| 23 | $255 | $383 |
| ... | ... | ... |
| 40 | $340 | $510 |
| ... | ... | ... |
| 64 | $750 | $1,125 |

**This is why the rate file has ~2.2 million rows:**
- 20,354 plans × 44 ages (21-64) × 2 tobacco statuses = ~1.8M rows
- Plus child rates, variations by rating area, etc.

### Why This Matters for the API

**Current Status:** Rate data is **not loaded** in our database.

**Impact:**
- API returns plan details but not age-specific premiums
- Users see "Plan costs vary by age" but not actual prices
- Cannot answer "How much will this plan cost ME?"

**To Add Premium Quotes:**
1. Fix plan ID matching issues (see below)
2. Load rate table into database
3. Accept age parameter in API
4. Return personalized premium quote

**Example API Enhancement:**
```
GET /aca/zip/33139.json?age=45&tobacco=no

Response includes:
{
  "plan_id": "13887FL0010001-00",
  "plan_name": "Gold Health Plan",
  "metal_level": "Gold",
  "your_monthly_premium": 385,  // ← Age 45 rate
  "with_tobacco": 578            // ← Age 45 tobacco rate
}
```

---

## 2. Plan ID Format Issues Explained

### The Problem

The **plan attributes file** uses one plan ID format, while the **rate file** uses a different format. This prevents us from matching rates to plans.

### Plan ID Formats in CMS PUF Files

#### Format 1: Plan Attributes File (Standard HIOS ID)

**Format:** `IssuerID + ProductID + VariantID`
**Length:** 14 characters
**Example:** `13887FL0010001`

**Breakdown:**
- `13887` - Issuer ID (5 digits)
- `FL` - State code (2 letters)
- `001` - Product ID (3 digits)
- `0001` - Variant ID (4 digits)

**Used in:** `plan-attributes-puf.csv`

#### Format 2: Rate File (Extended Format)

**Format:** `IssuerID + ProductID + VariantID + Suffix`
**Length:** 17 characters
**Example:** `13887FL0010001-00`

**Additional Components:**
- `-00` - Suffix (cost-sharing reduction variant or rating area indicator)
- Sometimes: `-01`, `-02`, `-03` for CSR plans

**Used in:** `rate-puf.csv`

#### Format 3: StandardComponentId

**Format:** Different structure entirely
**Example:** `13887FL0010001ABCD01`

**Used in:** Some files for cross-referencing

### Why Multiple Formats Exist

**CMS Reasoning:**
1. **Plan Attributes:** One plan design = one ID
2. **Rates:** Same plan can have different rates by:
   - Rating area within state
   - Cost-sharing reduction (CSR) level for subsidized plans
   - Network variations

**Example Scenario:**

```
Plan: "Blue Cross Silver PPO"
Plan Attributes ID: 13887FL0010001

Rate File Variations:
- 13887FL0010001-00  (Standard rating area 1)
- 13887FL0010001-01  (Rating area 2) 
- 13887FL0010001-02  (CSR 73 variant)
- 13887FL0010001-03  (CSR 87 variant)
- 13887FL0010001-04  (CSR 94 variant)
```

All are the "same plan" with different rates based on subsidy level or location.

### The Matching Problem

**Our Current Load Process:**

```python
# From plan attributes
plan_id = "13887FL0010001"

# From rate file
rate_plan_id = "13887FL0010001-00"

# Simple match fails:
if plan_id == rate_plan_id:  # False! String mismatch
    load_rate()
```

### Solutions

#### Solution 1: Strip Suffix (Simple)

```python
# Normalize rate file IDs
rate_plan_base = rate_plan_id.split('-')[0]  # "13887FL0010001"

if plan_id == rate_plan_base:
    load_rate()
```

**Issue:** Loses information about which variant the rate applies to.

#### Solution 2: Load All Variants

```python
# Load all rate variants for a plan
rates = {
    "13887FL0010001": [
        {"variant": "00", "age": 40, "rate": 340},
        {"variant": "01", "age": 40, "rate": 355},  # Different rating area
        {"variant": "02", "age": 40, "rate": 270}   # CSR plan (subsidized)
    ]
}
```

**Better:** Preserves all rate information.

#### Solution 3: Use StandardComponentId

```python
# Match using alternate ID field
standard_id = plan["StandardComponentId"]
rate_standard_id = rate["StandardComponentId"]

if standard_id == rate_standard_id:
    load_rate()
```

**Best:** Uses CMS's official cross-reference ID.

### What We Need to Fix

**In `database/load_data.py`:**

1. Update rate loading logic to handle ID variations
2. Add suffix stripping or variant tracking
3. Test matching across all 20,354 plans
4. Verify rate counts are reasonable

**Expected Result:**
- ~2.2 million rate records loaded
- Each plan has 40+ age-specific rates
- Rates properly linked to plans

---

## 3. Detailed Benefits from CMS PUF Files

### What Are "Benefits"?

The **Benefits and Cost Sharing PUF** file contains detailed information about what each plan covers and how much you pay for each type of service.

### File Structure

**File:** `benefits-and-cost-sharing-puf.csv`  
**Size:** Very large (hundreds of MB)  
**Rows:** Millions (one row per plan per benefit category)

### What's Included

#### Cost Sharing Summary

For each plan, overall limits:

**Medical:**
- `Medical Deductible - Individual` - $1,500, $3,000, $6,000, etc.
- `Medical Deductible - Family` - $3,000, $6,000, $12,000, etc.
- `Medical Maximum Out of Pocket - Individual` - $6,300, $8,700, etc.
- `Medical Maximum Out of Pocket - Family` - $12,600, $17,400, etc.

**Drug:**
- `Drug Deductible - Individual`
- `Drug Deductible - Family`
- `Drug Maximum Out of Pocket - Individual`
- `Drug Maximum Out of Pocket - Family`

**Combined:**
- `Combined Medical and Drug Deductible`
- `Combined Medical and Drug Maximum Out of Pocket`

#### Specific Service Categories (60+)

For each service, the plan specifies:

**Cost Sharing Type:**
- Copay (fixed amount): "$30 per visit"
- Coinsurance (percentage): "20% after deductible"
- No charge: "$0"
- Not covered: "Not Applicable"

**Whether Deductible Applies:**
- "Before Deductible" - You pay copay/coinsurance before meeting deductible
- "After Deductible" - You meet deductible first, then pay copay/coinsurance
- "Not Applicable" - Deductible doesn't apply (like preventive care)

**In-Network vs. Out-of-Network:**
- Different costs for in-network and out-of-network providers

### Benefit Categories

**Primary Care:**
- Primary Care Visit to Treat Injury or Illness
- Specialist Visit
- Other Practitioner Office Visit
- Preventive Care/Screening/Immunization

**Hospital Services:**
- Outpatient Facility Fee (Ambulatory Surgery Center)
- Outpatient Facility Fee (Hospital)
- Outpatient Surgery Physician/Surgical Services
- Inpatient Hospital Services (e.g., Hospital Stay)
- Inpatient Physician and Surgical Services

**Emergency Services:**
- Emergency Room Services
- Emergency Room Physician Services
- Urgent Care Centers or Facilities
- Ambulance Services

**Imaging:**
- Imaging (CT/PET Scans, MRIs)
- X-rays

**Tests and Labs:**
- Laboratory Outpatient and Professional Services
- Diagnostic Test (e.g., X-ray, blood work)

**Mental Health:**
- Mental/Behavioral Health Outpatient Services
- Mental/Behavioral Health Inpatient Services
- Substance Use Disorder Outpatient Services
- Substance Use Disorder Inpatient Services

**Pregnancy:**
- Prenatal and Postnatal Care
- Delivery and All Inpatient Services for Maternity Care

**Pediatric:**
- Pediatric Dental Services - Basic
- Pediatric Dental Services - Major
- Pediatric Dental Services - Orthodontia
- Pediatric Vision Services - Eye Exam
- Pediatric Vision Services - Glasses

**Rehabilitation:**
- Rehabilitation Services
- Habilitation Services
- Skilled Nursing Facility
- Home Health Care Services

**Durable Medical Equipment:**
- Durable Medical Equipment
- Prosthetic Devices

**Prescription Drugs:**
- Generic Drugs (Tier 1)
- Preferred Brand Drugs (Tier 2)
- Non-Preferred Brand Drugs (Tier 3)
- Specialty Drugs (Tier 4)

**Other Services:**
- Bariatric Surgery
- Chiropractic Care
- Acupuncture
- Infertility Treatment
- Routine Foot Care
- Routine Eye Exam (Adult)
- And 30+ more...

### Example Benefit Record

**Plan:** Silver PPO  
**Benefit:** Primary Care Visit

```csv
PlanId,BenefitName,IsCovered,CopayAmount,CoinsuranceRate,SubjectToDeductible
13887FL0010001,Primary Care Visit,Yes,$25,0%,No Before Deductible
```

**Translation:** 
- ✅ Covered
- 💵 $25 copay
- 🏥 You pay $25 even before meeting deductible
- 📊 No coinsurance (0%)

**Plan:** Bronze HDHP (High Deductible)  
**Benefit:** Primary Care Visit

```csv
PlanId,BenefitName,IsCovered,CopayAmount,CoinsuranceRate,SubjectToDeductible
13887FL0020002,Primary Care Visit,Yes,$0,20%,Yes After Deductible
```

**Translation:**
- ✅ Covered
- 💵 No copay
- 📊 20% coinsurance after deductible
- 🏥 Must meet $6,000 deductible first, then pay 20%

### Why This Is Valuable

**Current API Response:**
```json
{
  "plan_id": "13887FL0010001",
  "plan_name": "Silver PPO",
  "metal_level": "Silver",
  "deductible": "$1,500",  // From plan_attributes JSON
  "out_of_pocket_max": "$6,300"
}
```

**Enhanced API Response (with benefits loaded):**
```json
{
  "plan_id": "13887FL0010001",
  "plan_name": "Silver PPO",
  "metal_level": "Silver",
  "deductible": "$1,500",
  "out_of_pocket_max": "$6,300",
  "benefits": {
    "primary_care_visit": {
      "covered": true,
      "copay": "$25",
      "before_deductible": true
    },
    "specialist_visit": {
      "covered": true,
      "copay": "$60",
      "before_deductible": true
    },
    "emergency_room": {
      "covered": true,
      "copay": "$500",
      "after_deductible": false
    },
    "generic_drugs": {
      "covered": true,
      "copay": "$10",
      "before_deductible": true
    },
    // ... 60+ more benefit categories
  }
}
```

### Why We Haven't Loaded It Yet

**Challenges:**

1. **Volume:** Millions of rows (20,354 plans × 60+ benefits = 1.2M+ rows)
2. **Schema Complexity:** Each benefit has multiple attributes
3. **Plan ID Matching:** Same format issue as rates
4. **Database Size:** Would significantly increase RDS storage costs
5. **Query Performance:** Complex joins to retrieve all benefits

**Trade-offs:**

**Load Benefits:**
- ✅ Rich plan comparisons
- ✅ Answer "Does this plan cover X?"
- ✅ Show exact copays for common services
- ❌ Larger database (~5x size increase)
- ❌ Slower queries (more data to join)
- ❌ Higher AWS costs ($20→$40/month)

**Don't Load Benefits:**
- ✅ Fast queries
- ✅ Lower costs
- ❌ Less detailed plan information
- ❌ Users must check healthcare.gov for specifics

### How to Load Benefits

**If we decide to add this capability:**

1. **Update Schema:**
```sql
CREATE TABLE benefits (
    plan_id VARCHAR(50) REFERENCES plans(plan_id),
    benefit_name VARCHAR(200),
    is_covered BOOLEAN,
    copay_amount VARCHAR(50),
    coinsurance_rate VARCHAR(50),
    subject_to_deductible VARCHAR(50),
    in_network BOOLEAN,
    exclusions TEXT,
    cost_sharing_details JSONB,
    PRIMARY KEY (plan_id, benefit_name, in_network)
);
```

2. **Parse Benefits PUF:**
```python
def load_benefits(conn, benefits_file):
    with open(benefits_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            plan_id = normalize_plan_id(row['PlanId'])
            benefit = {
                'plan_id': plan_id,
                'benefit_name': row['BenefitName'],
                'is_covered': row['IsCovered'] == 'Yes',
                'copay_amount': row['CopayAmount'],
                'coinsurance_rate': row['CoinsuranceRate'],
                'subject_to_deductible': row['SubjectToDeductible']
            }
            insert_benefit(conn, benefit)
```

3. **Update API to return benefits:**
```python
def get_plan_details(plan_id):
    plan = get_plan(plan_id)
    benefits = get_benefits(plan_id)  # New query
    plan['benefits'] = benefits
    return plan
```

---

## Summary

### Age-Based Pricing
- ✅ Same coverage for all ages
- ✅ Premiums vary by age (3:1 max ratio)
- ✅ Also varies by tobacco use, location
- ⚠️ Rate data not loaded yet (need to fix plan ID matching)

### Plan ID Format Issues
- ❌ Plan attributes use 14-char format: `13887FL0010001`
- ❌ Rate file uses 17-char format: `13887FL0010001-00`
- 🔧 Fix: Strip suffix or use StandardComponentId
- 📝 Action: Update load_data.py to handle variations

### Benefits Data
- 📊 60+ service categories per plan
- 💰 Detailed copays, coinsurance, deductibles
- 📁 Available in CMS PUF but not loaded
- ⚠️ Large data volume (1.2M+ rows)
- 💡 Trade-off: Richness vs. performance/cost
- 🚀 Can be added as future enhancement

---

## Next Steps

**To Enable Full Premium Quotes:**
1. Fix plan ID matching in load_data.py
2. Load rate-puf.csv into database
3. Add age parameter to API
4. Return personalized premiums

**To Enable Benefit Comparisons:**
1. Evaluate database size impact
2. Update schema to add benefits table
3. Load benefits-and-cost-sharing-puf.csv
4. Update API to return benefit details
5. Consider caching/materialized views for performance

**Current Priority:**
Fix rate loading first (smaller impact, high value) before tackling benefits (larger impact).
