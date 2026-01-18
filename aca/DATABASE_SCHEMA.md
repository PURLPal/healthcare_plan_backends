# ACA Database Schema - Entity Diagram

## Overview

**7 Tables + 1 View**
- 20,354 plans across 30 states
- 1,210,850 age-based premium rates (for -01 variants)
- 1,421,810 benefit records

---

## Core Tables

### 1. **`plans`** (20,354 rows)
**Main plan information**

```
┌─────────────────────────────────────────┐
│              PLANS                      │
├─────────────────────────────────────────┤
│ plan_id              VARCHAR(50)  PK    │ ← e.g., "21525FL0020002-01"
│ state_code           VARCHAR(2)         │ ← "FL", "TX", "NY", etc.
│ issuer_id            VARCHAR(20)        │
│ issuer_name          VARCHAR(200)       │ ← "Florida Blue"
│ service_area_id      VARCHAR(50)        │ → links to service_areas
│ plan_marketing_name  VARCHAR(300)       │ ← "Bronze Classic 4700"
│ plan_type            VARCHAR(50)        │ ← "HMO", "PPO", "EPO"
│ metal_level          VARCHAR(50)        │ ← "Bronze", "Silver", "Gold"
│ is_new_plan          BOOLEAN            │
│ plan_attributes      JSONB              │ ← {deductible_individual: "4700", ...}
│ created_at           TIMESTAMP          │
└─────────────────────────────────────────┘
    │
    │ (1 plan → many rates, one per age)
    ↓
```

### 2. **`rates`** (1,210,850 rows after load completes)
**Age-based monthly premiums**

```
┌─────────────────────────────────────────┐
│              RATES                      │
├─────────────────────────────────────────┤
│ plan_id                 VARCHAR(50) PK  │ → FK to plans.plan_id
│ age                     INTEGER     PK  │ ← 0, 1, 2, ..., 64
│ individual_rate         DECIMAL(10,2)   │ ← $450.00
│ individual_tobacco_rate DECIMAL(10,2)   │ ← NULL (filtered out)
└─────────────────────────────────────────┘

Example rows for ONE plan:
  21525FL0020002-01 | 21 | 350.00
  21525FL0020002-01 | 22 | 355.00
  21525FL0020002-01 | 30 | 425.00
  21525FL0020002-01 | 40 | 550.00  ← Most common query age
  21525FL0020002-01 | 50 | 750.00
  21525FL0020002-01 | 64 | 1200.00

Each plan has ~50-60 rows (one per age)
4,044 plans × 50 ages = ~1.2M total rows
```

### 3. **`benefits`** (1,421,810 rows)
**Detailed cost-sharing for each benefit type**

```
┌─────────────────────────────────────────┐
│            BENEFITS                     │
├─────────────────────────────────────────┤
│ plan_id              VARCHAR(50)   PK   │ → FK to plans.plan_id
│ benefit_name         VARCHAR(200)  PK   │ ← "Primary Care Visit", "ER Visit"
│ is_covered           BOOLEAN            │
│ cost_sharing_details JSONB              │ ← {copay_in_network: "$25", ...}
└─────────────────────────────────────────┘

Example rows for ONE plan:
  21525FL0020002-01 | Primary Care Visit            | t | {"copay_in_network": "$25"}
  21525FL0020002-01 | Specialist Visit              | t | {"copay_in_network": "$75"}
  21525FL0020002-01 | Emergency Room Services       | t | {"copay_in_network": "$350"}
  21525FL0020002-01 | Generic Drugs                 | t | {"coinsurance": "50%"}
  21525FL0020002-01 | Hospital Inpatient Services   | t | {"coinsurance": "30%"}

Each plan has ~70 benefit types = 234 unique benefit names
```

---

## Geographic Tables

### 4. **`counties`** (3,234 rows)
**US County reference data**

```
┌─────────────────────────────────────────┐
│            COUNTIES                     │
├─────────────────────────────────────────┤
│ county_fips    VARCHAR(5)   PK          │ ← "12086" (Miami-Dade)
│ county_name    VARCHAR(100)             │ ← "Miami-Dade County"
│ state_code     VARCHAR(2)               │ ← "FL"
│ state_name     VARCHAR(100)             │ ← "Florida"
└─────────────────────────────────────────┘
```

### 5. **`zip_counties`** (handles multi-county ZIPs)
**Maps ZIP codes to counties**

```
┌─────────────────────────────────────────┐
│          ZIP_COUNTIES                   │
├─────────────────────────────────────────┤
│ zip_code       VARCHAR(5)   PK          │ ← "33433"
│ county_fips    VARCHAR(5)   PK          │ → FK to counties
│ state_code     VARCHAR(2)               │ ← "FL"
│ ratio          DECIMAL(10,6)            │ ← 1.0 (or split if multi-county)
└─────────────────────────────────────────┘

Example: ZIP 33433 (Boca Raton, FL)
  33433 | 12099 | FL | 1.0   → Palm Beach County
```

### 6. **`service_areas`** 
**Insurance company service area definitions**

```
┌─────────────────────────────────────────┐
│         SERVICE_AREAS                   │
├─────────────────────────────────────────┤
│ service_area_id      VARCHAR(50)   PK   │
│ state_code           VARCHAR(2)    PK   │
│ issuer_id            VARCHAR(20)        │
│ service_area_name    VARCHAR(200)       │
│ covers_entire_state  BOOLEAN            │
│ market_coverage      VARCHAR(50)        │
└─────────────────────────────────────────┘
```

### 7. **`plan_service_areas`**
**Links service areas to counties**

```
┌─────────────────────────────────────────┐
│       PLAN_SERVICE_AREAS                │
├─────────────────────────────────────────┤
│ service_area_id  VARCHAR(50)   PK       │
│ county_fips      VARCHAR(5)    PK       │
│ state_code       VARCHAR(2)             │
└─────────────────────────────────────────┘
```

---

## Complete Relationship Diagram

```
┌─────────────┐
│ zip_counties│
│             │
│ zip_code    │──┐
│ county_fips │──┼──→ ┌──────────┐
└─────────────┘  │    │ counties │
                 │    │          │
                 └───→│county_fips│
                      │state_code│
                      └────┬─────┘
                           │
    ┌──────────────────────┘
    │
    ↓
┌────────────────────┐         ┌──────────────────┐
│ plan_service_areas │────────→│ service_areas    │
│                    │         │                  │
│ service_area_id    │         │ service_area_id  │
│ county_fips        │         │ state_code       │
└────────┬───────────┘         └────────┬─────────┘
         │                              │
         │         ┌────────────────────┘
         │         │
         │         ↓
         │    ┌──────────────────────────────┐
         └───→│         PLANS                │ ← MAIN TABLE
              │                              │
              │ plan_id (PK)                 │
              │ state_code                   │
              │ issuer_name                  │
              │ plan_marketing_name          │
              │ plan_type (HMO/PPO/EPO)      │
              │ metal_level (Bronze/Silver)  │
              │ service_area_id              │
              │ plan_attributes (JSONB)      │
              └────────┬─────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
          ↓                         ↓
  ┌────────────────┐      ┌──────────────────┐
  │    RATES       │      │    BENEFITS      │
  │                │      │                  │
  │ plan_id (FK)   │      │ plan_id (FK)     │
  │ age            │      │ benefit_name     │
  │ individual_rate│      │ is_covered       │
  └────────────────┘      │ cost_sharing_... │
                          └──────────────────┘
   1 plan → ~60 rows       1 plan → ~70 rows
   (one per age)           (one per benefit)
```

---

## Common Query Patterns

### ✅ **Simple: 1-2 table joins**

#### Query 1: Get monthly premium for specific plan and age
```sql
SELECT p.plan_marketing_name, r.individual_rate
FROM plans p
JOIN rates r ON p.plan_id = r.plan_id
WHERE p.plan_id = '21525FL0020002-01' 
  AND r.age = 40;
```
**Joins: 2 tables** (plans + rates)

---

#### Query 2: Find cheapest plans in a state at age 40
```sql
SELECT p.plan_marketing_name, r.individual_rate, p.metal_level
FROM plans p
JOIN rates r ON p.plan_id = r.plan_id
WHERE p.state_code = 'FL'
  AND r.age = 40
ORDER BY r.individual_rate
LIMIT 10;
```
**Joins: 2 tables** (plans + rates)

---

#### Query 3: Get specialist copay for a plan
```sql
SELECT b.cost_sharing_details->>'copay_in_network' as specialist_copay
FROM benefits b
WHERE b.plan_id = '21525FL0020002-01'
  AND b.benefit_name = 'Specialist Visit';
```
**Joins: 1 table** (benefits only)

---

### ⚠️ **Complex: 3-5 table joins**

#### Query 4: Plans available in a ZIP code with rates
```sql
SELECT DISTINCT
    p.plan_id,
    p.plan_marketing_name,
    r.individual_rate
FROM zip_counties zc
JOIN plan_service_areas psa ON zc.county_fips = psa.county_fips
JOIN plans p ON psa.service_area_id = p.service_area_id 
            AND psa.state_code = p.state_code
JOIN rates r ON p.plan_id = r.plan_id
WHERE zc.zip_code = '33433'
  AND r.age = 40
ORDER BY r.individual_rate;
```
**Joins: 4 tables** (zip_counties → plan_service_areas → plans → rates)

---

## Key Insights

### 1. **Why ~60 rates per plan?**
ACA premiums are **age-rated**. Federal rules require different prices for each age:
- Age 21: $350/mo
- Age 30: $425/mo
- Age 40: $550/mo
- Age 50: $750/mo
- Age 64: $1,200/mo

**Older = higher premium** (3:1 age curve maximum by law)

### 2. **Most queries only need 1-2 joins**
- **Premium lookup:** `plans` → `rates` (2 tables)
- **Benefit lookup:** `plans` → `benefits` (2 tables)
- **Plan search by state:** `plans` → `rates` (2 tables)

### 3. **ZIP code queries need 4 joins**
Only complex query: ZIP → County → Service Area → Plans → Rates
This is rare - most queries will be direct plan lookups.

### 4. **Data volume**
- **Small:** plans (20K), counties (3K), service areas (8K)
- **Large:** rates (1.2M), benefits (1.4M)

---

## JSONB Fields

### `plans.plan_attributes`
```json
{
  "deductible_individual": "4700",
  "deductible_family": "9400",
  "moop_individual": "8550",
  "moop_family": "17100"
}
```

### `benefits.cost_sharing_details`
```json
{
  "copay_in_network": "$25",
  "copay_out_network": "Not Covered",
  "coinsurance_in_network": "0%",
  "has_deductible": "No"
}
```

---

## Index Summary

**Primary lookups:**
- `plans.plan_id` (PK) - instant
- `plans.state_code` (indexed)
- `plans.metal_level` (indexed)
- `rates(plan_id, age)` (PK) - instant
- `benefits(plan_id, benefit_name)` (PK) - instant

**All fast single-column lookups are indexed.**
