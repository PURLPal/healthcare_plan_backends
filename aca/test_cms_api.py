#!/usr/bin/env python3
"""
Test the CMS Marketplace API to validate:
1. API key works
2. Whether it includes state-based exchanges (CA, NY, MA, PA, NJ)
3. What data fields are available

Critical test: Does it return plans for Massachusetts ZIP 02108?
"""

import os
import sys
import requests
from dotenv import load_dotenv
import json

load_dotenv()

CMS_API_KEY = os.getenv('CMS_API_KEY')
CMS_API_BASE_URL = os.getenv('CMS_API_BASE_URL', 'https://marketplace.api.healthcare.gov/api/v1')

# Test ZIPs for state-based exchanges
TEST_ZIPS = {
    'MA': '02108',  # Boston, Massachusetts - THE KEY TEST!
    'CA': '90001',  # Los Angeles, California
    'NY': '10001',  # New York City, New York
    'PA': '19019',  # Philadelphia, Pennsylvania
    'NJ': '07302',  # Jersey City, New Jersey
}

# Control: Federal marketplace state
CONTROL_ZIP = {
    'FL': '33433'   # Boca Raton, Florida (should work)
}

def test_api_connection():
    """Test basic API connectivity."""
    print("=" * 80)
    print("TEST 1: API Connectivity")
    print("=" * 80)
    
    if not CMS_API_KEY:
        print("❌ ERROR: CMS_API_KEY not found in .env file")
        return False
    
    print(f"✅ API Key loaded: {CMS_API_KEY[:10]}...")
    print(f"✅ Base URL: {CMS_API_BASE_URL}")
    return True

def test_plans_endpoint(zip_code, state_name, county_fips=None):
    """Test the /plans endpoint for a given ZIP code."""
    
    url = f"{CMS_API_BASE_URL}/plans/search?apikey={CMS_API_KEY}"
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Build household payload (single 27-year-old adult)
    payload = {
        "household": {
            "income": 52000,
            "people": [
                {
                    "age": 27,
                    "aptc_eligible": True,
                    "gender": "Female",
                    "uses_tobacco": False
                }
            ]
        },
        "market": "Individual",
        "place": {
            "zipcode": zip_code,
            "state": state_name.split()[0][:2].upper()  # Extract state code
        },
        "year": 2026
    }
    
    # Add county FIPS if available
    if county_fips:
        payload["place"]["countyfips"] = county_fips
    
    print(f"\n{'=' * 80}")
    print(f"Testing ZIP {zip_code} ({state_name})")
    print(f"{'=' * 80}")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if plans exist
            if isinstance(data, dict):
                plans = data.get('plans', []) if 'plans' in data else []
                total = data.get('total', 0) if 'total' in data else len(plans)
            elif isinstance(data, list):
                plans = data
                total = len(plans)
            else:
                plans = []
                total = 0
            
            print(f"✅ SUCCESS: {total} plans found")
            
            if total > 0:
                # Show sample plan
                sample = plans[0] if plans else {}
                print(f"\nSample Plan:")
                print(f"  ID: {sample.get('id', 'N/A')}")
                print(f"  Name: {sample.get('name', 'N/A')}")
                print(f"  Issuer: {sample.get('issuer', {}).get('name', 'N/A')}")
                print(f"  Metal: {sample.get('metal_level', 'N/A')}")
                print(f"  Type: {sample.get('type', 'N/A')}")
                
                # Save full response for inspection
                filename = f"cms_api_response_{zip_code}.json"
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"\n📄 Full response saved to: {filename}")
            
            return True, total
        
        elif response.status_code == 401:
            print(f"❌ AUTHENTICATION FAILED: Invalid API key")
            return False, 0
        
        elif response.status_code == 404:
            print(f"⚠️  NO DATA: Endpoint not found or no plans available")
            return False, 0
        
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False, 0
    
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT: Request took too long")
        return False, 0
    
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")
        return False, 0
    
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False, 0

def main():
    """Run all API tests."""
    
    print("\n" + "=" * 80)
    print("CMS MARKETPLACE API TEST")
    print("=" * 80)
    print("\nObjective: Determine if CMS API includes state-based exchanges")
    print("Critical Question: Does it return plans for Massachusetts ZIP 02108?")
    
    # Test 1: Basic connectivity
    if not test_api_connection():
        sys.exit(1)
    
    # Test 2: Control test (federal marketplace state)
    print(f"\n{'=' * 80}")
    print("TEST 2: Control - Federal Marketplace State")
    print(f"{'=' * 80}")
    
    control_success, control_count = test_plans_endpoint(
        CONTROL_ZIP['FL'], 
        'Florida (Federal Marketplace)'
    )
    
    if not control_success:
        print("\n⚠️  WARNING: Control test failed. API may not be working correctly.")
    
    # Test 3: State-based exchanges (THE BIG TEST)
    print(f"\n{'=' * 80}")
    print("TEST 3: State-Based Exchanges (Critical Test)")
    print(f"{'=' * 80}")
    
    results = {}
    for state, zip_code in TEST_ZIPS.items():
        state_names = {
            'MA': 'Massachusetts',
            'CA': 'California',
            'NY': 'New York',
            'PA': 'Pennsylvania',
            'NJ': 'New Jersey'
        }
        success, count = test_plans_endpoint(zip_code, state_names[state])
        results[state] = {'success': success, 'count': count}
    
    # Summary
    print(f"\n{'=' * 80}")
    print("TEST SUMMARY")
    print(f"{'=' * 80}")
    
    print("\n📊 Control Test (Federal Marketplace):")
    print(f"  Florida (33433): {control_count} plans")
    
    print("\n📊 State-Based Exchanges:")
    for state, result in results.items():
        state_names = {
            'MA': 'Massachusetts',
            'CA': 'California',
            'NY': 'New York',
            'PA': 'Pennsylvania',
            'NJ': 'New Jersey'
        }
        status = "✅" if result['success'] and result['count'] > 0 else "❌"
        print(f"  {status} {state_names[state]} ({TEST_ZIPS[state]}): {result['count']} plans")
    
    # Final verdict
    print(f"\n{'=' * 80}")
    print("FINAL VERDICT")
    print(f"{'=' * 80}")
    
    sbm_with_data = sum(1 for r in results.values() if r['success'] and r['count'] > 0)
    
    if sbm_with_data == 5:
        print("\n🎉 SUCCESS! CMS API includes ALL state-based exchanges!")
        print("   → We can now get 100% coverage for all 50 states + DC")
        print("   → No need for state-by-state scraping")
        print("   → Massachusetts ZIP 02108 issue is SOLVED!")
        return 0
    
    elif sbm_with_data > 0:
        print(f"\n⚠️  PARTIAL SUCCESS: CMS API includes {sbm_with_data}/5 state-based exchanges")
        print("   → Some states available, but not complete coverage")
        print("   → May need hybrid approach")
        return 1
    
    else:
        print("\n❌ FAILURE: CMS API does NOT include state-based exchanges")
        print("   → API only covers 30 federal marketplace states")
        print("   → Need alternative approach for state exchanges")
        print("   → Fall back to state-by-state data acquisition")
        return 2

if __name__ == '__main__':
    sys.exit(main())
