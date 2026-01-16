# ACA Benefits SQL Query Examples

**Complete guide with copy-paste ready SQL queries**

---

## Connect to Database

### Using psql (Command Line)

```bash
# Set password
export PGPASSWORD="AvRePOWBfVFZyPsKPPG2tV3r"

# Connect
psql -h aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com \
     -U aca_admin \
     -d aca_plans
```

### Using TablePlus

```
Host: aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com
Port: 5432
User: aca_admin
Password: AvRePOWBfVFZyPsKPPG2tV3r
Database: aca_plans
```

---

## Query 1: Find Plans with Lowest Drug Costs

### Use Case
> "What plans in ZIP 33433 have the lowest generic drug costs?"

### SQL Query

```sql
-- Find plans with lowest generic drug costs
-- Using HealthSherpa plan IDs for ZIP 33433

WITH healthsherpa_plans AS (
    -- Replace these with your HealthSherpa plan IDs
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008', 
        '21525FL0020006', '44228FL0040005', '48121FL0070051',
        '48121FL0070107', '21525FL0020001', '21525FL0020004',
        '44228FL0040001', '21525FL0020005', '44228FL0040007',
        '19898FL0340092', '30252FL0070065', '19898FL0340017',
        '68398FL0090001', '68398FL0030058', '19898FL0340016',
        '21525FL0020003', '54172FL0010010'
    ]) AS base_id
),
matched_plans AS (
    -- Match base IDs to actual plan variants in database
    SELECT 
        p.plan_id, 
        p.plan_marketing_name, 
        p.metal_level,
        p.issuer_name,
        ROW_NUMBER() OVER (
            PARTITION BY SUBSTRING(p.plan_id, 1, 14) 
            ORDER BY p.plan_id
        ) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_id || '%'
)
SELECT 
    mp.plan_id,
    mp.plan_marketing_name,
    mp.issuer_name,
    mp.metal_level,
    b_gen.cost_sharing_details->>'copay_inn_tier1' as generic_copay,
    b_brand.cost_sharing_details->>'copay_inn_tier1' as brand_copay,
    b_npbrand.cost_sharing_details->>'copay_inn_tier1' as non_preferred_brand_copay,
    b_spec.cost_sharing_details->>'coins_inn_tier1' as specialty_coinsurance
FROM matched_plans mp
LEFT JOIN benefits b_gen ON mp.plan_id = b_gen.plan_id 
    AND b_gen.benefit_name = 'Generic Drugs'
    AND b_gen.is_covered = true
LEFT JOIN benefits b_brand ON mp.plan_id = b_brand.plan_id 
    AND b_brand.benefit_name = 'Preferred Brand Drugs'
    AND b_brand.is_covered = true
LEFT JOIN benefits b_npbrand ON mp.plan_id = b_npbrand.plan_id 
    AND b_npbrand.benefit_name = 'Non-Preferred Brand Drugs'
    AND b_npbrand.is_covered = true
LEFT JOIN benefits b_spec ON mp.plan_id = b_spec.plan_id 
    AND b_spec.benefit_name = 'Specialty Drugs'
    AND b_spec.is_covered = true
WHERE mp.rn = 1  -- Only first variant per base plan
ORDER BY 
    NULLIF(REGEXP_REPLACE(
        b_gen.cost_sharing_details->>'copay_inn_tier1', 
        '[^0-9.]', '', 'g'
    ), '')::NUMERIC NULLS LAST
LIMIT 20;
```

### Example Output

```
plan_id              | plan_marketing_name                    | issuer_name  | metal_level      | generic_copay | brand_copay
---------------------|----------------------------------------|--------------|------------------|---------------|------------------
48121FL0070051-00    | Connect myDiabetesCare Bronze Mid-Sou  | Cigna        | Expanded Bronze  | $3.00         | (null)
21525FL0020002-00    | Bronze Classic 4700                    | Oscar        | Expanded Bronze  | $3.00         | (null)
21525FL0020004-00    | Bronze Simple CKM                      | Oscar        | Expanded Bronze  | $3.00         | $75.00 Copay...
```

---

## Query 2: Find Plans with Lowest Out-of-Network Specialist Costs

### Use Case
> "What plans have the lowest out-of-network specialist costs?"

### SQL Query

```sql
-- Find plans with lowest out-of-network specialist costs

WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008', 
        '21525FL0020006', '44228FL0040005', '48121FL0070051',
        '48121FL0070107', '21525FL0020001', '21525FL0020004'
    ]) AS base_id
),
matched_plans AS (
    SELECT 
        p.plan_id, 
        p.plan_marketing_name, 
        p.metal_level,
        p.issuer_name,
        p.plan_type,
        ROW_NUMBER() OVER (
            PARTITION BY SUBSTRING(p.plan_id, 1, 14) 
            ORDER BY p.plan_id
        ) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_id || '%'
)
SELECT 
    mp.plan_id,
    mp.plan_marketing_name,
    mp.issuer_name,
    mp.metal_level,
    mp.plan_type,
    -- In-network costs
    b.cost_sharing_details->>'copay_inn_tier1' as in_network_copay,
    b.cost_sharing_details->>'coins_inn_tier1' as in_network_coinsurance,
    -- Out-of-network costs
    b.cost_sharing_details->>'copay_oon' as out_of_network_copay,
    b.cost_sharing_details->>'coins_oon' as out_of_network_coinsurance,
    b.cost_sharing_details->>'explanation' as explanation
FROM matched_plans mp
LEFT JOIN benefits b ON mp.plan_id = b.plan_id 
    AND b.benefit_name = 'Specialist Visit'
    AND b.is_covered = true
WHERE mp.rn = 1
ORDER BY 
    -- Sort by OON copay first, then OON coinsurance
    NULLIF(REGEXP_REPLACE(
        b.cost_sharing_details->>'copay_oon', 
        '[^0-9.]', '', 'g'
    ), '')::NUMERIC NULLS LAST,
    NULLIF(REGEXP_REPLACE(
        b.cost_sharing_details->>'coins_oon', 
        '[^0-9.]', '', 'g'
    ), '')::NUMERIC NULLS LAST
LIMIT 20;
```

### Example Output

```
plan_id            | metal_level      | in_network_copay | out_of_network_copay | out_of_network_coinsurance
-------------------|------------------|------------------|----------------------|---------------------------
19898FL0340017-00  | Expanded Bronze  | No Charge...     | (null)              | 100.00%
19898FL0340092-00  | Expanded Bronze  | $100.00          | (null)              | 100.00%
21525FL0020001-00  | Expanded Bronze  | $100.00          | (null)              | 100.00%
```

---

## Query 3: Find Plans with Lowest Maximum Out-of-Pocket

### Use Case
> "What plans have the lowest MOOP?"

### SQL Query

```sql
-- Find plans with lowest maximum out-of-pocket costs
-- This uses existing plan_attributes (no benefits table needed)

WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008', 
        '21525FL0020006', '44228FL0040005', '48121FL0070051'
    ]) AS base_id
),
matched_plans AS (
    SELECT 
        p.plan_id, 
        p.plan_marketing_name, 
        p.metal_level,
        p.issuer_name,
        p.plan_type,
        p.plan_attributes,
        ROW_NUMBER() OVER (
            PARTITION BY SUBSTRING(p.plan_id, 1, 14) 
            ORDER BY p.plan_id
        ) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_id || '%'
)
SELECT 
    plan_id,
    plan_marketing_name,
    issuer_name,
    metal_level,
    plan_type,
    plan_attributes->>'deductible_individual' as deductible_individual,
    plan_attributes->>'deductible_family' as deductible_family,
    plan_attributes->>'moop_individual' as moop_individual,
    plan_attributes->>'moop_family' as moop_family,
    plan_attributes->>'is_hsa_eligible' as hsa_eligible
FROM matched_plans
WHERE rn = 1
ORDER BY 
    NULLIF(REGEXP_REPLACE(
        plan_attributes->>'moop_individual', 
        '[^0-9.]', '', 'g'
    ), '')::NUMERIC NULLS LAST
LIMIT 20;
```

### Example Output

```
plan_id            | metal_level      | deductible_individual | moop_individual | hsa_eligible
-------------------|------------------|-----------------------|-----------------|-------------
48121FL0070051-00  | Expanded Bronze  | $6,500               | $9,200         | No
48121FL0070122-00  | Expanded Bronze  | $5,500               | $9,500         | No
19898FL0340092-00  | Expanded Bronze  | $7,500               | $10,000        | No
```

---

## Query 4: Comprehensive Plan Comparison

### Use Case
> "Compare all cost-sharing for specific plans"

### SQL Query

```sql
-- Get comprehensive benefit details for specific plans

SELECT 
    p.plan_id,
    p.plan_marketing_name,
    p.issuer_name,
    p.metal_level,
    b.benefit_name,
    b.is_covered,
    b.cost_sharing_details->>'copay_inn_tier1' as copay_in,
    b.cost_sharing_details->>'copay_oon' as copay_out,
    b.cost_sharing_details->>'coins_inn_tier1' as coinsurance_in,
    b.cost_sharing_details->>'coins_oon' as coinsurance_out
FROM plans p
LEFT JOIN benefits b ON p.plan_id = b.plan_id
WHERE p.plan_id IN (
    '21525FL0020002-00',
    '48121FL0070122-00',
    '44228FL0040008-00'
)
AND b.benefit_name IN (
    'Generic Drugs',
    'Preferred Brand Drugs',
    'Specialty Drugs',
    'Primary Care Visit to Treat an Injury or Illness',
    'Specialist Visit',
    'Emergency Room Services',
    'Urgent Care Centers or Facilities',
    'Outpatient Surgery Physician/Surgical Services'
)
AND b.is_covered = true
ORDER BY p.plan_id, b.benefit_name;
```

---

## Query 5: Find Plans by Usage Pattern

### Use Case
> "What's the cheapest plan for someone who takes 2 generic drugs and sees a specialist monthly?"

### SQL Query

```sql
-- Calculate annual cost for specific usage pattern
-- Assumes: 2 generic drugs (24 fills/year), 12 specialist visits/year

WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008'
    ]) AS base_id
),
matched_plans AS (
    SELECT 
        p.plan_id, 
        p.plan_marketing_name, 
        p.metal_level,
        p.issuer_name,
        p.plan_attributes,
        ROW_NUMBER() OVER (
            PARTITION BY SUBSTRING(p.plan_id, 1, 14) 
            ORDER BY p.plan_id
        ) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_id || '%'
),
benefit_costs AS (
    SELECT 
        mp.plan_id,
        mp.plan_marketing_name,
        mp.metal_level,
        mp.issuer_name,
        -- Extract numeric costs
        COALESCE(
            NULLIF(REGEXP_REPLACE(
                b_gen.cost_sharing_details->>'copay_inn_tier1', 
                '[^0-9.]', '', 'g'
            ), '')::NUMERIC, 0
        ) as generic_copay,
        COALESCE(
            NULLIF(REGEXP_REPLACE(
                b_spec.cost_sharing_details->>'copay_inn_tier1', 
                '[^0-9.]', '', 'g'
            ), '')::NUMERIC, 0
        ) as specialist_copay,
        COALESCE(
            NULLIF(REGEXP_REPLACE(
                mp.plan_attributes->>'deductible_individual', 
                '[^0-9.]', '', 'g'
            ), '')::NUMERIC, 0
        ) as deductible,
        COALESCE(
            NULLIF(REGEXP_REPLACE(
                mp.plan_attributes->>'moop_individual', 
                '[^0-9.]', '', 'g'
            ), '')::NUMERIC, 0
        ) as moop
    FROM matched_plans mp
    LEFT JOIN benefits b_gen ON mp.plan_id = b_gen.plan_id 
        AND b_gen.benefit_name = 'Generic Drugs'
    LEFT JOIN benefits b_spec ON mp.plan_id = b_spec.plan_id 
        AND b_spec.benefit_name = 'Specialist Visit'
    WHERE mp.rn = 1
)
SELECT 
    plan_id,
    plan_marketing_name,
    metal_level,
    issuer_name,
    generic_copay,
    specialist_copay,
    deductible,
    moop,
    -- Calculate estimated annual OOP
    (generic_copay * 24 + specialist_copay * 12) as estimated_annual_oop,
    -- Compare to MOOP
    CASE 
        WHEN (generic_copay * 24 + specialist_copay * 12) > moop 
        THEN moop
        ELSE (generic_copay * 24 + specialist_copay * 12)
    END as capped_annual_oop
FROM benefit_costs
ORDER BY capped_annual_oop
LIMIT 10;
```

### Example Output

```
plan_id            | generic_copay | specialist_copay | estimated_annual_oop | capped_annual_oop
-------------------|---------------|------------------|----------------------|------------------
48121FL0070051-00  | 3.00         | 0.00             | 72.00               | 72.00
21525FL0020002-00  | 3.00         | 125.00           | 1572.00             | 1572.00
```

---

## Query 6: Compare Drug Tiers Across Plans

### Use Case
> "Show me all drug costs (generic, brand, specialty) for these plans"

### SQL Query

```sql
-- Compare drug costs across all tiers

WITH target_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002-00',
        '48121FL0070122-00',
        '44228FL0040008-00'
    ]) AS plan_id
)
SELECT 
    p.plan_id,
    p.plan_marketing_name,
    p.metal_level,
    -- Generic drugs
    b_gen.cost_sharing_details->>'copay_inn_tier1' as generic_copay,
    b_gen.cost_sharing_details->>'coins_inn_tier1' as generic_coinsurance,
    -- Preferred brand
    b_pbrand.cost_sharing_details->>'copay_inn_tier1' as preferred_brand_copay,
    b_pbrand.cost_sharing_details->>'coins_inn_tier1' as preferred_brand_coinsurance,
    -- Non-preferred brand
    b_npbrand.cost_sharing_details->>'copay_inn_tier1' as non_preferred_brand_copay,
    b_npbrand.cost_sharing_details->>'coins_inn_tier1' as non_preferred_brand_coinsurance,
    -- Specialty
    b_spec.cost_sharing_details->>'copay_inn_tier1' as specialty_copay,
    b_spec.cost_sharing_details->>'coins_inn_tier1' as specialty_coinsurance
FROM plans p
JOIN target_plans tp ON p.plan_id = tp.plan_id
LEFT JOIN benefits b_gen ON p.plan_id = b_gen.plan_id 
    AND b_gen.benefit_name = 'Generic Drugs'
LEFT JOIN benefits b_pbrand ON p.plan_id = b_pbrand.plan_id 
    AND b_pbrand.benefit_name = 'Preferred Brand Drugs'
LEFT JOIN benefits b_npbrand ON p.plan_id = b_npbrand.plan_id 
    AND b_npbrand.benefit_name = 'Non-Preferred Brand Drugs'
LEFT JOIN benefits b_spec ON p.plan_id = b_spec.plan_id 
    AND b_spec.benefit_name = 'Specialty Drugs';
```

---

## Query 7: Find All Available Benefits for a Plan

### Use Case
> "What benefits does this plan cover?"

### SQL Query

```sql
-- Show all covered benefits for a specific plan

SELECT 
    benefit_name,
    is_covered,
    cost_sharing_details->>'copay_inn_tier1' as in_network_copay,
    cost_sharing_details->>'copay_oon' as out_of_network_copay,
    cost_sharing_details->>'coins_inn_tier1' as in_network_coinsurance,
    cost_sharing_details->>'coins_oon' as out_of_network_coinsurance,
    cost_sharing_details->>'has_quantity_limit' as has_limit,
    cost_sharing_details->>'limit_quantity' as limit_quantity,
    cost_sharing_details->>'limit_unit' as limit_unit
FROM benefits
WHERE plan_id = '21525FL0020002-00'
  AND is_covered = true
ORDER BY benefit_name;
```

---

## Query 8: Compare Primary Care vs Specialist Costs

### Use Case
> "Show me PCP and specialist costs side-by-side"

### SQL Query

```sql
-- Compare primary care and specialist visit costs

WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008', 
        '21525FL0020006', '44228FL0040005'
    ]) AS base_id
),
matched_plans AS (
    SELECT 
        p.plan_id, 
        p.plan_marketing_name, 
        p.metal_level,
        ROW_NUMBER() OVER (
            PARTITION BY SUBSTRING(p.plan_id, 1, 14) 
            ORDER BY p.plan_id
        ) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_id || '%'
)
SELECT 
    mp.plan_id,
    mp.plan_marketing_name,
    mp.metal_level,
    -- Primary care
    b_pcp.cost_sharing_details->>'copay_inn_tier1' as pcp_in_network,
    b_pcp.cost_sharing_details->>'copay_oon' as pcp_out_of_network,
    -- Specialist
    b_spec.cost_sharing_details->>'copay_inn_tier1' as specialist_in_network,
    b_spec.cost_sharing_details->>'copay_oon' as specialist_out_of_network,
    -- Preventive (usually $0)
    b_prev.cost_sharing_details->>'copay_inn_tier1' as preventive_in_network
FROM matched_plans mp
LEFT JOIN benefits b_pcp ON mp.plan_id = b_pcp.plan_id 
    AND b_pcp.benefit_name = 'Primary Care Visit to Treat an Injury or Illness'
LEFT JOIN benefits b_spec ON mp.plan_id = b_spec.plan_id 
    AND b_spec.benefit_name = 'Specialist Visit'
LEFT JOIN benefits b_prev ON mp.plan_id = b_prev.plan_id 
    AND b_prev.benefit_name = 'Preventive Care/Screening/Immunization'
WHERE mp.rn = 1
ORDER BY mp.metal_level, mp.plan_id;
```

---

## Query 9: Emergency & Urgent Care Costs

### Use Case
> "Compare ER and urgent care costs"

### SQL Query

```sql
-- Compare emergency room and urgent care costs

WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008'
    ]) AS base_id
),
matched_plans AS (
    SELECT 
        p.plan_id, 
        p.plan_marketing_name, 
        p.metal_level,
        p.plan_attributes,
        ROW_NUMBER() OVER (
            PARTITION BY SUBSTRING(p.plan_id, 1, 14) 
            ORDER BY p.plan_id
        ) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_id || '%'
)
SELECT 
    mp.plan_id,
    mp.plan_marketing_name,
    mp.metal_level,
    mp.plan_attributes->>'deductible_individual' as deductible,
    -- Emergency room
    b_er.cost_sharing_details->>'copay_inn_tier1' as er_copay,
    b_er.cost_sharing_details->>'coins_inn_tier1' as er_coinsurance,
    -- Urgent care
    b_uc.cost_sharing_details->>'copay_inn_tier1' as urgent_care_copay,
    b_uc.cost_sharing_details->>'coins_inn_tier1' as urgent_care_coinsurance,
    -- Ambulance
    b_amb.cost_sharing_details->>'copay_inn_tier1' as ambulance_copay,
    b_amb.cost_sharing_details->>'coins_inn_tier1' as ambulance_coinsurance
FROM matched_plans mp
LEFT JOIN benefits b_er ON mp.plan_id = b_er.plan_id 
    AND b_er.benefit_name = 'Emergency Room Services'
LEFT JOIN benefits b_uc ON mp.plan_id = b_uc.plan_id 
    AND b_uc.benefit_name = 'Urgent Care Centers or Facilities'
LEFT JOIN benefits b_amb ON mp.plan_id = b_amb.plan_id 
    AND b_amb.benefit_name = 'Emergency Transportation/Ambulance'
WHERE mp.rn = 1
ORDER BY mp.plan_id;
```

---

## Query 10: Hospital Stay Costs

### Use Case
> "What are the hospital costs if I need surgery?"

### SQL Query

```sql
-- Hospital and surgery costs

SELECT 
    p.plan_id,
    p.plan_marketing_name,
    p.metal_level,
    p.plan_attributes->>'deductible_individual' as deductible,
    p.plan_attributes->>'moop_individual' as moop,
    -- Inpatient hospital
    b_hosp_fac.cost_sharing_details->>'copay_inn_tier1' as hospital_facility_copay,
    b_hosp_fac.cost_sharing_details->>'coins_inn_tier1' as hospital_facility_coinsurance,
    b_hosp_phys.cost_sharing_details->>'copay_inn_tier1' as hospital_physician_copay,
    b_hosp_phys.cost_sharing_details->>'coins_inn_tier1' as hospital_physician_coinsurance,
    -- Outpatient surgery
    b_surg_fac.cost_sharing_details->>'copay_inn_tier1' as outpatient_surgery_facility_copay,
    b_surg_fac.cost_sharing_details->>'coins_inn_tier1' as outpatient_surgery_facility_coinsurance,
    b_surg_phys.cost_sharing_details->>'copay_inn_tier1' as outpatient_surgery_physician_copay,
    b_surg_phys.cost_sharing_details->>'coins_inn_tier1' as outpatient_surgery_physician_coinsurance
FROM plans p
LEFT JOIN benefits b_hosp_fac ON p.plan_id = b_hosp_fac.plan_id 
    AND b_hosp_fac.benefit_name = 'Inpatient Hospital Services (e.g., Hospital Stay)'
LEFT JOIN benefits b_hosp_phys ON p.plan_id = b_hosp_phys.plan_id 
    AND b_hosp_phys.benefit_name = 'Inpatient Physician and Surgical Services'
LEFT JOIN benefits b_surg_fac ON p.plan_id = b_surg_fac.plan_id 
    AND b_surg_fac.benefit_name = 'Outpatient Facility Fee (e.g., Ambulatory Surgery Center)'
LEFT JOIN benefits b_surg_phys ON p.plan_id = b_surg_phys.plan_id 
    AND b_surg_phys.benefit_name = 'Outpatient Surgery Physician/Surgical Services'
WHERE p.plan_id IN (
    '21525FL0020002-00',
    '48121FL0070122-00',
    '44228FL0040008-00'
);
```

---

## Useful Helper Queries

### List All Available Benefit Types

```sql
-- See what benefit types are available
SELECT DISTINCT benefit_name 
FROM benefits 
ORDER BY benefit_name;
```

### Count Plans by Metal Level

```sql
-- See plan distribution
SELECT 
    metal_level, 
    COUNT(*) as plan_count,
    COUNT(DISTINCT issuer_id) as issuer_count
FROM plans 
WHERE state_code = 'FL'
GROUP BY metal_level 
ORDER BY plan_count DESC;
```

### Find Plans by Issuer

```sql
-- See all plans from a specific carrier
SELECT 
    plan_id,
    plan_marketing_name,
    metal_level,
    plan_type
FROM plans
WHERE issuer_name LIKE '%Oscar%'
  AND state_code = 'FL'
ORDER BY metal_level, plan_marketing_name;
```

### Check Benefit Coverage Percentage

```sql
-- See what % of plans cover each benefit
SELECT 
    benefit_name,
    COUNT(*) as total_plans,
    SUM(CASE WHEN is_covered THEN 1 ELSE 0 END) as covered_plans,
    ROUND(
        100.0 * SUM(CASE WHEN is_covered THEN 1 ELSE 0 END) / COUNT(*), 
        1
    ) as coverage_pct
FROM benefits
GROUP BY benefit_name
HAVING SUM(CASE WHEN is_covered THEN 1 ELSE 0 END) > 0
ORDER BY coverage_pct DESC, benefit_name
LIMIT 30;
```

---

## Tips & Tricks

### 1. Handling Plan Variants

HealthSherpa shows base plan IDs (14 chars), but database has variants (`-00`, `-01`):

```sql
-- Match base ID to all variants
WHERE p.plan_id LIKE '21525FL0020002%'

-- Or get just first variant
ROW_NUMBER() OVER (PARTITION BY SUBSTRING(p.plan_id, 1, 14) ORDER BY p.plan_id)
```

### 2. Extracting Numeric Values

Cost fields are stored as strings with formatting (`$5,000`, `50%`):

```sql
-- Convert to numeric for sorting/math
NULLIF(REGEXP_REPLACE(
    cost_sharing_details->>'copay_inn_tier1', 
    '[^0-9.]', '', 'g'
), '')::NUMERIC
```

### 3. Dealing with NULL vs Empty

Some plans have `NULL`, others have empty strings or "Not Applicable":

```sql
-- Handle all cases
COALESCE(
    NULLIF(cost_sharing_details->>'copay_inn_tier1', ''),
    NULLIF(cost_sharing_details->>'copay_inn_tier1', 'Not Applicable'),
    '0'
)
```

### 4. Performance Optimization

Use EXPLAIN ANALYZE to check query performance:

```sql
EXPLAIN ANALYZE
SELECT ...
```

Our indexes optimize these patterns:
- `WHERE plan_id = 'X'` - very fast
- `WHERE benefit_name = 'X'` - very fast  
- `WHERE plan_id LIKE 'base%'` - fast with base_id index
- JSONB field access - fast with GIN index

---

## Common Benefit Names

```
Generic Drugs
Preferred Brand Drugs
Non-Preferred Brand Drugs
Specialty Drugs
Primary Care Visit to Treat an Injury or Illness
Specialist Visit
Preventive Care/Screening/Immunization
Emergency Room Services
Urgent Care Centers or Facilities
Emergency Transportation/Ambulance
Inpatient Hospital Services (e.g., Hospital Stay)
Inpatient Physician and Surgical Services
Outpatient Facility Fee (e.g., Ambulatory Surgery Center)
Outpatient Surgery Physician/Surgical Services
Mental/Behavioral Health Outpatient Services
Mental/Behavioral Health Inpatient Services
Substance Abuse Disorder Outpatient Services
Substance Abuse Disorder Inpatient Services
Durable Medical Equipment
Imaging (CT/PET Scans, MRIs)
Laboratory Outpatient and Professional Services
X-rays and Diagnostic Imaging
Physical Therapy
Occupational Therapy
Speech Therapy
Cardiac Rehabilitation
Pulmonary Rehabilitation
Skilled Nursing Facility
Home Health Care Services
Hospice Services
```

---

## Need Help?

**Check query performance:**
```sql
\timing on
-- Run your query
```

**View slow queries:**
```sql
SELECT * FROM pg_stat_statements 
ORDER BY total_exec_time DESC 
LIMIT 10;
```

**Database stats:**
```sql
SELECT 
    'Benefits' as table_name,
    COUNT(*) as rows,
    pg_size_pretty(pg_total_relation_size('benefits')) as total_size
FROM benefits
UNION ALL
SELECT 
    'Plans',
    COUNT(*),
    pg_size_pretty(pg_total_relation_size('plans'))
FROM plans;
```
