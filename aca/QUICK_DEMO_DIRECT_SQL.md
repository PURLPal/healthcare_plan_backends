# Quick Demo - Direct SQL (15 Minutes)

⚠️ **TEMPORARY SOLUTION FOR CLIENT DEMO**  
This uses direct SQL. Migrate to REST API later.

---

## Setup (2 minutes)

### 1. Install PostgreSQL client
```bash
npm install pg
```

### 2. Connection Script

Create `demo-query.js`:

```javascript
const { Client } = require('pg');

// Database credentials
const client = new Client({
  host: 'aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com',
  port: 5432,
  database: 'aca_plans',
  user: 'aca_admin',
  password: 'AvRePOWBfVFZyPsKPPG2tV3r',
  ssl: { rejectUnauthorized: false }
});

async function runQuery(sql, params = []) {
  try {
    await client.connect();
    const result = await client.query(sql, params);
    return result.rows;
  } catch (error) {
    console.error('Query error:', error.message);
    throw error;
  } finally {
    await client.end();
  }
}

module.exports = { runQuery };
```

---

## Copy-Paste Queries (Ready to Demo)

### Query 1: Monthly Costs for Age 35

```javascript
const sql = `
SELECT 
  p.plan_id,
  p.plan_marketing_name,
  p.issuer_name,
  p.metal_level,
  r.individual_rate as monthly_premium,
  p.plan_attributes->>'deductible_individual' as deductible,
  p.plan_attributes->>'moop_individual' as moop
FROM plans p
LEFT JOIN rates r ON p.plan_id = r.plan_id AND r.age = $1
WHERE p.plan_id IN ($2, $3, $4)
ORDER BY r.individual_rate ASC;
`;

const result = await runQuery(sql, [
  35,
  '21525FL0020002-00',
  '48121FL0070122-00',
  '44228FL0040008-00'
]);

console.log(result);
```

**Output:**
```json
[
  {
    "plan_id": "21525FL0020002-00",
    "plan_marketing_name": "Oscar Bronze Classic 4700",
    "issuer_name": "Oscar Health",
    "metal_level": "Expanded Bronze",
    "monthly_premium": "284.50",
    "deductible": "$4,700",
    "moop": "$9,100"
  }
]
```

---

### Query 2: Specialist Costs

```javascript
const sql = `
SELECT 
  p.plan_id,
  p.plan_marketing_name,
  p.issuer_name,
  p.metal_level,
  b.cost_sharing_details->>'copay_inn_tier1' as specialist_copay,
  b.cost_sharing_details->>'coins_inn_tier1' as specialist_coinsurance,
  b.cost_sharing_details->>'explanation' as explanation
FROM plans p
LEFT JOIN benefits b ON p.plan_id = b.plan_id 
  AND b.benefit_name = 'Specialist Visit'
WHERE p.plan_id IN ($1, $2, $3)
ORDER BY 
  NULLIF(REGEXP_REPLACE(
    b.cost_sharing_details->>'copay_inn_tier1', 
    '[^0-9.]', '', 'g'
  ), '')::NUMERIC ASC;
`;

const result = await runQuery(sql, [
  '21525FL0020002-00',
  '48121FL0070122-00',
  '44228FL0040008-00'
]);

console.log(result);
```

**Output:**
```json
[
  {
    "plan_id": "48121FL0070051-00",
    "plan_marketing_name": "Cigna Connect myDiabetesCare",
    "issuer_name": "Cigna",
    "specialist_copay": "$0.00",
    "specialist_coinsurance": "0.00%",
    "explanation": "After deductible"
  }
]
```

---

### Query 3: Emergency Room Coverage

```javascript
const sql = `
SELECT 
  p.plan_id,
  p.plan_marketing_name,
  p.issuer_name,
  p.metal_level,
  b_er.cost_sharing_details->>'copay_inn_tier1' as er_copay,
  b_uc.cost_sharing_details->>'copay_inn_tier1' as urgent_care_copay,
  b_amb.cost_sharing_details->>'copay_inn_tier1' as ambulance_copay
FROM plans p
LEFT JOIN benefits b_er ON p.plan_id = b_er.plan_id 
  AND b_er.benefit_name = 'Emergency Room Services'
LEFT JOIN benefits b_uc ON p.plan_id = b_uc.plan_id 
  AND b_uc.benefit_name = 'Urgent Care Centers or Facilities'
LEFT JOIN benefits b_amb ON p.plan_id = b_amb.plan_id 
  AND b_amb.benefit_name = 'Emergency Transportation/Ambulance'
WHERE p.plan_id IN ($1, $2, $3);
`;

const result = await runQuery(sql, [
  '21525FL0020002-00',
  '48121FL0070122-00',
  '44228FL0040008-00'
]);

console.log(result);
```

---

### Query 4: Drug Costs Comparison

```javascript
const sql = `
SELECT 
  p.plan_id,
  p.plan_marketing_name,
  b_gen.cost_sharing_details->>'copay_inn_tier1' as generic_copay,
  b_pbrand.cost_sharing_details->>'copay_inn_tier1' as preferred_brand_copay,
  b_spec.cost_sharing_details->>'coins_inn_tier1' as specialty_coinsurance
FROM plans p
LEFT JOIN benefits b_gen ON p.plan_id = b_gen.plan_id 
  AND b_gen.benefit_name = 'Generic Drugs'
LEFT JOIN benefits b_pbrand ON p.plan_id = b_pbrand.plan_id 
  AND b_pbrand.benefit_name = 'Preferred Brand Drugs'
LEFT JOIN benefits b_spec ON p.plan_id = b_spec.plan_id 
  AND b_spec.benefit_name = 'Specialty Drugs'
WHERE p.plan_id IN ($1, $2, $3);
`;

const result = await runQuery(sql, [
  '21525FL0020002-00',
  '48121FL0070122-00',
  '44228FL0040008-00'
]);

console.log(result);
```

---

### Query 5: In-Network vs Out-of-Network

```javascript
const sql = `
SELECT 
  p.plan_id,
  p.plan_marketing_name,
  p.plan_type,
  b.cost_sharing_details->>'copay_inn_tier1' as in_network_copay,
  b.cost_sharing_details->>'copay_oon' as out_of_network_copay,
  CASE 
    WHEN p.plan_type IN ('HMO', 'EPO') THEN 'No OON coverage'
    WHEN b.cost_sharing_details->>'copay_oon' IS NOT NULL THEN 'Has OON coverage'
    ELSE 'Check plan details'
  END as oon_status
FROM plans p
LEFT JOIN benefits b ON p.plan_id = b.plan_id 
  AND b.benefit_name = 'Specialist Visit'
WHERE p.plan_id IN ($1, $2, $3);
`;

const result = await runQuery(sql, [
  '21525FL0020002-00',
  '48121FL0070122-00',
  '44228FL0040008-00'
]);

console.log(result);
```

---

### Query 6: Complete Plan Comparison

```javascript
const sql = `
SELECT 
  p.plan_id,
  p.plan_marketing_name,
  p.issuer_name,
  p.metal_level,
  p.plan_type,
  r.individual_rate as monthly_premium_age_40,
  p.plan_attributes->>'deductible_individual' as deductible,
  p.plan_attributes->>'moop_individual' as moop,
  -- Specialist
  b_spec.cost_sharing_details->>'copay_inn_tier1' as specialist_copay,
  -- Primary Care
  b_pcp.cost_sharing_details->>'copay_inn_tier1' as primary_care_copay,
  -- Generic Drugs
  b_drug.cost_sharing_details->>'copay_inn_tier1' as generic_drug_copay,
  -- ER
  b_er.cost_sharing_details->>'copay_inn_tier1' as er_copay
FROM plans p
LEFT JOIN rates r ON p.plan_id = r.plan_id AND r.age = 40
LEFT JOIN benefits b_spec ON p.plan_id = b_spec.plan_id 
  AND b_spec.benefit_name = 'Specialist Visit'
LEFT JOIN benefits b_pcp ON p.plan_id = b_pcp.plan_id 
  AND b_pcp.benefit_name = 'Primary Care Visit to Treat an Injury or Illness'
LEFT JOIN benefits b_drug ON p.plan_id = b_drug.plan_id 
  AND b_drug.benefit_name = 'Generic Drugs'
LEFT JOIN benefits b_er ON p.plan_id = b_er.plan_id 
  AND b_er.benefit_name = 'Emergency Room Services'
WHERE p.plan_id IN ($1, $2, $3)
ORDER BY r.individual_rate ASC;
`;

const result = await runQuery(sql, [
  '21525FL0020002-00',
  '48121FL0070122-00',
  '44228FL0040008-00'
]);

console.log(result);
```

**Output:**
```json
[
  {
    "plan_id": "21525FL0020002-00",
    "plan_marketing_name": "Oscar Bronze Classic 4700",
    "issuer_name": "Oscar Health",
    "metal_level": "Expanded Bronze",
    "plan_type": "EPO",
    "monthly_premium_age_40": "329.16",
    "deductible": "$4,700",
    "moop": "$9,100",
    "specialist_copay": "$125.00",
    "primary_care_copay": "$50.00",
    "generic_drug_copay": "$10.00",
    "er_copay": "$500.00"
  }
]
```

---

### Query 7: Plans by ZIP Code

```javascript
const sql = `
SELECT DISTINCT
  p.plan_id,
  p.plan_marketing_name,
  p.issuer_name,
  p.metal_level,
  r.individual_rate as monthly_premium_age_40
FROM plans p
JOIN plan_service_areas psa ON p.plan_id = psa.plan_id
JOIN zip_counties zc ON psa.county_fips = zc.county_fips
LEFT JOIN rates r ON p.plan_id = r.plan_id AND r.age = 40
WHERE zc.zip_code = $1
ORDER BY p.metal_level, r.individual_rate ASC
LIMIT 20;
`;

const result = await runQuery(sql, ['33433']);

console.log(result);
```

---

## Complete Demo Script (Copy & Run)

**File:** `demo.js`

```javascript
const { Client } = require('pg');

const client = new Client({
  host: 'aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com',
  port: 5432,
  database: 'aca_plans',
  user: 'aca_admin',
  password: 'AvRePOWBfVFZyPsKPPG2tV3r',
  ssl: { rejectUnauthorized: false }
});

async function demo() {
  try {
    await client.connect();
    console.log('✅ Connected to database\n');

    // DEMO 1: Monthly costs for 3 plans
    console.log('═══ DEMO 1: Monthly Costs (Age 40) ═══');
    const costs = await client.query(`
      SELECT 
        p.plan_marketing_name,
        p.issuer_name,
        p.metal_level,
        r.individual_rate as monthly_premium,
        p.plan_attributes->>'deductible_individual' as deductible,
        p.plan_attributes->>'moop_individual' as moop
      FROM plans p
      LEFT JOIN rates r ON p.plan_id = r.plan_id AND r.age = 40
      WHERE p.plan_id IN ($1, $2, $3)
      ORDER BY r.individual_rate ASC;
    `, ['21525FL0020002-00', '48121FL0070122-00', '44228FL0040008-00']);
    console.table(costs.rows);

    // DEMO 2: Specialist costs
    console.log('\n═══ DEMO 2: Specialist Visit Costs ═══');
    const specialist = await client.query(`
      SELECT 
        p.plan_marketing_name,
        p.issuer_name,
        b.cost_sharing_details->>'copay_inn_tier1' as specialist_copay,
        b.cost_sharing_details->>'explanation' as notes
      FROM plans p
      LEFT JOIN benefits b ON p.plan_id = b.plan_id 
        AND b.benefit_name = 'Specialist Visit'
      WHERE p.plan_id IN ($1, $2, $3);
    `, ['21525FL0020002-00', '48121FL0070122-00', '44228FL0040008-00']);
    console.table(specialist.rows);

    // DEMO 3: Emergency Room
    console.log('\n═══ DEMO 3: Emergency Coverage ═══');
    const emergency = await client.query(`
      SELECT 
        p.plan_marketing_name,
        b_er.cost_sharing_details->>'copay_inn_tier1' as er_copay,
        b_uc.cost_sharing_details->>'copay_inn_tier1' as urgent_care_copay,
        b_amb.cost_sharing_details->>'copay_inn_tier1' as ambulance_copay
      FROM plans p
      LEFT JOIN benefits b_er ON p.plan_id = b_er.plan_id 
        AND b_er.benefit_name = 'Emergency Room Services'
      LEFT JOIN benefits b_uc ON p.plan_id = b_uc.plan_id 
        AND b_uc.benefit_name = 'Urgent Care Centers or Facilities'
      LEFT JOIN benefits b_amb ON p.plan_id = b_amb.plan_id 
        AND b_amb.benefit_name = 'Emergency Transportation/Ambulance'
      WHERE p.plan_id IN ($1, $2, $3);
    `, ['21525FL0020002-00', '48121FL0070122-00', '44228FL0040008-00']);
    console.table(emergency.rows);

    // DEMO 4: Drug costs
    console.log('\n═══ DEMO 4: Prescription Drug Costs ═══');
    const drugs = await client.query(`
      SELECT 
        p.plan_marketing_name,
        b_gen.cost_sharing_details->>'copay_inn_tier1' as generic,
        b_pbrand.cost_sharing_details->>'copay_inn_tier1' as preferred_brand,
        b_spec.cost_sharing_details->>'coins_inn_tier1' as specialty_coinsurance
      FROM plans p
      LEFT JOIN benefits b_gen ON p.plan_id = b_gen.plan_id 
        AND b_gen.benefit_name = 'Generic Drugs'
      LEFT JOIN benefits b_pbrand ON p.plan_id = b_pbrand.plan_id 
        AND b_pbrand.benefit_name = 'Preferred Brand Drugs'
      LEFT JOIN benefits b_spec ON p.plan_id = b_spec.plan_id 
        AND b_spec.benefit_name = 'Specialty Drugs'
      WHERE p.plan_id IN ($1, $2, $3);
    `, ['21525FL0020002-00', '48121FL0070122-00', '44228FL0040008-00']);
    console.table(drugs.rows);

    // DEMO 5: Full comparison
    console.log('\n═══ DEMO 5: Complete Plan Comparison ═══');
    const comparison = await client.query(`
      SELECT 
        p.plan_marketing_name as plan,
        p.issuer_name as carrier,
        p.metal_level as level,
        r.individual_rate as premium,
        p.plan_attributes->>'deductible_individual' as deductible,
        p.plan_attributes->>'moop_individual' as moop,
        b_pcp.cost_sharing_details->>'copay_inn_tier1' as pcp_copay,
        b_spec.cost_sharing_details->>'copay_inn_tier1' as specialist_copay,
        b_er.cost_sharing_details->>'copay_inn_tier1' as er_copay,
        b_drug.cost_sharing_details->>'copay_inn_tier1' as generic_drug
      FROM plans p
      LEFT JOIN rates r ON p.plan_id = r.plan_id AND r.age = 40
      LEFT JOIN benefits b_pcp ON p.plan_id = b_pcp.plan_id 
        AND b_pcp.benefit_name = 'Primary Care Visit to Treat an Injury or Illness'
      LEFT JOIN benefits b_spec ON p.plan_id = b_spec.plan_id 
        AND b_spec.benefit_name = 'Specialist Visit'
      LEFT JOIN benefits b_er ON p.plan_id = b_er.plan_id 
        AND b_er.benefit_name = 'Emergency Room Services'
      LEFT JOIN benefits b_drug ON p.plan_id = b_drug.plan_id 
        AND b_drug.benefit_name = 'Generic Drugs'
      WHERE p.plan_id IN ($1, $2, $3)
      ORDER BY r.individual_rate ASC;
    `, ['21525FL0020002-00', '48121FL0070122-00', '44228FL0040008-00']);
    console.table(comparison.rows);

    console.log('\n✅ Demo complete!');
  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    await client.end();
  }
}

demo();
```

**Run:**
```bash
node demo.js
```

---

## For Chrome Extension (Direct SQL)

**Option A: Send SQL to Backend Service**

```javascript
// Chrome Extension sends SQL + params
async function queryDatabase(sql, params) {
  const response = await fetch('https://your-backend.com/execute-sql', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sql, params })
  });
  return await response.json();
}

// Usage
const sql = `SELECT * FROM plans WHERE plan_id = $1`;
const result = await queryDatabase(sql, ['21525FL0020002-00']);
```

**Backend (Express.js):**
```javascript
const express = require('express');
const { Client } = require('pg');

const app = express();
app.use(express.json());

app.post('/execute-sql', async (req, res) => {
  const { sql, params } = req.body;
  
  const client = new Client({
    host: 'aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com',
    port: 5432,
    database: 'aca_plans',
    user: 'aca_admin',
    password: 'AvRePOWBfVFZyPsKPPG2tV3r',
    ssl: { rejectUnauthorized: false }
  });
  
  try {
    await client.connect();
    const result = await client.query(sql, params);
    res.json(result.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  } finally {
    await client.end();
  }
});

app.listen(3000, () => console.log('SQL proxy running on port 3000'));
```

---

## Test Plan IDs

Use these for your demo:

**Florida Plans (ZIP 33433):**
```
'21525FL0020002-00'  // Oscar Bronze Classic 4700
'48121FL0070122-00'  // Cigna Connect Bronze Mid-South
'44228FL0040008-00'  // Oscar Silver Simple Save
'48121FL0070051-00'  // Cigna Connect myDiabetesCare
```

---

## Common Benefit Names

```javascript
const BENEFITS = {
  PRIMARY_CARE: 'Primary Care Visit to Treat an Injury or Illness',
  SPECIALIST: 'Specialist Visit',
  ER: 'Emergency Room Services',
  URGENT_CARE: 'Urgent Care Centers or Facilities',
  AMBULANCE: 'Emergency Transportation/Ambulance',
  GENERIC_DRUGS: 'Generic Drugs',
  BRAND_DRUGS: 'Preferred Brand Drugs',
  SPECIALTY_DRUGS: 'Specialty Drugs',
  HOSPITAL_INPATIENT: 'Inpatient Hospital Services (e.g., Hospital Stay)',
  XRAY: 'X-rays and Diagnostic Imaging',
  MRI: 'Imaging (CT/PET Scans, MRIs)',
  LAB: 'Laboratory Outpatient and Professional Services'
};
```

---

## ⚡ Quick Wins for Demo

### Show This First:
1. **Monthly costs** - Clients love seeing premium comparisons
2. **Total annual cost** - Premium × 12 + MOOP
3. **Specialist costs** - Common use case
4. **Drug costs** - Generic vs brand comparison
5. **Emergency coverage** - Peace of mind

### Demo Script (2 minutes):
```
"Let me show you how we can compare these 3 plans:

1. Monthly premium at age 40: $284 to $395
2. If you visit a specialist: $0 to $125 copay
3. If you need the ER: $350 to $500
4. Your generic prescriptions: $5 to $10
5. Worst case annual cost: $12,500 to $14,000"
```

---

## Next Steps (After Demo)

1. ✅ **Working SQL queries** (done)
2. 🔄 **Build REST API** (migrate from direct SQL)
3. 🔄 **Add authentication** (API keys)
4. 🔄 **Add rate limiting** (prevent abuse)
5. 🔄 **Cache results** (improve performance)

But for now... **this will work for the demo!** 🚀
