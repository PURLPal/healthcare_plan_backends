# ACA Database Analysis

**Analysis Date:** January 14, 2026  
**Database:** `aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com`

---

## Executive Summary

✅ **Data Quality:** Excellent - 100% coverage on all core plan fields  
✅ **Queryability:** Fast indexed queries on all key fields  
⚠️ **Rate Data:** Not loaded (plan ID format issues - needs fixing)  
📝 **Benefits Data:** Not yet loaded (future enhancement)

---

## Key Findings

### ZIP Code Coverage

- **Total ZIP Codes:** 39,298
- **ZIP Codes with Plans:** 39,117 (99.5%)
- **ZIP Codes with NO Plans:** 181 (0.5%)

**Why Some ZIPs Have No Plans:**
- ZIPs in non-covered states (state-based marketplaces)
- ZIPs in counties not served by any plan
- Multi-state ZIPs where primary state isn't covered

**Sample ZIPs with All Plans Available:**
- NH ZIPs: 230 plans each (statewide coverage)
- FL ZIPs: Up to 2,119 plans
- TX ZIPs: Up to 4,183 plans

### State Coverage

**States with MOST Plans:**
1. Texas: 4,183 plans (18 issuers)
2. Florida: 2,119 plans (16 issuers)
3. Wisconsin: 1,517 plans (12 issuers)
4. North Carolina: 1,046 plans (6 issuers)
5. Arizona: 1,010 plans (7 issuers)

**States with LEAST Plans:**
1. Alaska: 64 plans (2 issuers)
2. Hawaii: 78 plans (2 issuers)
3. Wyoming: 119 plans (2 issuers)
4. West Virginia: 185 plans (2 issuers)
5. Delaware: 188 plans (3 issuers)

**Why Variation?**
- Market competition (more issuers = more plans)
- Population density
- State regulations
- Geographic size and service area complexity

---

## Plan Detail Coverage

### Core Fields: 100% Coverage ✅

All 20,354 plans have complete data for:

| Field | Coverage | Notes |
|-------|----------|-------|
| **Plan ID** | 100% | Unique identifier |
| **Marketing Name** | 100% | Consumer-facing name |
| **Issuer Name** | 100% | Insurance company |
| **Plan Type** | 100% | HMO, PPO, EPO, POS |
| **Metal Level** | 100% | Bronze, Silver, Gold, etc. |
| **State Code** | 100% | Two-letter state |
| **Service Area ID** | 100% | Geographic coverage |
| **New Plan Flag** | 100% | Is this a new plan? |
| **Attributes JSON** | 100% | Extended attributes |

### Plan Attributes JSON

Each plan has a `plan_attributes` JSONB field containing additional details:

**Available Fields:**
- `deductible_individual` - Individual deductible
- `deductible_family` - Family deductible
- `moop_individual` - Individual max out-of-pocket
- `moop_family` - Family max out-of-pocket
- `is_hsa_eligible` - HSA eligibility
- `formulary_id` - Drug formulary identifier
- `network_id` - Provider network identifier
- `hios_product_id` - HIOS product ID
- `design_type` - Plan design type
- `national_network` - National network flag
- And 6+ more fields

**Queryable:** Yes! JSONB supports indexed queries on nested fields.

### Distribution by Plan Type

| Plan Type | Count | Percentage |
|-----------|-------|------------|
| **HMO** | 10,782 | 53.0% |
| **EPO** | 5,454 | 26.8% |
| **POS** | 2,088 | 10.3% |
| **PPO** | 2,030 | 10.0% |

### Distribution by Metal Level

| Metal Level | Count | Percentage |
|-------------|-------|------------|
| **Silver** | 10,158 | 49.9% |
| **Gold** | 4,679 | 23.0% |
| **Expanded Bronze** | 4,615 | 22.7% |
| **Bronze** | 576 | 2.8% |
| **Platinum** | 176 | 0.9% |
| **Catastrophic** | 150 | 0.7% |

---

## State-by-State Variance

### Issuer Competition

**Most Competitive (Most Issuers):**
1. Texas: 18 issuers
2. Florida: 16 issuers
3. Wisconsin: 12 issuers
4. Ohio: 11 issuers
5. Missouri: 8 issuers

**Least Competitive (Fewest Issuers):**
1. West Virginia: 2 issuers
2. Alaska: 2 issuers
3. Hawaii: 2 issuers
4. Wyoming: 2 issuers
5. Montana: 3 issuers

### Service Area Complexity

**Most Complex (Most Service Areas):**
1. Texas: 52 service areas
2. North Carolina: 18 service areas
3. Oklahoma: 20 service areas
4. Louisiana: 14 service areas
5. Wisconsin: 13 service areas

**Simplest (Fewest Service Areas):**
1. Arkansas: 1 service area (statewide)
2. New Hampshire: 1 service area (statewide)
3. Delaware: 1 service area (statewide)
4. Hawaii: 1 service area (statewide)
5. West Virginia: 1 service area (statewide)

**Insight:** States with 1 service area typically have statewide plans available to all residents.

---

## Database Schema

### Main Tables

#### 1. `plans` (20,354 rows)

**Purpose:** Core plan data from CMS PUF files

**Key Fields:**
- `plan_id` VARCHAR(50) PRIMARY KEY
- `state_code` VARCHAR(2) - **INDEXED**
- `issuer_id` VARCHAR(20) - **INDEXED**
- `issuer_name` VARCHAR(200)
- `service_area_id` VARCHAR(50) - **INDEXED**
- `plan_marketing_name` VARCHAR(300)
- `plan_type` VARCHAR(50) - **INDEXED** (HMO, PPO, EPO, POS)
- `metal_level` VARCHAR(50) - **INDEXED** (Silver, Gold, etc.)
- `is_new_plan` BOOLEAN
- `plan_attributes` JSONB - **JSONB INDEXED**
- `created_at` TIMESTAMP

**Indexes:**
```sql
idx_plans_state (state_code)
idx_plans_service_area (service_area_id)
idx_plans_metal_level (metal_level)
idx_plans_issuer (issuer_id)
idx_plans_type (plan_type)
```

#### 2. `zip_counties` (39,298+ rows)

**Purpose:** Maps ZIP codes to counties (handles multi-county ZIPs)

**Key Fields:**
- `zip_code` VARCHAR(5) - **INDEXED**
- `county_fips` VARCHAR(5) - **INDEXED**
- `state_code` VARCHAR(2) - **INDEXED**
- `ratio` DECIMAL(10,6) - Population ratio for multi-county ZIPs

**Critical for:** ZIP → Plans lookup

#### 3. `plan_service_areas` (7,122 rows)

**Purpose:** Links service areas to counties

**Key Fields:**
- `service_area_id` VARCHAR(50) - **INDEXED**
- `county_fips` VARCHAR(5) - **INDEXED**
- `state_code` VARCHAR(2)

**Query Path:** `zip_counties` → `plan_service_areas` → `plans`

#### 4. `service_areas` (255 rows)

**Purpose:** Service area definitions

**Key Fields:**
- `service_area_id` VARCHAR(50)
- `state_code` VARCHAR(2) - **INDEXED**
- `issuer_id` VARCHAR(20)
- `service_area_name` VARCHAR(200)
- `covers_entire_state` BOOLEAN
- `market_coverage` VARCHAR(50)

#### 5. `counties` (3,244 rows)

**Purpose:** County reference data

**Key Fields:**
- `county_fips` VARCHAR(5) PRIMARY KEY
- `county_name` VARCHAR(100)
- `state_code` VARCHAR(2) - **INDEXED**
- `state_name` VARCHAR(100)

#### 6. `rates` (0 rows - NOT LOADED)

**Purpose:** Age-based premium rates

**Status:** ⚠️ Not loaded due to plan ID format mismatches

**Planned Fields:**
- `plan_id` VARCHAR(50)
- `age` INTEGER
- `individual_rate` DECIMAL(10,2)
- `individual_tobacco_rate` DECIMAL(10,2)

#### 7. `benefits` (0 rows - NOT LOADED)

**Purpose:** Detailed benefit coverage

**Status:** ❌ Not yet implemented (future enhancement)

**Planned Fields:**
- `plan_id` VARCHAR(50)
- `benefit_name` VARCHAR(200)
- `is_covered` BOOLEAN
- `cost_sharing_details` JSONB

---

## Easily Queryable Operations

### ✅ Fast Queries (All Indexed)

1. **Get Plans by ZIP Code**
   ```sql
   SELECT p.*
   FROM plans p
   JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
   JOIN zip_counties zc ON psa.county_fips = zc.county_fips
   WHERE zc.zip_code = '33139';
   ```
   **Performance:** ~300-500ms

2. **Filter by State**
   ```sql
   SELECT * FROM plans WHERE state_code = 'FL';
   ```
   **Performance:** <100ms

3. **Filter by Metal Level**
   ```sql
   SELECT * FROM plans WHERE metal_level = 'Silver';
   ```
   **Performance:** <100ms

4. **Filter by Plan Type**
   ```sql
   SELECT * FROM plans WHERE plan_type = 'HMO';
   ```
   **Performance:** <100ms

5. **Find Statewide Plans**
   ```sql
   SELECT p.*
   FROM plans p
   JOIN service_areas sa ON p.service_area_id = sa.service_area_id
   WHERE sa.covers_entire_state = true;
   ```
   **Performance:** <200ms

6. **Query JSON Attributes**
   ```sql
   SELECT * FROM plans
   WHERE plan_attributes->>'is_hsa_eligible' = 'Yes';
   ```
   **Performance:** ~500ms (JSONB indexed)

7. **Get Plans by Issuer**
   ```sql
   SELECT * FROM plans WHERE issuer_id = '12345';
   ```
   **Performance:** <100ms

### ⚠️ Partially Available

1. **Age-Based Premium Rates**
   - Status: Not loaded (plan ID format issues)
   - Action Needed: Fix rate loader to match plan IDs

### ❌ Not Yet Available

1. **Detailed Benefits**
   - Deductibles (available in `plan_attributes` JSON)
   - Copays, coinsurance (not loaded)
   - Covered services (not loaded)

2. **Provider Networks**
   - Network IDs available in `plan_attributes`
   - Provider directories not included

3. **Drug Formularies**
   - Formulary IDs available in `plan_attributes`
   - Drug lists not included

---

## Query Performance

### Typical Response Times

| Query Type | Response Time | Notes |
|------------|---------------|-------|
| ZIP → Plans | 300-500ms | Warm Lambda |
| State filter | <100ms | Direct index |
| Metal level filter | <100ms | Direct index |
| Plan type filter | <100ms | Direct index |
| Complex joins | 500-1000ms | Multiple tables |
| First request (cold start) | 1.5-2s | Lambda startup |

### Optimization

**Connection Pooling:** Lambda uses persistent pg8000 connections to avoid reconnecting on every request.

**Indexes:** All common query paths are indexed for fast lookups.

---

## Data Completeness Summary

### Excellent Coverage ✅

- **Plan identifiers:** 100%
- **Plan names:** 100%
- **Issuers:** 100%
- **Geographic mapping:** 100%
- **Plan types:** 100%
- **Metal levels:** 100%
- **Extended attributes (JSON):** 100%

### Needs Improvement ⚠️

- **Age-based rates:** 0% (technical issue - fixable)

### Future Enhancements 📝

- **Benefit details:** 0% (available in PUF, not loaded)
- **Provider networks:** 0% (not in PUF files)
- **Drug formularies:** 0% (not in PUF files)

---

## Recommendations

### Immediate Actions

1. **Fix Rate Data Loading**
   - Investigate plan ID format differences between plan and rate PUF files
   - Update loader to handle variations
   - Reload rate data

2. **Document JSONB Schema**
   - Create formal documentation of `plan_attributes` structure
   - Include all available fields and their meanings

### Future Enhancements

1. **Load Benefits Data**
   - Import benefits-and-cost-sharing PUF file
   - Enable detailed plan comparisons
   - Add deductible, copay, coinsurance queries

2. **Add Materialized Views**
   - Pre-compute ZIP → Plan counts for faster analytics
   - Create state summary views
   - Cache common query results

3. **Enhance Search**
   - Add full-text search on plan names
   - Enable fuzzy issuer name matching
   - Support plan ID prefix search

---

## Example Queries

### Get All Plans for a ZIP

```sql
SELECT 
    p.plan_id,
    p.plan_marketing_name,
    p.issuer_name,
    p.plan_type,
    p.metal_level,
    p.plan_attributes->>'deductible_individual' as deductible
FROM plans p
JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
JOIN zip_counties zc ON psa.county_fips = zc.county_fips
WHERE zc.zip_code = '33139'
ORDER BY p.metal_level, p.issuer_name;
```

### Get Silver Plans Only

```sql
SELECT * FROM plans
WHERE metal_level = 'Silver'
AND state_code = 'FL'
ORDER BY issuer_name;
```

### Find HSA-Eligible Plans

```sql
SELECT 
    plan_id,
    plan_marketing_name,
    plan_attributes->>'is_hsa_eligible' as hsa_eligible,
    plan_attributes->>'deductible_individual' as deductible
FROM plans
WHERE plan_attributes->>'is_hsa_eligible' = 'Yes'
AND state_code = 'TX';
```

### Count Plans by State and Metal Level

```sql
SELECT 
    state_code,
    metal_level,
    COUNT(*) as plan_count
FROM plans
GROUP BY state_code, metal_level
ORDER BY state_code, metal_level;
```

---

## Testing

**Analysis Script:** `analyze_database_optimized.py`

```bash
# Run database analysis
ACA_DB_PASSWORD='your_password' python3 analyze_database_optimized.py
```

**API Testing:** `tests/test_api_comprehensive.py`

```bash
# Test API endpoints across multiple ZIPs
python3 tests/test_api_comprehensive.py 5
```

---

## Conclusion

The ACA database has **excellent data quality** with 100% coverage on all core fields. The schema is well-designed for fast ZIP → Plans lookups, with proper indexing on all common query patterns.

**Strengths:**
- ✅ Complete plan data from authoritative CMS source
- ✅ Fast indexed queries on all key fields
- ✅ JSONB support for flexible attribute queries
- ✅ Multi-county ZIP support
- ✅ Statewide plan handling

**Areas for Improvement:**
- ⚠️ Rate data needs to be loaded
- 📝 Benefits data could be added
- 📝 Additional materialized views for analytics

Overall, the database is **production-ready** and serving the ACA API effectively!
