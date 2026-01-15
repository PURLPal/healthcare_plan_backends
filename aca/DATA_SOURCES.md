# ACA API Data Sources

Complete documentation of data sources and collection methodology for the ACA Marketplace API.

---

## Overview

The ACA API uses **official CMS Public Use Files (PUFs)** as its primary data source. Unlike the Medicare API which requires web scraping, ACA marketplace data is provided directly by CMS in structured CSV format.

**Key Advantage:** No scraping required - all data comes from authoritative government sources.

---

## Primary Data Source

### CMS Public Use Files (PUFs)

**Source:** Centers for Medicare & Medicaid Services (CMS)  
**URL:** https://www.cms.gov/marketplace/resources/data/public-use-files  
**Update Frequency:** Annual (November/December)  
**Format:** CSV files  
**License:** Public domain

#### What Are PUFs?

Public Use Files (PUFs) are official CMS datasets that provide comprehensive information about qualified health plans (QHPs) offered through the Health Insurance Marketplace. These files are released annually for researchers, developers, and the public.

---

## Data Files Used

### 1. Plan Attributes File

**File:** `plan-attributes-puf.csv`  
**Size:** ~20,000 rows (2026 plan year)  
**Purpose:** Core plan information

#### Fields Used

**Plan Identification:**
- `PlanId` - Unique 14-character plan identifier
- `StandardComponentId` - Standard plan component ID
- `IssuerId` - Insurance company identifier
- `IssuerName` - Insurance company name

**Plan Characteristics:**
- `PlanMarketingName` - Consumer-facing plan name
- `PlanType` - HMO, PPO, EPO, POS
- `MetalLevel` - Bronze, Silver, Gold, Platinum, Catastrophic, Expanded Bronze
- `IssuerActuarialValue` - Actuarial value (60%, 70%, 80%, 90%)
- `AVCalculatorOutputNumber` - AV for comparison

**Market Type:**
- `MarketCoverage` - Individual, Small Group, SHOP
- `DentalOnlyPlan` - Yes/No flag

**Geographic Coverage:**
- `StateCode` - Two-letter state code
- `ServiceAreaId` - Service area identifier
- `IssuerId2` - Secondary issuer ID

**Special Designations:**
- `IsNewPlan` - Indicator for new plans
- `PlanEffectiveDate` - When plan becomes available
- `PlanExpirationDate` - When plan ends

#### What We Extract

```sql
SELECT 
    PlanId,
    PlanMarketingName,
    IssuerName,
    PlanType,
    MetalLevel,
    StateCode,
    ServiceAreaId,
    MarketCoverage,
    DentalOnlyPlan
FROM plan_attributes
WHERE MarketCoverage = 'Individual'
  AND DentalOnlyPlan = 'No'
```

**Result:** 20,354 medical plans for individual market

---

### 2. Service Area File

**File:** `service-area-puf.csv`  
**Size:** ~8,800 rows  
**Purpose:** Define geographic coverage areas

#### Fields Used

**Service Area Identification:**
- `ServiceAreaId` - Unique service area identifier
- `ServiceAreaName` - Human-readable name
- `StateCode` - State abbreviation
- `IssuerId` - Insurance company offering this area

**Coverage Details:**
- `CoverEntireState` - Yes/No (statewide vs. regional)
- `County` - FIPS code for county coverage
- `ZIPCode` - ZIP codes in service area (partial)
- `MarketCoverage` - Individual, Small Group, etc.

**Important:** Service areas define WHERE plans are available. A plan's `ServiceAreaId` determines which counties can access it.

#### Service Area Types

**Statewide Service Areas:**
```
ServiceAreaId: AKS001
State: AK
CoverEntireState: Yes
Counties: All 30 Alaska counties
```

Plans with statewide service areas are available to ALL residents of that state.

**County-Specific Service Areas:**
```
ServiceAreaId: FLS033
State: FL
CoverEntireState: No
Counties: 12086 (Miami-Dade), 12011 (Broward)
```

Plans with county-specific areas are only available in listed counties.

---

### 3. Rate File

**File:** `rate-puf.csv`  
**Size:** ~2.2 million rows  
**Purpose:** Age-based premium rates

#### Fields Used

**Rate Identification:**
- `PlanId` - Links to plan attributes
- `RateEffectiveDate` - When rate applies
- `RateExpirationDate` - When rate expires
- `StateCode` - State abbreviation

**Premium Rates by Age:**
- `IndividualRate` - Base rate
- `Age0-20` - Rate for children
- `Age21`, `Age22`, ..., `Age64` - Individual age rates
- `Age65+` - Senior rates (rare in ACA marketplace)

**Rating Area:**
- `RatingAreaId` - Geographic rating area
- `Tobacco` - Tobacco use status (Yes/No)

#### Why Age-Based Rates?

Unlike Medicare (flat premiums), ACA plans charge different premiums based on:
- **Age:** Older adults pay more (3:1 ratio max)
- **Tobacco use:** Smokers may pay up to 50% more
- **Geography:** Rating areas within states

**Example Rate Table:**
```
Plan: 13887FL0010001-00
Age 21: $250/month
Age 30: $280/month
Age 40: $340/month
Age 50: $480/month
Age 64: $750/month
```

---

### 4. Benefits and Cost Sharing File

**File:** `benefits-and-cost-sharing-puf.csv`  
**Size:** Large (varies by year)  
**Purpose:** Detailed benefit information

#### Fields Available (Not All Used)

**Cost Sharing:**
- `Deductible` - Individual/family deductibles
- `OutOfPocketMaximum` - Annual limit
- `Copayment` - Fixed copay amounts
- `Coinsurance` - Percentage cost sharing

**Covered Benefits:**
- Primary care visits
- Specialist visits
- Emergency room
- Hospitalization
- Prescription drugs
- Preventive care
- Mental health services
- And 60+ other benefit categories

**Current Implementation:**

The benefits file is **not currently loaded** into the database due to:
- Large data volume
- Complex structure (many benefit categories)
- Plan ID format mismatches in some files

**Future Enhancement:** Load benefits data for detailed plan comparisons.

---

## ZIP Code to County Mapping

**Source:** US Census Bureau + Existing Medicare Mapping  
**File:** `unified_zip_to_fips.json`

**Reused from Medicare API:**

The same ZIP-to-county mapping used for Medicare is used for ACA plans. This ensures consistency across both APIs.

**Why Critical for ACA:**

1. ACA plans are defined by **service areas** (county-based)
2. Users search by **ZIP code**
3. Mapping connects user location → county → service area → plans

**Example:**
```
ZIP 33139 (Miami Beach, FL)
  → County 12086 (Miami-Dade County)
  → Service Areas: FLS033, FLS034, etc.
  → Plans: 1,858 plans available
```

---

## County Reference Data

**Source:** US Census Bureau + CMS County Files  
**File:** `fips_to_county_name.json`

Maps FIPS codes to county names:
```json
{
  "12086": {
    "name": "Miami-Dade County",
    "state": "FL"
  }
}
```

This provides human-readable county names in API responses.

---

## Data Collection Process

### Step 1: Download PUF Files

```bash
# Download from CMS
wget https://download.cms.gov/marketplace-puf/2026/plan-attributes-puf.zip
wget https://download.cms.gov/marketplace-puf/2026/service-area-puf.zip
wget https://download.cms.gov/marketplace-puf/2026/rate-puf.zip
wget https://download.cms.gov/marketplace-puf/2026/benefits-puf.zip

# Extract
unzip plan-attributes-puf.zip
unzip service-area-puf.zip
unzip rate-puf.zip
```

**No Scraping Required!** All data comes pre-structured from CMS.

### Step 2: Load Data into Database

```bash
python3 database/load_data.py "host=... dbname=aca_plans user=... password=..."
```

**Data Loading Script (`load_data.py`) performs:**

1. **Load County Reference Data**
   - Load `fips_to_county_name.json`
   - Load `unified_zip_to_fips.json`
   - Insert into `counties` and `zip_counties` tables

2. **Load Service Areas**
   - Parse `service-area-puf.csv`
   - Filter for Individual market
   - Insert into `service_areas` table
   - Map counties to service areas in `plan_service_areas` table
   - Handle statewide service areas (map to ALL counties in state)

3. **Load Plans**
   - Parse `plan-attributes-puf.csv`
   - Filter for Individual market medical plans (exclude dental, SHOP)
   - Insert into `plans` table
   - Link to service areas

4. **Load Rates** (Optional)
   - Parse `rate-puf.csv`
   - Match plan IDs
   - Insert age-based rates into `rates` table

### Step 3: API Queries

Lambda function queries PostgreSQL database in real-time:

```sql
-- Get plans for ZIP code
SELECT p.*
FROM plans p
JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
JOIN zip_counties zc ON psa.county_fips = zc.county_fips
WHERE zc.zip_code = '33139'
  AND p.market_coverage = 'Individual'
ORDER BY p.metal_level, p.issuer_name
```

---

## Data Filtering

### Filters Applied During Loading

**Market Type:**
```
✅ Individual market only
❌ Small Group market (excluded)
❌ SHOP (Small Business Health Options Program) (excluded)
```

**Plan Type:**
```
✅ Medical plans
❌ Dental-only plans (excluded)
❌ Vision-only plans (excluded)
```

**Reason:** The API focuses on individual consumers shopping for comprehensive medical coverage.

---

## Coverage and Limitations

### Geographic Coverage

**Included (30 States):**

ACA API includes only **federally-facilitated marketplace (FFM) states**:

AK, AL, AR, AZ, DE, FL, HI, IA, IN, KS, LA, ME, MI, MO, MS, MT, NC, ND, NE, NH, OH, OK, SC, SD, TN, TX, UT, VA, WI, WY

**Not Included (State-Based Marketplaces):**

These states run their own exchanges and are **not in CMS PUF files**:

- California (Covered California)
- Colorado (Connect for Health Colorado)
- Connecticut (Access Health CT)
- District of Columbia (DC Health Link)
- Idaho (Your Health Idaho)
- Maryland (Maryland Health Connection)
- Massachusetts (MA Health Connector)
- Minnesota (MNsure)
- Nevada (Nevada Health Link)
- New Jersey (Get Covered NJ)
- New Mexico (beWellnm)
- New York (NY State of Health)
- Pennsylvania (Pennie)
- Rhode Island (HealthSource RI)
- Vermont (Vermont Health Connect)
- Washington (WA Health Benefit Exchange)

**Impact:** ~40% of US population uses state-based marketplaces not included in this API.

---

## Data Quality and Completeness

### Data Completeness

**High Quality Fields (100% populated):**
- ✅ Plan ID
- ✅ Plan name
- ✅ Issuer name
- ✅ Metal level
- ✅ Plan type
- ✅ State code
- ✅ Service area

**Partially Populated:**
- ⚠️ Age-based rates (plan ID format issues in some files)
- ⚠️ Benefits details (not currently loaded)

### Known Issues

**Rate Data:**

Current issue: Many rate records don't match plan IDs due to format differences between files. This is being investigated.

**Workaround:** API returns plan attributes without specific rate quotes. Users should verify rates on healthcare.gov.

---

## Data Updates

### Annual Update Cycle

**November/December:**
- CMS releases new PUF files for upcoming plan year
- Open enrollment begins

**Update Process:**

1. **Download new PUF files** from CMS
   ```bash
   cd data/raw
   wget https://download.cms.gov/marketplace-puf/2027/...
   ```

2. **Verify file formats**
   - Check column names (CMS sometimes changes format)
   - Update `load_data.py` if schema changed

3. **Load into database**
   ```bash
   python3 database/load_data.py "<connection_string>"
   ```

4. **Test API**
   ```bash
   python3 tests/test_api_comprehensive.py 10
   ```

5. **Deploy** (no Lambda changes needed if schema unchanged)

**Time Required:** 15-30 minutes (vs. weeks for Medicare scraping!)

---

## Advantages Over Scraping

### Why PUFs Are Better

**1. Official Data**
- ✅ Directly from CMS
- ✅ Authoritative source
- ✅ No interpretation errors

**2. Structured Format**
- ✅ Clean CSV files
- ✅ Consistent schema
- ✅ Well-documented fields

**3. Comprehensive**
- ✅ All FFM plans included
- ✅ Complete attributes
- ✅ Historical data available

**4. No Technical Challenges**
- ✅ No web scraping needed
- ✅ No rate limiting issues
- ✅ No CAPTCHA handling
- ✅ No JavaScript rendering

**5. Easy Updates**
- ✅ Download new files
- ✅ Reload database
- ✅ Done in minutes

**6. Legal Clarity**
- ✅ Public domain data
- ✅ Explicit permission to use
- ✅ No Terms of Service concerns

---

## Data Processing Pipeline

### Complete Flow

```
CMS PUF Files
    ↓
Download CSVs
    ↓
Filter & Clean
    ├─ Individual market only
    ├─ Medical plans only
    └─ Active plans only
    ↓
Load into PostgreSQL
    ├─ Counties table
    ├─ ZIP mappings table
    ├─ Service areas table
    ├─ Plans table
    └─ Rates table
    ↓
API Lambda Function
    ↓
Query by ZIP code
    ↓
Return JSON response
```

### Processing Time

- **Download:** 2-5 minutes
- **Database load:** 2-3 minutes
- **Total:** Under 10 minutes for complete data refresh

Compare to Medicare: 2-3 weeks of scraping!

---

## Database Schema

### Tables Created

**1. counties**
- County reference data (FIPS, names, states)

**2. zip_counties**
- ZIP to county mappings
- Handles multi-county ZIPs

**3. service_areas**
- Service area definitions
- Statewide vs. county-specific flags

**4. plan_service_areas**
- Links service areas to counties
- Enables ZIP → Plans lookup

**5. plans**
- Plan attributes from PUF
- Links to service areas

**6. rates**
- Age-based premium rates
- Links to plans

**7. benefits**
- Benefit details (future)
- Links to plans

---

## Sample Data Examples

### Plan Attributes Record

```csv
PlanId,PlanMarketingName,IssuerName,MetalLevel,PlanType,StateCode,ServiceAreaId
13887FL0010001-00,Gold 22 Health,22 Health,Gold,HMO,FL,FLS033
```

### Service Area Record

```csv
ServiceAreaId,StateCode,IssuerId,ServiceAreaName,CoverEntireState,County
FLS033,FL,13887,Miami-Dade Service Area,No,12086
```

### Rate Record (Age-Based)

```csv
PlanId,StateCode,Age21,Age30,Age40,Age50,Age64
13887FL0010001-00,FL,250.00,280.00,340.00,480.00,750.00
```

---

## Data Validation

### Validation Checks Performed

**1. Plan Count Validation**
```sql
-- Should be ~20,000 plans
SELECT COUNT(*) FROM plans;
```

**2. State Coverage**
```sql
-- Should be ~30 FFM states
SELECT COUNT(DISTINCT state_code) FROM plans;
```

**3. Service Area Mapping**
```sql
-- All plans should map to counties
SELECT COUNT(DISTINCT service_area_id) 
FROM plans p
WHERE EXISTS (
    SELECT 1 FROM plan_service_areas psa
    WHERE psa.service_area_id = p.service_area_id
);
```

**4. ZIP Code Coverage**
```sql
-- Should cover all ~39,000 ZIPs
SELECT COUNT(DISTINCT zip_code) FROM zip_counties;
```

---

## Comparison: ACA vs Medicare Data Sources

| Aspect | ACA API | Medicare API |
|--------|---------|--------------|
| **Primary Source** | CMS PUF files | CMS Crosswalk + Scraping |
| **Format** | CSV (structured) | CSV + HTML (mixed) |
| **Collection Method** | Direct download | Download + web scraping |
| **Update Time** | 10 minutes | 2-3 weeks |
| **Data Completeness** | Very high | High (with gaps) |
| **Technical Complexity** | Low | High |
| **Legal Concerns** | None | Minimal |
| **Reliability** | Very high | Medium-high |
| **Official Source** | Yes (100%) | Partial (structure only) |

---

## Compliance and Attribution

### Data License

**CMS PUF Files:**
- Public domain
- No restrictions on use
- No attribution required (but recommended)

**Recommended Attribution:**
```
Plan data sourced from CMS Marketplace Public Use Files
Source: Centers for Medicare & Medicaid Services
https://www.cms.gov/marketplace/resources/data/public-use-files
```

### Terms of Use

- ✅ Free to use for any purpose
- ✅ Can redistribute
- ✅ Can modify
- ✅ Commercial use allowed
- ⚠️ No warranty provided (data as-is)
- ⚠️ CMS may change format/availability

---

## Future Enhancements

### Planned Data Additions

**1. Benefits Data**
- Load benefits-and-cost-sharing-puf.csv
- Enable detailed plan comparisons
- Include deductibles, copays, coinsurance

**2. Provider Networks**
- If CMS releases provider network PUFs
- Enable "find doctors" functionality

**3. Formulary Data**
- If CMS releases drug formulary PUFs
- Enable "find my drugs" functionality

**4. Historical Data**
- Load previous years' data
- Enable year-over-year comparisons
- Track plan changes

### Data Quality Improvements

**1. Rate Data Loading**
- Fix plan ID matching issues
- Enable accurate premium quotes
- Support tobacco user rates

**2. Enhanced Validation**
- Cross-check with healthcare.gov
- Automated data quality reports
- Anomaly detection

---

## Technical Documentation

### Code Locations

**Data Loader:**
- `database/load_data.py` - Main loading script
- `database/schema.sql` - Database schema

**Supporting Files:**
- `data/reference/unified_zip_to_fips.json` - ZIP mappings
- `data/reference/fips_to_county_name.json` - County names

**API:**
- `lambda/aca_api.py` - Lambda function
- Queries database in real-time

---

## Statistics

### Current Data (2026 Plan Year)

- **Total Plans:** 20,354
  - Silver: 10,158 (49.9%)
  - Expanded Bronze: 4,615 (22.7%)
  - Gold: 4,679 (23.0%)
  - Bronze: 576 (2.8%)
  - Platinum: 176 (0.9%)
  - Catastrophic: 150 (0.7%)
- **States:** 30 (FFM only)
- **Counties:** 3,244
- **Service Areas:** 255
- **ZIP Codes:** 39,298

---

## Resources

### Official CMS Documentation

- **PUF Homepage:** https://www.cms.gov/marketplace/resources/data/public-use-files
- **Data Dictionary:** https://www.cms.gov/files/document/puf-data-dictionary.pdf
- **Technical Guide:** https://www.cms.gov/files/document/puf-technical-guidance.pdf

### Healthcare.gov

- **Plan Finder:** https://www.healthcare.gov/see-plans/
- **Official enrollment site**

---

## Summary

The ACA API benefits from **high-quality, structured data** directly from CMS. Unlike Medicare which requires complex web scraping, ACA data is:

- ✅ **Official and authoritative**
- ✅ **Complete and comprehensive**
- ✅ **Easy to update** (minutes vs. weeks)
- ✅ **Well-documented** by CMS
- ✅ **Free and public domain**
- ✅ **Structured and clean**

This makes the ACA API **more reliable and easier to maintain** than scraped alternatives.

---

**Last Updated:** January 2026  
**Data Year:** 2026 Plan Year  
**Next Update:** November/December 2026
