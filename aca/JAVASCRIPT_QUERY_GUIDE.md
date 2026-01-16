# JavaScript Query Guide for ACA Database
## Chrome Extension Integration

**For:** JavaScript developers querying the ACA PostgreSQL database  
**Use Case:** Chrome Extension that compares ACA plans  
**Database:** PostgreSQL on AWS RDS

---

## Table of Contents

1. [Database Connection Setup](#database-connection-setup)
2. [Table Schema Reference](#table-schema-reference)
3. [Query Examples by Use Case](#query-examples-by-use-case)
4. [Chrome Extension Architecture](#chrome-extension-architecture)

---

## Database Connection Setup

### ⚠️ Important: Security Considerations

**DO NOT connect directly from Chrome Extension to PostgreSQL!**

PostgreSQL requires credentials and direct connections are:
- ❌ Insecure (exposes database credentials)
- ❌ Not supported by Chrome Extensions (no native PostgreSQL drivers)
- ❌ Violates CORS policies

### ✅ Recommended Architecture

```
Chrome Extension → REST API (Lambda/Node.js) → PostgreSQL Database
```

---

## Option 1: Using AWS Lambda (Serverless)

### Backend: Lambda Function (Node.js)

```javascript
// lambda/aca-query-api.js
const { Client } = require('pg');

// Database connection (from environment variables)
const client = new Client({
  host: process.env.DB_HOST,
  port: 5432,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  ssl: { rejectUnauthorized: false }
});

exports.handler = async (event) => {
  const { queryType, params } = JSON.parse(event.body);
  
  try {
    await client.connect();
    
    let result;
    switch(queryType) {
      case 'monthly_costs':
        result = await getMonthlyCosts(params);
        break;
      case 'moop':
        result = await getMOOP(params);
        break;
      case 'deductibles':
        result = await getDeductibles(params);
        break;
      case 'specialist':
        result = await getSpecialistCosts(params);
        break;
      case 'in_vs_out_network':
        result = await getInVsOutNetwork(params);
        break;
      case 'emergency':
        result = await getEmergencyRoomCosts(params);
        break;
      default:
        throw new Error('Invalid query type');
    }
    
    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      },
      body: JSON.stringify(result)
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message })
    };
  } finally {
    await client.end();
  }
};

// Query functions (see below for implementations)
async function getMonthlyCosts(params) { /* ... */ }
async function getMOOP(params) { /* ... */ }
// ... etc
```

### Frontend: Chrome Extension JavaScript

```javascript
// chrome-extension/content.js

class ACAQueryClient {
  constructor(apiEndpoint) {
    this.apiEndpoint = apiEndpoint; // e.g., 'https://api.yoursite.com/aca-query'
  }

  async query(queryType, params) {
    const response = await fetch(this.apiEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ queryType, params })
    });
    
    if (!response.ok) {
      throw new Error(`Query failed: ${response.statusText}`);
    }
    
    return await response.json();
  }

  // Convenience methods for each query type
  async getMonthlyCosts(planIds, age = 40) {
    return this.query('monthly_costs', { planIds, age });
  }

  async getMOOP(planIds) {
    return this.query('moop', { planIds });
  }

  async getDeductibles(planIds) {
    return this.query('deductibles', { planIds });
  }

  async getSpecialistCosts(planIds) {
    return this.query('specialist', { planIds });
  }

  async getInVsOutNetwork(planIds, benefitName) {
    return this.query('in_vs_out_network', { planIds, benefitName });
  }

  async getEmergencyRoomCosts(planIds) {
    return this.query('emergency', { planIds });
  }
}

// Usage in your extension
const client = new ACAQueryClient('https://your-api.com/aca-query');

// Example: Get monthly costs for specific plans
const plans = ['21525FL0020002-00', '48121FL0070122-00'];
const costs = await client.getMonthlyCosts(plans, 35);
console.log(costs);
```

---

## Table Schema Reference

### 1. `plans` Table

**Description:** Core plan information

**Key Columns:**
```
plan_id              TEXT PRIMARY KEY     // e.g., '21525FL0020002-00'
state_code           TEXT                 // e.g., 'FL'
issuer_id            TEXT                 // Insurance company ID
issuer_name          TEXT                 // e.g., 'Oscar Health'
plan_marketing_name  TEXT                 // User-friendly plan name
plan_type            TEXT                 // HMO, PPO, EPO, POS
metal_level          TEXT                 // Bronze, Silver, Gold, Platinum, Expanded Bronze
service_area_id      TEXT                 // Links to service_areas table
is_new_plan          BOOLEAN              // True if new for 2026
plan_attributes      JSONB                // Contains deductibles, MOOP, etc.
```

**Important `plan_attributes` Fields (JSONB):**
```javascript
{
  "deductible_individual": "$5,500",          // Individual deductible
  "deductible_family": "$11,000",             // Family deductible  
  "moop_individual": "$9,200",                // Max out-of-pocket (individual)
  "moop_family": "$18,400",                   // Max out-of-pocket (family)
  "is_hsa_eligible": "No",                    // HSA eligibility
  "hios_product_id": "21525FL002",            // HIOS ID
  "network_id": "FLN001",                     // Network identifier
  "formulary_id": "FL001"                     // Drug formulary ID
}
```

### 2. `rates` Table

**Description:** Age-based monthly premiums

**Key Columns:**
```
plan_id                    TEXT            // Foreign key to plans
age                        INTEGER         // 0-99 (0 = family rate)
individual_rate            NUMERIC(10,2)   // Monthly premium
individual_tobacco_rate    NUMERIC(10,2)   // Monthly premium for tobacco users
PRIMARY KEY (plan_id, age)
```

**How Age Works:**
- `age = 0`: Family rate (2 adults + 3 children)
- `age = 21-64`: Individual rates by age
- Rates increase with age (3:1 ratio, max at age 64)

### 3. `benefits` Table

**Description:** Detailed cost-sharing for all covered services

**Key Columns:**
```
plan_id                 TEXT              // Foreign key to plans
benefit_name            TEXT              // e.g., 'Generic Drugs', 'Specialist Visit'
is_covered              BOOLEAN           // True if benefit is covered
cost_sharing_details    JSONB             // Copays, coinsurance, etc.
PRIMARY KEY (plan_id, benefit_name)
```

**`cost_sharing_details` Structure (JSONB):**
```javascript
{
  "copay_inn_tier1": "$50.00",                    // In-network tier 1 copay
  "copay_inn_tier2": "$75.00",                    // In-network tier 2 copay
  "copay_oon": "Not Applicable",                  // Out-of-network copay
  "coins_inn_tier1": "20.00%",                    // In-network tier 1 coinsurance
  "coins_inn_tier2": "30.00%",                    // In-network tier 2 coinsurance  
  "coins_oon": "50.00%",                          // Out-of-network coinsurance
  "exclusions": "Prior authorization required",   // Coverage restrictions
  "explanation": "After deductible",              // Additional details
  "has_quantity_limit": true,                     // If service has limits
  "limit_quantity": "30",                         // Limit amount
  "limit_unit": "visits per year"                 // Limit unit
}
```

### 4. `service_areas` & `plan_service_areas` Tables

**Description:** Geographic coverage mapping

**service_areas:**
```
service_area_id    TEXT PRIMARY KEY     // e.g., 'FLS001'
state_code         TEXT                 // e.g., 'FL'
issuer_id          TEXT                 // Insurance company
```

**plan_service_areas:**
```
plan_id            TEXT                 // Foreign key to plans
service_area_id    TEXT                 // Foreign key to service_areas
county_fips        TEXT                 // County identifier
```

### 5. `zip_counties` Table

**Description:** Maps ZIP codes to counties

```
zip_code           TEXT                 // e.g., '33433'
county_fips        TEXT                 // e.g., '12099'
state_code         TEXT                 // e.g., 'FL'
allocation_factor  NUMERIC              // % of ZIP in this county
```

---

## Query Examples by Use Case

### Use Case 1: Monthly Plan Costs

**What:** Get monthly premiums for specific plans at a given age

**JavaScript Implementation:**

```javascript
async function getMonthlyCosts(params) {
  const { planIds, age = 40 } = params;
  
  const query = `
    SELECT 
      p.plan_id,
      p.plan_marketing_name,
      p.issuer_name,
      p.metal_level,
      p.plan_type,
      r.individual_rate as monthly_premium,
      r.individual_tobacco_rate as monthly_premium_tobacco,
      p.plan_attributes->>'deductible_individual' as deductible,
      p.plan_attributes->>'moop_individual' as moop
    FROM plans p
    LEFT JOIN rates r ON p.plan_id = r.plan_id AND r.age = $1
    WHERE p.plan_id = ANY($2)
    ORDER BY r.individual_rate ASC
  `;
  
  const result = await client.query(query, [age, planIds]);
  return result.rows;
}
```

**SQL Query (Direct):**
```sql
-- Get monthly costs for specific plans at age 35
SELECT 
  p.plan_id,
  p.plan_marketing_name,
  p.issuer_name,
  p.metal_level,
  p.plan_type,
  r.individual_rate as monthly_premium,
  r.individual_tobacco_rate as monthly_premium_tobacco,
  p.plan_attributes->>'deductible_individual' as deductible,
  p.plan_attributes->>'moop_individual' as moop
FROM plans p
LEFT JOIN rates r ON p.plan_id = r.plan_id AND r.age = 35
WHERE p.plan_id IN (
  '21525FL0020002-00',
  '48121FL0070122-00',
  '44228FL0040008-00'
)
ORDER BY r.individual_rate ASC;
```

**Expected Response:**
```javascript
[
  {
    plan_id: '21525FL0020002-00',
    plan_marketing_name: 'Oscar Bronze Classic 4700',
    issuer_name: 'Oscar Health',
    metal_level: 'Expanded Bronze',
    plan_type: 'EPO',
    monthly_premium: 284.50,
    monthly_premium_tobacco: 355.63,
    deductible: '$4,700',
    moop: '$9,100'
  },
  // ... more plans
]
```

---

### Use Case 2: Maximum Out-of-Pocket (MOOP)

**What:** Get MOOP limits for plans (individual and family)

**JavaScript Implementation:**

```javascript
async function getMOOP(params) {
  const { planIds } = params;
  
  const query = `
    SELECT 
      plan_id,
      plan_marketing_name,
      issuer_name,
      metal_level,
      plan_attributes->>'moop_individual' as moop_individual,
      plan_attributes->>'moop_family' as moop_family,
      plan_attributes->>'deductible_individual' as deductible_individual,
      plan_attributes->>'deductible_family' as deductible_family
    FROM plans
    WHERE plan_id = ANY($1)
    ORDER BY 
      NULLIF(REGEXP_REPLACE(
        plan_attributes->>'moop_individual', 
        '[^0-9.]', '', 'g'
      ), '')::NUMERIC ASC
  `;
  
  const result = await client.query(query, [planIds]);
  return result.rows;
}
```

**SQL Query (Direct):**
```sql
-- Get MOOP for specific plans, sorted by lowest MOOP
SELECT 
  plan_id,
  plan_marketing_name,
  issuer_name,
  metal_level,
  plan_attributes->>'moop_individual' as moop_individual,
  plan_attributes->>'moop_family' as moop_family,
  plan_attributes->>'deductible_individual' as deductible_individual,
  plan_attributes->>'deductible_family' as deductible_family
FROM plans
WHERE plan_id IN (
  '21525FL0020002-00',
  '48121FL0070122-00'
)
ORDER BY 
  NULLIF(REGEXP_REPLACE(
    plan_attributes->>'moop_individual', 
    '[^0-9.]', '', 'g'
  ), '')::NUMERIC ASC;
```

**Expected Response:**
```javascript
[
  {
    plan_id: '48121FL0070122-00',
    plan_marketing_name: 'Cigna Connect Bronze Mid-South',
    issuer_name: 'Cigna',
    metal_level: 'Expanded Bronze',
    moop_individual: '$9,200',
    moop_family: '$18,400',
    deductible_individual: '$6,500',
    deductible_family: '$13,000'
  },
  // ... more plans
]
```

---

### Use Case 3: Deductibles

**What:** Get deductible amounts (individual and family)

**JavaScript Implementation:**

```javascript
async function getDeductibles(params) {
  const { planIds } = params;
  
  const query = `
    SELECT 
      plan_id,
      plan_marketing_name,
      issuer_name,
      metal_level,
      plan_type,
      plan_attributes->>'deductible_individual' as deductible_individual,
      plan_attributes->>'deductible_family' as deductible_family,
      plan_attributes->>'is_hsa_eligible' as hsa_eligible
    FROM plans
    WHERE plan_id = ANY($1)
    ORDER BY 
      NULLIF(REGEXP_REPLACE(
        plan_attributes->>'deductible_individual', 
        '[^0-9.]', '', 'g'
      ), '')::NUMERIC ASC
  `;
  
  const result = await client.query(query, [planIds]);
  return result.rows;
}
```

**SQL Query (Direct):**
```sql
-- Get deductibles, sorted by lowest deductible
SELECT 
  plan_id,
  plan_marketing_name,
  issuer_name,
  metal_level,
  plan_type,
  plan_attributes->>'deductible_individual' as deductible_individual,
  plan_attributes->>'deductible_family' as deductible_family,
  plan_attributes->>'is_hsa_eligible' as hsa_eligible
FROM plans
WHERE plan_id IN (
  '21525FL0020002-00',
  '48121FL0070122-00'
)
ORDER BY 
  NULLIF(REGEXP_REPLACE(
    plan_attributes->>'deductible_individual', 
    '[^0-9.]', '', 'g'
  ), '')::NUMERIC ASC;
```

**Expected Response:**
```javascript
[
  {
    plan_id: '21525FL0020002-00',
    plan_marketing_name: 'Oscar Bronze Classic 4700',
    issuer_name: 'Oscar Health',
    metal_level: 'Expanded Bronze',
    plan_type: 'EPO',
    deductible_individual: '$4,700',
    deductible_family: '$9,400',
    hsa_eligible: 'No'
  },
  // ... more plans
]
```

---

### Use Case 4: Out-of-Pocket Coverage

**What:** Get comprehensive out-of-pocket information (deductible + MOOP)

**JavaScript Implementation:**

```javascript
async function getOutOfPocketCoverage(params) {
  const { planIds, age = 40 } = params;
  
  const query = `
    SELECT 
      p.plan_id,
      p.plan_marketing_name,
      p.issuer_name,
      p.metal_level,
      r.individual_rate as monthly_premium,
      p.plan_attributes->>'deductible_individual' as deductible,
      p.plan_attributes->>'moop_individual' as moop,
      -- Calculate annual costs
      (r.individual_rate * 12) as annual_premium,
      NULLIF(REGEXP_REPLACE(
        p.plan_attributes->>'moop_individual', 
        '[^0-9.]', '', 'g'
      ), '')::NUMERIC as moop_numeric,
      -- Estimated max annual OOP (premium + MOOP)
      (r.individual_rate * 12) + 
      NULLIF(REGEXP_REPLACE(
        p.plan_attributes->>'moop_individual', 
        '[^0-9.]', '', 'g'
      ), '')::NUMERIC as max_annual_cost
    FROM plans p
    LEFT JOIN rates r ON p.plan_id = r.plan_id AND r.age = $1
    WHERE p.plan_id = ANY($2)
    ORDER BY max_annual_cost ASC
  `;
  
  const result = await client.query(query, [age, planIds]);
  return result.rows;
}
```

**SQL Query (Direct):**
```sql
-- Get out-of-pocket coverage with annual cost estimates
SELECT 
  p.plan_id,
  p.plan_marketing_name,
  p.issuer_name,
  p.metal_level,
  r.individual_rate as monthly_premium,
  p.plan_attributes->>'deductible_individual' as deductible,
  p.plan_attributes->>'moop_individual' as moop,
  -- Calculate annual costs
  (r.individual_rate * 12) as annual_premium,
  NULLIF(REGEXP_REPLACE(
    p.plan_attributes->>'moop_individual', 
    '[^0-9.]', '', 'g'
  ), '')::NUMERIC as moop_numeric,
  -- Estimated max annual OOP (premium + MOOP)
  (r.individual_rate * 12) + 
  NULLIF(REGEXP_REPLACE(
    p.plan_attributes->>'moop_individual', 
    '[^0-9.]', '', 'g'
  ), '')::NUMERIC as max_annual_cost
FROM plans p
LEFT JOIN rates r ON p.plan_id = r.plan_id AND r.age = 40
WHERE p.plan_id IN (
  '21525FL0020002-00',
  '48121FL0070122-00'
)
ORDER BY max_annual_cost ASC;
```

**Expected Response:**
```javascript
[
  {
    plan_id: '21525FL0020002-00',
    plan_marketing_name: 'Oscar Bronze Classic 4700',
    issuer_name: 'Oscar Health',
    metal_level: 'Expanded Bronze',
    monthly_premium: 284.50,
    deductible: '$4,700',
    moop: '$9,100',
    annual_premium: 3414.00,
    moop_numeric: 9100,
    max_annual_cost: 12514.00  // Worst case: premium + MOOP
  },
  // ... more plans
]
```

---

### Use Case 5: Specialist Coverage

**What:** Get specialist visit costs (in-network and out-of-network)

**JavaScript Implementation:**

```javascript
async function getSpecialistCosts(params) {
  const { planIds } = params;
  
  const query = `
    SELECT 
      p.plan_id,
      p.plan_marketing_name,
      p.issuer_name,
      p.metal_level,
      p.plan_type,
      b.cost_sharing_details->>'copay_inn_tier1' as specialist_copay_in,
      b.cost_sharing_details->>'copay_oon' as specialist_copay_out,
      b.cost_sharing_details->>'coins_inn_tier1' as specialist_coinsurance_in,
      b.cost_sharing_details->>'coins_oon' as specialist_coinsurance_out,
      b.cost_sharing_details->>'explanation' as explanation
    FROM plans p
    LEFT JOIN benefits b ON p.plan_id = b.plan_id 
      AND b.benefit_name = 'Specialist Visit'
      AND b.is_covered = true
    WHERE p.plan_id = ANY($1)
    ORDER BY 
      NULLIF(REGEXP_REPLACE(
        b.cost_sharing_details->>'copay_inn_tier1', 
        '[^0-9.]', '', 'g'
      ), '')::NUMERIC ASC
  `;
  
  const result = await client.query(query, [planIds]);
  return result.rows;
}
```

**SQL Query (Direct):**
```sql
-- Get specialist visit costs
SELECT 
  p.plan_id,
  p.plan_marketing_name,
  p.issuer_name,
  p.metal_level,
  p.plan_type,
  b.cost_sharing_details->>'copay_inn_tier1' as specialist_copay_in,
  b.cost_sharing_details->>'copay_oon' as specialist_copay_out,
  b.cost_sharing_details->>'coins_inn_tier1' as specialist_coinsurance_in,
  b.cost_sharing_details->>'coins_oon' as specialist_coinsurance_out,
  b.cost_sharing_details->>'explanation' as explanation
FROM plans p
LEFT JOIN benefits b ON p.plan_id = b.plan_id 
  AND b.benefit_name = 'Specialist Visit'
  AND b.is_covered = true
WHERE p.plan_id IN (
  '21525FL0020002-00',
  '48121FL0070122-00',
  '44228FL0040008-00'
)
ORDER BY 
  NULLIF(REGEXP_REPLACE(
    b.cost_sharing_details->>'copay_inn_tier1', 
    '[^0-9.]', '', 'g'
  ), '')::NUMERIC ASC;
```

**Expected Response:**
```javascript
[
  {
    plan_id: '48121FL0070051-00',
    plan_marketing_name: 'Cigna Connect myDiabetesCare',
    issuer_name: 'Cigna',
    metal_level: 'Expanded Bronze',
    plan_type: 'HMO',
    specialist_copay_in: '$0.00',
    specialist_copay_out: null,
    specialist_coinsurance_in: '0.00%',
    specialist_coinsurance_out: '60.00%',
    explanation: 'After deductible'
  },
  // ... more plans
]
```

---

### Use Case 6: In-Network vs Out-of-Network Costs

**What:** Compare in-network and out-of-network costs for any benefit

**JavaScript Implementation:**

```javascript
async function getInVsOutNetwork(params) {
  const { planIds, benefitName = 'Specialist Visit' } = params;
  
  const query = `
    SELECT 
      p.plan_id,
      p.plan_marketing_name,
      p.issuer_name,
      p.metal_level,
      p.plan_type,
      b.benefit_name,
      -- In-network costs
      b.cost_sharing_details->>'copay_inn_tier1' as in_network_copay,
      b.cost_sharing_details->>'coins_inn_tier1' as in_network_coinsurance,
      -- Out-of-network costs
      b.cost_sharing_details->>'copay_oon' as out_of_network_copay,
      b.cost_sharing_details->>'coins_oon' as out_of_network_coinsurance,
      -- Additional info
      b.cost_sharing_details->>'explanation' as explanation,
      -- Calculate potential cost difference
      CASE 
        WHEN b.cost_sharing_details->>'copay_oon' IS NOT NULL 
        THEN 'Has OON coverage'
        WHEN p.plan_type IN ('HMO', 'EPO')
        THEN 'No OON coverage (HMO/EPO)'
        ELSE 'Check plan details'
      END as oon_status
    FROM plans p
    LEFT JOIN benefits b ON p.plan_id = b.plan_id 
      AND b.benefit_name = $1
      AND b.is_covered = true
    WHERE p.plan_id = ANY($2)
    ORDER BY p.plan_id
  `;
  
  const result = await client.query(query, [benefitName, planIds]);
  return result.rows;
}
```

**SQL Query (Direct):**
```sql
-- Compare in-network vs out-of-network for specialist visits
SELECT 
  p.plan_id,
  p.plan_marketing_name,
  p.issuer_name,
  p.metal_level,
  p.plan_type,
  b.benefit_name,
  -- In-network costs
  b.cost_sharing_details->>'copay_inn_tier1' as in_network_copay,
  b.cost_sharing_details->>'coins_inn_tier1' as in_network_coinsurance,
  -- Out-of-network costs
  b.cost_sharing_details->>'copay_oon' as out_of_network_copay,
  b.cost_sharing_details->>'coins_oon' as out_of_network_coinsurance,
  -- Additional info
  b.cost_sharing_details->>'explanation' as explanation,
  -- Calculate potential cost difference
  CASE 
    WHEN b.cost_sharing_details->>'copay_oon' IS NOT NULL 
    THEN 'Has OON coverage'
    WHEN p.plan_type IN ('HMO', 'EPO')
    THEN 'No OON coverage (HMO/EPO)'
    ELSE 'Check plan details'
  END as oon_status
FROM plans p
LEFT JOIN benefits b ON p.plan_id = b.plan_id 
  AND b.benefit_name = 'Specialist Visit'
  AND b.is_covered = true
WHERE p.plan_id IN (
  '21525FL0020002-00',
  '48121FL0070122-00',
  '44228FL0040008-00'
)
ORDER BY p.plan_id;
```

**Expected Response:**
```javascript
[
  {
    plan_id: '21525FL0020002-00',
    plan_marketing_name: 'Oscar Bronze Classic 4700',
    issuer_name: 'Oscar Health',
    metal_level: 'Expanded Bronze',
    plan_type: 'EPO',
    benefit_name: 'Specialist Visit',
    in_network_copay: '$125.00',
    in_network_coinsurance: null,
    out_of_network_copay: null,
    out_of_network_coinsurance: '100.00%',
    explanation: 'After deductible',
    oon_status: 'Has OON coverage'
  },
  // ... more plans
]
```

---

### Use Case 7: Emergency Room Coverage

**What:** Get ER costs, ambulance costs, and urgent care costs

**JavaScript Implementation:**

```javascript
async function getEmergencyRoomCosts(params) {
  const { planIds } = params;
  
  const query = `
    SELECT 
      p.plan_id,
      p.plan_marketing_name,
      p.issuer_name,
      p.metal_level,
      p.plan_attributes->>'deductible_individual' as deductible,
      -- Emergency Room
      b_er.cost_sharing_details->>'copay_inn_tier1' as er_copay,
      b_er.cost_sharing_details->>'coins_inn_tier1' as er_coinsurance,
      b_er.cost_sharing_details->>'explanation' as er_explanation,
      -- Urgent Care
      b_uc.cost_sharing_details->>'copay_inn_tier1' as urgent_care_copay,
      b_uc.cost_sharing_details->>'coins_inn_tier1' as urgent_care_coinsurance,
      -- Ambulance
      b_amb.cost_sharing_details->>'copay_inn_tier1' as ambulance_copay,
      b_amb.cost_sharing_details->>'coins_inn_tier1' as ambulance_coinsurance
    FROM plans p
    LEFT JOIN benefits b_er ON p.plan_id = b_er.plan_id 
      AND b_er.benefit_name = 'Emergency Room Services'
    LEFT JOIN benefits b_uc ON p.plan_id = b_uc.plan_id 
      AND b_uc.benefit_name = 'Urgent Care Centers or Facilities'
    LEFT JOIN benefits b_amb ON p.plan_id = b_amb.plan_id 
      AND b_amb.benefit_name = 'Emergency Transportation/Ambulance'
    WHERE p.plan_id = ANY($1)
    ORDER BY 
      NULLIF(REGEXP_REPLACE(
        b_er.cost_sharing_details->>'copay_inn_tier1', 
        '[^0-9.]', '', 'g'
      ), '')::NUMERIC ASC
  `;
  
  const result = await client.query(query, [planIds]);
  return result.rows;
}
```

**SQL Query (Direct):**
```sql
-- Get emergency room, urgent care, and ambulance costs
SELECT 
  p.plan_id,
  p.plan_marketing_name,
  p.issuer_name,
  p.metal_level,
  p.plan_attributes->>'deductible_individual' as deductible,
  -- Emergency Room
  b_er.cost_sharing_details->>'copay_inn_tier1' as er_copay,
  b_er.cost_sharing_details->>'coins_inn_tier1' as er_coinsurance,
  b_er.cost_sharing_details->>'explanation' as er_explanation,
  -- Urgent Care
  b_uc.cost_sharing_details->>'copay_inn_tier1' as urgent_care_copay,
  b_uc.cost_sharing_details->>'coins_inn_tier1' as urgent_care_coinsurance,
  -- Ambulance
  b_amb.cost_sharing_details->>'copay_inn_tier1' as ambulance_copay,
  b_amb.cost_sharing_details->>'coins_inn_tier1' as ambulance_coinsurance
FROM plans p
LEFT JOIN benefits b_er ON p.plan_id = b_er.plan_id 
  AND b_er.benefit_name = 'Emergency Room Services'
LEFT JOIN benefits b_uc ON p.plan_id = b_uc.plan_id 
  AND b_uc.benefit_name = 'Urgent Care Centers or Facilities'
LEFT JOIN benefits b_amb ON p.plan_id = b_amb.plan_id 
  AND b_amb.benefit_name = 'Emergency Transportation/Ambulance'
WHERE p.plan_id IN (
  '21525FL0020002-00',
  '48121FL0070122-00',
  '44228FL0040008-00'
)
ORDER BY 
  NULLIF(REGEXP_REPLACE(
    b_er.cost_sharing_details->>'copay_inn_tier1', 
    '[^0-9.]', '', 'g'
  ), '')::NUMERIC ASC;
```

**Expected Response:**
```javascript
[
  {
    plan_id: '21525FL0020002-00',
    plan_marketing_name: 'Oscar Bronze Classic 4700',
    issuer_name: 'Oscar Health',
    metal_level: 'Expanded Bronze',
    deductible: '$4,700',
    er_copay: '$500.00',
    er_coinsurance: null,
    er_explanation: 'After deductible',
    urgent_care_copay: '$125.00',
    urgent_care_coinsurance: null,
    ambulance_copay: '$500.00',
    ambulance_coinsurance: null
  },
  // ... more plans
]
```

---

## Chrome Extension Architecture

### Recommended Setup

```
chrome-extension/
├── manifest.json           # Extension configuration
├── background.js           # Service worker (API calls)
├── content.js             # Page interaction
├── popup/
│   ├── popup.html         # Extension popup UI
│   └── popup.js           # Popup logic
└── lib/
    └── aca-client.js      # ACA query client
```

### manifest.json

```json
{
  "manifest_version": 3,
  "name": "ACA Plan Comparison",
  "version": "1.0",
  "permissions": [
    "storage"
  ],
  "host_permissions": [
    "https://your-api.com/*",
    "https://www.healthsherpa.com/*"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [{
    "matches": ["https://www.healthsherpa.com/*"],
    "js": ["content.js"]
  }],
  "action": {
    "default_popup": "popup/popup.html"
  }
}
```

### background.js (Service Worker)

```javascript
// Background service worker handles API calls
import { ACAQueryClient } from './lib/aca-client.js';

const client = new ACAQueryClient('https://your-api.com/aca-query');

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'queryPlans') {
    handlePlanQuery(request.data)
      .then(sendResponse)
      .catch(error => sendResponse({ error: error.message }));
    return true; // Keep channel open for async response
  }
});

async function handlePlanQuery(data) {
  const { queryType, params } = data;
  
  switch(queryType) {
    case 'monthly_costs':
      return await client.getMonthlyCosts(params.planIds, params.age);
    case 'specialist':
      return await client.getSpecialistCosts(params.planIds);
    case 'emergency':
      return await client.getEmergencyRoomCosts(params.planIds);
    // ... other cases
    default:
      throw new Error('Unknown query type');
  }
}
```

### content.js (Page Integration)

```javascript
// Extract plan IDs from HealthSherpa page
function extractPlanIds() {
  const planElements = document.querySelectorAll('[data-plan-id]');
  return Array.from(planElements).map(el => el.dataset.planId);
}

// Query additional plan details
async function enrichPlanData() {
  const planIds = extractPlanIds();
  
  if (planIds.length === 0) return;
  
  // Request data from background script
  const response = await chrome.runtime.sendMessage({
    action: 'queryPlans',
    data: {
      queryType: 'specialist',
      params: { planIds }
    }
  });
  
  if (response.error) {
    console.error('Query failed:', response.error);
    return;
  }
  
  // Display additional data on page
  displayEnrichedData(response);
}

function displayEnrichedData(data) {
  data.forEach(plan => {
    const planElement = document.querySelector(`[data-plan-id="${plan.plan_id}"]`);
    if (planElement) {
      // Add specialist cost badge
      const badge = document.createElement('div');
      badge.className = 'specialist-cost-badge';
      badge.textContent = `Specialist: ${plan.specialist_copay_in}`;
      planElement.appendChild(badge);
    }
  });
}

// Run when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', enrichPlanData);
} else {
  enrichPlanData();
}
```

### popup.js (Extension Popup)

```javascript
// Popup UI for manual queries
document.getElementById('queryBtn').addEventListener('click', async () => {
  const planIds = document.getElementById('planIds').value.split(',').map(s => s.trim());
  const age = parseInt(document.getElementById('age').value) || 40;
  
  const response = await chrome.runtime.sendMessage({
    action: 'queryPlans',
    data: {
      queryType: 'monthly_costs',
      params: { planIds, age }
    }
  });
  
  displayResults(response);
});

function displayResults(data) {
  const resultsDiv = document.getElementById('results');
  resultsDiv.innerHTML = '';
  
  data.forEach(plan => {
    const planDiv = document.createElement('div');
    planDiv.className = 'plan-result';
    planDiv.innerHTML = `
      <h3>${plan.plan_marketing_name}</h3>
      <p><strong>Monthly Premium:</strong> $${plan.monthly_premium}</p>
      <p><strong>Deductible:</strong> ${plan.deductible}</p>
      <p><strong>MOOP:</strong> ${plan.moop}</p>
    `;
    resultsDiv.appendChild(planDiv);
  });
}
```

---

## Additional Query Examples

### Get Plans by ZIP Code

```javascript
async function getPlansByZip(zipCode, metalLevel = null) {
  let query = `
    SELECT DISTINCT
      p.plan_id,
      p.plan_marketing_name,
      p.issuer_name,
      p.metal_level,
      p.plan_type
    FROM plans p
    JOIN plan_service_areas psa ON p.plan_id = psa.plan_id
    JOIN zip_counties zc ON psa.county_fips = zc.county_fips
    WHERE zc.zip_code = $1
  `;
  
  const params = [zipCode];
  
  if (metalLevel) {
    query += ` AND p.metal_level = $2`;
    params.push(metalLevel);
  }
  
  query += ` ORDER BY p.metal_level, p.issuer_name`;
  
  const result = await client.query(query, params);
  return result.rows;
}
```

### Compare Drug Costs

```javascript
async function compareDrugCosts(planIds) {
  const query = `
    SELECT 
      p.plan_id,
      p.plan_marketing_name,
      -- Generic drugs
      b_gen.cost_sharing_details->>'copay_inn_tier1' as generic_copay,
      -- Preferred brand
      b_pbrand.cost_sharing_details->>'copay_inn_tier1' as preferred_brand_copay,
      -- Specialty drugs
      b_spec.cost_sharing_details->>'coins_inn_tier1' as specialty_coinsurance
    FROM plans p
    LEFT JOIN benefits b_gen ON p.plan_id = b_gen.plan_id 
      AND b_gen.benefit_name = 'Generic Drugs'
    LEFT JOIN benefits b_pbrand ON p.plan_id = b_pbrand.plan_id 
      AND b_pbrand.benefit_name = 'Preferred Brand Drugs'
    LEFT JOIN benefits b_spec ON p.plan_id = b_spec.plan_id 
      AND b_spec.benefit_name = 'Specialty Drugs'
    WHERE p.plan_id = ANY($1)
    ORDER BY 
      NULLIF(REGEXP_REPLACE(
        b_gen.cost_sharing_details->>'copay_inn_tier1', 
        '[^0-9.]', '', 'g'
      ), '')::NUMERIC ASC
  `;
  
  const result = await client.query(query, [planIds]);
  return result.rows;
}
```

---

## Common Benefit Names Reference

Use these exact strings when querying the `benefits` table:

### Doctor Visits
- `'Primary Care Visit to Treat an Injury or Illness'`
- `'Specialist Visit'`
- `'Preventive Care/Screening/Immunization'`

### Prescription Drugs
- `'Generic Drugs'`
- `'Preferred Brand Drugs'`
- `'Non-Preferred Brand Drugs'`
- `'Specialty Drugs'`

### Emergency & Urgent
- `'Emergency Room Services'`
- `'Urgent Care Centers or Facilities'`
- `'Emergency Transportation/Ambulance'`

### Hospital
- `'Inpatient Hospital Services (e.g., Hospital Stay)'`
- `'Inpatient Physician and Surgical Services'`
- `'Outpatient Facility Fee (e.g., Ambulatory Surgery Center)'`
- `'Outpatient Surgery Physician/Surgical Services'`

### Mental Health
- `'Mental/Behavioral Health Outpatient Services'`
- `'Mental/Behavioral Health Inpatient Services'`

### Imaging & Labs
- `'Imaging (CT/PET Scans, MRIs)'`
- `'X-rays and Diagnostic Imaging'`
- `'Laboratory Outpatient and Professional Services'`

---

## Error Handling

```javascript
class ACAQueryClient {
  async query(queryType, params) {
    try {
      const response = await fetch(this.apiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ queryType, params })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      return data;
    } catch (error) {
      console.error('ACA Query Error:', error);
      
      // Return user-friendly error
      if (error.message.includes('Failed to fetch')) {
        throw new Error('Network error: Unable to reach API');
      } else if (error.message.includes('timeout')) {
        throw new Error('Request timeout: Try again');
      } else {
        throw error;
      }
    }
  }
}
```

---

## Performance Tips

1. **Cache Results:** Store plan data in Chrome storage
```javascript
// Cache for 1 hour
const CACHE_DURATION = 60 * 60 * 1000;

async function getCachedOrFetch(planIds, queryType) {
  const cacheKey = `${queryType}_${planIds.join('_')}`;
  
  // Check cache
  const cached = await chrome.storage.local.get(cacheKey);
  if (cached[cacheKey] && Date.now() - cached[cacheKey].timestamp < CACHE_DURATION) {
    return cached[cacheKey].data;
  }
  
  // Fetch fresh data
  const data = await client.query(queryType, { planIds });
  
  // Store in cache
  await chrome.storage.local.set({
    [cacheKey]: {
      data,
      timestamp: Date.now()
    }
  });
  
  return data;
}
```

2. **Batch Queries:** Request multiple plan IDs at once (not one-by-one)

3. **Use Indexes:** All queries in this guide use indexed columns for fast performance

4. **Limit Results:** Always use `LIMIT` when appropriate

---

## Security Checklist

- ✅ **Never expose database credentials** in extension code
- ✅ **Use HTTPS** for all API calls
- ✅ **Validate user input** before sending to API
- ✅ **Rate limit** API calls to prevent abuse
- ✅ **Use API keys** for authentication (if deploying publicly)
- ✅ **Sanitize SQL** in backend (use parameterized queries)

---

## Testing

```javascript
// Test all query types
async function testQueries() {
  const testPlanIds = [
    '21525FL0020002-00',
    '48121FL0070122-00'
  ];
  
  console.log('Testing Monthly Costs...');
  const costs = await client.getMonthlyCosts(testPlanIds, 35);
  console.log(costs);
  
  console.log('Testing MOOP...');
  const moop = await client.getMOOP(testPlanIds);
  console.log(moop);
  
  console.log('Testing Specialist...');
  const specialist = await client.getSpecialistCosts(testPlanIds);
  console.log(specialist);
  
  console.log('Testing Emergency...');
  const emergency = await client.getEmergencyRoomCosts(testPlanIds);
  console.log(emergency);
  
  console.log('All tests complete!');
}
```

---

## Additional Resources

- **Full SQL Examples:** `SQL_QUERY_EXAMPLES.md`
- **Table Schemas:** `database/schema.sql`
- **Benefits Catalog:** `BENEFITS_NOW_INDEXED.md`
- **Database Setup:** `README.md`

---

## Quick Reference: Plan ID Format

ACA plan IDs have variants (e.g., `-00`, `-01`):
- **Base ID:** `21525FL0020002` (14 characters)
- **Full ID:** `21525FL0020002-00` (17 characters with variant)

HealthSherpa may show base IDs. Always query with full IDs including variant suffix.
