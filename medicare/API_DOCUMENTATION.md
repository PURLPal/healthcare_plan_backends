# Medicare API Documentation

**Base URL:** `https://medicare.purlpal-api.com`

Complete API for Medicare plans, healthcare providers, and pharmacies across all 50 US states.

---

## Table of Contents

1. [Overview](#overview)
2. [Provider Endpoints](#provider-endpoints)
3. [Pharmacy Endpoints](#pharmacy-endpoints)
4. [Plan Endpoints](#plan-endpoints)
5. [Response Formats](#response-formats)
6. [Error Handling](#error-handling)
7. [Integration Examples](#integration-examples)
8. [Rate Limits & Performance](#rate-limits--performance)

---

## Overview

### API Statistics
- **50,000 healthcare providers** (NPPES NPI Registry)
- **9,891 pharmacies** across 50 states
- **5,804 Medicare plans** with county-level coverage
- **39,298 ZIP codes** mapped
- **Response time:** 50-200ms average

### Authentication
No authentication required. CORS enabled for all origins.

### Base URL
```
https://medicare.purlpal-api.com
```

---

## Provider Endpoints

### Search Providers

Search for healthcare providers by ZIP code, name, NPI, or specialty.

**Endpoint:**
```
GET /medicare/providers
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `zip` | string | Yes | 5-digit ZIP code |
| `search` | string | No | Search by name, NPI, or specialty |
| `limit` | integer | No | Max results (default: 10, max: 100) |

**Examples:**

```bash
# Search by last name
curl "https://medicare.purlpal-api.com/medicare/providers?zip=02108&search=smith&limit=10"

# Search by specialty
curl "https://medicare.purlpal-api.com/medicare/providers?zip=90210&search=cardiology&limit=5"

# Search by NPI
curl "https://medicare.purlpal-api.com/medicare/providers?zip=10001&search=1234567890"

# Random providers in a ZIP code
curl "https://medicare.purlpal-api.com/medicare/providers?zip=60601&limit=20"
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
      "middle_name": "A",
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

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `npi` | string | National Provider Identifier (10 digits) |
| `first_name` | string | Provider first name |
| `last_name` | string | Provider last name |
| `credentials` | string | Professional credentials (MD, DO, NP, etc.) |
| `specialty` | string | Medical specialty or taxonomy description |
| `gender` | string | M, F, or null |
| `practice_address` | string | Practice location street address |
| `practice_city` | string | Practice city |
| `practice_state` | string | Practice state (2-letter code) |
| `practice_zip` | string | Practice ZIP code (5 digits) |
| `practice_phone` | string | Practice phone number |

---

## Pharmacy Endpoints

### Search Pharmacies

Search for retail pharmacies by ZIP code, name, city, or chain.

**Endpoint:**
```
GET /medicare/pharmacies
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `zip` | string | Yes | 5-digit ZIP code |
| `search` | string | No | Search by name, city, or chain |
| `limit` | integer | No | Max results (default: 10, max: 100) |

**Examples:**

```bash
# Search by chain
curl "https://medicare.purlpal-api.com/medicare/pharmacies?zip=02108&search=walgreens&limit=10"

# Search by city
curl "https://medicare.purlpal-api.com/medicare/pharmacies?zip=90210&search=los+angeles&limit=5"

# Search by name
curl "https://medicare.purlpal-api.com/medicare/pharmacies?zip=10001&search=cvs"

# Random pharmacies in a ZIP code
curl "https://medicare.purlpal-api.com/medicare/pharmacies?zip=60601&limit=20"
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

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `license_number` | string | State pharmacy license number |
| `name` | string | Pharmacy name |
| `chain` | string | Pharmacy chain (CVS, Walgreens, etc.) or null |
| `address` | string | Street address |
| `city` | string | City |
| `state` | string | State (2-letter code) |
| `zip` | string | ZIP code (5 digits) |
| `manager_first_name` | string | Pharmacy manager first name |
| `manager_last_name` | string | Pharmacy manager last name |
| `controlled_substances` | boolean | Licensed for controlled substances |
| `full_address` | string | Complete address string for display |

---

## Plan Endpoints

### Get Plans by ZIP Code

Get all Medicare plans available in a ZIP code.

**Endpoint:**
```
GET /medicare/zip/{zip_code}.json
GET /medicare/zip/{zip_code}_{category}.json
```

**Categories:** `MAPD`, `MA`, `PD`

**Examples:**

```bash
# All plans
curl "https://medicare.purlpal-api.com/medicare/zip/02108.json"

# MAPD plans only
curl "https://medicare.purlpal-api.com/medicare/zip/02108_MAPD.json"

# Medicare Advantage only
curl "https://medicare.purlpal-api.com/medicare/zip/02108_MA.json"
```

**Response:**

```json
{
  "zip_code": "02108",
  "multi_county": false,
  "multi_state": false,
  "states": ["MA"],
  "primary_state": "MA",
  "counties": [
    {
      "id": 8146,
      "name": "Suffolk County",
      "fips": "25025",
      "state": "MA",
      "ratio": 1.0
    }
  ],
  "plans": [
    {
      "plan_id": "H0777_001_0",
      "category": "MAPD",
      "plan_type": "HMO",
      "plan_info": {...},
      "premiums": {...},
      "deductibles": {...},
      "out_of_pocket": {...},
      "benefits": {...}
    }
  ],
  "plan_count": 50
}
```

### List All States

Get all states with plan counts.

**Endpoint:**
```
GET /medicare/states.json
```

**Response:**

```json
{
  "state_count": 51,
  "total_plans": 5804,
  "states": [
    {
      "abbrev": "AL",
      "name": "Alabama",
      "plan_count": 110,
      "info_url": "/medicare/state/AL/info.json",
      "plans_url": "/medicare/state/AL/plans.json"
    }
  ]
}
```

### State Information

**Endpoint:**
```
GET /medicare/state/{state}/info.json
```

**Example:**
```bash
curl "https://medicare.purlpal-api.com/medicare/state/MA/info.json"
```

**Response:**
```json
{
  "state": "Massachusetts",
  "state_abbrev": "MA",
  "plan_count": 94
}
```

### State Plans

Get all plans in a state.

**Endpoint:**
```
GET /medicare/state/{state}/plans.json
```

**Example:**
```bash
curl "https://medicare.purlpal-api.com/medicare/state/MA/plans.json"
```

### Individual Plan Details

**Endpoint:**
```
GET /medicare/plan/{plan_id}.json
```

**Example:**
```bash
curl "https://medicare.purlpal-api.com/medicare/plan/H0777_001_0.json"
```

---

## Response Formats

### Success Response
All successful responses return JSON with appropriate data.

**HTTP Status:** `200 OK`

```json
{
  "data": "...",
  "count": 10
}
```

### Error Responses

**400 Bad Request** - Missing or invalid parameters
```json
{
  "error": "ZIP code required",
  "usage": "/medicare/providers?zip=12345&search=smith&limit=10"
}
```

**404 Not Found** - Resource not found
```json
{
  "error": "ZIP code not found"
}
```

**500 Internal Server Error** - Server error
```json
{
  "error": "Internal server error",
  "message": "Database connection failed"
}
```

---

## Error Handling

### Best Practices

1. **Always check HTTP status code** before parsing JSON
2. **Handle empty results gracefully** - Empty arrays are valid responses
3. **Validate ZIP codes** client-side before making requests
4. **Implement retry logic** with exponential backoff for 5xx errors

### Example Error Handling (JavaScript)

```javascript
async function searchProviders(zip, search = '') {
  try {
    const response = await fetch(
      `https://medicare.purlpal-api.com/medicare/providers?zip=${zip}&search=${encodeURIComponent(search)}&limit=10`
    );
    
    if (!response.ok) {
      if (response.status === 404) {
        return { error: 'ZIP code not found', providers: [] };
      }
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error('Provider search failed:', error);
    return { error: error.message, providers: [] };
  }
}
```

---

## Integration Examples

### React/Next.js

```typescript
import { useState, useEffect } from 'react';

interface Provider {
  npi: string;
  first_name: string;
  last_name: string;
  credentials: string;
  specialty: string;
  practice_address: string;
  practice_city: string;
  practice_state: string;
  practice_zip: string;
  practice_phone: string;
}

function ProviderSearch({ zipCode }: { zipCode: string }) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!zipCode || search.length < 2) {
      setProviders([]);
      return;
    }

    const fetchProviders = async () => {
      setLoading(true);
      try {
        const response = await fetch(
          `https://medicare.purlpal-api.com/medicare/providers?zip=${zipCode}&search=${encodeURIComponent(search)}&limit=10`
        );
        const data = await response.json();
        setProviders(data.providers || []);
      } catch (error) {
        console.error('Failed to fetch providers:', error);
        setProviders([]);
      } finally {
        setLoading(false);
      }
    };

    const debounce = setTimeout(fetchProviders, 300);
    return () => clearTimeout(debounce);
  }, [zipCode, search]);

  return (
    <div>
      <input
        type="text"
        placeholder="Search providers..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {loading && <div>Loading...</div>}
      <ul>
        {providers.map((provider) => (
          <li key={provider.npi}>
            <strong>{provider.first_name} {provider.last_name}, {provider.credentials}</strong>
            <div>{provider.specialty}</div>
            <div>{provider.practice_address}, {provider.practice_city}, {provider.practice_state}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Pharmacy Search

```typescript
interface Pharmacy {
  license_number: string;
  name: string;
  chain: string | null;
  address: string;
  city: string;
  state: string;
  zip: string;
  full_address: string;
}

async function searchPharmacies(
  zipCode: string,
  searchTerm: string,
  limit: number = 10
): Promise<Pharmacy[]> {
  const response = await fetch(
    `https://medicare.purlpal-api.com/medicare/pharmacies?zip=${zipCode}&search=${encodeURIComponent(searchTerm)}&limit=${limit}`
  );
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  const data = await response.json();
  return data.retail || [];
}
```

---

## Rate Limits & Performance

### Performance Characteristics

| Metric | Value |
|--------|-------|
| **Average Response Time** | 50-200ms |
| **Cold Start** | ~500ms (first request) |
| **Warm Requests** | ~100ms |
| **Database** | PostgreSQL 15.8 with indexes |
| **Region** | us-east-1 |

### Rate Limits

Currently **no rate limits** are enforced. However:
- Keep requests reasonable (< 100/second)
- Implement client-side caching for repeated queries
- Use debouncing for search-as-you-type features

### Caching Recommendations

**Provider & Pharmacy Searches:**
- Cache results for 5-10 minutes
- Cache by `zip + search + limit` key

**Medicare Plans:**
- Cache for 24 hours
- Plans update quarterly

**Example with React Query:**

```typescript
import { useQuery } from '@tanstack/react-query';

function useProviderSearch(zip: string, search: string) {
  return useQuery({
    queryKey: ['providers', zip, search],
    queryFn: async () => {
      const response = await fetch(
        `https://medicare.purlpal-api.com/medicare/providers?zip=${zip}&search=${search}&limit=10`
      );
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: zip.length === 5 && search.length >= 2,
  });
}
```

---

## Data Sources & Accuracy

### Providers
- **Source:** NPPES NPI Registry (CMS official database)
- **Records:** 50,000 active individual providers
- **Coverage:** All 50 US states
- **Fields:** NPI, name, credentials, specialty, practice location
- **Update Frequency:** Data from December 2024 snapshot

### Pharmacies
- **Source:** Generated demo data (realistic samples)
- **Records:** 9,891 retail pharmacies
- **Coverage:** All 50 US states
- **Chains:** CVS, Walgreens, Rite Aid, Walmart, Costco, Target, etc.
- **Note:** Demo data for development/testing purposes

### Medicare Plans
- **Source:** CMS Medicare Plan Finder
- **Records:** 5,804 plans
- **Coverage:** 56 states/territories, 39,298 ZIP codes
- **Update Frequency:** Quarterly (plan year updates)

---

## Support & Contact

**API Endpoint:** https://medicare.purlpal-api.com  
**Documentation:** This file  
**Status:** Production Ready ✅

**Infrastructure:**
- AWS RDS PostgreSQL 15.8
- AWS Lambda (Python 3.11)
- AWS API Gateway (HTTP API)
- CloudFront CDN via custom domain

**Cost:** ~$15-25/month (shared infrastructure)

---

## Quick Reference

### All Endpoints Summary

```bash
# Providers
GET /medicare/providers?zip={ZIP}&search={TERM}&limit={NUM}

# Pharmacies
GET /medicare/pharmacies?zip={ZIP}&search={TERM}&limit={NUM}

# Plans by ZIP
GET /medicare/zip/{ZIP}.json
GET /medicare/zip/{ZIP}_{CATEGORY}.json

# States
GET /medicare/states.json
GET /medicare/state/{STATE}/info.json
GET /medicare/state/{STATE}/plans.json

# Individual Plan
GET /medicare/plan/{PLAN_ID}.json
```

### Common Use Cases

**1. Provider lookup during enrollment:**
```javascript
const providers = await fetch(
  `https://medicare.purlpal-api.com/medicare/providers?zip=${userZip}&search=${doctorName}&limit=10`
).then(r => r.json());
```

**2. Find nearby pharmacies:**
```javascript
const pharmacies = await fetch(
  `https://medicare.purlpal-api.com/medicare/pharmacies?zip=${userZip}&limit=20`
).then(r => r.json());
```

**3. Get plans for ZIP code:**
```javascript
const plans = await fetch(
  `https://medicare.purlpal-api.com/medicare/zip/${userZip}_MAPD.json`
).then(r => r.json());
```

---

**Last Updated:** January 3, 2026  
**Version:** 2.0 (Added Providers & Pharmacies)  
**Status:** ✅ Production
