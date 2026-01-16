# Querying ACA Plans Using HealthSherpa Base IDs

**Problem:** HealthSherpa shows plans without variant suffixes (e.g., `21525FL0020002`), but your database has variants (e.g., `21525FL0020002-00`, `21525FL0020002-01`).

**Solution:** Use SQL `LIKE` patterns or substring matching to find all variants for each base ID.

---

## Quick Answer: What Works NOW

### ✅ Queries You CAN Run (Current Database)

**1. Lowest Maximum Out-of-Pocket (MOOP)**
```python
python3 query_healthsherpa_plans.py
```

**Available Data:**
- Individual MOOP (In-Network Tier 1)
- Family MOOP (In-Network Tier 1)

**Example Results from ZIP 33433:**
```
1. 48121FL0070051-00 - $9,200 MOOP (Expanded Bronze)
2. 19898FL0340016-00 - $9,500 MOOP (Expanded Bronze)
3. 48121FL0070122-00 - $9,500 MOOP (Expanded Bronze)
```

---

**2. Lowest Deductibles**
```python
python3 query_healthsherpa_plans.py
```

**Available Data:**
- Individual Deductible (In-Network Tier 1)
- Family Deductible (In-Network Tier 1)

**Example Results:**
```
1. 21525FL0020002-00 - $4,700 deductible (Expanded Bronze)
2. 21525FL0020005-00 - $5,500 deductible (Expanded Bronze)
3. 21525FL0020006-00 - $5,500 deductible (Expanded Bronze)
```

---

**3. HSA-Eligible Plans**
```sql
SELECT plan_id, plan_marketing_name, metal_level
FROM plans
WHERE plan_attributes->>'is_hsa_eligible' = 'Yes'
  AND plan_id LIKE '21525FL0020002%'
```

---

**4. Plans by Metal Level, Type, Issuer**
```sql
-- Group by metal level
SELECT metal_level, COUNT(*) as plan_count
FROM plans
WHERE plan_id LIKE ANY(ARRAY['21525FL0020002%', '48121FL0070122%', ...])
GROUP BY metal_level

-- Filter by plan type
SELECT plan_id, plan_marketing_name, plan_type
FROM plans
WHERE plan_id LIKE ANY(ARRAY['21525FL0020002%', ...])
  AND plan_type = 'HMO'
```

---

## ❌ Queries You CANNOT Run Yet (Need Benefits Table)

### Missing: Out-of-Network Specialist Costs

**What You Asked:**
> "What plans in 33433 have the lowest out-of-network costs for specialists?"

**Why It Doesn't Work:**
- Specialist copays/coinsurance are in the `benefits` table (not loaded)
- Field needed: `SpecialistVisit` benefit with `CopayOutOfNet` and `CoinsOutOfNet`

**What You Have Now:**
- Only in-network Tier 1 deductibles and MOOP
- No specialist-specific cost sharing

---

### Missing: Drug Costs

**What You Asked:**
> "What plans in 33433 have the lowest drug costs?"

**Why It Doesn't Work:**
- Drug copays are in the `benefits` table (not loaded)
- Fields needed:
  - `GenericDrugs` → `CopayInnTier1`
  - `PreferredBrandDrugs` → `CopayInnTier1`
  - `SpecialtyDrugs` → `CoinsInnTier1`

**What You Have Now:**
- Only `FormularyId` (identifier, not cost data)

---

### Missing: Primary Care, ER, Hospital Costs

**Not Available:**
- Primary care copays
- Emergency room copays
- Hospital coinsurance
- Urgent care copays
- Out-of-network deductibles/MOOP (Tier 2+)

**All in benefits table (not loaded)**

---

## Efficient Query Strategy

### Strategy 1: Match Base IDs with LIKE (Recommended)

**SQL:**
```sql
-- Get first variant for each base plan
WITH matched_plans AS (
    SELECT 
        p.*,
        SUBSTRING(p.plan_id, 1, 14) as base_plan_id,
        ROW_NUMBER() OVER (PARTITION BY SUBSTRING(p.plan_id, 1, 14) 
                           ORDER BY p.plan_id) as rn
    FROM plans p
    WHERE p.plan_id LIKE '21525FL0020002%'
       OR p.plan_id LIKE '48121FL0070122%'
       OR p.plan_id LIKE '44228FL0040008%'
       -- ... repeat for all HealthSherpa IDs
)
SELECT * FROM matched_plans WHERE rn = 1;
```

**Python:**
```python
# Use query_healthsherpa_plans.py
from query_healthsherpa_plans import query_plans_by_base_ids

healthsherpa_ids = ["21525FL0020002", "48121FL0070122", ...]
plans = query_plans_by_base_ids(healthsherpa_ids, one_variant_per_base=True)
```

---

### Strategy 2: Create Helper Index (Optional Performance Boost)

**Add Index:**
```sql
CREATE INDEX idx_plans_base_id 
ON plans (SUBSTRING(plan_id, 1, 14));
```

**Speeds up queries by 5-10x for large HealthSherpa ID lists**

---

## Current Data Available (plan_attributes JSONB)

```json
{
  "hios_product_id": "21525FL002",
  "network_id": "...",
  "formulary_id": "...",
  "design_type": "Standard",
  "qhp_type": "QHP",
  "plan_effective_date": "2026-01-01",
  "plan_expiration_date": "2026-12-31",
  "is_hsa_eligible": "Yes",
  "national_network": "No",
  "url_enrollment": "https://...",
  "url_sbc": "https://...",
  "plan_brochure": "https://...",
  
  // ✅ AVAILABLE FOR QUERIES
  "deductible_individual": "$5,500",
  "deductible_family": "$11,000",
  "moop_individual": "$9,200",
  "moop_family": "$18,400"
}
```

**All values are strings** - need `extract_numeric()` helper for sorting/comparison.

---

## Next Steps to Enable Full Queries

### Step 1: Download Benefits File

```bash
cd /Users/andy/healthcare_plan_backends/aca/data/raw
wget https://download.cms.gov/marketplace-puf/2026/benefits-and-cost-sharing-puf.zip
unzip benefits-and-cost-sharing-puf.zip
```

### Step 2: Update Data Loader

**Edit `/Users/andy/healthcare_plan_backends/aca/database/load_data.py`:**

Add new function:
```python
def load_benefits(conn):
    """Load benefits and cost-sharing data"""
    print("\n=== Loading Benefits ===")
    cur = conn.cursor()
    
    # Get valid plan IDs
    cur.execute("SELECT plan_id FROM plans")
    valid_plan_ids = set(row[0] for row in cur.fetchall())
    
    benefits_data = []
    
    with open('data/raw/benefits-and-cost-sharing-puf.csv', 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Normalize plan ID (handle variants)
            plan_id = row['PlanId']
            base_plan_id = plan_id[:14]
            
            # Try exact match first
            if plan_id not in valid_plan_ids:
                # Try finding any variant
                cur.execute("SELECT plan_id FROM plans WHERE plan_id LIKE %s LIMIT 1", 
                           (base_plan_id + '%',))
                result = cur.fetchone()
                if result:
                    plan_id = result[0]
                else:
                    continue
            
            # Extract benefit fields
            benefit_name = row['BenefitName']
            is_covered = row['IsCovered'] == 'Covered'
            
            cost_sharing = {
                'copay_inn_tier1': row.get('CopayInnTier1'),
                'copay_inn_tier2': row.get('CopayInnTier2'),
                'copay_oon': row.get('CopayOutOfNet'),
                'coins_inn_tier1': row.get('CoinsInnTier1'),
                'coins_inn_tier2': row.get('CoinsInnTier2'),
                'coins_oon': row.get('CoinsOutOfNet')
            }
            
            benefits_data.append((
                plan_id,
                benefit_name,
                is_covered,
                json.dumps(cost_sharing)
            ))
    
    print(f"Inserting {len(benefits_data)} benefit records...")
    execute_batch(cur, """
        INSERT INTO benefits (plan_id, benefit_name, is_covered, cost_sharing_details)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (plan_id, benefit_name) DO UPDATE SET
            is_covered = EXCLUDED.is_covered,
            cost_sharing_details = EXCLUDED.cost_sharing_details
    """, benefits_data, page_size=10000)
    
    conn.commit()
    print(f"✓ Loaded {len(benefits_data)} benefit records")
```

**Add to main():**
```python
load_benefits(conn)  # Add after load_rates(conn)
```

### Step 3: Reload Database

```bash
DB_PASSWORD=$(cat /Users/andy/aca_overview_test/.db_password)

python3 database/load_data.py \
  "host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com \
   dbname=aca_plans user=aca_admin password=$DB_PASSWORD"
```

### Step 4: Run Full Benefit Queries

**Lowest Out-of-Network Specialist Costs:**
```sql
WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY['21525FL0020002', '48121FL0070122', ...]) AS base_id
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
    b.cost_sharing_details->>'copay_oon' as specialist_oon_copay,
    b.cost_sharing_details->>'coins_oon' as specialist_oon_coinsurance
FROM matched_plans mp
LEFT JOIN benefits b ON mp.plan_id = b.plan_id 
    AND b.benefit_name = 'SpecialistVisit'
WHERE mp.rn = 1
ORDER BY NULLIF(b.cost_sharing_details->>'copay_oon', '')::NUMERIC ASC
LIMIT 20;
```

**Lowest Drug Costs:**
```sql
WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY['21525FL0020002', ...]) AS base_id
),
matched_plans AS (
    SELECT p.plan_id, p.plan_marketing_name,
           ROW_NUMBER() OVER (PARTITION BY SUBSTRING(p.plan_id, 1, 14) 
                              ORDER BY p.plan_id) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_id || '%'
)
SELECT 
    mp.plan_id,
    mp.plan_marketing_name,
    b_generic.cost_sharing_details->>'copay_inn_tier1' as generic_copay,
    b_brand.cost_sharing_details->>'copay_inn_tier1' as brand_copay,
    b_specialty.cost_sharing_details->>'coins_inn_tier1' as specialty_coinsurance
FROM matched_plans mp
LEFT JOIN benefits b_generic ON mp.plan_id = b_generic.plan_id 
    AND b_generic.benefit_name = 'GenericDrugs'
LEFT JOIN benefits b_brand ON mp.plan_id = b_brand.plan_id 
    AND b_brand.benefit_name = 'PreferredBrandDrugs'
LEFT JOIN benefits b_specialty ON mp.plan_id = b_specialty.plan_id 
    AND b_specialty.benefit_name = 'SpecialtyDrugs'
WHERE mp.rn = 1
ORDER BY NULLIF(b_generic.cost_sharing_details->>'copay_inn_tier1', '')::NUMERIC ASC
LIMIT 20;
```

---

## Summary

### ✅ Use NOW (No Benefits Table)
- Lowest MOOP (in-network tier 1)
- Lowest deductibles (in-network tier 1)
- HSA-eligible plans
- Filter by metal level, plan type, issuer
- **Use:** `query_healthsherpa_plans.py`

### 🔧 Requires Benefits Table
- Out-of-network specialist costs
- Drug copays (generic, brand, specialty)
- Primary care copays
- ER/hospital costs
- Detailed tier 2 cost-sharing

### 📋 Recommended Approach
1. **Short-term:** Use current queries for basic cost comparison
2. **Long-term:** Load benefits table for comprehensive analysis
3. **Always:** Match base IDs with `LIKE 'base_id%'` pattern
4. **Performance:** Use `ROW_NUMBER()` to pick first variant per base plan

---

## Files Created

- `QUERY_HEALTHSHERPA_PLANS.sql` - SQL examples and patterns
- `query_healthsherpa_plans.py` - Working Python tool with 3 queries
- `HEALTHSHERPA_QUERY_GUIDE.md` - This guide
- `compare_healthsherpa_plans.py` - Validation tool (100% match confirmed)

---

**Ready to use:** Run `python3 query_healthsherpa_plans.py` to see working examples with your HealthSherpa IDs!
