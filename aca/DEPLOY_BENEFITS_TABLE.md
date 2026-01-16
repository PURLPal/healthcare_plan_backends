# Deploy Benefits Table - Complete Guide

**Status:** ✅ Ready to Deploy  
**Impact:** Enables drug cost, specialist cost, and out-of-network queries  
**Time:** ~45 minutes (30 min processing + 15 min validation)

---

## What This Unlocks

### Before (Current State)
```sql
-- ❌ Only basic cost-sharing
plan_attributes = {
  "deductible_individual": "$5,500",
  "moop_individual": "$9,200"
}
```

### After (With Benefits Table)
```sql
-- ✅ All detailed benefits
SELECT * FROM benefits WHERE plan_id = '21525FL0020002-00';

-- Returns 60+ benefit types:
GenericDrugs: {"copay_inn_tier1": "$10", "copay_oon": "$50"}
SpecialistVisit: {"copay_inn_tier1": "$50", "copay_oon": "50%"}
EmergencyRoom: {"copay_inn_tier1": "$500"}
PrimaryCare: {"copay_inn_tier1": "$0"}
+ 56 more benefits
```

---

## Pre-Deployment Checklist

**Files Required:**
- ✅ `data/raw/benefits-and-cost-sharing-puf.csv` (downloaded, 1.4M rows)
- ✅ `database/load_data.py` (updated with load_benefits())
- ✅ `test_benefits_loader.py` (validation passed)

**Database:**
- ✅ Benefits table exists in schema
- ✅ Database credentials available
- ✅ ~5 GB free space for benefits data

---

## Deployment Steps

### Step 1: Test Locally (Optional but Recommended)

**If you have a local PostgreSQL instance:**

```bash
# Create local test database
createdb aca_plans_test

# Load schema
psql aca_plans_test < database/schema.sql

# Test with sample data (first 1000 plans)
# Edit load_data.py temporarily to limit row processing
python3 database/load_data.py "host=localhost dbname=aca_plans_test user=$USER"
```

**Skip this step if testing directly on RDS.**

---

### Step 2: Deploy to RDS (Production)

**Time: ~45 minutes**

```bash
cd /Users/andy/healthcare_plan_backends/aca

# Get database password
DB_PASSWORD=$(cat /Users/andy/aca_overview_test/.db_password)

# Run full data load (includes benefits)
python3 database/load_data.py \
  "host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com \
   dbname=aca_plans user=aca_admin password=$DB_PASSWORD"
```

**Expected Output:**
```
============================================================
ACA Plan Data Loader
============================================================
Started: 2026-01-16 14:30:00

Connecting to database...
✓ Connected

=== Loading Counties and ZIP Mapping ===
Loading county reference data...
Inserting 3,221 counties...
Loading ZIP-to-county mapping...
Inserting 73,845 ZIP-county mappings...
✓ Loaded 3,221 counties, 73,845 ZIP mappings

=== Loading Service Areas ===
Inserting 1,247 service areas...
Inserting 12,458 plan-service area mappings...
✓ Loaded 1,247 service areas with full county coverage

=== Loading Plans ===
Inserting 20,354 plans...
✓ Loaded 20,354 plans

=== Loading Rates ===
Found 20,354 valid plan IDs
Processing rate file...
Inserting 1,234,567 rate records...
✓ Loaded 1,234,567 rate records

=== Loading Benefits ===
Found 20,354 valid plan IDs
Processing benefits file...
  Processed 100,000 rows (85,234 matched, 14,766 skipped)...
  Processed 200,000 rows (171,456 matched, 28,544 skipped)...
  ...
  Processed 1,400,000 rows (1,198,765 matched, 201,235 skipped)...

Inserting 1,198,765 benefit records...
✓ Loaded 1,198,765 benefit records (1,198,765 matched, 201,235 skipped)

=== Database Summary ===
Counties: 3,221
ZIP Codes: 39,298
Service Areas: 1,247
Plans: 20,354
Rates: 1,234,567
Benefits: 1,198,765
States with Plans: 30

Plans by Metal Level:
  Expanded Bronze: 8,234
  Silver: 5,678
  Gold: 3,456
  Bronze: 2,345
  Platinum: 641

Top 10 Benefits by Coverage:
  Primary Care Visit to Treat an Injury or Illness: 19,234 plans
  Specialist Visit: 19,234 plans
  Generic Drugs: 19,178 plans
  Emergency Room Services: 19,234 plans
  Preventive Care/Screening/Immunization: 19,234 plans
  ...

✓ Data load complete! (2026-01-16 15:15:00)
```

---

### Step 3: Verify Benefits Data

**Connect to database:**
```bash
# Using psql
psql "host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com \
     dbname=aca_plans user=aca_admin password=$DB_PASSWORD"
```

**Run verification queries:**

```sql
-- Check total benefits loaded
SELECT COUNT(*) FROM benefits;
-- Expected: ~1.2M records

-- Check unique benefit types
SELECT COUNT(DISTINCT benefit_name) FROM benefits;
-- Expected: ~60-70 unique benefits

-- Check coverage for key benefits
SELECT benefit_name, COUNT(*) as plan_count
FROM benefits
WHERE is_covered = true
  AND benefit_name IN (
    'Generic Drugs',
    'Specialist Visit',
    'Emergency Room Services'
  )
GROUP BY benefit_name;
-- Expected: ~19K-20K plans for each

-- Check sample plan benefits
SELECT plan_id, benefit_name, 
       cost_sharing_details->>'copay_inn_tier1' as copay_in,
       cost_sharing_details->>'copay_oon' as copay_out
FROM benefits
WHERE plan_id = '21525FL0020002-00'
  AND benefit_name IN ('Generic Drugs', 'Specialist Visit')
ORDER BY benefit_name;
-- Should return cost-sharing details
```

---

### Step 4: Test Your 3 Queries

Now you can run the queries you originally asked about!

#### Query 1: Lowest Drug Costs

```sql
WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008',
        '21525FL0020006', '44228FL0040005', '48121FL0070051'
    ]) AS base_id
),
matched_plans AS (
    SELECT p.plan_id, p.plan_marketing_name, p.metal_level,
           ROW_NUMBER() OVER (PARTITION BY SUBSTRING(p.plan_id, 1, 14) 
                              ORDER BY p.plan_id) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_id || '%'
)
SELECT 
    mp.plan_id,
    mp.plan_marketing_name,
    mp.metal_level,
    b_gen.cost_sharing_details->>'copay_inn_tier1' as generic_copay,
    b_brand.cost_sharing_details->>'copay_inn_tier1' as brand_copay,
    b_spec.cost_sharing_details->>'coins_inn_tier1' as specialty_coinsurance
FROM matched_plans mp
LEFT JOIN benefits b_gen ON mp.plan_id = b_gen.plan_id 
    AND b_gen.benefit_name = 'Generic Drugs'
LEFT JOIN benefits b_brand ON mp.plan_id = b_brand.plan_id 
    AND b_brand.benefit_name = 'Preferred Brand Drugs'
LEFT JOIN benefits b_spec ON mp.plan_id = b_spec.plan_id 
    AND b_spec.benefit_name = 'Specialty Drugs'
WHERE mp.rn = 1
ORDER BY 
    NULLIF(REGEXP_REPLACE(b_gen.cost_sharing_details->>'copay_inn_tier1', '[^0-9.]', '', 'g'), '')::NUMERIC NULLS LAST
LIMIT 10;
```

#### Query 2: Lowest Out-of-Network Specialist Costs

```sql
WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008',
        '21525FL0020006', '44228FL0040005', '48121FL0070051'
    ]) AS base_id
),
matched_plans AS (
    SELECT p.plan_id, p.plan_marketing_name, p.metal_level,
           ROW_NUMBER() OVER (PARTITION BY SUBSTRING(p.plan_id, 1, 14) 
                              ORDER BY p.plan_id) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_id || '%'
)
SELECT 
    mp.plan_id,
    mp.plan_marketing_name,
    mp.metal_level,
    b.cost_sharing_details->>'copay_inn_tier1' as specialist_in_copay,
    b.cost_sharing_details->>'copay_oon' as specialist_oon_copay,
    b.cost_sharing_details->>'coins_inn_tier1' as specialist_in_coinsurance,
    b.cost_sharing_details->>'coins_oon' as specialist_oon_coinsurance
FROM matched_plans mp
LEFT JOIN benefits b ON mp.plan_id = b.plan_id 
    AND b.benefit_name = 'Specialist Visit'
WHERE mp.rn = 1
ORDER BY 
    NULLIF(REGEXP_REPLACE(b.cost_sharing_details->>'copay_oon', '[^0-9.]', '', 'g'), '')::NUMERIC NULLS LAST,
    NULLIF(REGEXP_REPLACE(b.cost_sharing_details->>'coins_oon', '[^0-9.]', '', 'g'), '')::NUMERIC NULLS LAST
LIMIT 10;
```

#### Query 3: Lowest Maximum Out-of-Pocket (Still Works)

```sql
-- This query already works with current data
WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008'
    ]) AS base_id
),
matched_plans AS (
    SELECT p.*, 
           ROW_NUMBER() OVER (PARTITION BY SUBSTRING(p.plan_id, 1, 14) 
                              ORDER BY p.plan_id) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_id || '%'
)
SELECT 
    plan_id,
    plan_marketing_name,
    metal_level,
    plan_attributes->>'moop_individual' as moop,
    plan_attributes->>'deductible_individual' as deductible
FROM matched_plans
WHERE rn = 1
ORDER BY NULLIF(REGEXP_REPLACE(plan_attributes->>'moop_individual', '[^0-9.]', '', 'g'), '')::NUMERIC
LIMIT 10;
```

---

### Step 5: Update Python Query Tool

Update `query_healthsherpa_plans.py` to include benefit queries:

```python
def find_lowest_drug_costs(base_plan_ids):
    """Find plans with lowest drug costs"""
    conn = get_connection()
    cur = conn.cursor()
    
    like_conditions = ' OR '.join([f"p.plan_id LIKE %s" for _ in base_plan_ids])
    like_params = [f"{base_id}%" for base_id in base_plan_ids]
    
    query = f"""
    WITH matched_plans AS (
        SELECT 
            p.plan_id, p.plan_marketing_name, p.metal_level,
            ROW_NUMBER() OVER (PARTITION BY SUBSTRING(p.plan_id, 1, 14) 
                               ORDER BY p.plan_id) as rn
        FROM plans p
        WHERE {like_conditions}
    )
    SELECT 
        mp.plan_id,
        mp.plan_marketing_name,
        mp.metal_level,
        b_gen.cost_sharing_details->>'copay_inn_tier1' as generic_copay,
        b_brand.cost_sharing_details->>'copay_inn_tier1' as brand_copay
    FROM matched_plans mp
    LEFT JOIN benefits b_gen ON mp.plan_id = b_gen.plan_id 
        AND b_gen.benefit_name = 'Generic Drugs'
    LEFT JOIN benefits b_brand ON mp.plan_id = b_brand.plan_id 
        AND b_brand.benefit_name = 'Preferred Brand Drugs'
    WHERE mp.rn = 1
    ORDER BY NULLIF(REGEXP_REPLACE(b_gen.cost_sharing_details->>'copay_inn_tier1', '[^0-9.]', '', 'g'), '')::NUMERIC NULLS LAST
    LIMIT 20
    """
    
    cur.execute(query, like_params)
    results = [dict(row) for row in cur.fetchall()]
    conn.close()
    return results
```

---

## Performance Optimization (Optional)

### Create Indexes for Faster Queries

```sql
-- Index on benefit_name for faster filtering
CREATE INDEX idx_benefits_benefit_name ON benefits(benefit_name);

-- Index on plan_id for JOINs
CREATE INDEX idx_benefits_plan_id ON benefits(plan_id);

-- Composite index for common queries
CREATE INDEX idx_benefits_plan_benefit ON benefits(plan_id, benefit_name);

-- GIN index for JSONB cost_sharing queries
CREATE INDEX idx_benefits_cost_sharing ON benefits USING GIN(cost_sharing_details);
```

**Expected speedup:** 5-10x for benefit-specific queries

---

## Troubleshooting

### Issue: "Too many rows skipped"

**Symptom:**
```
✓ Loaded 800,000 benefit records (800,000 matched, 600,000 skipped)
```

**Cause:** Benefits file has plan IDs not in your database (other states, dental plans, etc.)

**Solution:** This is normal! You're only loading 30 states, so ~40% skipped is expected.

---

### Issue: "Out of memory"

**Symptom:**
```
MemoryError: Unable to allocate array
```

**Solution:** The loader batches inserts (10,000 rows at a time). If this still happens:

```python
# Edit load_data.py, reduce page_size:
execute_batch(cur, """...""", benefits_data, page_size=5000)  # Reduce from 10000
```

---

### Issue: "Connection timeout"

**Symptom:**
```
psycopg2.OperationalError: server closed the connection unexpectedly
```

**Solution:** RDS connection timeout. The load takes ~30 minutes:

```python
# Add to connection string:
connection_string = "...connect_timeout=3600"
```

---

## Rollback Plan

**If something goes wrong:**

```sql
-- Clear benefits table
TRUNCATE TABLE benefits;

-- Verify it's empty
SELECT COUNT(*) FROM benefits;
-- Should return 0

-- Re-run load_data.py
```

**Database will still work without benefits table** - you just won't have detailed cost-sharing queries.

---

## Post-Deployment Verification

### Checklist

- [ ] Benefits table has ~1.2M records
- [ ] Test query 1 (drug costs) returns results
- [ ] Test query 2 (specialist OON) returns results
- [ ] Test query 3 (MOOP) still works
- [ ] `query_healthsherpa_plans.py` updated with new functions
- [ ] Performance acceptable (<500ms for benefit queries)

---

## Next Steps After Deployment

### 1. Update S3 JSON (Optional)

Generate updated JSON files with benefit data:

```python
# Create export_to_json.py
def export_benefits_to_json(state_code='FL'):
    """Export database to JSON matching S3 format"""
    # Query database
    # Build JSON structure
    # Upload to S3
```

### 2. Update API Endpoints

```python
# Lambda function
@app.route('/aca/plans/compare')
def compare_plans():
    plan_ids = request.json.get('plan_ids', [])
    
    # Query benefits table
    # Return comparison
```

### 3. Build Plan Comparison Tool

```python
# compare_aca_plans.py
def compare_plans(plan_ids, user_usage):
    """
    Compare plans based on user usage pattern
    - Drug usage (generic, brand, specialty)
    - Doctor visits (PCP, specialist)
    - Expected utilization
    
    Returns cost estimates for each plan
    """
```

---

## Summary

**What You're Deploying:**
- 1.4M benefit records
- 60+ benefit types per plan
- Full cost-sharing details (copays, coinsurance, in/out network)

**What This Enables:**
- ✅ Drug cost queries (generic, brand, specialty)
- ✅ Specialist cost queries (in-network and out-of-network)
- ✅ Out-of-network queries for all benefits
- ✅ Primary care, ER, hospital cost queries
- ✅ Complete plan comparison

**Time Investment:**
- Deploy: 45 minutes
- Test: 15 minutes
- Update code: 30 minutes
- **Total: ~90 minutes**

**ROI:**
- Unlock 60+ new query fields
- Match S3 JSON capability
- Enable comprehensive plan comparison
- Support LLM-powered plan recommendations

---

## Ready to Deploy?

```bash
# One command to rule them all:
cd /Users/andy/healthcare_plan_backends/aca && \
DB_PASSWORD=$(cat /Users/andy/aca_overview_test/.db_password) && \
python3 database/load_data.py \
  "host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com \
   dbname=aca_plans user=aca_admin password=$DB_PASSWORD"
```

🚀 **Let it run for ~45 minutes and you're done!**
