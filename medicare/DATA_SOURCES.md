# Medicare API Data Sources

Complete documentation of data sources and collection methodology for the Medicare API.

---

## Overview

The Medicare API combines data from **two primary sources**:

1. **CMS Public Crosswalk Files** - Plan structure and geographic coverage
2. **Medicare.gov Plan Finder** - Detailed plan attributes via web scraping

This hybrid approach provides comprehensive, accurate plan data across all 50 states, DC, and US territories.

---

## Primary Data Sources

### 1. CMS Public Crosswalk Files

**Source:** Centers for Medicare & Medicaid Services (CMS)  
**URL:** https://www.cms.gov/files/zip/2026-plan-crosswalk.zip  
**Update Frequency:** Annual (October)  
**Format:** CSV files

#### Files Used

**a) Plan Crosswalk (`2026_Plan_Crosswalk.csv`)**
- Plan IDs and basic identifiers
- Plan types (MAPD, MA-Only, PDP)
- Contract and segment information
- Parent organization details

**b) Geographic Coverage (`2026_Service_Area.csv`)**
- Plan service areas by county (FIPS codes)
- State and county mappings
- Plan availability by geographic area

#### What We Get From Crosswalk

- ✅ **Plan IDs:** Unique identifiers for all Medicare plans
- ✅ **Plan Types:** Classification (MAPD, MA, PDP)
- ✅ **Contract/Segment:** Organizational structure
- ✅ **Geographic Coverage:** Which counties each plan serves
- ✅ **Parent Organizations:** Company/issuer information

#### Limitations of Crosswalk Data

- ❌ No plan names or marketing names
- ❌ No premium information
- ❌ No benefit details
- ❌ No drug coverage specifics
- ❌ No star ratings
- ❌ No provider network information

---

### 2. Medicare.gov Plan Finder (Web Scraping)

**Source:** Medicare Plan Finder  
**URL:** https://www.medicare.gov/plan-compare/  
**Update Frequency:** Annual (October)  
**Method:** Selenium-based web scraping

#### Why Scraping Was Necessary

CMS does not provide a comprehensive public API or bulk download for detailed plan information. The Plan Finder website contains the most complete, consumer-facing plan details but is only accessible through their interactive web interface.

#### What We Scrape

**Plan Details:**
- ✅ **Plan Name:** Marketing name (e.g., "Humana Gold Plus H1036-258")
- ✅ **Monthly Premium:** Base premium cost
- ✅ **Star Rating:** CMS quality rating (1-5 stars)
- ✅ **Plan Type:** Human-readable type
- ✅ **Special Needs Plan (SNP) Type:** If applicable
- ✅ **Drug Coverage:** Formulary tier structure
- ✅ **Maximum Out-of-Pocket:** Annual cost limit
- ✅ **Part B Premium Reduction:** If offered

**Organization Details:**
- ✅ **Organization Name:** Parent company
- ✅ **Organization Phone:** Customer service number
- ✅ **Organization Website:** Company URL

**Coverage Details:**
- ✅ **Service Area:** Counties/regions covered
- ✅ **Availability:** Plan enrollment status

#### Scraping Methodology

**Tools Used:**
- **Selenium WebDriver** - Browser automation
- **ChromeDriver** - Chrome browser control
- **BeautifulSoup** - HTML parsing (for some states)

**Process:**
1. Navigate to Medicare Plan Finder for specific ZIP code
2. Select year (2026)
3. Filter by plan type (MA, MAPD, PDP)
4. Extract plan cards with details
5. Follow links to detailed plan pages for additional data
6. Parse and structure data into JSON

**State-Specific Scrapers:**

Different states required different scraping approaches due to variations in plan availability and page structure:

- **Generic scraper:** Most states (AK, AL, CO, GA, etc.)
- **State-specific scrapers:** 
  - Arizona (`scrape_arizona.py`)
  - Arkansas (`scrape_arkansas.py`)
  - Florida (`scrape_florida.py`)
  - Massachusetts (`scrape_massachusetts.py`)
  - New Jersey (`scrape_new_jersey.py`)
  - New York (`scrape_new_york.py`)
  - Rhode Island (`scrape_rhode_island.py`)
  - South Carolina (`scrape_south_carolina.py`)
  - Washington (`scrape_washington.py`)

**Challenges Addressed:**
- Rate limiting and CAPTCHA avoidance
- Dynamic content loading (JavaScript rendering)
- Pagination handling
- Session management
- Data quality validation

---

## Data Integration Process

### Step 1: Load Crosswalk Data

```python
# Load plan structure from CMS Crosswalk
crosswalk_plans = load_crosswalk_csv('2026_Plan_Crosswalk.csv')
service_areas = load_crosswalk_csv('2026_Service_Area.csv')
```

**Result:** Base plan structure with ~6,000 plans and geographic mappings

### Step 2: Scrape Plan Details

```bash
# Scrape each state
python3 src/scrapers/state_scrapers/scrape_state_generic.py
```

**Result:** JSON files with detailed plan attributes for each state

### Step 3: Merge Data

```python
# Combine Crosswalk structure with scraped details
merged_plans = merge_crosswalk_with_scraped(crosswalk_plans, scraped_plans)
```

**Matching Logic:**
- Primary: Plan ID match
- Fallback: Contract ID + Plan Type match
- Validation: Geographic area consistency check

### Step 4: Build Static API

```python
# Generate JSON files for each ZIP code
python3 src/builders/build_static_api.py
```

**Result:** ~40,000 JSON files for ZIP code API endpoints

---

## Data Quality and Validation

### Validation Steps

1. **Completeness Check**
   - All plans from Crosswalk have details?
   - All states represented?
   - All ZIP codes mapped?

2. **Consistency Check**
   - Plan IDs match across sources?
   - Geographic coverage aligns?
   - Premium values reasonable?

3. **Accuracy Check**
   - Spot-check against Medicare.gov
   - Validate star ratings
   - Verify organization names

### Known Data Gaps

**Missing Plan Details:**
- Some plans in Crosswalk may not appear in scraped data (usually inactive plans)
- Some new plans may not be in Crosswalk yet

**Incomplete Information:**
- Not all plans have star ratings (new plans)
- Some SNP details may be partial
- Provider network data not included

---

## ZIP Code to County Mapping

**Source:** US Census Bureau ZCTA (ZIP Code Tabulation Areas)  
**URL:** https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.html  
**File:** `unified_zip_to_fips.json`

**Why This Is Critical:**

Medicare plans are defined by **county** coverage, but users search by **ZIP code**. The mapping handles:

- **Simple ZIPs:** One ZIP → One County (majority)
- **Multi-County ZIPs:** One ZIP → Multiple Counties (137 ZIPs)
- **Multi-State ZIPs:** ZIP spans state borders (rare)

**Ratio Calculation:**

For multi-county ZIPs, we calculate the **percentage of ZIP in each county** based on population distribution:

```json
{
  "42223": {
    "primary_state": "KY",
    "states": ["KY", "TN"],
    "counties": {
      "21007": {"name": "Ballard County", "state": "KY", "ratio": 0.85},
      "47095": {"name": "Lake County", "state": "TN", "ratio": 0.15}
    }
  }
}
```

This ensures users see plans from ALL counties their ZIP code touches.

---

## Data Freshness and Updates

### Annual Update Cycle

**October:**
- CMS releases new Crosswalk files
- Medicare Plan Finder updated with new plans

**Update Process:**
1. Download new Crosswalk files
2. Re-scrape all states (or incrementally update)
3. Rebuild static API files
4. Deploy to S3/CloudFront
5. Run comprehensive tests

**Incremental Updates:**

For mid-year plan changes:
```bash
# Update specific states
python3 src/scrapers/state_scrapers/scrape_florida.py
python3 src/builders/build_static_api.py --state FL
./src/deploy/deploy_medicare_api.sh
```

---

## Data Storage and Processing

### Raw Data Storage

**Scraped HTML/JSON:**
- Location: `data/raw/` (not in git)
- Format: HTML files + parsed JSON
- Size: ~2-5 GB total
- Retention: Keep for validation/re-processing

**Processed Data:**
- Location: `data/processed/`
- Format: Structured JSON
- Size: ~50-100 MB
- Content: Merged Crosswalk + scraped data

### Static API Files

**Generated Files:**
- Location: `data/static_api/medicare/`
- Count: ~40,000 JSON files
- Size: ~42 MB total
- Structure:
  ```
  medicare/
  ├── zip/{zipcode}.json          # All plans for ZIP
  ├── zip/{zipcode}_MAPD.json     # MAPD only
  ├── zip/{zipcode}_MA.json       # MA only
  ├── zip/{zipcode}_PD.json       # PD only
  ├── states.json                 # State index
  └── plan/{plan_id}.json         # Individual plans
  ```

---

## Sample Data Flow

### Example: South Carolina ZIP 29401 (Charleston)

**Step 1: Crosswalk Data**
```csv
H5216-030,MAPD,BlueChoice HealthPlan,45019,Charleston County,SC
```

**Step 2: Scraped Data**
```json
{
  "plan_id": "H5216-030",
  "plan_name": "BlueMedicare Choice (PPO)",
  "monthly_premium": 0,
  "star_rating": 4.5,
  "organization_name": "BlueChoice HealthPlan of South Carolina"
}
```

**Step 3: Merged Data**
```json
{
  "plan_id": "H5216-030",
  "plan_name": "BlueMedicare Choice (PPO)",
  "type": "MAPD",
  "monthly_premium": 0,
  "star_rating": 4.5,
  "counties": ["45019"],
  "organization_name": "BlueChoice HealthPlan of South Carolina"
}
```

**Step 4: ZIP API File (`zip/29401.json`)**
```json
{
  "zip_code": "29401",
  "state": "SC",
  "counties": [
    {
      "fips": "45019",
      "name": "Charleston County",
      "plans": [
        {
          "plan_id": "H5216-030",
          "plan_name": "BlueMedicare Choice (PPO)",
          "type": "MAPD",
          "monthly_premium": 0,
          "star_rating": 4.5
        }
        // ... more plans
      ]
    }
  ]
}
```

---

## Compliance and Terms of Service

### CMS Crosswalk Data

**License:** Public domain  
**Terms:** Free to use, no restrictions  
**Attribution:** Not required but recommended

### Medicare.gov Scraping

**Legal Considerations:**
- Medicare.gov is a public government website
- Plan data is publicly available information
- No authentication required for access
- Scraping done at respectful rate (2 requests/second)
- No violation of robots.txt
- Educational/research use case

**Best Practices:**
- Rate limiting to avoid server load
- User-Agent identification
- Respectful crawling behavior
- Data used for public benefit (plan comparison)

---

## Data Accuracy and Disclaimers

### Accuracy Claims

✅ **High Confidence:**
- Plan existence and IDs (from CMS Crosswalk)
- Geographic coverage (from CMS Crosswalk)
- Plan types (from CMS Crosswalk)

⚠️ **Medium Confidence:**
- Plan names (from scraping, may have variations)
- Premiums (accurate at time of scraping, may change)
- Star ratings (updated annually by CMS)

❓ **Use With Caution:**
- Provider networks (not included in our data)
- Formulary details (high-level only)
- Mid-year plan changes (requires re-scraping)

### Disclaimer

This data is provided for informational purposes. Users should **always verify plan details** directly with Medicare.gov or plan providers before making enrollment decisions.

**Official Source:** https://www.medicare.gov/plan-compare/

---

## Technical Implementation

### Code Locations

**Scrapers:**
- `src/scrapers/state_scrapers/` - State-specific scrapers
- `src/scrapers/selenium_scraper.py` - Core scraping logic
- `src/scrapers/parsers/` - HTML parsing utilities

**Builders:**
- `src/builders/build_static_api.py` - Generate JSON files
- `src/builders/build_unified_zip_mapping.py` - ZIP → County mapping

**Data Loading:**
- Load Crosswalk CSVs
- Merge with scraped JSON
- Generate static API

---

## Statistics

### Data Coverage (2026 Plan Year)

- **Total Plans:** 5,734
  - MAPD: 2,844 (49.6%)
  - MA-Only: 1,632 (28.5%)
  - PDP: 1,258 (21.9%)
- **States/Territories:** 51 (all 50 + DC + PR, VI, GU, AS, MP)
- **Counties:** 3,244
- **ZIP Codes:** 39,298
- **Scraped Pages:** ~15,000+
- **Data Collection Time:** ~2-3 weeks (full scrape)

---

## Future Enhancements

### Planned Improvements

1. **Automated Updates**
   - Scheduled scraping (monthly or quarterly)
   - Change detection and alerts
   - Incremental updates only for changed plans

2. **Additional Data Points**
   - Provider directories
   - Pharmacy networks
   - Detailed formulary information
   - Prior authorization requirements

3. **Data Validation**
   - Automated cross-checking with Medicare.gov
   - Historical data comparison
   - Anomaly detection

4. **Performance**
   - Parallel scraping across states
   - Distributed scraping architecture
   - Faster re-indexing

---

## Contact and Questions

For questions about data sources or methodology:
- Review documentation in `docs/scraping/`
- Check state-specific guides in `docs/scraping/state-guides/`
- See scraping process docs in `docs/scraping/successful-process.md`

---

**Last Updated:** January 2026  
**Data Year:** 2026 Medicare Plan Year  
**Next Update:** October 2026
