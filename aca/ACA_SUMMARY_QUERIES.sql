-- ============================================================================
-- ACA Database Summary Statistics Queries
-- ============================================================================
-- Run these in TablePlus to explore your 30-state federal marketplace database
--
-- Database: aca_plans
-- Host: aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Overall Database Summary
-- ----------------------------------------------------------------------------
SELECT 
    'Plans' as metric, 
    COUNT(*)::text as value 
FROM plans

UNION ALL

SELECT 
    'States', 
    COUNT(DISTINCT state_code)::text 
FROM plans

UNION ALL

SELECT 
    'Counties', 
    COUNT(*)::text 
FROM counties

UNION ALL

SELECT 
    'ZIP Codes', 
    COUNT(DISTINCT zip_code)::text 
FROM zip_counties

UNION ALL

SELECT 
    'Service Areas', 
    COUNT(DISTINCT service_area_id)::text 
FROM service_areas

UNION ALL

SELECT 
    'Issuers', 
    COUNT(DISTINCT issuer_id)::text 
FROM plans;


-- ----------------------------------------------------------------------------
-- 2. Plans by Metal Level (Overall)
-- ----------------------------------------------------------------------------
SELECT 
    metal_level,
    COUNT(*) as plan_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
FROM plans
GROUP BY metal_level
ORDER BY plan_count DESC;


-- ----------------------------------------------------------------------------
-- 3. Plans by State (All 30 States)
-- ----------------------------------------------------------------------------
SELECT 
    p.state_code,
    c.state_name,
    COUNT(*) as plan_count,
    COUNT(DISTINCT p.issuer_id) as issuer_count,
    COUNT(DISTINCT p.service_area_id) as service_area_count
FROM plans p
LEFT JOIN counties c ON p.state_code = c.state_code
GROUP BY p.state_code, c.state_name
ORDER BY plan_count DESC;


-- ----------------------------------------------------------------------------
-- 4. Average Plans per State
-- ----------------------------------------------------------------------------
SELECT 
    ROUND(AVG(plan_count), 0) as avg_plans_per_state,
    MIN(plan_count) as min_plans,
    MAX(plan_count) as max_plans,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY plan_count) as median_plans
FROM (
    SELECT state_code, COUNT(*) as plan_count
    FROM plans
    GROUP BY state_code
) state_counts;


-- ----------------------------------------------------------------------------
-- 5. Top 10 States by Plan Count
-- ----------------------------------------------------------------------------
SELECT 
    p.state_code,
    c.state_name,
    COUNT(*) as total_plans,
    COUNT(*) FILTER (WHERE p.metal_level = 'Silver') as silver_plans,
    COUNT(*) FILTER (WHERE p.metal_level = 'Gold') as gold_plans,
    COUNT(*) FILTER (WHERE p.metal_level = 'Bronze') as bronze_plans,
    COUNT(*) FILTER (WHERE p.metal_level = 'Expanded Bronze') as expanded_bronze_plans,
    COUNT(*) FILTER (WHERE p.metal_level = 'Platinum') as platinum_plans,
    COUNT(DISTINCT p.issuer_name) as unique_issuers
FROM plans p
LEFT JOIN counties c ON p.state_code = c.state_code
GROUP BY p.state_code, c.state_name
ORDER BY total_plans DESC
LIMIT 10;


-- ----------------------------------------------------------------------------
-- 6. Bottom 10 States by Plan Count
-- ----------------------------------------------------------------------------
SELECT 
    p.state_code,
    c.state_name,
    COUNT(*) as total_plans,
    COUNT(DISTINCT p.issuer_name) as unique_issuers
FROM plans p
LEFT JOIN counties c ON p.state_code = c.state_code
GROUP BY p.state_code, c.state_name
ORDER BY total_plans ASC
LIMIT 10;


-- ----------------------------------------------------------------------------
-- 7. Plans by Plan Type
-- ----------------------------------------------------------------------------
SELECT 
    plan_type,
    COUNT(*) as plan_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
FROM plans
WHERE plan_type IS NOT NULL AND plan_type != ''
GROUP BY plan_type
ORDER BY plan_count DESC;


-- ----------------------------------------------------------------------------
-- 8. Metal Level Distribution by State (Top 5 States)
-- ----------------------------------------------------------------------------
SELECT 
    state_code,
    metal_level,
    COUNT(*) as plans,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY state_code), 1) as pct_of_state
FROM plans
WHERE state_code IN (
    SELECT state_code 
    FROM plans 
    GROUP BY state_code 
    ORDER BY COUNT(*) DESC 
    LIMIT 5
)
GROUP BY state_code, metal_level
ORDER BY state_code, plans DESC;


-- ----------------------------------------------------------------------------
-- 9. Issuer Market Share (Top 15 Issuers)
-- ----------------------------------------------------------------------------
SELECT 
    issuer_name,
    COUNT(*) as plan_count,
    COUNT(DISTINCT state_code) as states_operating_in,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as market_share_pct
FROM plans
WHERE issuer_name IS NOT NULL
GROUP BY issuer_name
ORDER BY plan_count DESC
LIMIT 15;


-- ----------------------------------------------------------------------------
-- 10. Service Area Coverage Statistics
-- ----------------------------------------------------------------------------
SELECT 
    state_code,
    COUNT(DISTINCT service_area_id) as service_areas,
    SUM(CASE WHEN covers_entire_state THEN 1 ELSE 0 END) as statewide_areas,
    SUM(CASE WHEN NOT covers_entire_state THEN 1 ELSE 0 END) as county_specific_areas
FROM service_areas
GROUP BY state_code
ORDER BY service_areas DESC;


-- ----------------------------------------------------------------------------
-- 11. ZIP Code Coverage by State
-- ----------------------------------------------------------------------------
SELECT 
    zc.state_code,
    COUNT(DISTINCT zc.zip_code) as zip_codes_covered,
    COUNT(DISTINCT zc.county_fips) as counties_covered
FROM zip_counties zc
WHERE zc.state_code IN (SELECT DISTINCT state_code FROM plans)
GROUP BY zc.state_code
ORDER BY zip_codes_covered DESC;


-- ----------------------------------------------------------------------------
-- 12. New Plans vs Existing Plans
-- ----------------------------------------------------------------------------
SELECT 
    CASE 
        WHEN is_new_plan THEN 'New Plan'
        ELSE 'Existing Plan'
    END as plan_status,
    COUNT(*) as plan_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
FROM plans
GROUP BY is_new_plan
ORDER BY plan_count DESC;


-- ----------------------------------------------------------------------------
-- 13. HSA-Eligible Plans
-- ----------------------------------------------------------------------------
SELECT 
    (plan_attributes->>'is_hsa_eligible') as hsa_eligible,
    COUNT(*) as plan_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
FROM plans
WHERE plan_attributes->>'is_hsa_eligible' IS NOT NULL
GROUP BY plan_attributes->>'is_hsa_eligible'
ORDER BY plan_count DESC;


-- ----------------------------------------------------------------------------
-- 14. Plans by Design Type
-- ----------------------------------------------------------------------------
SELECT 
    plan_attributes->>'design_type' as design_type,
    COUNT(*) as plan_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
FROM plans
WHERE plan_attributes->>'design_type' IS NOT NULL 
    AND plan_attributes->>'design_type' != ''
GROUP BY plan_attributes->>'design_type'
ORDER BY plan_count DESC;


-- ----------------------------------------------------------------------------
-- 15. Average Plans per ZIP Code (Sample)
-- ----------------------------------------------------------------------------
WITH zip_plan_counts AS (
    SELECT 
        zc.zip_code,
        zc.state_code,
        COUNT(DISTINCT p.plan_id) as plans_available
    FROM zip_counties zc
    JOIN plan_service_areas psa ON zc.county_fips = psa.county_fips
    JOIN plans p ON psa.service_area_id = p.service_area_id
    GROUP BY zc.zip_code, zc.state_code
)
SELECT 
    state_code,
    ROUND(AVG(plans_available), 0) as avg_plans_per_zip,
    MIN(plans_available) as min_plans,
    MAX(plans_available) as max_plans,
    COUNT(*) as zip_codes_sampled
FROM zip_plan_counts
GROUP BY state_code
ORDER BY avg_plans_per_zip DESC
LIMIT 15;


-- ----------------------------------------------------------------------------
-- 16. Sample High-Coverage ZIPs (Most Plans)
-- ----------------------------------------------------------------------------
WITH zip_plan_counts AS (
    SELECT 
        zc.zip_code,
        zc.state_code,
        COUNT(DISTINCT p.plan_id) as plans_available
    FROM zip_counties zc
    JOIN plan_service_areas psa ON zc.county_fips = psa.county_fips
    JOIN plans p ON psa.service_area_id = p.service_area_id
    GROUP BY zc.zip_code, zc.state_code
)
SELECT 
    zip_code,
    state_code,
    plans_available
FROM zip_plan_counts
ORDER BY plans_available DESC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- 17. Sample Low-Coverage ZIPs (Fewest Plans)
-- ----------------------------------------------------------------------------
WITH zip_plan_counts AS (
    SELECT 
        zc.zip_code,
        zc.state_code,
        COUNT(DISTINCT p.plan_id) as plans_available
    FROM zip_counties zc
    JOIN plan_service_areas psa ON zc.county_fips = psa.county_fips
    JOIN plans p ON psa.service_area_id = p.service_area_id
    GROUP BY zc.zip_code, zc.state_code
)
SELECT 
    zip_code,
    state_code,
    plans_available
FROM zip_plan_counts
ORDER BY plans_available ASC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- 18. Multi-County Service Areas
-- ----------------------------------------------------------------------------
SELECT 
    service_area_id,
    state_code,
    COUNT(DISTINCT county_fips) as counties_covered
FROM plan_service_areas
GROUP BY service_area_id, state_code
HAVING COUNT(DISTINCT county_fips) > 10
ORDER BY counties_covered DESC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- 19. Plans with Deductible Information
-- ----------------------------------------------------------------------------
SELECT 
    'Plans with Individual Deductible' as metric,
    COUNT(*) as plan_count
FROM plans
WHERE plan_attributes->>'deductible_individual' IS NOT NULL 
    AND plan_attributes->>'deductible_individual' != ''

UNION ALL

SELECT 
    'Plans with Family Deductible',
    COUNT(*)
FROM plans
WHERE plan_attributes->>'deductible_family' IS NOT NULL 
    AND plan_attributes->>'deductible_family' != ''

UNION ALL

SELECT 
    'Plans with Individual MOOP',
    COUNT(*)
FROM plans
WHERE plan_attributes->>'moop_individual' IS NOT NULL 
    AND plan_attributes->>'moop_individual' != ''

UNION ALL

SELECT 
    'Plans with Family MOOP',
    COUNT(*)
FROM plans
WHERE plan_attributes->>'moop_family' IS NOT NULL 
    AND plan_attributes->>'moop_family' != '';


-- ----------------------------------------------------------------------------
-- 20. Complete State Summary (All 30 States)
-- ----------------------------------------------------------------------------
SELECT 
    p.state_code,
    MAX(c.state_name) as state_name,
    COUNT(*) as total_plans,
    COUNT(DISTINCT p.issuer_id) as issuers,
    COUNT(DISTINCT p.service_area_id) as service_areas,
    COUNT(*) FILTER (WHERE p.metal_level = 'Silver') as silver,
    COUNT(*) FILTER (WHERE p.metal_level = 'Gold') as gold,
    COUNT(*) FILTER (WHERE p.metal_level = 'Expanded Bronze') as exp_bronze,
    COUNT(*) FILTER (WHERE p.metal_level = 'Bronze') as bronze,
    COUNT(*) FILTER (WHERE p.metal_level = 'Platinum') as platinum,
    COUNT(*) FILTER (WHERE p.metal_level = 'Catastrophic') as catastrophic
FROM plans p
LEFT JOIN counties c ON p.state_code = c.state_code
GROUP BY p.state_code
ORDER BY total_plans DESC;
