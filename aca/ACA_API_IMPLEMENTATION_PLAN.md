# ACA Plan API Implementation Plan

## Overview
Build an API similar to the Medicare API to serve ACA (Affordable Care Act) marketplace plan data by ZIP code.

---

## Data Analysis Summary

### Available Data Files (2026 Plan Year)
Located in `/Users/andy/DEMOS_FINAL_SPRINT/data_aca/`:

| File | Records | Purpose |
|------|---------|---------|
| `plan-attributes-puf.csv` | 22,060 | Plan details, metadata, issuer info |
| `service-area-puf.csv` | 8,821 | Service areas (counties covered by plans) |
| `rate-puf.csv` | 2.2M | Premium rates by age, tobacco use |
| `benefits-and-cost-sharing-puf.csv` | 1.5M | Detailed benefits, copays, deductibles |
| `business-rules-puf.csv` | 5,145 | Business rules for plans |
| `network-puf.csv` | 549 | Network details |

### Key Statistics
- **Individual Market Plans:** 19,272 medical plans (non-dental)
- **Service Areas:** 8,202 for Individual market
- **States Covered:** ~32 states (federally-facilitated marketplace)
- **Service Area Definition:** County-based (7,981 have county FIPS codes)

### Data Relationships

```
ZIP Code → County (FIPS) → Service Area → Plan IDs → Plan Details + Rates + Benefits
```

**Key Fields:**
- `plan-attributes-puf.csv`: `PlanId`, `ServiceAreaId`, `StateCode`, `MetalLevel`, `PlanType`
- `service-area-puf.csv`: `ServiceAreaId`, `County` (FIPS), `StateCode`, `CoverEntireState`
- `rate-puf.csv`: `PlanId`, `Age`, `IndividualRate`
- `benefits-and-cost-sharing-puf.csv`: `PlanId`, benefit details

---

## Critical Finding: We Need ZIP → County Mapping

**Problem:** 
- ACA service areas are defined by counties (FIPS codes)
- Only 23 service areas list explicit ZIP codes
- We need to map ZIP codes to counties to find which plans are available

**Solution:**
✅ **We already have this data from Medicare project!**
- `/Users/andy/medicare_overview_test/data/reference/unified_zip_to_fips.json`
- Contains ZIP → County (FIPS) mapping for all US ZIP codes
- Handles multi-county ZIPs with ratios

---

## Differences from Medicare API

| Feature | Medicare API | ACA API |
|---------|--------------|---------|
| **Market** | Medicare Advantage + Part D | ACA Individual Marketplace |
| **Categories** | MAPD, MA, PD | Bronze, Silver, Gold, Platinum, Catastrophic |
| **Geography** | County-based | County-based (via service areas) |
| **Age Factor** | No (Medicare is 65+) | Yes (rates vary by age) |
| **Rate Structure** | Simple monthly premium | Age-rated, tobacco surcharge |
| **Plan Count** | ~5,800 plans | ~19,000 medical plans |
| **States** | All 50 + DC | ~32 federally-facilitated states |

---

## Architecture (Same as Medicare)

### Database Schema

```sql
-- Core tables
CREATE TABLE plans (
    plan_id VARCHAR PRIMARY KEY,
    state_code VARCHAR(2),
    issuer_name VARCHAR,
    plan_name VARCHAR,
    service_area_id VARCHAR,
    plan_type VARCHAR,
    metal_level VARCHAR,
    plan_attributes JSONB,
    benefits JSONB
);

CREATE TABLE service_areas (
    service_area_id VARCHAR,
    state_code VARCHAR(2),
    county_fips VARCHAR(5),
    covers_entire_state BOOLEAN,
    PRIMARY KEY (service_area_id, county_fips)
);

CREATE TABLE rates (
    plan_id VARCHAR,
    age INTEGER,
    rate DECIMAL,
    tobacco_rate DECIMAL,
    PRIMARY KEY (plan_id, age)
);

CREATE TABLE zip_county (
    zip_code VARCHAR(5),
    county_fips VARCHAR(5),
    state_code VARCHAR(2),
    ratio DECIMAL,
    PRIMARY KEY (zip_code, county_fips)
);
```

### API Endpoints

```
GET /aca/zip/{zipcode}.json
GET /aca/zip/{zipcode}_{metal_level}.json  (e.g., _Silver, _Gold)
GET /aca/states.json
GET /aca/state/{STATE}/info.json
GET /aca/state/{STATE}/plans.json
GET /aca/plan/{plan_id}.json
GET /aca/openapi.yaml
```

### Response Format (Same as Medicare)

For multi-county ZIPs, group plans by county:

```json
{
  "zip_code": "02108",
  "multi_county": false,
  "states": ["MA"],
  "counties": [
    {
      "name": "Suffolk County",
      "fips": "25025",
      "state": "MA",
      "ratio": 1.0,
      "plans": [...],
      "plan_count": 42
    }
  ],
  "plan_counts_by_metal_level": {
    "Bronze": 8,
    "Silver": 15,
    "Gold": 12,
    "Platinum": 7
  }
}
```

---

## Implementation Steps

### Phase 1: Data Setup ✅
1. ✅ Copy ACA data files to `/Users/andy/aca_overview_test/data/`
2. ✅ Copy ZIP → County mapping from Medicare project
3. ✅ Create data loading scripts

### Phase 2: Database Setup
1. Create RDS PostgreSQL database (similar to Medicare)
2. Create database schema
3. Load data:
   - Load plans from `plan-attributes-puf.csv`
   - Load service areas from `service-area-puf.csv`
   - Load rates from `rate-puf.csv`
   - Load benefits from `benefits-and-cost-sharing-puf.csv`
   - Load ZIP → County mapping
4. Create indexes for fast lookups

### Phase 3: Lambda API
1. Copy Medicare Lambda structure
2. Modify for ACA-specific fields:
   - Metal levels instead of categories
   - Age-based rates
   - Different plan attributes
3. Implement endpoints
4. Add connection pooling (like Medicare)

### Phase 4: Testing & Deployment
1. Create test scripts (similar to Medicare)
2. Deploy to AWS Lambda
3. Set up API Gateway
4. Configure custom domain
5. Create OpenAPI spec

### Phase 5: Documentation
1. API User Guide
2. README
3. Deployment docs

---

## Data Quality Checks Needed

1. **Filter Individual Market Only**
   ```python
   df = df[df['MarketCoverage'] == 'Individual']
   ```

2. **Exclude Dental-Only Plans** (unless user wants them)
   ```python
   df = df[df['DentalOnlyPlan'] != 'Yes']
   ```

3. **Valid Service Areas**
   - Ensure all plan service areas exist in service-area-puf.csv
   - Verify county FIPS codes are valid

4. **Rate Data**
   - Ensure rates exist for all plan IDs
   - Check age range coverage (typically 0-64, or 21-64)

---

## Estimated Complexity

| Task | Complexity | Time | Notes |
|------|-----------|------|-------|
| Data analysis | Low | ✅ Done | Data structure understood |
| Data loading | Medium | 2-3 hours | Similar to Medicare, more tables |
| Database setup | Low | 1 hour | Reuse Medicare RDS setup |
| Lambda API | Low | 2-3 hours | Copy Medicare structure |
| Testing | Medium | 1-2 hours | New test data needed |
| Deployment | Low | 1 hour | Same AWS infrastructure |
| **TOTAL** | **Medium** | **8-12 hours** | Mostly reusing Medicare code |

---

## Data Sufficiency: ✅ YES

**We have everything needed:**
- ✅ Plan details (plan-attributes-puf.csv)
- ✅ Service areas with county mapping (service-area-puf.csv)
- ✅ Premium rates (rate-puf.csv)
- ✅ Benefits and cost sharing (benefits-and-cost-sharing-puf.csv)
- ✅ ZIP → County mapping (from Medicare project)

**Missing but not critical:**
- State-based exchanges (CA, NY, CO, etc.) - would need separate data sources
- Provider networks (have file, but may be sparse)
- Formulary details (not typically shown in plan search)

---

## Next Steps

1. **Copy necessary data files** to aca_overview_test
2. **Create database schema** based on Medicare model
3. **Write data loading script** to process CSVs into PostgreSQL
4. **Build Lambda API** using Medicare code as template
5. **Test and deploy**

---

## Questions to Resolve

1. **Age-based rates:** Should API return rates for all ages, or let client specify age?
   - Recommendation: Return sample rate (e.g., age 40) + rate table
   
2. **Dental plans:** Include or exclude?
   - Recommendation: Exclude by default, add `_dental` category filter if needed
   
3. **SHOP plans:** Include or exclude?
   - Recommendation: Exclude (focus on Individual market like Healthcare.gov)

4. **Database:** New RDS instance or share with Medicare?
   - Recommendation: New database (different schema, separate data)

---

## Cost Estimate

- **RDS PostgreSQL:** ~$15-25/month (same tier as Medicare)
- **Lambda:** ~$5/month (minimal with connection pooling)
- **API Gateway:** Free tier or ~$1/month
- **Total:** ~$20-30/month

---

## Success Criteria

✅ API returns ACA plans for any US ZIP code
✅ Multi-county ZIPs show plans for all counties
✅ Response time < 500ms (with connection pooling)
✅ Proper metal level filtering (Bronze, Silver, Gold, Platinum)
✅ OpenAPI spec available
✅ Comprehensive test coverage
✅ Documentation complete
