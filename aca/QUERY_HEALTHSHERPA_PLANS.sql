-- ============================================================================
-- Querying Plans from HealthSherpa Base IDs (Without Variant Suffixes)
-- ============================================================================
-- Problem: HealthSherpa gives base IDs like "21525FL0020002"
--          Database has variants like "21525FL0020002-00", "21525FL0020002-01"
-- Solution: Match using LIKE pattern or substring matching
-- ============================================================================

-- ----------------------------------------------------------------------------
-- METHOD 1: Query All Variants for HealthSherpa Base Plans
-- ----------------------------------------------------------------------------
-- This gets ALL variants for the base plan IDs from HealthSherpa

WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008', '21525FL0020006',
        '44228FL0040005', '48121FL0070051', '48121FL0070107', '21525FL0020001',
        '21525FL0020004', '44228FL0040001', '21525FL0020005', '44228FL0040007',
        '19898FL0340092', '30252FL0070065', '19898FL0340017', '68398FL0090001',
        '68398FL0030058', '19898FL0340016', '21525FL0020003', '54172FL0010010'
        -- Add more as needed...
    ]) AS base_plan_id
)
SELECT 
    p.plan_id,
    p.plan_marketing_name,
    p.metal_level,
    p.plan_type,
    p.issuer_name,
    -- Extract cost-sharing data from JSONB
    p.plan_attributes->>'deductible_individual' as individual_deductible,
    p.plan_attributes->>'deductible_family' as family_deductible,
    p.plan_attributes->>'moop_individual' as individual_moop,
    p.plan_attributes->>'moop_family' as family_moop,
    p.plan_attributes->>'is_hsa_eligible' as hsa_eligible
FROM plans p
JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_plan_id || '%'
WHERE p.state_code = 'FL'
ORDER BY p.plan_id;


-- ----------------------------------------------------------------------------
-- METHOD 2: Get ONLY ONE Variant per Base Plan (Cleaner)
-- ----------------------------------------------------------------------------
-- This picks the first variant (usually -00) for each base plan

WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008', '21525FL0020006',
        '44228FL0040005', '48121FL0070051', '48121FL0070107', '21525FL0020001'
        -- etc...
    ]) AS base_plan_id
),
matched_plans AS (
    SELECT 
        p.*,
        hs.base_plan_id,
        ROW_NUMBER() OVER (PARTITION BY hs.base_plan_id ORDER BY p.plan_id) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_plan_id || '%'
    WHERE p.state_code = 'FL'
)
SELECT 
    plan_id,
    plan_marketing_name,
    metal_level,
    plan_type,
    issuer_name,
    plan_attributes->>'deductible_individual' as individual_deductible,
    plan_attributes->>'moop_individual' as individual_moop
FROM matched_plans
WHERE rn = 1
ORDER BY plan_id;


-- ----------------------------------------------------------------------------
-- QUERY 1: Plans with Lowest Maximum Out-of-Pocket Costs
-- ----------------------------------------------------------------------------
-- NOTE: This uses data currently in plan_attributes JSONB field
-- For more detailed MOOP data (Tier 2, OON), you need the benefits table loaded

WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008', '21525FL0020006',
        '44228FL0040005', '48121FL0070051', '48121FL0070107', '21525FL0020001',
        '21525FL0020004', '44228FL0040001', '21525FL0020005', '44228FL0040007',
        '19898FL0340092', '30252FL0070065', '19898FL0340017', '68398FL0090001'
        -- Full list...
    ]) AS base_plan_id
),
matched_plans AS (
    SELECT 
        p.plan_id,
        p.plan_marketing_name,
        p.metal_level,
        p.plan_type,
        p.issuer_name,
        -- Convert MOOP strings to numbers for sorting
        NULLIF(REGEXP_REPLACE(p.plan_attributes->>'moop_individual', '[^0-9.]', '', 'g'), '')::NUMERIC as moop_individual_num,
        p.plan_attributes->>'moop_individual' as moop_individual,
        p.plan_attributes->>'moop_family' as moop_family,
        ROW_NUMBER() OVER (PARTITION BY hs.base_plan_id ORDER BY p.plan_id) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_plan_id || '%'
    WHERE p.state_code = 'FL'
)
SELECT 
    plan_id,
    plan_marketing_name,
    metal_level,
    plan_type,
    issuer_name,
    moop_individual,
    moop_family
FROM matched_plans
WHERE rn = 1 
  AND moop_individual_num IS NOT NULL
ORDER BY moop_individual_num ASC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- QUERY 2: Plans with Lowest Deductibles
-- ----------------------------------------------------------------------------

WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008', '21525FL0020006'
        -- Full list...
    ]) AS base_plan_id
),
matched_plans AS (
    SELECT 
        p.plan_id,
        p.plan_marketing_name,
        p.metal_level,
        p.plan_type,
        p.issuer_name,
        NULLIF(REGEXP_REPLACE(p.plan_attributes->>'deductible_individual', '[^0-9.]', '', 'g'), '')::NUMERIC as deductible_individual_num,
        p.plan_attributes->>'deductible_individual' as deductible_individual,
        p.plan_attributes->>'deductible_family' as deductible_family,
        p.plan_attributes->>'moop_individual' as moop_individual,
        ROW_NUMBER() OVER (PARTITION BY hs.base_plan_id ORDER BY p.plan_id) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_plan_id || '%'
    WHERE p.state_code = 'FL'
)
SELECT 
    plan_id,
    plan_marketing_name,
    metal_level,
    plan_type,
    issuer_name,
    deductible_individual,
    deductible_family,
    moop_individual
FROM matched_plans
WHERE rn = 1 
  AND deductible_individual_num IS NOT NULL
ORDER BY deductible_individual_num ASC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- QUERY 3: Plans Grouped by Metal Level with Cost Summary
-- ----------------------------------------------------------------------------

WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY[
        '21525FL0020002', '48121FL0070122', '44228FL0040008'
        -- Full list...
    ]) AS base_plan_id
),
matched_plans AS (
    SELECT 
        p.plan_id,
        p.plan_marketing_name,
        p.metal_level,
        p.plan_type,
        p.issuer_name,
        NULLIF(REGEXP_REPLACE(p.plan_attributes->>'deductible_individual', '[^0-9.]', '', 'g'), '')::NUMERIC as deductible_num,
        NULLIF(REGEXP_REPLACE(p.plan_attributes->>'moop_individual', '[^0-9.]', '', 'g'), '')::NUMERIC as moop_num,
        p.plan_attributes->>'is_hsa_eligible' as hsa_eligible,
        ROW_NUMBER() OVER (PARTITION BY hs.base_plan_id ORDER BY p.plan_id) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_plan_id || '%'
    WHERE p.state_code = 'FL'
)
SELECT 
    metal_level,
    COUNT(*) as plan_count,
    ROUND(AVG(deductible_num), 0) as avg_deductible,
    MIN(deductible_num) as min_deductible,
    MAX(deductible_num) as max_deductible,
    ROUND(AVG(moop_num), 0) as avg_moop,
    MIN(moop_num) as min_moop,
    MAX(moop_num) as max_moop,
    SUM(CASE WHEN hsa_eligible = 'Yes' THEN 1 ELSE 0 END) as hsa_eligible_count
FROM matched_plans
WHERE rn = 1
GROUP BY metal_level
ORDER BY 
    CASE metal_level
        WHEN 'Platinum' THEN 1
        WHEN 'Gold' THEN 2
        WHEN 'Silver' THEN 3
        WHEN 'Expanded Bronze' THEN 4
        WHEN 'Bronze' THEN 5
        WHEN 'Catastrophic' THEN 6
        ELSE 7
    END;


-- ============================================================================
-- WHAT'S MISSING: Detailed Benefit Data
-- ============================================================================
-- The queries above can ONLY use data in the plan_attributes JSONB field:
--   ✅ Individual/Family Deductible (In-Network Tier 1)
--   ✅ Individual/Family MOOP (In-Network Tier 1)
--   ✅ HSA Eligibility
--   ✅ Plan Type, Metal Level, Issuer
--
-- For your desired queries, you need data from the benefits table:
--   ❌ Out-of-network specialist costs (not in plan_attributes)
--   ❌ Drug copays/coinsurance (not in plan_attributes)
--   ❌ Primary care copays (not in plan_attributes)
--   ❌ ER copays (not in plan_attributes)
--   ❌ Tier 2 deductibles/MOOP (not in plan_attributes)
--
-- SOLUTION: Load the benefits-and-cost-sharing-puf.csv file
-- ============================================================================


-- ----------------------------------------------------------------------------
-- EXAMPLE: What Queries WOULD Look Like With Benefits Data Loaded
-- ----------------------------------------------------------------------------

-- Query: Plans with lowest out-of-network specialist costs
/*
WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY['21525FL0020002', ...]) AS base_plan_id
),
matched_plans AS (
    SELECT 
        p.plan_id,
        p.plan_marketing_name,
        p.metal_level,
        hs.base_plan_id,
        ROW_NUMBER() OVER (PARTITION BY hs.base_plan_id ORDER BY p.plan_id) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_plan_id || '%'
)
SELECT 
    mp.plan_id,
    mp.plan_marketing_name,
    mp.metal_level,
    -- Specialist visit cost sharing
    b_specialist.cost_sharing_details->>'CopayOutOfNet' as specialist_oon_copay,
    b_specialist.cost_sharing_details->>'CoinsOutOfNet' as specialist_oon_coinsurance,
    -- Out-of-network MOOP
    p.plan_attributes->>'TEHBOutOfNetIndividualMOOP' as oon_moop
FROM matched_plans mp
JOIN plans p ON mp.plan_id = p.plan_id
LEFT JOIN benefits b_specialist ON mp.plan_id = b_specialist.plan_id 
    AND b_specialist.benefit_name = 'SpecialistVisit'
WHERE mp.rn = 1
ORDER BY 
    NULLIF(REGEXP_REPLACE(b_specialist.cost_sharing_details->>'CopayOutOfNet', '[^0-9.]', '', 'g'), '')::NUMERIC ASC
LIMIT 20;
*/


-- Query: Plans with lowest drug costs
/*
WITH healthsherpa_plans AS (
    SELECT unnest(ARRAY['21525FL0020002', ...]) AS base_plan_id
),
matched_plans AS (
    SELECT 
        p.plan_id,
        p.plan_marketing_name,
        p.metal_level,
        ROW_NUMBER() OVER (PARTITION BY hs.base_plan_id ORDER BY p.plan_id) as rn
    FROM plans p
    JOIN healthsherpa_plans hs ON p.plan_id LIKE hs.base_plan_id || '%'
)
SELECT 
    mp.plan_id,
    mp.plan_marketing_name,
    mp.metal_level,
    -- Drug costs
    b_generic.cost_sharing_details->>'CopayInnTier1' as generic_copay,
    b_brand.cost_sharing_details->>'CopayInnTier1' as preferred_brand_copay,
    b_specialty.cost_sharing_details->>'CoinsInnTier1' as specialty_coinsurance
FROM matched_plans mp
LEFT JOIN benefits b_generic ON mp.plan_id = b_generic.plan_id 
    AND b_generic.benefit_name = 'GenericDrugs'
LEFT JOIN benefits b_brand ON mp.plan_id = b_brand.plan_id 
    AND b_brand.benefit_name = 'PreferredBrandDrugs'
LEFT JOIN benefits b_specialty ON mp.plan_id = b_specialty.plan_id 
    AND b_specialty.benefit_name = 'SpecialtyDrugs'
WHERE mp.rn = 1
ORDER BY 
    NULLIF(b_generic.cost_sharing_details->>'CopayInnTier1', '')::NUMERIC ASC
LIMIT 20;
*/


-- ============================================================================
-- RECOMMENDED APPROACH
-- ============================================================================
-- 1. Use METHOD 2 above to match HealthSherpa base IDs to database variants
--    (Pick first variant per base plan to avoid duplicates)
--
-- 2. For current limited queries, use plan_attributes JSONB:
--    - Deductibles (Tier 1 in-network only)
--    - MOOP (Tier 1 in-network only)
--    - HSA eligibility
--
-- 3. For detailed benefit queries (specialists, drugs, etc.):
--    - Download benefits-and-cost-sharing-puf.csv from CMS
--    - Update load_data.py to load benefits table
--    - Use benefit JOIN queries (examples commented out above)
--
-- 4. Performance optimization:
--    - Create index on SUBSTRING(plan_id, 1, 14) for faster base ID matching
--    - Create GIN index on plan_attributes JSONB
--    - Pre-compute common benefit aggregations
-- ============================================================================


-- ----------------------------------------------------------------------------
-- CREATE USEFUL INDEX for Base Plan ID Matching
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_plans_base_id 
ON plans (SUBSTRING(plan_id, 1, 14));

-- This speeds up queries like: plan_id LIKE 'base_id%'
