# ACA Plan API

Database-backed API for ACA (Affordable Care Act) marketplace plan lookup by ZIP code.

## Overview

- **Plans:** 19,272 medical plans (2026 Individual market)
- **Coverage:** ~32 federally-facilitated states
- **Metal Levels:** Bronze, Silver, Gold, Platinum, Catastrophic
- **Geography:** County-based service areas
- **API URL:** `https://aca.purlpal-api.com/aca/` (when deployed)

## Quick Start

### Get plans for a ZIP code
```bash
curl "https://aca.purlpal-api.com/aca/zip/90210.json"
```

### Filter by metal level
```bash
curl "https://aca.purlpal-api.com/aca/zip/90210_Silver.json"
curl "https://aca.purlpal-api.com/aca/zip/90210_Gold.json"
```

### List all states
```bash
curl "https://aca.purlpal-api.com/aca/states.json"
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /aca/zip/{zipcode}.json` | All plans for ZIP code |
| `GET /aca/zip/{zipcode}_{metal}.json` | Filter by metal level |
| `GET /aca/states.json` | List all states |
| `GET /aca/state/{STATE}/info.json` | State information |
| `GET /aca/plan/{plan_id}.json` | Individual plan details |
| `GET /aca/openapi.yaml` | OpenAPI specification |

## Metal Levels

- **Bronze:** ~60% actuarial value (lower premiums, higher out-of-pocket)
- **Silver:** ~70% actuarial value (moderate premiums and costs)
- **Gold:** ~80% actuarial value (higher premiums, lower out-of-pocket)
- **Platinum:** ~90% actuarial value (highest premiums, lowest out-of-pocket)
- **Catastrophic:** Emergency coverage only (age < 30 or hardship exemption)

## Response Format

### ZIP Code Query Response

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
      "plans": [
        {
          "plan_id": "12345MA0010001-01",
          "issuer_name": "Blue Cross Blue Shield",
          "plan_name": "Silver Saver Plan",
          "plan_type": "HMO",
          "metal_level": "Silver",
          "rate_age_40": 425.50
        }
      ],
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

## Architecture

### Database Schema

- **PostgreSQL** on AWS RDS
- **Tables:** plans, service_areas, rates, benefits, zip_counties
- **Connection pooling** for performance

### Lambda Function

- **Runtime:** Python 3.11
- **Handler:** `aca_api.lambda_handler`
- **Memory:** 512 MB
- **Timeout:** 30 seconds
- **Connection pooling:** Reuses DB connections across invocations

### API Gateway

- HTTP API (v2)
- Custom domain: `aca.purlpal-api.com`
- CORS enabled for all origins

## Data Sources

ACA plan data from CMS.gov:
- Plan Attributes PUF (Public Use File)
- Service Area PUF
- Rate PUF
- Benefits and Cost Sharing PUF

Data year: **2026**

Sources:
- https://www.cms.gov/marketplace/resources/data/public-use-files
- https://data.healthcare.gov/

## Setup

### Prerequisites

- AWS account with permissions for RDS, Lambda, API Gateway
- AWS CLI configured
- PostgreSQL client
- Python 3.11+

### 1. Create RDS Database

```bash
# Create PostgreSQL database
aws rds create-db-instance \
  --db-instance-identifier aca-plans-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username aca_admin \
  --master-user-password <PASSWORD> \
  --allocated-storage 20 \
  --publicly-accessible \
  --backup-retention-period 7 \
  --region us-east-1
```

### 2. Initialize Database Schema

```bash
# Create schema
psql -h <RDS_ENDPOINT> -U aca_admin -d aca_plans -f database/schema.sql
```

### 3. Load Data

```bash
# Install dependencies
pip3 install psycopg2-binary

# Load data
python3 database/load_data.py "host=<RDS_ENDPOINT> dbname=aca_plans user=aca_admin password=<PASSWORD>"
```

### 4. Deploy Lambda Function

```bash
cd lambda
mkdir package
pip3 install --target ./package pg8000
cp aca_api.py package/
cd package
zip -r ../aca-api.zip .
cd ..

# Upload to Lambda
aws lambda create-function \
  --function-name ACA_API \
  --runtime python3.11 \
  --handler aca_api.lambda_handler \
  --role <LAMBDA_ROLE_ARN> \
  --zip-file fileb://aca-api.zip \
  --environment Variables="{DB_HOST=<RDS_ENDPOINT>,DB_PORT=5432,DB_NAME=aca_plans,DB_USER=aca_admin,DB_PASSWORD=<PASSWORD>}" \
  --timeout 30 \
  --memory-size 512 \
  --region us-east-1
```

### 5. Set up API Gateway

1. Create HTTP API
2. Add route: `ANY /aca/{proxy+}`
3. Integrate with Lambda function
4. Configure custom domain
5. Deploy

## Performance

- **Response time:** 300-500ms (warm requests with connection pooling)
- **Cold start:** ~1.5s (first request after idle)
- **Database queries:** Optimized with indexes
- **Connection pooling:** Reuses connections across Lambda invocations

## Testing

```bash
# Run quick API test
./tests/quick_test.sh

# Test specific ZIP codes
curl "https://aca.purlpal-api.com/aca/zip/02108.json" | jq '.plan_count'
curl "https://aca.purlpal-api.com/aca/zip/90210_Silver.json" | jq '.plan_counts_by_metal_level'
```

## Multi-County ZIP Codes

Some ZIP codes span multiple counties. The API returns plans for **all counties** that the ZIP intersects:

```json
{
  "zip_code": "12345",
  "multi_county": true,
  "counties": [
    {
      "name": "County A",
      "ratio": 0.8,
      "plans": [...]
    },
    {
      "name": "County B", 
      "ratio": 0.2,
      "plans": [...]
    }
  ]
}
```

The `ratio` field indicates what percentage of the ZIP code falls within each county.

## Differences from Medicare API

| Feature | Medicare API | ACA API |
|---------|--------------|---------|
| **Market** | Medicare Advantage + Part D | ACA Individual Marketplace |
| **Categories** | MAPD, MA, PD | Bronze, Silver, Gold, Platinum |
| **Age Factor** | No (65+ only) | Yes (rates vary 21-64) |
| **Plans** | 5,734 | 19,272 |
| **States** | All 50 + DC | ~32 federally-facilitated |

## Cost Estimate

- **RDS PostgreSQL (db.t3.micro):** $15-25/month
- **Lambda:** $5/month (with free tier)
- **API Gateway:** $1-5/month (depends on usage)
- **Total:** ~$20-35/month

## Limitations

- **State-based exchanges:** CA, NY, CO, etc. are not included (they run their own exchanges)
- **SHOP plans:** Not included (focus on Individual market)
- **Dental plans:** Excluded by default
- **Rates:** Vary by age, location, tobacco use (API returns age 40 as default)

## Development

### Project Structure

```
aca_overview_test/
├── data/
│   ├── raw/              # Source CSV files
│   └── reference/        # ZIP-to-county mappings
├── database/
│   ├── schema.sql        # Database schema
│   └── load_data.py      # Data loading script
├── lambda/
│   └── aca_api.py        # Lambda function
├── tests/
│   └── quick_test.sh     # API test script
└── docs/
    └── ACA_API_IMPLEMENTATION_PLAN.md
```

## Support

For questions or issues:
- Check OpenAPI spec: `/aca/openapi.yaml`
- Review implementation plan: `docs/ACA_API_IMPLEMENTATION_PLAN.md`
- Test locally before deploying

## License

Public domain - ACA plan data is publicly available from CMS.gov.
