# Healthcare Plan Backends

Monorepo containing backend APIs for Medicare and ACA marketplace health insurance plans.

---

## 🏥 APIs

### Medicare API
**URL:** `https://medicare.purlpal-api.com/medicare`

- **Plans:** 5,734 Medicare Advantage (MA), Medicare Advantage Prescription Drug (MAPD), and Part D plans
- **Coverage:** All 50 states + DC + territories
- **Architecture:** Static JSON files on S3 + CloudFront
- **Data Source:** Medicare.gov Plan Finder (scraped)

### ACA API
**URL:** `https://aca.purlpal-api.com/aca`

- **Plans:** 20,354 ACA marketplace medical plans
- **Coverage:** 30 federally-facilitated marketplace states
- **Architecture:** PostgreSQL RDS + Lambda + API Gateway
- **Data Source:** CMS.gov Public Use Files

---

## 📁 Repository Structure

```
healthcare_plan_backends/
├── medicare/           # Medicare API backend
│   ├── database/       # PostgreSQL schema and loaders
│   ├── lambda/         # Lambda functions
│   ├── src/            # Source code (scrapers, builders, parsers)
│   ├── tests/          # API tests
│   └── docs/           # Documentation
├── aca/                # ACA API backend
│   ├── database/       # PostgreSQL schema and loaders
│   ├── lambda/         # Lambda function
│   ├── tests/          # API tests
│   └── docs/           # Documentation
└── shared/             # Shared resources
    ├── unified_zip_to_fips.json    # ZIP to county mapping
    └── fips_to_county_name.json    # County reference data
```

---

## 🚀 Quick Start

### Medicare API

```bash
cd medicare

# Build static API files
python3 src/builders/build_static_api.py

# Deploy to AWS
./src/deploy/deploy_medicare_api.sh

# Test
./tests/test_live_api.sh
```

### ACA API

```bash
cd aca

# Load data into RDS
python3 database/load_data.py "host=<RDS_HOST> dbname=aca_plans user=aca_admin password=<PASSWORD>"

# Deploy Lambda
cd lambda
zip -r aca-api.zip .
aws lambda update-function-code --function-name ACA_API --zip-file fileb://aca-api.zip

# Test
python3 tests/test_api_comprehensive.py 5
```

---

## 🗺️ Shared Resources

### ZIP Code to County Mapping

**File:** `shared/unified_zip_to_fips.json`

Maps ZIP codes to counties (FIPS codes) with support for multi-county ZIPs.

```json
{
  "02108": {
    "primary_state": "MA",
    "states": ["MA"],
    "counties": {
      "25025": {
        "name": "Suffolk County",
        "state": "MA",
        "ratio": 1.0
      }
    }
  }
}
```

### County Reference Data

**File:** `shared/fips_to_county_name.json`

Maps FIPS codes to county names and states.

```json
{
  "25025": {
    "name": "Suffolk County",
    "state": "MA"
  }
}
```

---

## 🛠️ Technology Stack

### Medicare API
- **Frontend:** Static JSON files (~40,000 files, 42MB total)
- **Storage:** AWS S3
- **CDN:** CloudFront
- **DNS:** Route 53
- **Build:** Python scripts

### ACA API
- **Database:** PostgreSQL 15.8 on RDS (db.t3.micro)
- **API:** AWS Lambda (Python 3.11) + API Gateway
- **Connection Pooling:** pg8000 with persistent connections
- **DNS:** Route 53

---

## 📊 Data Coverage

### Medicare API
- **States:** All 50 + DC + PR, VI, GU, AS, MP
- **Plans:** 5,734 total
  - MAPD: 2,844 plans
  - MA-Only: 1,632 plans
  - PD: 1,258 plans
- **ZIP Codes:** 39,298
- **Update Frequency:** Annual (October)

### ACA API
- **States:** 30 federal marketplace states
  - AK, AL, AR, AZ, DE, FL, HI, IA, IN, KS, LA, ME, MI, MO, MS, MT, NC, ND, NE, NH, OH, OK, SC, SD, TN, TX, UT, VA, WI, WY
- **Plans:** 20,354 total
  - Silver: 10,158 (49.9%)
  - Expanded Bronze: 4,615 (22.7%)
  - Gold: 4,679 (23.0%)
  - Bronze: 576 (2.8%)
  - Platinum: 176 (0.9%)
  - Catastrophic: 150 (0.7%)
- **ZIP Codes:** 39,298
- **Update Frequency:** Annual (November)

---

## 🧪 Testing

### Comprehensive API Tests

Both APIs have comprehensive test suites that test multiple ZIP codes per state:

```bash
# Medicare API - test 5 ZIPs per state
cd medicare
python3 tests/test_api_comprehensive.py 5

# ACA API - test 5 ZIPs per state
cd aca
python3 tests/test_api_comprehensive.py 5
```

### Quick Tests

```bash
# Medicare
cd medicare
./tests/test_live_api.sh

# ACA
cd aca
./tests/quick_test.sh
```

---

## 📖 Documentation

### Medicare API
- **User Guide:** `medicare/docs/api/user-guide.md`
- **API Reference:** `medicare/docs/api/reference.md`
- **Architecture:** `medicare/docs/api/architecture.md`
- **Deployment:** `medicare/docs/deployment/`
- **Scraping Guide:** `medicare/docs/scraping/guide.md`

### ACA API
- **Quick Start:** `aca/QUICK_START.md`
- **User Guide:** `aca/README.md`
- **Deployment Guide:** `aca/DEPLOYMENT_GUIDE.md`
- **Implementation Plan:** `aca/ACA_API_IMPLEMENTATION_PLAN.md`
- **Deployment Success:** `aca/DEPLOYMENT_SUCCESS.md`

---

## 🔄 Update Process

### Medicare API (Annual Updates)

1. **Scrape new data** (October)
   ```bash
   cd medicare/src/scrapers/state_scrapers
   python3 scrape_state_generic.py
   ```

2. **Build static API**
   ```bash
   python3 src/builders/build_static_api.py
   ```

3. **Deploy to S3**
   ```bash
   ./src/deploy/deploy_medicare_api.sh
   ```

4. **Test**
   ```bash
   python3 tests/test_api_comprehensive.py 10
   ```

### ACA API (Annual Updates)

1. **Download new data** from CMS.gov (November)
   - Plan attributes
   - Service areas
   - Rates
   - Benefits

2. **Load into database**
   ```bash
   python3 database/load_data.py "<connection_string>"
   ```

3. **Test**
   ```bash
   python3 tests/test_api_comprehensive.py 10
   ```

---

## 💰 AWS Costs

### Medicare API
- **S3:** ~$0.50/month (storage)
- **CloudFront:** ~$1-5/month (depends on traffic)
- **Route 53:** $0.50/month (hosted zone)
- **Total:** ~$2-6/month

### ACA API
- **RDS (db.t3.micro):** ~$15-20/month
- **Lambda:** ~$2-5/month
- **API Gateway:** ~$1-3/month
- **Route 53:** $0.50/month
- **Total:** ~$20-30/month

**Combined:** ~$25-35/month

---

## 🔒 Security

- ✅ HTTPS only (SSL/TLS via ACM)
- ✅ CORS enabled for web access
- ✅ No hardcoded credentials
- ✅ IAM roles with minimal permissions
- ✅ Database credentials in environment variables
- ✅ `.gitignore` excludes secrets and credentials

---

## 📝 What's NOT Version Controlled

Per `.gitignore`:
- Raw scraped data (CSV, HTML, JSON)
- Processed data files
- Static API files (~40,000 files for Medicare)
- Database dumps
- Credentials and secrets
- Lambda deployment packages
- Build artifacts

**What IS version controlled:**
- Source code (scrapers, builders, API)
- Database schemas
- Lambda functions
- Documentation
- Tests
- Shared reference data (ZIP mappings, county data)

---

## 🤝 Contributing

### Adding a New State (Medicare)

1. Create scraper in `medicare/src/scrapers/state_scrapers/`
2. Create parser in `medicare/src/scrapers/parsers/`
3. Add state guide in `medicare/docs/scraping/state-guides/`
4. Test with single county
5. Run full state scrape
6. Rebuild static API
7. Deploy

### Updating ACA Data

1. Download new PUF files from CMS.gov
2. Place in `aca/data/raw/`
3. Update `aca/database/load_data.py` if schema changed
4. Reload database
5. Test API endpoints

---

## 📞 Support

- **Medicare API Issues:** Check `medicare/docs/`
- **ACA API Issues:** Check `aca/DEPLOYMENT_SUCCESS.md`
- **AWS Console:** CloudWatch Logs for Lambda errors
- **Testing:** Run comprehensive tests to identify issues

---

## 🎯 Architecture Comparison

| Feature | Medicare API | ACA API |
|---------|--------------|---------|
| **Approach** | Static files | Database-backed |
| **Storage** | S3 (42MB) | PostgreSQL (20GB) |
| **Compute** | None (CDN only) | Lambda |
| **Cold Start** | None | ~1.5s |
| **Warm Response** | ~100-200ms | ~300-500ms |
| **Scaling** | CloudFront CDN | Lambda autoscaling |
| **Cost** | $2-6/month | $20-30/month |
| **Updates** | Rebuild all files | Database reload |
| **Data Source** | Scraped | CMS PUF files |

---

## 🌟 Key Features

### Both APIs
- ✅ Multi-county ZIP support
- ✅ Metal level / category filtering
- ✅ Plan detail endpoints
- ✅ State information endpoints
- ✅ OpenAPI specifications
- ✅ Comprehensive test suites
- ✅ Custom domains with SSL
- ✅ CORS enabled

### Medicare API Specific
- ✅ Minified responses
- ✅ Priority plan filtering
- ✅ Category-based filtering (MAPD, MA, PD)

### ACA API Specific
- ✅ Age-based rate tables (when loaded)
- ✅ Service area coverage
- ✅ Connection pooling
- ✅ Statewide plan support

---

## 📅 Last Updated

- **Medicare API:** January 2026
- **ACA API:** January 2026
- **Repository Created:** January 14, 2026

---

## 🏆 Production Status

| API | Status | URL | Plans | Coverage |
|-----|--------|-----|-------|----------|
| **Medicare** | ✅ Live | medicare.purlpal-api.com | 5,734 | 51 states/territories |
| **ACA** | ✅ Live | aca.purlpal-api.com | 20,354 | 30 states |

Both APIs are production-ready and serving live traffic! 🎉
