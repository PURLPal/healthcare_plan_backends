# ACA Database Query Examples

Complete guide to querying the ACA plans database with real-world examples.

---

## Table of Contents
1. [Basic Rate Queries](#basic-rate-queries)
2. [Benefits Queries](#benefits-queries)
3. [Geographic Queries](#geographic-queries)
4. [Complex Multi-Table Queries](#complex-multi-table-queries)
5. [Performance Tips](#performance-tips)

---

## Database Summary

**Tables:**
- `plans` (20,354 records) - main plan information
- `rates` (202,200 records) - age-based monthly premiums
- `benefits` (1,421,810 records) - detailed cost-sharing for 234 benefit types
- `counties`, `zip_counties`, `service_areas`, `plan_service_areas` - geographic data

**Key Facts:**
- Only **-01 variant plans** have rates loaded (4,044 plans = 19.9% of all plans)
- Each plan has **50 age bands** (ages 14-63)
- Each plan has **~70 benefit records** on average
- Benefits use **JSONB** for flexible cost-sharing details that vary by benefit type

---

## Basic Rate Queries

### 1. Get monthly premium for specific plan and age

```sql
SELECT 
    p.plan_marketing_name,
    p.metal_level,
    r.individual_rate as monthly_premium
FROM plans p
JOIN rates r ON p.plan_id = r.plan_id
WHERE p.plan_id = '96751NH0150024-01'  -- Must be -01 variant
  AND r.age = 40;
```

**Result:**
```
plan_marketing_name                    | metal_level   | monthly_premium
---------------------------------------|---------------|----------------
Anthem Catastrophic Pathway X Enhanced | Catastrophic  | 277.59
```

---

### 2. Find cheapest plans in a state at specific age

```sql
SELECT 
    p.plan_marketing_name,
    p.metal_level,
    p.plan_type,
    r.individual_rate as monthly_premium
FROM plans p
JOIN rates r ON p.plan_id = r.plan_id
WHERE p.state_code = 'NH'
  AND r.age = 40
ORDER BY r.individual_rate
LIMIT 10;
```

**Use cases:**
- Show cheapest options for a ZIP code
- Compare plans by price
- Filter by metal level: `AND p.metal_level = 'Bronze'`

---

### 3. Compare premiums across age ranges for one plan

```sql
SELECT 
    r.age,
    r.individual_rate as monthly_premium,
    r.individual_rate * 12 as annual_premium
FROM rates r
WHERE r.plan_id = '96751NH0150024-01'
  AND r.age IN (21, 30, 40, 50, 60)
ORDER BY r.age;
```

**Result:**
```
age | monthly_premium | annual_premium
----|-----------------|---------------
21  |          217.21 |        2606.52
30  |          246.53 |        2958.36
40  |          277.59 |        3331.08
50  |          387.94 |        4655.28
60  |          589.51 |        7074.12
```

**Shows:** How premiums increase with age (ACA allows up to 3:1 age rating)

---

### 4. Average premium by metal level at age 40

```sql
SELECT 
    p.metal_level,
    COUNT(DISTINCT p.plan_id) as plan_count,
    MIN(r.individual_rate) as min_premium,
    AVG(r.individual_rate) as avg_premium,
    MAX(r.individual_rate) as max_premium
FROM plans p
JOIN rates r ON p.plan_id = r.plan_id
WHERE r.age = 40
GROUP BY p.metal_level
ORDER BY avg_premium;
```

**Result:**
```
metal_level      | plan_count | min_premium | avg_premium | max_premium
-----------------|------------|-------------|-------------|------------
Catastrophic     |         75 |      277.59 |      496.11 |      913.02
Bronze           |        144 |      345.23 |      534.99 |      875.25
Expanded Bronze  |      1,156 |      316.89 |      561.54 |     1084.48
Silver           |      1,453 |      388.00 |      752.16 |     1460.12
Gold             |      1,172 |      416.60 |      770.90 |     1455.08
Platinum         |         44 |      608.22 |     1235.15 |     1858.71
```

---

### 5. State-by-state price comparison at age 40

```sql
SELECT 
    p.state_code,
    COUNT(DISTINCT p.plan_id) as plan_count,
    MIN(r.individual_rate) as cheapest,
    AVG(r.individual_rate) as avg_premium,
    MAX(r.individual_rate) as most_expensive
FROM plans p
JOIN rates r ON p.plan_id = r.plan_id
WHERE r.age = 40
GROUP BY p.state_code
ORDER BY avg_premium
LIMIT 10;
```

**Shows:** Which states have cheapest/most expensive insurance

---

## Benefits Queries

### 6. Get all benefits for a specific plan

```sql
SELECT 
    benefit_name,
    is_covered,
    cost_sharing_details
FROM benefits
WHERE plan_id = '96751NH0150024-01'
ORDER BY benefit_name;
```

**Result (sample):**
```
benefit_name              | is_covered | cost_sharing_details
------------------------------|------------|---------------------
Primary Care Visit            | true       | {"copay_inn_tier1": "$25.00", "coins_oon": "60.00%"}
Specialist Visit              | true       | {"copay_inn_tier1": "$60.00", "coins_oon": "60.00%"}
Emergency Room Services       | true       | {"copay_inn_tier1": "$300.00", "coins_inn_tier1": "30.00%"}
Generic Drugs                 | true       | {"copay_inn_tier1": "$15.00", "coins_oon": "0.00%"}
```

---

### 7. Get specific benefit cost-sharing (e.g., specialist copay)

```sql
SELECT 
    p.plan_marketing_name,
    b.cost_sharing_details->>'copay_inn_tier1' as specialist_copay,
    b.cost_sharing_details->>'coins_inn_tier1' as specialist_coinsurance
FROM plans p
JOIN benefits b ON p.plan_id = b.plan_id
WHERE b.benefit_name = 'Specialist Visit'
  AND p.state_code = 'NH'
ORDER BY specialist_copay;
```

**JSONB operator:** `->>` extracts text value from JSON key

---

### 8. Find plans with $0 primary care copay

```sql
SELECT 
    p.state_code,
    p.plan_marketing_name,
    p.metal_level,
    b.cost_sharing_details->>'copay_inn_tier1' as pcp_copay
FROM plans p
JOIN benefits b ON p.plan_id = b.plan_id
WHERE b.benefit_name = 'Primary Care Visit'
  AND b.cost_sharing_details->>'copay_inn_tier1' = '$0.00'
LIMIT 20;
```

---

### 9. Compare drug costs across plans

```sql
SELECT 
    p.plan_marketing_name,
    p.metal_level,
    b.cost_sharing_details->>'copay_inn_tier1' as generic_copay,
    b.cost_sharing_details->>'coins_inn_tier1' as generic_coinsurance
FROM plans p
JOIN benefits b ON p.plan_id = b.plan_id
WHERE b.benefit_name = 'Generic Drugs'
  AND p.state_code = 'FL'
ORDER BY generic_copay
LIMIT 20;
```

---

### 10. Get ER copay for a plan

```sql
SELECT 
    cost_sharing_details->>'copay_inn_tier1' as er_copay,
    cost_sharing_details->>'coins_inn_tier1' as er_coinsurance,
    cost_sharing_details->>'explanation' as details
FROM benefits
WHERE plan_id = '96751NH0150024-01'
  AND benefit_name = 'Emergency Room Services';
```

**Common ER cost structures:**
- Copay only: `{"copay_inn_tier1": "$300.00"}`
- Coinsurance only: `{"coins_inn_tier1": "30.00% Coinsurance after deductible"}`
- Both: `{"copay_inn_tier1": "$300.00", "coins_inn_tier1": "30.00%"}`

---

## Understanding JSONB Cost Sharing

### Why JSONB?

Different benefit types have **completely different** cost structures:

**Generic Drugs keys:**
- `copay_inn_tier1`, `copay_inn_tier2` (multi-tier drug pricing)
- `coins_inn_tier1`, `coins_oon`
- `explanation`, `exclusions`
- `limit_unit`, `limit_quantity`, `has_quantity_limit`

**Specialist Visit keys:**
- `copay_inn_tier1` (simpler - just one tier)
- `coins_oon`
- `explanation`

**Emergency Room keys:**
- `copay_inn_tier1`, `copay_oon`
- `coins_inn_tier1`, `coins_oon`

### Common JSONB Keys

**Copay keys:** (dollar amounts)
- `copay_inn_tier1` - In-network tier 1 copay: `"$25.00"`
- `copay_inn_tier2` - In-network tier 2 copay: `"$50.00"`
- `copay_oon` - Out-of-network copay: `"$100.00"`

**Coinsurance keys:** (percentages)
- `coins_inn_tier1` - In-network coinsurance: `"30.00% Coinsurance after deductible"`
- `coins_oon` - Out-of-network coinsurance: `"60.00%"`

**Metadata keys:**
- `explanation` - Long text describing coverage
- `exclusions` - What's not covered
- `limit_unit` - "Days per Month", "Item(s) per Month"
- `limit_quantity` - "90.0", "30.0"

### Querying JSONB

```sql
-- Extract single field
SELECT cost_sharing_details->>'copay_inn_tier1' FROM benefits;

-- Check if key exists
SELECT * FROM benefits WHERE cost_sharing_details ? 'copay_inn_tier1';

-- Filter by JSONB value
SELECT * FROM benefits 
WHERE cost_sharing_details->>'copay_inn_tier1' = '$0.00';

-- Get all keys for a benefit type
SELECT DISTINCT jsonb_object_keys(cost_sharing_details)
FROM benefits
WHERE benefit_name = 'Generic Drugs';
```

---

## Combined Rate + Benefit Queries

### 11. Find cheapest plan with specific benefit coverage

```sql
SELECT 
    p.plan_marketing_name,
    p.metal_level,
    r.individual_rate as monthly_premium,
    b.cost_sharing_details->>'copay_inn_tier1' as specialist_copay
FROM plans p
JOIN rates r ON p.plan_id = r.plan_id
JOIN benefits b ON p.plan_id = b.plan_id
WHERE p.state_code = 'NH'
  AND r.age = 40
  AND b.benefit_name = 'Specialist Visit'
  AND b.is_covered = true
ORDER BY r.individual_rate
LIMIT 10;
```

**Shows:** Cheapest plans that cover specialist visits

---

### 12. Total monthly cost estimate (premium + typical copays)

```sql
WITH plan_costs AS (
  SELECT 
    p.plan_id,
    p.plan_marketing_name,
    r.individual_rate as monthly_premium,
    (SELECT cost_sharing_details->>'copay_inn_tier1' 
     FROM benefits 
     WHERE plan_id = p.plan_id AND benefit_name = 'Primary Care Visit') as pcp_copay,
    (SELECT cost_sharing_details->>'copay_inn_tier1' 
     FROM benefits 
     WHERE plan_id = p.plan_id AND benefit_name = 'Generic Drugs') as drug_copay
  FROM plans p
  JOIN rates r ON p.plan_id = r.plan_id
  WHERE p.state_code = 'NH' AND r.age = 40
)
SELECT 
  plan_marketing_name,
  monthly_premium,
  pcp_copay,
  drug_copay
FROM plan_costs
ORDER BY monthly_premium
LIMIT 10;
```

---

## Geographic Queries

### 13. Find plans available in a ZIP code

```sql
SELECT DISTINCT
    p.plan_id,
    p.plan_marketing_name,
    p.metal_level,
    p.plan_type
FROM zip_counties zc
JOIN plan_service_areas psa ON zc.county_fips = psa.county_fips
JOIN plans p ON psa.service_area_id = p.service_area_id 
            AND psa.state_code = p.state_code
WHERE zc.zip_code = '33433'  -- Boca Raton, FL
ORDER BY p.plan_marketing_name;
```

**Note:** This is a 4-table join (most complex query pattern)

---

### 14. Plans available in ZIP with rates at age 40

```sql
SELECT DISTINCT
    p.plan_id,
    p.plan_marketing_name,
    p.metal_level,
    r.individual_rate as monthly_premium
FROM zip_counties zc
JOIN plan_service_areas psa ON zc.county_fips = psa.county_fips
JOIN plans p ON psa.service_area_id = p.service_area_id 
            AND psa.state_code = p.state_code
JOIN rates r ON p.plan_id = r.plan_id
WHERE zc.zip_code = '33433'
  AND r.age = 40
ORDER BY r.individual_rate
LIMIT 20;
```

---

## Performance Tips

### Indexes to Use

**Fast lookups (all indexed):**
- `plans.plan_id` (PK)
- `plans.state_code`
- `plans.metal_level`
- `rates(plan_id, age)` (PK)
- `benefits(plan_id, benefit_name)` (PK)

**Query patterns:**
- ✅ **Fast:** Filter by `plan_id`, `state_code`, `metal_level`, specific age
- ✅ **Fast:** Join `plans` → `rates` on `plan_id`
- ✅ **Fast:** Join `plans` → `benefits` on `plan_id`
- ⚠️ **Slower:** JSONB field filtering (not fully indexed)
- ⚠️ **Slower:** ZIP code queries (4-table join)

### Best Practices

1. **Always filter by age when querying rates**
   ```sql
   WHERE r.age = 40  -- Don't pull all 50 ages unless needed
   ```

2. **Use LIMIT for exploratory queries**
   ```sql
   LIMIT 100  -- Prevents accidental full table scans
   ```

3. **Filter by state_code early**
   ```sql
   WHERE p.state_code = 'FL'  -- Reduces result set quickly
   ```

4. **Use specific benefit_name lookups**
   ```sql
   WHERE b.benefit_name = 'Specialist Visit'  -- Indexed
   ```

5. **Prefer plan_id lookups when possible**
   ```sql
   WHERE p.plan_id = '96751NH0150024-01'  -- Fastest (PK lookup)
   ```

---

## Common Use Cases

### Use Case 1: "Show me the cheapest Bronze plans in Florida for a 35-year-old"

```sql
SELECT 
    p.plan_marketing_name,
    p.plan_type,
    r.individual_rate as monthly_premium
FROM plans p
JOIN rates r ON p.plan_id = r.plan_id
WHERE p.state_code = 'FL'
  AND p.metal_level = 'Bronze'
  AND r.age = 35
ORDER BY r.individual_rate
LIMIT 10;
```

---

### Use Case 2: "What's the specialist copay for this plan?"

```sql
SELECT 
    cost_sharing_details->>'copay_inn_tier1' as specialist_copay
FROM benefits
WHERE plan_id = '21525FL0020002-01'
  AND benefit_name = 'Specialist Visit';
```

---

### Use Case 3: "Compare monthly premiums across ages for one plan"

```sql
SELECT 
    age,
    individual_rate as monthly_premium,
    individual_rate * 12 as annual_cost
FROM rates
WHERE plan_id = '21525FL0020002-01'
ORDER BY age;
```

---

### Use Case 4: "Find plans with low drug copays and premiums under $500"

```sql
SELECT 
    p.plan_marketing_name,
    r.individual_rate as monthly_premium,
    b.cost_sharing_details->>'copay_inn_tier1' as generic_copay
FROM plans p
JOIN rates r ON p.plan_id = r.plan_id
JOIN benefits b ON p.plan_id = b.plan_id
WHERE p.state_code = 'TX'
  AND r.age = 40
  AND r.individual_rate < 500
  AND b.benefit_name = 'Generic Drugs'
  AND (b.cost_sharing_details->>'copay_inn_tier1')::text ~ '^\$[0-9]{1,2}\.00$'  -- $0-$99
ORDER BY r.individual_rate;
```

---

## Data Completeness Notes

**What's loaded:**
- ✅ All 20,354 plans (all variants: -00, -01, -02, -03, -04, -05, -06)
- ✅ Rates for **4,044 plans** (only -01 variants = 19.9% of plans)
- ✅ Benefits for **all 20,354 plans** (all variants)

**Querying rates:**
```sql
-- ✅ This works (plan has -01 variant)
SELECT * FROM rates WHERE plan_id = '96751NH0150024-01';

-- ❌ This returns nothing (plan is -00 variant, no rates loaded)
SELECT * FROM rates WHERE plan_id = '96751NH0150024-00';
```

**To find which plans have rates:**
```sql
SELECT COUNT(*) FROM plans WHERE plan_id LIKE '%-01';  -- 4,044 plans
SELECT COUNT(DISTINCT plan_id) FROM rates;             -- 4,044 plans
```

---

## Summary

**Simple Queries (1-2 tables):**
- Premium lookup: `plans` + `rates`
- Benefit lookup: `plans` + `benefits`
- Fast, indexed, production-ready

**Complex Queries (3-4 tables):**
- ZIP code availability: `zip_counties` → `plan_service_areas` → `plans` → `rates`
- Slower but still performant with proper indexing

**JSONB Flexibility:**
- Benefits have varying cost structures
- Use `->` for JSON objects, `->>` for text values
- Common pattern: `cost_sharing_details->>'copay_inn_tier1'`
