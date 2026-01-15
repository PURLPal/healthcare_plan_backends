# Adding Providers & Pharmacies to Medicare API

This guide extends the existing Medicare Plan API with provider and pharmacy data.

---

## Overview

**What we're adding:**
- 50,000 providers from NPPES NPI Registry
- 10,000 pharmacies across all 50 states
- New API endpoints for searching providers and pharmacies by ZIP code

**Infrastructure:**
- **Same RDS database** - Adding 2 new tables to existing `medicare_plans` DB
- **Same Lambda function** - Enhanced with new endpoints
- **Same API Gateway** - No changes needed
- **Zero additional cost** - Uses existing infrastructure

---

## Step 1: Add Database Schema

Run the new schema file to create `providers` and `pharmacies` tables:

```bash
cd /Users/andy/medicare_overview_test/database

# Get DB credentials
source db_credentials.json  # or manually export DB_HOST, DB_PASSWORD, etc.

# Apply schema
PGPASSWORD='<password>' psql \
  -h medicare-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com \
  -U medicare_admin \
  -d medicare_plans \
  -f schema_providers_pharmacies.sql
```

**What this creates:**
- `providers` table with indexes on NPI, name, state, ZIP, specialty
- `pharmacies` table with indexes on name, state, ZIP, chain
- Full-text search indexes for both tables
- Useful views: `provider_stats`, `pharmacy_stats`

---

## Step 2: Load Provider & Pharmacy Data

```bash
# Install pg8000 if not already installed
pip3 install pg8000

# Load data from JSON files
python3 load_providers_pharmacies.py \
  "host=medicare-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com dbname=medicare_plans user=medicare_admin password=<password>" \
  /Users/andy/DEMOS_FINAL_SPRINT/purlpal_analytics/apps/healthsherpa/public/data
```

**This will:**
- Load 50 provider JSON files → `providers` table
- Load 50 pharmacy JSON files → `pharmacies` table
- Use bulk inserts (1000 records at a time)
- Show progress for each state
- Display final statistics

**Expected output:**
```
📋 Loading providers from 50 state files...
  Loading AL... ✅ 1,000 providers
  Loading AK... ✅ 1,000 providers
  ...
✅ Total providers loaded: 50,000

💊 Loading pharmacies from 50 state files...
  Loading AL... ✅ 200 pharmacies
  Loading AK... ✅ 200 pharmacies
  ...
✅ Total pharmacies loaded: 10,000
```

---

## Step 3: Update Lambda Function

Replace the Lambda function code with the enhanced version:

```bash
cd /Users/andy/medicare_overview_test/lambda

# Package the new Lambda function
mkdir -p package
pip3 install pg8000==1.30.3 -t package/
cp medicare_api_enhanced.py package/medicare_api.py
cd package && zip -r ../medicare-api-enhanced.zip .
cd ..

# Update Lambda function
aws lambda update-function-code \
  --function-name MedicareAPI \
  --zip-file fileb://medicare-api-enhanced.zip \
  --profile silverman \
  --region us-east-1
```

**No environment variable changes needed** - uses same DB connection.

---

## Step 4: Test New Endpoints

### Provider Search

```bash
# Search providers by ZIP code and name
curl "https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/providers?zip=02108&search=smith&limit=10" | jq .

# Get random providers in a state
curl "https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/providers?zip=90210&limit=5" | jq .
```

**Response:**
```json
{
  "zip_code": "02108",
  "state": "MA",
  "search_term": "smith",
  "count": 10,
  "providers": [
    {
      "npi": "1234567890",
      "first_name": "John",
      "last_name": "Smith",
      "credentials": "MD",
      "specialty": "Internal Medicine",
      "gender": "M",
      "practice_address": "123 Main St",
      "practice_city": "Boston",
      "practice_state": "MA",
      "practice_zip": "02108",
      "practice_phone": "617-555-1234"
    }
  ]
}
```

### Pharmacy Search

```bash
# Search pharmacies by ZIP code and name
curl "https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/pharmacies?zip=02108&search=cvs&limit=10" | jq .

# Get random pharmacies in a state
curl "https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/pharmacies?zip=10001&limit=5" | jq .
```

**Response:**
```json
{
  "zip_code": "02108",
  "state": "MA",
  "search_term": "cvs",
  "count": 5,
  "retail": [
    {
      "license_number": "MA12345",
      "name": "CVS 1234",
      "chain": "CVS",
      "address": "456 Boylston St",
      "city": "Boston",
      "state": "MA",
      "zip": "02108",
      "manager_first_name": "Jane",
      "manager_last_name": "Doe",
      "controlled_substances": true,
      "full_address": "Jane Doe, 456 Boylston St, Boston, MA 02108"
    }
  ]
}
```

---

## New API Endpoints

### Providers

**Endpoint:** `GET /medicare/providers`

**Query Parameters:**
- `zip` (required) - 5-digit ZIP code
- `search` (optional) - Search by name, NPI, or specialty
- `limit` (optional) - Max results (default 10, max 100)

**Examples:**
```bash
# Search by last name
/medicare/providers?zip=02108&search=smith&limit=10

# Search by specialty
/medicare/providers?zip=90210&search=cardiology&limit=5

# Search by NPI
/medicare/providers?zip=33101&search=1234567890

# Random sample from state
/medicare/providers?zip=60601&limit=20
```

### Pharmacies

**Endpoint:** `GET /medicare/pharmacies`

**Query Parameters:**
- `zip` (required) - 5-digit ZIP code
- `search` (optional) - Search by name, city, or chain
- `limit` (optional) - Max results (default 10, max 100)

**Examples:**
```bash
# Search by chain
/medicare/pharmacies?zip=02108&search=walgreens&limit=10

# Search by city
/medicare/pharmacies?zip=90210&search=los+angeles&limit=5

# Random sample from state
/medicare/pharmacies?zip=10001&limit=20
```

---

## Database Statistics

After loading, check statistics:

```sql
-- Provider counts
SELECT COUNT(*) FROM providers;  -- 50,000

-- Pharmacy counts
SELECT COUNT(*) FROM pharmacies;  -- 10,000

-- By state
SELECT * FROM provider_stats ORDER BY provider_count DESC LIMIT 10;
SELECT * FROM pharmacy_stats ORDER BY pharmacy_count DESC LIMIT 10;

-- Index usage
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE tablename IN ('providers', 'pharmacies');
```

---

## Integration with HealthPorter & Moonlight

### Before (Static Files)
```typescript
// Client loads 1000 providers from JSON
fetch('/data/ma_providers.json')
  .then(res => res.json())
  .then(data => {
    // Filter client-side
    const matches = data.providers.filter(p => 
      p.last_name.toLowerCase().includes(search)
    );
  });
```

### After (API)
```typescript
// Server returns only matching results
fetch(`https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/providers?zip=${zip}&search=${search}&limit=10`)
  .then(res => res.json())
  .then(data => {
    // Already filtered, ready to display
    setProviders(data.providers);
  });
```

**Benefits:**
- ✅ **90% smaller payload** - 10 results vs 1000
- ✅ **Faster response** - Server-side indexed search
- ✅ **Cross-state search** - Not limited to single state file
- ✅ **Centralized data** - Update once, available everywhere

---

## Performance

**Query Performance:**
- Provider search: ~50-100ms (indexed)
- Pharmacy search: ~50-100ms (indexed)
- Full-text search: ~100-200ms

**Lambda:**
- Cold start: ~500ms (first request)
- Warm requests: ~100-200ms
- Memory: 512 MB (same as before)
- Timeout: 30 seconds (same as before)

**Database:**
- Same RDS instance (db.t3.micro)
- Indexes optimized for common queries
- Connection pooling via Lambda

---

## Cost Impact

**Zero additional cost!**

Uses existing infrastructure:
- Same RDS instance (no size increase needed)
- Same Lambda function (minimal memory increase)
- Same API Gateway

**Storage increase:**
- Providers: ~50MB
- Pharmacies: ~10MB
- Indexes: ~20MB
- **Total: ~80MB** (well within db.t3.micro 20GB limit)

---

## Rollback Plan

If needed, roll back to original Lambda:

```bash
# Restore original Lambda code
aws lambda update-function-code \
  --function-name MedicareAPI \
  --zip-file fileb://medicare-api-original.zip \
  --profile silverman \
  --region us-east-1
```

Database tables remain but won't affect existing plan endpoints.

To remove tables:
```sql
DROP TABLE IF EXISTS pharmacies CASCADE;
DROP TABLE IF EXISTS providers CASCADE;
```

---

## Next Steps

1. **Test locally** - Verify schema and data load
2. **Update Lambda** - Deploy enhanced API
3. **Update HealthPorter** - Switch from static files to API
4. **Update Moonlight** - Use same API endpoints
5. **Monitor** - Check CloudWatch logs for performance

---

## Support Files

- `schema_providers_pharmacies.sql` - Database schema
- `load_providers_pharmacies.py` - Data loader
- `medicare_api_enhanced.py` - Enhanced Lambda function
- `DEPLOY_PROVIDERS_PHARMACIES.md` - This guide

---

**Ready to deploy!** Start with Step 1 above.
