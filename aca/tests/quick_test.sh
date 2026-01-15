#!/bin/bash
# Quick ACA API Test - Tests a few ZIP codes across different states

echo "=========================================="
echo "ACA API Quick Test"
echo "=========================================="
echo ""

API_BASE="${1:-https://aca.purlpal-api.com/aca}"

# Test OpenAPI spec
echo "1. Testing OpenAPI Spec..."
if curl -sf "$API_BASE/openapi.yaml" > /dev/null; then
    echo "   ✅ OpenAPI spec available at /aca/openapi.yaml"
else
    echo "   ❌ OpenAPI spec not found (may not be deployed yet)"
fi
echo ""

# Test states endpoint
echo "2. Testing States List..."
STATE_COUNT=$(curl -s "$API_BASE/states.json" | jq -r '.state_count // 0')
PLAN_COUNT=$(curl -s "$API_BASE/states.json" | jq -r '.total_plans // 0')
if [ "$STATE_COUNT" -gt 0 ]; then
    echo "   ✅ $STATE_COUNT states, $PLAN_COUNT total plans"
else
    echo "   ⚠️  States endpoint not responding (database may not be loaded)"
fi
echo ""

# Test a few ZIP codes
echo "3. Testing Sample ZIP Codes..."
echo ""

test_zip() {
    local zip=$1
    local name=$2
    echo -n "   $name ($zip): "
    
    result=$(curl -s "$API_BASE/zip/${zip}.json")
    
    if [ -n "$result" ] && echo "$result" | jq -e '.plan_count' > /dev/null 2>&1; then
        plan_count=$(echo "$result" | jq -r '.plan_count // 0')
        bronze=$(echo "$result" | jq -r '.plan_counts_by_metal_level.Bronze // 0')
        silver=$(echo "$result" | jq -r '.plan_counts_by_metal_level.Silver // 0')
        gold=$(echo "$result" | jq -r '.plan_counts_by_metal_level.Gold // 0')
        platinum=$(echo "$result" | jq -r '.plan_counts_by_metal_level.Platinum // 0')
        
        echo "$plan_count plans (Bronze:$bronze, Silver:$silver, Gold:$gold, Platinum:$platinum)"
    else
        echo "❌ Failed or no data"
    fi
}

# Test various locations
test_zip "02108" "Boston, MA"
test_zip "10001" "New York, NY"
test_zip "90210" "Beverly Hills, CA"
test_zip "60601" "Chicago, IL"
test_zip "33139" "Miami Beach, FL"
test_zip "78701" "Austin, TX"

echo ""
echo "4. Testing Metal Level Filtering..."
echo -n "   Boston Silver plans only: "
silver_count=$(curl -s "$API_BASE/zip/02108_Silver.json" | jq -r '.plan_count // 0')
if [ "$silver_count" -gt 0 ]; then
    echo "$silver_count plans ✅"
else
    echo "No data"
fi

echo -n "   Boston Gold plans only: "
gold_count=$(curl -s "$API_BASE/zip/02108_Gold.json" | jq -r '.plan_count // 0')
if [ "$gold_count" -gt 0 ]; then
    echo "$gold_count plans ✅"
else
    echo "No data"
fi

echo ""
echo "=========================================="
echo "Test Complete!"
echo ""
echo "Note: If tests failed, the API may not be deployed yet."
echo "Usage: $0 [API_BASE_URL]"
echo "Example: $0 http://localhost:3000/aca"
echo "=========================================="
