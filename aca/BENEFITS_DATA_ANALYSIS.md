# Benefits Data - What We Have That HealthSherpa Doesn't

## Database Benefits Inventory

**Total Benefit Rows:** 1,421,810  
**Unique Benefit Categories:** 196  
**Plans with Benefits:** 20,354  
**Benefits with Detailed Cost-Sharing:** 1,097,582 (77.2%)

---

## What Makes Our Benefits Data Unique

HealthSherpa **displays** benefits nicely, but you cannot:
- ❌ Filter plans by specific benefit coverage
- ❌ Query "Show me plans where generic drugs are $0 copay"
- ❌ Find plans with no deductible for primary care
- ❌ Compare benefit costs across multiple plans
- ❌ Build custom benefit comparison tools

**Our database enables all of these queries.**

---

## 196 Benefit Categories We Track

### Core Medical Services (20,354 plans each)
- Primary Care Visit to Treat an Injury or Illness
- Specialist Visit
- Emergency Room Services
- Urgent Care Centers or Facilities
- Mental/Behavioral Health Urgent Care
- Preventive Care/Screening/Immunization
- Diagnostic Test (X-Ray, Blood Work)
- Imaging (CT/PET Scans, MRIs)
- Outpatient Surgery Physician/Surgical Services
- Outpatient Facility Fee (e.g., Ambulatory Surgery Center)
- Inpatient Hospital Services (e.g., Hospital Stay)
- Inpatient Physician and Surgical Services

### Prescription Drugs (20,354 plans each)
- Generic Drugs
- Preferred Brand Drugs
- Non-Preferred Brand Drugs
- Specialty Drugs
- Non-Preferred Specialty Drugs
- Non-Preferred Generic Drugs
- Generic Drugs Maintenance (90-day supply)

### Mental Health & Substance Abuse (20,354 plans each)
- Mental/Behavioral Health Outpatient Services
- Mental/Behavioral Health Inpatient Services
- Substance Abuse Disorder Outpatient Services
- Substance Abuse Disorder Inpatient Services

### Rehabilitation & Therapy (20,354 plans each)
- Rehabilitative Speech Therapy
- Rehabilitative Occupational and Rehabilitative Physical Therapy
- Habilitative Speech Therapy
- Habilitative Occupational and Habilitative Physical Therapy
- Chiropractic Care

### Specialty Services (20,354 plans each)
- Skilled Nursing Facility
- Durable Medical Equipment
- Home Health Care Services
- Hospice Services
- Emergency Transportation/Ambulance
- Routine Eye Exam (Adult)
- Eye Glasses (Adult)
- Routine Dental Services (Adult)
- Orthodontia (Adult)
- Routine Eye Exam for Children
- Eye Glasses for Children
- Dental Check-Up for Children
- Basic Dental Care - Child
- Orthodontia - Child

### Maternity & Prenatal
- Prenatal and Postnatal Care
- Delivery and All Inpatient Services for Maternity Care
- Well Baby Visits and Care
- Child Health Supervision

### Additional Covered Services
- Acupuncture (20,354 plans)
- Bariatric Surgery (20,354 plans)
- Hearing Aids (20,354 plans)
- Infertility Treatment (9,690 plans)
- Routine Foot Care (20,354 plans)
- Diabetic Supplies (many plans)
- Smoking Cessation (various)
- Weight Loss Programs (various)
- Gender Affirming Treatment (4,000+ plans)
- Biomarker Testing (5,000+ plans)
- Virtual Care / Telehealth (5,000+ plans)

---

## Cost-Sharing Details JSONB Structure

**77.2% of benefits have detailed cost-sharing information** in JSONB format:

### Fields Available:

#### 1. **Copay Amounts**
- `copay_inn_tier1` - In-network tier 1 copay
- `copay_inn_tier2` - In-network tier 2 copay  
- `copay_oon` - Out-of-network copay

**Sample Values:**
```json
{
  "copay_inn_tier1": "$30.00",
  "copay_inn_tier2": "$50.00",
  "copay_oon": "$100.00"
}
```

**Top Copay Values:**
- $0.00 (196,441 benefits)
- No Charge (64,508 benefits)
- $40.00 (27,503 benefits)
- $50.00 (21,992 benefits)
- $30.00 (21,949 benefits)

#### 2. **Coinsurance Rates**
- `coins_inn_tier1` - In-network tier 1 coinsurance
- `coins_inn_tier2` - In-network tier 2 coinsurance
- `coins_oon` - Out-of-network coinsurance

**Sample Values:**
```json
{
  "coins_inn_tier1": "30.00% Coinsurance after deductible",
  "coins_inn_tier2": "40.00% Coinsurance after deductible",
  "coins_oon": "60.00% Coinsurance after deductible"
}
```

**Top Coinsurance Values:**
- 0.00% (177,988 benefits)
- 50% after deductible (144,675 benefits)
- 40% after deductible (99,642 benefits)
- 30% after deductible (62,396 benefits)
- 25% after deductible (48,404 benefits)

#### 3. **Visit/Quantity Limits**
- `has_quantity_limit` - Boolean (194,606 benefits have limits)
- `limit_quantity` - Number of visits/items
- `limit_unit` - Type of limit

**Sample Values:**
```json
{
  "has_quantity_limit": true,
  "limit_quantity": "20.0",
  "limit_unit": "Visit(s) per Year"
}
```

**Top Limit Units:**
- Visit(s) per Year (59,487 benefits)
- Visit(s) per Benefit Period (47,857 benefits)
- Item(s) per Year (12,123 benefits)
- Exam(s) per Year (11,842 benefits)
- Days per Benefit Period (9,419 benefits)

**Top Limit Quantities:**
- 1 visit/item (52,763 benefits)
- 30 visits (28,197 benefits)
- 35 visits (25,338 benefits)
- 60 visits (22,363 benefits)
- 20 visits (16,256 benefits)

#### 4. **Explanations & Exclusions**
- `explanation` - Detailed benefit explanation
- `exclusions` - What's not covered

**Sample Explanations:**
- "See policy or plan document for additional benefit explanation" (17,640)
- "Member cost share may increase when using Hospital-based facility" (11,679)
- "Prior authorization may be required" (6,982)

**Sample Exclusions:**
- "Coverage for certain medication categories may also be excluded" (13,668)
- "Excludes dental restorations, orthodontics" (3,226)
- "Non-emergency and non-urgent care from out-of-network" (3,149)

---

## Real-World Use Cases (User-Focused)

### 1. **Find Plans with $0 Copay Primary Care**

**User Need:** "I visit my doctor frequently, show me plans where I don't pay anything"

**Query:**
```sql
SELECT DISTINCT p.plan_id, p.plan_marketing_name, p.metal_level
FROM plans p
JOIN benefits b ON p.plan_id = b.plan_id
WHERE b.benefit_name = 'Primary Care Visit to Treat an Injury or Illness'
  AND b.cost_sharing_details->>'copay_inn_tier1' = '$0.00'
  AND p.state_code = 'TX';
```

**HealthSherpa:** Cannot filter by copay amount, must click through each plan  
**Our Database:** Returns exact list of matching plans instantly

---

### 2. **Compare Drug Coverage Across Plans**

**User Need:** "I take specialty medications - show me the cheapest options"

**Query:**
```sql
SELECT 
    p.plan_marketing_name,
    b.cost_sharing_details->>'copay_inn_tier1' as specialty_cost
FROM plans p
JOIN benefits b ON p.plan_id = b.plan_id
WHERE b.benefit_name = 'Specialty Drugs'
  AND p.state_code = 'FL'
  AND p.plan_id IN (user_filtered_plans)
ORDER BY 
    CAST(REPLACE(REPLACE(b.cost_sharing_details->>'copay_inn_tier1', '$', ''), ' Copay', '') AS DECIMAL);
```

**Result:** Sort plans by specialty drug cost

---

### 3. **Find Plans with No Visit Limits for Mental Health**

**User Need:** "I need ongoing therapy - which plans don't limit visits?"

**Query:**
```sql
SELECT DISTINCT p.plan_id, p.plan_marketing_name
FROM plans p
JOIN benefits b ON p.plan_id = b.plan_id
WHERE b.benefit_name LIKE '%Mental%Outpatient%'
  AND (b.cost_sharing_details->>'has_quantity_limit' IS NULL 
       OR b.cost_sharing_details->>'has_quantity_limit' = 'false')
  AND p.state_code = 'CA';
```

**HealthSherpa:** No way to filter by visit limits  
**Our Database:** Find unlimited mental health plans

---

### 4. **Compare Emergency Room Costs**

**User Need:** "My kid is clumsy - what's my ER cost for each plan?"

**Query:**
```sql
SELECT 
    p.plan_marketing_name,
    p.metal_level,
    b.cost_sharing_details->>'copay_inn_tier1' as er_copay,
    b.cost_sharing_details->>'coins_inn_tier1' as er_coinsurance
FROM plans p
JOIN benefits b ON p.plan_id = b.plan_id
WHERE b.benefit_name = 'Emergency Room Services'
  AND p.plan_id IN (user_shortlist)
ORDER BY p.metal_level;
```

**HealthSherpa:** Must click through each plan to see ER costs  
**Our Database:** Side-by-side ER cost comparison

---

### 5. **Filter by Specific Benefits Coverage**

**User Need:** "I need a plan that covers acupuncture"

**Query:**
```sql
SELECT DISTINCT p.plan_id, p.plan_marketing_name
FROM plans p
JOIN benefits b ON p.plan_id = b.plan_id
WHERE b.benefit_name = 'Acupuncture'
  AND b.is_covered = true
  AND p.state_code = 'WA';
```

**HealthSherpa:** Must manually check each plan's benefit details  
**Our Database:** Filter immediately to acupuncture-covering plans

---

### 6. **Find Low-Cost Generic Drug Plans**

**User Need:** "I only take generic medications - cheapest options?"

**Query:**
```sql
SELECT 
    p.plan_marketing_name,
    b.cost_sharing_details->>'copay_inn_tier1' as generic_cost,
    r.individual_rate as premium_age_40
FROM plans p
JOIN benefits b ON p.plan_id = b.plan_id
JOIN rates r ON p.plan_id = r.plan_id AND r.age = 40
WHERE b.benefit_name = 'Generic Drugs'
  AND p.state_code = 'TX'
ORDER BY 
    CAST(REPLACE(b.cost_sharing_details->>'copay_inn_tier1', '$', '') AS DECIMAL),
    r.individual_rate;
```

**Result:** Plans sorted by generic drug cost, then premium

---

### 7. **Compare Out-of-Network Coverage**

**User Need:** "My doctor isn't in-network - what will out-of-network visits cost?"

**Query:**
```sql
SELECT 
    p.plan_marketing_name,
    p.plan_type,
    b.cost_sharing_details->>'copay_oon' as oon_specialist_copay,
    b.cost_sharing_details->>'coins_oon' as oon_specialist_coinsurance
FROM plans p
JOIN benefits b ON p.plan_id = b.plan_id
WHERE b.benefit_name = 'Specialist Visit'
  AND p.plan_type = 'PPO'  -- Only PPOs have out-of-network
  AND p.plan_id IN (user_shortlist);
```

**HealthSherpa:** Shows out-of-network but can't filter/compare  
**Our Database:** Compare all OON costs at once

---

### 8. **Find Plans with Telehealth/Virtual Care**

**User Need:** "I want virtual doctor visits - which plans offer this?"

**Query:**
```sql
SELECT DISTINCT p.plan_id, p.plan_marketing_name,
       b.cost_sharing_details->>'copay_inn_tier1' as virtual_cost
FROM plans p
JOIN benefits b ON p.plan_id = b.plan_id
WHERE (b.benefit_name LIKE '%Virtual%' OR b.benefit_name LIKE '%Telehealth%')
  AND b.is_covered = true
  AND p.state_code = 'NY';
```

---

### 9. **Compare Maternity Coverage**

**User Need:** "Planning to have a baby - what's my out-of-pocket for delivery?"

**Query:**
```sql
SELECT 
    p.plan_marketing_name,
    prenatal.cost_sharing_details->>'copay_inn_tier1' as prenatal_cost,
    delivery.cost_sharing_details->>'coins_inn_tier1' as delivery_coinsurance,
    p.plan_attributes->>'moop_individual' as max_oop
FROM plans p
JOIN benefits prenatal ON p.plan_id = prenatal.plan_id 
    AND prenatal.benefit_name = 'Prenatal and Postnatal Care'
JOIN benefits delivery ON p.plan_id = delivery.plan_id 
    AND delivery.benefit_name = 'Delivery and All Inpatient Services for Maternity Care'
WHERE p.state_code = 'CA';
```

**HealthSherpa:** Must check multiple benefit sections per plan  
**Our Database:** Combined maternity cost view

---

### 10. **Diabetic-Friendly Plans**

**User Need:** "I'm diabetic - show me plans with good diabetic supply coverage"

**Query:**
```sql
SELECT 
    p.plan_marketing_name,
    supplies.cost_sharing_details->>'copay_inn_tier1' as supplies_cost,
    eye.cost_sharing_details->>'copay_inn_tier1' as eye_exam_cost,
    foot.cost_sharing_details->>'copay_inn_tier1' as foot_care_cost
FROM plans p
JOIN benefits supplies ON p.plan_id = supplies.plan_id 
    AND supplies.benefit_name = 'Diabetic Supplies'
JOIN benefits eye ON p.plan_id = eye.plan_id 
    AND (eye.benefit_name LIKE '%Diabetic%Eye%' OR eye.benefit_name LIKE '%Retinal%')
JOIN benefits foot ON p.plan_id = foot.plan_id 
    AND foot.benefit_name = 'Routine Foot Care'
WHERE p.state_code = 'TX'
  AND supplies.is_covered = true;
```

---

## Sample Benefit Record

**Complete Example:** Acupuncture benefit for Plan 38344AK1060001-01

```json
{
  "plan_id": "38344AK1060001-01",
  "benefit_name": "Acupuncture",
  "is_covered": true,
  "cost_sharing_details": {
    "copay_inn_tier1": "$30.00",
    "coins_oon": "60.00% Coinsurance after deductible",
    "has_quantity_limit": true,
    "limit_quantity": "12.0",
    "limit_unit": "Visit(s) per Year",
    "explanation": "Services must be medically necessary to relieve pain, induce surgical anesthesia, or to treat a covered illness, injury or condition."
  }
}
```

**What this tells users:**
- ✅ Acupuncture is covered
- ✅ In-network copay: $30 per visit
- ✅ Out-of-network: 60% coinsurance after deductible
- ✅ Limited to 12 visits per year
- ✅ Must be medically necessary

---

## Key Advantage: Filtering & Comparison

**HealthSherpa:**
- ✅ Beautiful UI for viewing benefits
- ❌ Cannot filter plans by specific benefit costs
- ❌ Cannot compare benefits across multiple plans simultaneously
- ❌ Must click through each plan individually

**Our Database:**
- ✅ Filter plans by any benefit criteria
- ✅ Compare benefits across unlimited plans
- ✅ Build custom "find my perfect plan" tools
- ✅ Create benefit-based recommendations
- ✅ Enable questions like:
  - "Show me Silver plans where primary care is $0 and ER copay < $500"
  - "Which plans cover acupuncture with no visit limits?"
  - "Cheapest plans for specialty drug users"
  - "Best plans for frequent mental health therapy"

---

## What We Can Build

### 1. **Benefit-Based Plan Finder**
User selects important benefits → Database filters to matching plans

### 2. **Chronic Condition Optimizer**
User indicates diabetes, heart disease, etc. → Database finds plans with best coverage for those specific services

### 3. **Drug Cost Calculator**
User enters medications → Database calculates total drug cost across plans

### 4. **Therapy/Mental Health Finder**
User needs ongoing therapy → Database filters to unlimited or high-limit plans

### 5. **Maternity Planner**
User planning pregnancy → Database calculates total maternity costs per plan

### 6. **Specialist Heavy User Tool**
User sees specialists frequently → Database finds low specialist copay plans

### 7. **Out-of-Network Calculator**
User's doctor not in-network → Database compares OON costs

---

## Summary: The Real Value

**HealthSherpa shows you benefits nicely.**

**Our database lets you:**
1. ✅ **Filter** plans by specific benefit costs
2. ✅ **Compare** benefits across multiple plans instantly
3. ✅ **Calculate** total estimated costs based on usage patterns
4. ✅ **Find** plans optimized for specific medical needs
5. ✅ **Build** custom benefit comparison tools
6. ✅ **Answer** complex questions like "Best plan for diabetic with heart disease who takes 3 specialty medications"

**The 1.4 million benefit records with detailed cost-sharing information enable intelligent plan recommendations that HealthSherpa's UI cannot provide.**

---

## Bottom Line

**HealthSherpa:** Get exact premium dollar amounts  
**Our Database:** Get intelligent benefit-based filtering and comparison

**Together:** Complete solution for plan shopping
