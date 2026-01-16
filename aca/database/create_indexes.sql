-- Optimized Indexes for ACA Benefits Queries
-- Run AFTER loading benefits table
-- These indexes optimize the 3 key queries: drug costs, specialist costs, MOOP

-- ============================================================
-- CRITICAL INDEXES (Must Have)
-- ============================================================

-- Benefits table: plan_id + benefit_name (composite for JOINs)
-- Speeds up: JOIN benefits ON plan_id WHERE benefit_name = 'X'
CREATE INDEX IF NOT EXISTS idx_benefits_plan_benefit 
ON benefits(plan_id, benefit_name);

-- Benefits table: benefit_name (for filtering)
-- Speeds up: WHERE benefit_name = 'Generic Drugs'
CREATE INDEX IF NOT EXISTS idx_benefits_benefit_name 
ON benefits(benefit_name);

-- Benefits table: GIN index for JSONB queries
-- Speeds up: cost_sharing_details->>'copay_inn_tier1'
CREATE INDEX IF NOT EXISTS idx_benefits_cost_sharing_gin 
ON benefits USING GIN(cost_sharing_details);

-- Plans table: base plan ID substring (for variant matching)
-- Speeds up: WHERE plan_id LIKE 'base_id%'
CREATE INDEX IF NOT EXISTS idx_plans_base_id 
ON plans(SUBSTRING(plan_id, 1, 14));

-- Plans table: state_code (for multi-state queries)
CREATE INDEX IF NOT EXISTS idx_plans_state_code 
ON plans(state_code);

-- ============================================================
-- OPTIONAL INDEXES (Nice to Have)
-- ============================================================

-- Benefits table: is_covered (for filtering covered benefits)
CREATE INDEX IF NOT EXISTS idx_benefits_is_covered 
ON benefits(is_covered) WHERE is_covered = true;

-- Plans table: metal_level (for filtering by tier)
CREATE INDEX IF NOT EXISTS idx_plans_metal_level 
ON plans(metal_level);

-- Plans table: issuer_id (for carrier comparisons)
CREATE INDEX IF NOT EXISTS idx_plans_issuer_id 
ON plans(issuer_id);

-- ============================================================
-- ANALYZE for Query Planner
-- ============================================================

-- Update statistics for query optimizer
ANALYZE benefits;
ANALYZE plans;
ANALYZE rates;

-- ============================================================
-- Index Statistics
-- ============================================================

-- View index sizes
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- View table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) AS total_size,
    pg_size_pretty(pg_relation_size(tablename::regclass)) AS table_size,
    pg_size_pretty(pg_total_relation_size(tablename::regclass) - pg_relation_size(tablename::regclass)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;
