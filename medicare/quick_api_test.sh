#!/bin/bash
# Quick API Test - Tests a few ZIP codes across different states

echo "=========================================="
echo "Medicare API Quick Test"
echo "=========================================="
echo ""

# Test OpenAPI spec
echo "1. Testing OpenAPI Spec..."
if curl -sf "https://medicare.purlpal-api.com/medicare/openapi.yaml" > /dev/null; then
    echo "   ✅ OpenAPI spec available at /medicare/openapi.yaml"
else
    echo "   ❌ OpenAPI spec not found"
fi
echo ""

# Test states endpoint
echo "2. Testing States List..."
STATE_COUNT=$(curl -s "https://medicare.purlpal-api.com/medicare/states.json" | jq -r '.state_count')
PLAN_COUNT=$(curl -s "https://medicare.purlpal-api.com/medicare/states.json" | jq -r '.total_plans')
echo "   ✅ $STATE_COUNT states, $PLAN_COUNT total plans"
echo ""

# Test a few ZIP codes
echo "3. Testing Sample ZIP Codes..."
echo ""

test_zip() {
    local zip=$1
    local name=$2
    echo -n "   $name ($zip): "
    
    start=$(perl -MTime::HiRes -e 'printf("%.0f\n",Time::HiRes::time()*1000)')
    result=$(curl -s "https://medicare.purlpal-api.com/medicare/zip/${zip}.json")
    end=$(perl -MTime::HiRes -e 'printf("%.0f\n",Time::HiRes::time()*1000)')
    elapsed=$((end - start))
    
    if [ -n "$result" ]; then
        plan_count=$(echo "$result" | jq -r '.plan_count // 0')
        mapd=$(echo "$result" | jq -r '.plan_counts_by_category.MAPD // 0')
        ma=$(echo "$result" | jq -r '.plan_counts_by_category.MA // 0')
        pd=$(echo "$result" | jq -r '.plan_counts_by_category.PD // 0')
        
        echo "$plan_count plans (MAPD: $mapd, MA: $ma, PD: $pd) - ${elapsed}ms"
    else
        echo "❌ Failed"
    fi
}

# Test various locations
test_zip "02108" "Boston, MA"
test_zip "10001" "New York, NY"
test_zip "90210" "Beverly Hills, CA"
test_zip "60601" "Chicago, IL"
test_zip "33139" "Miami Beach, FL"
test_zip "98101" "Seattle, WA"

echo ""
echo "4. Testing Category Filtering..."
echo -n "   Boston MAPD plans only: "
mapd_count=$(curl -s "https://medicare.purlpal-api.com/medicare/zip/02108_MAPD.json" | jq -r '.plan_count')
echo "$mapd_count plans ✅"

echo -n "   Boston MA plans only: "
ma_count=$(curl -s "https://medicare.purlpal-api.com/medicare/zip/02108_MA.json" | jq -r '.plan_count')
echo "$ma_count plans ✅"

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
