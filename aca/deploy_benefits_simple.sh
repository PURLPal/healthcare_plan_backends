#!/bin/bash
# Simple Benefits-Only Deployment (to existing database)
set -e

echo "============================================================"
echo "ACA Benefits - Optimized Deployment"
echo "============================================================"

DB_PASSWORD=$(cat /Users/andy/aca_overview_test/.db_password)
DB_HOST="aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com"
DB_NAME="aca_plans"
DB_USER="aca_admin"

CONN_STRING="host=$DB_HOST dbname=$DB_NAME user=$DB_USER password=$DB_PASSWORD connect_timeout=3600"

echo "Loading benefits (optimized with COPY)..."
START=$(date +%s)

python3 load_benefits_only.py "$CONN_STRING"

echo ""
echo "Creating indexes..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f database/create_indexes.sql

END=$(date +%s)
DURATION=$((END - START))
echo ""
echo "✓ Complete! Duration: $((DURATION / 60))m $((DURATION % 60))s"
