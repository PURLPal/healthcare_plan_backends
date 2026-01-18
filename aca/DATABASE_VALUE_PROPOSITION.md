# Database Value Proposition & Unique Capabilities

**What can our database answer that HealthSherpa cannot?**

---

## Executive Summary

HealthSherpa is excellent for **individual plan shopping** (user-friendly UI, one person at a time).

Our database enables:
- ✅ **Multi-age household calculations** (all ages instantly, no page reloads)
- ✅ **Geographic analysis** (compare plans across ZIPs/counties/states)
- ✅ **Market research** (issuer market share, pricing strategies)
- ✅ **Programmatic API access** (build custom tools)
- ✅ **Bulk statistics** (analyze thousands of plans at once)
- ✅ **Rating area analysis** (premium variation by location)
- ✅ **Service area mapping** (which counties does a plan cover?)

---

## 10 Unique Database Capabilities

| # | Capability | HealthSherpa | Our Database |
|---|------------|--------------|--------------|
| 1 | **Age Curves** | One age per request (page reload) | All ages (14-120) instantly |
| 2 | **Geographic Analysis** | One ZIP at a time | All ZIPs/counties at once |
| 3 | **Cross-ZIP Comparison** | Not possible | Compare same plan across areas |
| 4 | **Issuer Analysis** | Limited to current view | Full market presence data |
| 5 | **Complex Queries** | Basic filtering | Filter by any attribute combo |
| 6 | **Bulk Statistics** | Manual comparison | Analyze thousands of plans |
| 7 | **Service Areas** | No visibility | Complete coverage mapping |
| 8 | **Historical/Bulk Export** | Manual scraping | Programmatic export |
| 9 | **API Integration** | Web UI only | Full API access |
| 10 | **Rating Area Analysis** | Not visible | Premium variation by area |

---

## Detailed Capabilities

### 1. Age-Based Premium Curves ⭐⭐⭐

**HealthSherpa:** Shows premium for ONE age at a time (requires page reload for each age)

**Our Database:** Has premiums for ALL ages (14-120) for every plan in a single query

**Example Use Case:**
```
Family with ages 42, 38, and 15 wants to know total household premium.

HealthSherpa: Must reload page 3 times, manually add up values
Our Database: Single query returns all three ages instantly

SELECT age, individual_rate 
FROM rates 
WHERE plan_id = '11718TX0140016-01' 
  AND age IN (42, 38, 15);

Result:
  Age 42: $410.05
  Age 38: $385.62  
  Age 15: $258.61
  Total:  $1,054.28 (instant calculation)
```

**Age Curve Impact:**
- Youngest (Age 14): $237.49
- Oldest (Age 64): $916.45
- **Ratio: 3.86x** (64-year-old pays nearly 4x more than 14-year-old)

---

### 2. Geographic Coverage & Service Areas ⭐⭐⭐

**HealthSherpa:** Shows plans for ONE ZIP code at a time

**Our Database:** Can query:
- Which ZIPs/counties a plan covers
- All plans available in a county
- Compare plan availability across regions

**Example Use Case:**
```sql
-- "Which counties does this plan cover?"
SELECT c.county_name, COUNT(DISTINCT zc.zip_code) as zip_count
FROM plan_service_areas psa
JOIN zip_counties zc ON psa.county_fips = zc.county_fips
JOIN counties c ON zc.county_fips = c.county_fips
WHERE psa.service_area_id = 'TXS001'
GROUP BY c.county_name;

-- "Show all plans available in Harris County"
SELECT p.plan_marketing_name, p.issuer_name
FROM plans p
JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
WHERE psa.county_fips = '48201';  -- Harris County
```

**Texas County Plan Availability:**
- Harris County: 1,276 plans
- Dallas County: 1,207 plans
- El Paso County: 1,166 plans

---

### 3. Cross-ZIP & Rating Area Analysis ⭐⭐⭐

**HealthSherpa:** One ZIP at a time, no comparison

**Our Database:** Compare premiums for the same plan across different ZIPs/counties

**Example Use Case:**
```sql
-- "Is this plan cheaper in the next ZIP code?"
SELECT 
    zc.zip_code,
    c.county_name,
    r.individual_rate
FROM rates r
JOIN plans p ON r.plan_id = p.plan_id
JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
JOIN zip_counties zc ON psa.county_fips = zc.county_fips
JOIN counties c ON zc.county_fips = c.county_fips
WHERE p.plan_id LIKE '11718TX0140016%'
  AND r.age = 40
  AND zc.zip_code IN ('77002', '77447', '77459')
ORDER BY r.individual_rate;
```

**Finding:** Same Houston-area plan costs $396.76 across all ZIPs (same rating area)

---

### 4. Issuer & Market Analysis ⭐⭐

**HealthSherpa:** Shows issuers for displayed plans only

**Our Database:** Complete market intelligence

**Example Analysis:**
```sql
-- "Which insurers dominate the Texas market?"
SELECT 
    issuer_name,
    COUNT(DISTINCT plan_id) as plans,
    COUNT(DISTINCT metal_level) as metal_levels,
    COUNT(DISTINCT plan_type) as plan_types
FROM plans
WHERE state_code = 'TX'
GROUP BY issuer_name
ORDER BY plans DESC;
```

**Texas Market Share:**
1. Blue Cross Blue Shield of Texas: 2,649 plans
2. Oscar Insurance: 577 plans
3. Ambetter from Superior HealthPlan: 174 plans
4. UnitedHealthcare: 157 plans

**Questions We Can Answer:**
- "Show me all Blue Cross plans in Texas"
- "Which issuers offer the most Gold plans?"
- "Compare issuer pricing strategies"

---

### 5. Structured Plan Attributes & Complex Queries ⭐⭐

**HealthSherpa:** Attributes embedded in display, limited filtering

**Our Database:** JSONB attributes enable complex queries

**Example Use Cases:**
```sql
-- "Show HSA-eligible plans with deductible < $5,000"
SELECT plan_id, plan_marketing_name
FROM plans
WHERE (plan_attributes->>'is_hsa_eligible') = 'Yes'
  AND REPLACE(REPLACE(plan_attributes->>'deductible_individual', '$', ''), ',', '')::numeric < 5000;

-- "Plans with zero copay for primary care"
SELECT p.plan_id, b.benefit_name, b.cost_sharing_details
FROM plans p
JOIN benefits b ON p.plan_id = b.plan_id
WHERE b.benefit_name LIKE '%Primary Care%'
  AND b.cost_sharing_details->>'copay_amount' = '0';

-- "Low OOP max plans for chronic conditions"
SELECT plan_id, 
       plan_attributes->>'moop_individual' as oop_max
FROM plans
WHERE REPLACE(REPLACE(plan_attributes->>'moop_individual', '$', ''), ',', '')::numeric < 7000
ORDER BY oop_max;
```

---

### 6. Bulk Analysis & Statistics ⭐⭐⭐

**HealthSherpa:** Manual comparison, one page at a time

**Our Database:** Statistical analysis across thousands of plans

**Example Analysis:**
```sql
-- Average premiums and deductibles by state and metal level
SELECT 
    state_code,
    metal_level,
    COUNT(*) as plans,
    AVG(rate_age_40) as avg_premium,
    AVG(deductible) as avg_deductible
FROM plan_summary_view
GROUP BY state_code, metal_level;
```

**Questions We Can Answer:**
- "What's the average Silver plan premium in Texas?"
- "How do Bronze deductibles compare across states?"
- "Premium trends by metal level"
- "Most/least expensive markets"

---

### 7. Service Area Mapping ⭐

**HealthSherpa:** No visibility into service area structure

**Our Database:** Complete service area to county/ZIP mappings

**Example:**
```sql
-- "Which service area has the most plans?"
SELECT 
    sa.service_area_id,
    sa.service_area_name,
    COUNT(DISTINCT psa.county_fips) as counties,
    COUNT(DISTINCT p.plan_id) as plans
FROM service_areas sa
JOIN plan_service_areas psa ON sa.service_area_id = psa.service_area_id
JOIN plans p ON sa.service_area_id = p.service_area_id
GROUP BY sa.service_area_id, sa.service_area_name;
```

---

### 8-10. Additional Capabilities

**8. Historical/Bulk Export**
- HealthSherpa: Manual screen scraping
- Database: Export entire datasets programmatically

**9. API Integration**
- HealthSherpa: Web UI only
- Database: Full programmatic access for custom apps

**10. Rating Area Analysis**
- HealthSherpa: Premium variation not visible
- Database: Analyze rate differences by geography

---

## Fields We Have That HealthSherpa Doesn't Show

### 1. Complete Age Curves (All Ages)

HealthSherpa shows: One age at a time  
Database has: **All ages 14-120 for every plan**

```
Age 14: $237.49
Age 15: $258.61
...
Age 62: $703.72
Age 63: $738.86
Age 64: $916.45
```

---

### 2. Service Area Metadata

HealthSherpa: Not visible  
Database has:
- `service_area_id`
- `service_area_name`
- `covers_entire_state` (boolean)
- `market_coverage`
- County-to-service-area mappings

**Use:** Understand geographic coverage patterns

---

### 3. Rating Area Relationships

HealthSherpa: Opaque  
Database has:
- ZIP to county mappings (with ratios for multi-county ZIPs)
- County FIPS codes
- Service area to county mappings

**Use:** Rating area analysis, premium variation studies

---

### 4. Issuer Metadata

HealthSherpa shows: Issuer name only  
Database has:
- `issuer_id`
- `issuer_name`
- Customer service phone
- Payment phone
- Website URLs
- Salesforce names

**Use:** Contact information, issuer tracking

---

### 5. Plan Relationships

HealthSherpa: Individual plans  
Database has:
- Plan variant tracking (base plan ID + variants)
- CSR level relationships
- Network tier information

**Use:** Understanding plan families and CSR variations

---

### 6. Structural Data

HealthSherpa: Display-oriented  
Database has:
- Relational structure (plans → rates → benefits)
- Normalized data (no duplication)
- JSONB for flexible attributes
- Indexed for fast queries

**Use:** Efficient querying, data integrity

---

## What HealthSherpa Has That We're Missing

### 1. Family Deductibles & OOP Max ❌

HealthSherpa shows:
- Family Deductible: `$18,900`
- Family OOP Max: `$20,000`

Our database: **MISSING** (only has individual)

**Impact:** Families cannot see true cost-sharing limits

---

### 2. Detailed Benefit Cost-Sharing ❌

HealthSherpa shows:
- Primary Care: `"$35 copay"`
- Emergency Room: `"$500 copay + 30% coinsurance after deductible"`
- Generic Rx: `"$3 copay"`

Our database shows:
- Primary Care: `"Covered"` ⚠️
- Emergency Room: `"Covered"` ⚠️
- Generic Rx: **MISSING** ❌

**Impact:** Users can't see actual out-of-pocket costs

---

### 3. Prescription Drug Tiers (4 Tiers) ❌

HealthSherpa shows:
- Generic: `"$3 copay"`
- Preferred Brand: `"$55 copay after deductible"`
- Non-Preferred: `"$100 copay after deductible"`
- Specialty: `"30% coinsurance after deductible"`

Our database: **COMPLETELY MISSING**

---

### 4. Subsidized Premiums 💡

HealthSherpa shows:
- Gross Premium: `$1,200`
- Your Cost (after subsidy): `$150`

Our database: Only has gross premium

**Note:** This is intentional - subsidies are user-specific, not plan data

---

### 5. Quality Ratings ⚠️

HealthSherpa shows:
- Star ratings
- Quality metrics

Our database: Has `quality` field but may not be populated

---

## Summary: Complementary Strengths

### HealthSherpa Strengths
- ✅ User-friendly UI for individual shopping
- ✅ Real-time subsidy calculations
- ✅ Detailed benefit displays
- ✅ Enrollment integration
- ✅ Family cost aggregation

### Our Database Strengths
- ✅ Multi-age queries (household calculations)
- ✅ Geographic analysis (cross-ZIP comparisons)
- ✅ Market intelligence (issuer analysis)
- ✅ Programmatic access (API)
- ✅ Bulk statistics (market trends)
- ✅ Service area mapping
- ✅ Age curve analysis
- ✅ Rating area research

---

## Use Case Comparison

| Use Case | Best Tool |
|----------|-----------|
| Individual shopping for one plan | HealthSherpa |
| Family premium calculation | **Our Database** |
| Compare plans across ZIP codes | **Our Database** |
| Market research & analysis | **Our Database** |
| Build custom comparison tool | **Our Database** |
| Enroll in a plan | HealthSherpa |
| See subsidy amount | HealthSherpa |
| Bulk data export | **Our Database** |
| Geographic coverage analysis | **Our Database** |
| Issuer market share | **Our Database** |

---

## Value Proposition

**HealthSherpa** = Great consumer shopping experience  
**Our Database** = Powerful analytical & programmatic platform

**We enable questions HealthSherpa cannot answer:**
- "What's the total premium for a family with ages 42, 38, and 15?"
- "Is this plan cheaper in the neighboring ZIP code?"
- "Which insurers dominate the Texas market?"
- "Show all HSA plans with deductible under $5,000"
- "Compare average premiums across all states"
- "Which counties have the fewest plan options?"

**Together:** Comprehensive ACA plan data ecosystem
