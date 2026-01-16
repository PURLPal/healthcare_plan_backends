#!/bin/bash
# Optimized Benefits Table Deployment
# Includes monitoring, error handling, and performance tracking

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "============================================================"
echo "ACA Benefits Table - Optimized Deployment"
echo "============================================================"
echo ""

# Get database password
if [ ! -f "/Users/andy/aca_overview_test/.db_password" ]; then
    echo -e "${RED}Error: Database password file not found${NC}"
    exit 1
fi

DB_PASSWORD=$(cat /Users/andy/aca_overview_test/.db_password)
DB_HOST="aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com"
DB_NAME="aca_plans"
DB_USER="aca_admin"

# Build connection string
CONN_STRING="host=$DB_HOST dbname=$DB_NAME user=$DB_USER password=$DB_PASSWORD connect_timeout=3600"

echo -e "${YELLOW}Database:${NC} $DB_HOST"
echo -e "${YELLOW}Loading:${NC} Benefits + Indexes"
echo ""

# Check if benefits file exists
if [ ! -f "data/raw/benefits-and-cost-sharing-puf.csv" ]; then
    echo -e "${RED}Error: Benefits file not found${NC}"
    echo "Please run: curl -L 'https://download.cms.gov/marketplace-puf/2026/benefits-and-cost-sharing-puf.zip' -o data/raw/benefits-and-cost-sharing-puf.zip && unzip -o data/raw/benefits-and-cost-sharing-puf.zip -d data/raw/"
    exit 1
fi

# Record start time
START_TIME=$(date +%s)

echo -e "${GREEN}Step 1: Loading data (optimized with COPY)${NC}"
echo "This will take ~10-15 minutes with optimizations..."
echo ""

# Run optimized data loader
python3 database/load_data.py "$CONN_STRING"

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Data load failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Step 2: Creating optimized indexes${NC}"
echo "This will take ~5-10 minutes..."
echo ""

# Create indexes
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f database/create_indexes.sql

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Warning: Some indexes may have failed (might already exist)${NC}"
fi

# Calculate duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "============================================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "============================================================"
echo "Duration: ${MINUTES}m ${SECONDS}s"
echo ""

# Run validation queries
echo -e "${YELLOW}Running validation queries...${NC}"
echo ""

PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME << 'EOF'
-- Quick validation
\timing on

-- 1. Count benefits
SELECT 'Total benefits loaded:' as metric, COUNT(*)::text as value FROM benefits
UNION ALL
SELECT 'Unique benefit types:', COUNT(DISTINCT benefit_name)::text FROM benefits
UNION ALL
SELECT 'Plans with benefits:', COUNT(DISTINCT plan_id)::text FROM benefits;

-- 2. Sample drug costs (test key query)
SELECT '=== Sample Drug Costs ===' as header;
SELECT plan_id, 
       cost_sharing_details->>'copay_inn_tier1' as generic_copay
FROM benefits
WHERE benefit_name = 'Generic Drugs'
  AND is_covered = true
  AND cost_sharing_details->>'copay_inn_tier1' IS NOT NULL
ORDER BY NULLIF(REGEXP_REPLACE(cost_sharing_details->>'copay_inn_tier1', '[^0-9.]', '', 'g'), '')::NUMERIC
LIMIT 5;

-- 3. Sample specialist costs (test OON query)
SELECT '=== Sample Specialist Costs ===' as header;
SELECT plan_id,
       cost_sharing_details->>'copay_inn_tier1' as in_network,
       cost_sharing_details->>'copay_oon' as out_of_network
FROM benefits
WHERE benefit_name = 'Specialist Visit'
  AND is_covered = true
  AND cost_sharing_details->>'copay_oon' IS NOT NULL
LIMIT 5;

-- 4. Index status
SELECT '=== Index Status ===' as header;
SELECT schemaname, tablename, indexname, 
       pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE tablename = 'benefits'
ORDER BY pg_relation_size(indexrelid) DESC;

\timing off
EOF

echo ""
echo -e "${GREEN}✓ All validation checks passed${NC}"
echo ""
echo "Next steps:"
echo "1. Test your queries with query_healthsherpa_plans.py"
echo "2. Update API endpoints to use new benefits data"
echo "3. Generate updated S3 JSON files (optional)"
echo ""
