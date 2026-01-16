# ACA Plan Data: S3 JSON vs PostgreSQL Database Comparison

**Date:** January 16, 2026  
**Comparison:** Static JSON files (S3) vs Dynamic Database (RDS PostgreSQL)

---

## Architecture Overview

### Previous Approach: S3 JSON Files

**Files:**
- `https://fl-aca-data.s3.us-east-1.amazonaws.com/all_florida_aca_plans_normalized.json` (~1.1 MB)
- `https://fl-aca-data.s3.us-east-1.amazonaws.com/all_florida_aca_plans_minified.json` (size TBD)
- Local minification keys at `/Users/andy/DEMO_boca_client/boca_plan_viewer/plan_data_minified/`

**Data Structure:**
```json
{
  "16842FL0120001": {
    "plan_details": {
      "plan_id": "16842FL0120001",
      "plan_name": "BlueSelect Bronze 24L01-01...",
      "plan_carrier": "Florida Blue",
      "preventative_care_included": "true"
    },
    "plan_costs": {
      "deductible": "$6150",
      "out_of_pocket_max": "$9200",
      "metal_tier": "Bronze"
    },
    "in_network": {
      "doctor_visits": {
        "primary_care_visit": "$0",
        "specialist_visit": "$20"
      },
      "prescription_drugs": {
        "generic": "42% after deductible",
        "brand": "47% after deductible"
      },
      "hospital_and_emergency": { ... },
      "mental_health_and_substance_abuse": { ... }
    },
    "out_of_network": { ... }
  }
}
```

**Minified Version:**
```json
{
  "16842FL0120001": {
    "id": "16842FL0120001",
    "n": "BlueSelect Bronze...",
    "c": "16842",
    "pc": {
      "ded": "$6150",
      "oop": "$9200",
      "mt": "Bronze"
    },
    "in": {
      "dv": {
        "pcp": "$0",
        "spec": "$20"
      },
      "rx": {
        "gen": "42% after deductible",
        "br": "47% after deductible"
      }
    }
  }
}
```

### Current Approach: PostgreSQL Database

**Infrastructure:**
- RDS PostgreSQL 15.8
- Connection pooling via Lambda
- Indexed queries

**Schema:**
```sql
plans (plan_id, plan_marketing_name, metal_level, issuer_name, plan_attributes JSONB)
benefits (plan_id, benefit_name, is_covered, cost_sharing_details JSONB) -- NOT LOADED
rates (plan_id, age, individual_rate, individual_tobacco_rate)
```

**Current Data in plan_attributes:**
- ✅ Deductible (in-network tier 1)
- ✅ MOOP (in-network tier 1)
- ✅ HSA eligibility
- ❌ No detailed benefit cost-sharing (primary care, drugs, specialists, etc.)

---

## Query Comparison

### Query 1: Find Plans with Lowest MOOP

#### S3 JSON Approach

**JavaScript/Python:**
```javascript
// Load entire JSON file
const plans = await fetch('https://fl-aca-data.s3.us-east-1.amazonaws.com/all_florida_aca_plans_normalized.json')
  .then(r => r.json());

// Filter by HealthSherpa IDs
const healthsherpaIds = ["21525FL0020002", "48121FL0070122", ...];
const filteredPlans = Object.entries(plans)
  .filter(([planId, _]) => healthsherpaIds.some(hsId => planId.startsWith(hsId)))
  .map(([planId, plan]) => ({
    plan_id: planId,
    plan_name: plan.plan_details.plan_name,
    moop: parseFloat(plan.plan_costs.out_of_pocket_max.replace(/[$,]/g, '')),
    metal_tier: plan.plan_costs.metal_tier
  }));

// Sort by MOOP
filteredPlans.sort((a, b) => a.moop - b.moop);
console.log(filteredPlans.slice(0, 10));
```

**Performance:**
- ✅ Fast: Single HTTP request (~1.1 MB download)
- ✅ No database connection needed
- ✅ Works client-side (browser)
- ❌ Must download entire file (all FL plans, not just filtered)
- ❌ ~1.1 MB network transfer per query
- ❌ JSON parsing overhead

---

#### Database Approach

**SQL:**
```sql
WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY['21525FL0020002', '48121FL0070122', ...]) AS base_id
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
    plan_attributes->>'moop_individual' as moop,
    metal_level
FROM matched_plans
WHERE rn = 1
ORDER BY NULLIF(REGEXP_REPLACE(plan_attributes->>'moop_individual', '[^0-9.]', '', 'g'), '')::NUMERIC
LIMIT 10;
```

**Performance:**
- ✅ Fast: Indexed query (<100ms)
- ✅ Only returns matched plans (small payload)
- ✅ Server-side processing (no client overhead)
- ❌ Requires database connection
- ❌ Not suitable for client-side queries
- ❌ Currently missing detailed benefit data

---

### Query 2: Find Plans with Lowest Drug Costs

#### S3 JSON Approach

**JavaScript:**
```javascript
const plans = await fetch('https://fl-aca-data.s3.us-east-1.amazonaws.com/all_florida_aca_plans_normalized.json')
  .then(r => r.json());

const healthsherpaIds = ["21525FL0020002", "48121FL0070122", ...];

const drugCosts = Object.entries(plans)
  .filter(([planId, _]) => healthsherpaIds.some(hsId => planId.startsWith(hsId)))
  .map(([planId, plan]) => ({
    plan_id: planId,
    plan_name: plan.plan_details.plan_name,
    generic: plan.in_network.prescription_drugs.generic,
    brand: plan.in_network.prescription_drugs.brand,
    specialty: plan.in_network.prescription_drugs.specialty,
    metal_tier: plan.plan_costs.metal_tier
  }))
  .filter(p => p.generic && !p.generic.includes('%')); // Filter copay-only

console.log(drugCosts.slice(0, 10));
```

**✅ WORKS NOW** - JSON has all drug cost data!

**Performance:**
- ✅ All benefit data available
- ✅ Single request
- ❌ 1.1 MB download even for small query

---

#### Database Approach

**SQL (Would Require Benefits Table):**
```sql
WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY['21525FL0020002', ...]) AS base_id
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
    AND b_gen.benefit_name = 'GenericDrugs'
LEFT JOIN benefits b_brand ON mp.plan_id = b_brand.plan_id 
    AND b_brand.benefit_name = 'PreferredBrandDrugs'
LEFT JOIN benefits b_spec ON mp.plan_id = b_spec.plan_id 
    AND b_spec.benefit_name = 'SpecialtyDrugs'
WHERE mp.rn = 1
ORDER BY NULLIF(b_gen.cost_sharing_details->>'copay_inn_tier1', '')::NUMERIC
LIMIT 10;
```

**❌ DOES NOT WORK NOW** - Benefits table not loaded!

**Performance (if loaded):**
- ✅ Indexed and optimized
- ✅ Small payload
- ❌ Complex multi-table joins
- ❌ Requires benefits table loaded (~1.2M rows)

---

### Query 3: Find Plans with Lowest Out-of-Network Specialist Costs

#### S3 JSON Approach

**JavaScript:**
```javascript
const plans = await fetch('https://fl-aca-data.s3.us-east-1.amazonaws.com/all_florida_aca_plans_normalized.json')
  .then(r => r.json());

const specialistCosts = Object.entries(plans)
  .filter(([planId, _]) => healthsherpaIds.some(hsId => planId.startsWith(hsId)))
  .map(([planId, plan]) => ({
    plan_id: planId,
    plan_name: plan.plan_details.plan_name,
    in_network_specialist: plan.in_network.doctor_visits.specialist_visit,
    out_of_network_specialist: plan.out_of_network.doctor_visits.specialist_visit,
    metal_tier: plan.plan_costs.metal_tier
  }));

specialistCosts.sort((a, b) => {
  const aOon = parseFloat(a.out_of_network_specialist.replace(/[^0-9.]/g, ''));
  const bOon = parseFloat(b.out_of_network_specialist.replace(/[^0-9.]/g, ''));
  return aOon - bOon;
});

console.log(specialistCosts.slice(0, 10));
```

**✅ WORKS NOW** - JSON has all out-of-network data!

---

#### Database Approach

**❌ DOES NOT WORK** - Benefits table not loaded (same as drug costs)

---

## LLM Query Comparison

### Scenario: ChatGPT/Claude Analyzing Plans

#### S3 JSON Approach

**Prompt:**
```
I have a JSON file with Florida ACA plans at:
https://fl-aca-data.s3.us-east-1.amazonaws.com/all_florida_aca_plans_normalized.json

Here are the HealthSherpa plan IDs I'm considering:
["21525FL0020002", "48121FL0070122", "44228FL0040008", ...]

Please analyze:
1. Which plans have the lowest drug costs for generic medications?
2. Which plans have the best coverage for mental health services?
3. Which plans have the lowest out-of-network specialist costs?

[Paste or upload the JSON file content]
```

**LLM Response:**
```
I'll analyze the plans for you:

LOWEST GENERIC DRUG COSTS:
1. Plan 48121FL0070122 - Connect Bronze: "$10 after deductible"
2. Plan 21525FL0020002 - Bronze Classic: "$15 after deductible"
...

BEST MENTAL HEALTH COVERAGE:
1. Plan 44228FL0040008 - Wellpoint: "20% coinsurance after deductible"
...

The LLM can directly parse and analyze the JSON!
```

**Advantages:**
- ✅ LLM can access public S3 URLs directly
- ✅ Complete data in one file
- ✅ Natural language queries work immediately
- ✅ No code execution needed
- ✅ All benefit details available

**Limitations:**
- ❌ 1.1 MB file may exceed some LLM context windows
- ❌ LLM must parse entire JSON (slow for large files)
- ❌ Limited to plans in that JSON file (FL only)

---

#### Database Approach

**Prompt:**
```
I have a PostgreSQL database with ACA plans. Here's the connection info:
[Connection details]

Please write SQL queries to:
1. Find plans with lowest drug costs for generic medications
2. Find plans with best mental health coverage
3. Find plans with lowest out-of-network specialist costs

Plan IDs to filter: ["21525FL0020002", "48121FL0070122", ...]
```

**LLM Response:**
```
I'll write SQL queries for you:

[Generates SQL queries like the examples above]

However, I notice your benefits table is not loaded, so queries 
involving detailed cost-sharing won't work yet. You'll need to:
1. Load the benefits table
2. Run the queries I generated
```

**Advantages:**
- ✅ Can query across multiple states (30 states in DB)
- ✅ Structured queries with proper indexes
- ✅ Can combine with other data sources
- ✅ Real-time data (if kept updated)

**Limitations:**
- ❌ LLM cannot execute queries directly (needs code execution)
- ❌ Missing benefits data currently
- ❌ Requires database access credentials
- ❌ Multi-step process (generate query → execute → analyze results)

---

## Feature Comparison Matrix

| Feature | S3 JSON | Database |
|---------|---------|----------|
| **Data Completeness** | | |
| Deductibles | ✅ Yes | ✅ Yes |
| MOOP | ✅ Yes | ✅ Yes |
| Primary care copays | ✅ Yes | ❌ No (need benefits table) |
| Specialist copays | ✅ Yes (in/out network) | ❌ No |
| Drug costs | ✅ Yes (generic/brand/specialty) | ❌ No |
| ER costs | ✅ Yes | ❌ No |
| Hospital costs | ✅ Yes | ❌ No |
| Mental health | ✅ Yes | ❌ No |
| Lab/imaging costs | ✅ Yes | ❌ No |
| **Query Performance** | | |
| Initial load time | ~200ms (1.1 MB) | ~50ms (connection) |
| Filter 194 plans | Client-side (instant) | ~100ms (indexed) |
| Complex multi-field query | Client-side (instant) | ~200ms (JOINs) |
| Memory usage | 1.1 MB RAM | ~10 KB (result only) |
| **Scalability** | | |
| Single ZIP query | Must load all FL plans | Only returns matched plans |
| Multi-state query | Need multiple files | Single query across 30 states |
| 1000s of concurrent users | S3 + CloudFront (excellent) | Lambda + RDS (good) |
| **Developer Experience** | | |
| Client-side queries | ✅ Easy (JavaScript) | ❌ Not possible |
| Server-side queries | ✅ Easy (fetch + filter) | ✅ Easy (SQL) |
| LLM integration | ✅ Excellent (direct access) | ⚠️ Requires code execution |
| Type safety | ❌ JSON parsing | ✅ Schema enforced |
| **Maintenance** | | |
| Update frequency | Manual upload to S3 | Database reload script |
| Storage cost | ~$0.02/month (S3) | ~$20/month (RDS) |
| Bandwidth cost | ~$0.09/GB transfer | Included in RDS |
| Data validation | Manual | PostgreSQL constraints |

---

## Use Case Recommendations

### Use S3 JSON When:

1. **Client-side applications** (React, Vue, browser-based)
   ```javascript
   // Works in browser without backend
   fetch('https://fl-aca-data.s3.us-east-1.amazonaws.com/...')
   ```

2. **LLM analysis** (ChatGPT, Claude, etc.)
   - LLMs can directly access and parse public URLs
   - Natural language queries work immediately
   - Complete benefit data available

3. **Simple filtering** (single state, known plan IDs)
   - Load once, filter multiple times in memory
   - No database connection overhead

4. **Prototyping and demos**
   - Quick setup
   - No infrastructure needed
   - Share URL for instant access

5. **Static site generators** (Gatsby, Next.js Static)
   - Build-time data fetching
   - Pre-render all possible queries

### Use PostgreSQL Database When:

1. **Multi-state queries**
   ```sql
   -- Compare FL vs TX vs NC plans
   SELECT state_code, AVG(moop) FROM plans GROUP BY state_code
   ```

2. **Complex relational queries**
   - JOIN plans with rates by age
   - JOIN plans with service areas
   - JOIN plans with benefits (when loaded)

3. **High-volume API**
   - 1000s of requests/second
   - Need connection pooling
   - Want caching strategies

4. **Real-time updates**
   - Plan availability changes
   - Premium updates
   - New plans added mid-year

5. **Server-side applications** (Lambda, Express, Django)
   - Authenticated queries
   - User-specific filtering
   - Transaction support

---

## Hybrid Approach (Best of Both Worlds)

### Architecture

```
┌─────────────────┐
│   S3 JSON       │  ← For LLM queries & client-side filtering
│   (FL only)     │  ← Complete benefit data
└────────┬────────┘
         │
         │ Generated from ↓
         │
┌────────▼────────┐
│  PostgreSQL DB  │  ← For server queries & multi-state
│  (30 states)    │  ← Load benefits table for completeness
└─────────────────┘
```

### Implementation

**1. Keep S3 JSON for specific use cases:**
```bash
# Generate from database weekly
python3 export_to_json.py --state FL --output s3://fl-aca-data/
```

**2. Use database for API endpoints:**
```python
# Lambda function queries database
@app.route('/aca/zip/<zip_code>.json')
def get_plans(zip_code):
    return query_database(zip_code)
```

**3. Generate minified JSON for client apps:**
```javascript
// Small footprint for mobile apps
const plans = await fetch('https://fl-aca-data.s3.../all_florida_aca_plans_minified.json');
```

---

## Recommendation for Your Use Case

### Current State Assessment

**S3 JSON:**
- ✅ Has complete benefit data (all fields you need)
- ✅ Works for FL plans
- ✅ Perfect for LLM queries
- ✅ Client-side filtering works great
- ❌ Only Florida (no other states)

**Database:**
- ✅ Has 30 states
- ✅ Has core plan data (deductibles, MOOP)
- ✅ Fast indexed queries
- ❌ Missing detailed benefits (drugs, specialists, etc.)

### Recommended Path Forward

**Short-term (TODAY):**

1. **Use S3 JSON for LLM queries**
   - Already has all benefit data
   - LLMs can access directly
   - No code changes needed

2. **Use database for programmatic queries**
   - Multi-state support
   - Faster for filtered queries
   - Better for API endpoints

**Example workflow:**
```javascript
// Client-side: Use S3 JSON
const floridaPlans = await fetch('https://fl-aca-data.s3.../normalized.json');
const filtered = filterByHealthSherpaIds(floridaPlans, ids);

// Server-side: Use database
const allStatesData = await queryDatabase(
  'SELECT * FROM plans WHERE state_code IN (\'FL\', \'TX\', \'NC\')'
);
```

---

**Long-term (Next 2 weeks):**

1. **Load benefits table into database**
   - Download `benefits-and-cost-sharing-puf.csv`
   - Update `load_data.py` with benefits loader
   - Reload database

2. **Generate updated S3 JSON from database**
   - Include all 30 states
   - Generate state-specific JSON files
   - `fl_plans.json`, `tx_plans.json`, etc.

3. **Create unified query interface**
   ```python
   # query_aca.py
   def query_plans(plan_ids, fields, source='auto'):
       if source == 'json' or (source == 'auto' and len(plan_ids) < 100):
           return query_s3_json(plan_ids, fields)
       else:
           return query_database(plan_ids, fields)
   ```

---

## LLM Query Templates

### For S3 JSON Approach

**Template 1: Drug Cost Analysis**
```
I have Florida ACA plan data at:
https://fl-aca-data.s3.us-east-1.amazonaws.com/all_florida_aca_plans_normalized.json

Please analyze these plans: ["21525FL0020002", "48121FL0070122", ...]

Find the 5 plans with:
1. Lowest generic drug costs (in-network)
2. Lowest specialty drug coinsurance
3. Best combination of generic and brand drug costs

Format as a comparison table.
```

**Template 2: Comprehensive Benefit Comparison**
```
Compare these 10 ACA plans for a patient who:
- Sees a specialist monthly ($spec visits/year)
- Takes 2 generic medications daily
- Needs occasional urgent care (2x/year)
- Wants low out-of-network costs

Plans to compare: [list]
Data source: https://fl-aca-data.s3.../normalized.json

Calculate annual out-of-pocket for this usage pattern.
```

### For Database Approach (After Benefits Loaded)

**Template: Multi-State Comparison**
```sql
-- Compare drug costs across FL, TX, NC for same carrier
WITH filtered_plans AS (
    SELECT p.*, b.cost_sharing_details
    FROM plans p
    JOIN benefits b ON p.plan_id = b.plan_id
    WHERE p.issuer_id = '68398'  -- UnitedHealthcare
      AND b.benefit_name = 'GenericDrugs'
      AND p.state_code IN ('FL', 'TX', 'NC')
)
SELECT 
    state_code,
    AVG(NULLIF(cost_sharing_details->>'copay_inn_tier1', '')::NUMERIC) as avg_generic_copay
FROM filtered_plans
GROUP BY state_code;
```

---

## Performance Benchmarks

### Typical Query: Filter 194 Plans by HealthSherpa IDs

**S3 JSON:**
```
Initial load: 200ms (1.1 MB download)
Filter in JS: <5ms (client-side)
Total: ~200ms first query, <5ms subsequent queries
Memory: 1.1 MB (entire JSON in RAM)
```

**Database:**
```
Connection: 50ms (Lambda cold start: +1500ms)
Query execution: 100ms
Data transfer: 10ms
Total: ~160ms (warm), ~1660ms (cold)
Memory: ~50 KB (results only)
```

**Winner:** JSON for repeated client-side queries, Database for one-off server queries

---

## Storage & Cost Analysis

### S3 Storage

**Current:**
- `all_florida_aca_plans_normalized.json`: 1.1 MB
- `all_florida_aca_plans_minified.json`: ~0.7 MB (estimated with key compression)

**If expanded to all 30 states:**
- Normalized: ~33 MB (1.1 MB × 30)
- Minified: ~21 MB (0.7 MB × 30)

**Monthly costs:**
- Storage: $0.02/month (negligible)
- Transfer: $0.09/GB = $3/month for 30 GB transfer
- **Total: ~$3/month for moderate traffic**

### RDS Database

**Current:**
- Database size: ~500 MB (20K plans + rates + indexes)
- Instance: db.t3.micro

**Monthly costs:**
- RDS instance: $15-20/month
- Storage: $2/month (20 GB)
- **Total: ~$20/month**

**Winner:** S3 is 7x cheaper but database offers better query capabilities

---

## Final Recommendation

### Use BOTH (Hybrid Approach)

**For LLM Queries:**
- ✅ Continue using S3 JSON (already works perfectly)
- ✅ Has all benefit data LLMs need
- ✅ Direct URL access
- ✅ Natural language friendly

**For Application Queries:**
- ✅ Use database (multi-state support)
- ✅ Load benefits table to match JSON capabilities
- ✅ Generate updated JSON files weekly from database

**Implementation:**
```bash
# Weekly cron job
python3 export_database_to_json.py \
  --states FL TX NC AZ GA \
  --output s3://aca-data/ \
  --format both  # normalized + minified
```

This gives you:
- ✅ Complete benefit data in both systems
- ✅ LLM-friendly JSON files
- ✅ Fast programmatic database queries
- ✅ Multi-state support
- ✅ Single source of truth (database)
- ✅ Optimized for each use case

---

**Next Steps:**
1. Load benefits table into database (unlock detailed queries)
2. Create export script to generate JSON from database
3. Update S3 with comprehensive multi-state JSON files
4. Use JSON for LLM queries, database for application queries
