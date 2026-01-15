#!/usr/bin/env python3
"""
Comprehensive ACA API Test Script
Tests multiple random ZIP codes per state via the ACA API
"""

import json
import random
import time
import sys
from pathlib import Path
import urllib.request
import urllib.error
from collections import defaultdict
import ssl

API_BASE_URL = "https://aca.purlpal-api.com/aca"

# Test configuration
ZIPS_PER_STATE = int(sys.argv[1]) if len(sys.argv) > 1 else 5  # Default 5 ZIPs per state
REQUESTS_PER_SECOND = 2
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds

def load_zip_data():
    """Load ZIP code data to sample from"""
    zip_file = Path("data/reference/unified_zip_to_fips.json")
    if not zip_file.exists():
        print("❌ unified_zip_to_fips.json not found")
        return {}
    
    with open(zip_file) as f:
        return json.load(f)

def get_zips_by_state(zip_data):
    """Organize ZIP codes by state"""
    zips_by_state = defaultdict(list)
    
    for zip_code, info in zip_data.items():
        states = info.get('states', [])
        primary_state = info.get('primary_state')
        
        if primary_state:
            zips_by_state[primary_state].append(zip_code)
        elif states:
            zips_by_state[states[0]].append(zip_code)
    
    return zips_by_state

def test_api_endpoint(url, timeout=30, retry_count=0):
    """Test a single API endpoint with retry logic"""
    start_time = time.time()
    
    try:
        # Create SSL context that's more tolerant
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'ACA-API-Test/1.0')
        
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            elapsed = time.time() - start_time
            data = json.loads(response.read().decode('utf-8'))
            
            return {
                'success': True,
                'status_code': response.status,
                'elapsed_ms': round(elapsed * 1000, 2),
                'data': data,
                'retries': retry_count
            }
    
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_time
        try:
            error_data = json.loads(e.read().decode('utf-8'))
        except:
            error_data = {'error': str(e)}
        
        return {
            'success': False,
            'status_code': e.code,
            'elapsed_ms': round(elapsed * 1000, 2),
            'error': error_data,
            'retries': retry_count
        }
    
    except (urllib.error.URLError, ssl.SSLError, TimeoutError, ConnectionError) as e:
        # Retry on network/SSL errors
        if retry_count < RETRY_ATTEMPTS:
            time.sleep(RETRY_DELAY)
            return test_api_endpoint(url, timeout, retry_count + 1)
        
        elapsed = time.time() - start_time
        return {
            'success': False,
            'status_code': 0,
            'elapsed_ms': round(elapsed * 1000, 2),
            'error': str(e),
            'retries': retry_count
        }

def test_zip_code(zip_code):
    """Test a single ZIP code with all plan types"""
    results = {
        'zip_code': zip_code,
        'tests': {}
    }
    
    # Rate limiting
    time.sleep(1.0 / REQUESTS_PER_SECOND)
    
    # Test 1: Get available plan categories
    categories_url = f"{API_BASE_URL}/zip/{zip_code}.json"
    categories_result = test_api_endpoint(categories_url)
    
    results['tests']['all_plans'] = categories_result
    
    if not categories_result['success']:
        return results
    
    data = categories_result['data']
    plan_count = data.get('plan_count', 0)
    categories = data.get('plan_counts_by_metal_level', {})
    
    print(f"  ZIP {zip_code}: {plan_count} total plans", end=" ")
    
    # Test 2: Silver plans if available
    if categories.get('Silver', 0) > 0:
        silver_url = f"{API_BASE_URL}/zip/{zip_code}_Silver.json"
        silver_result = test_api_endpoint(silver_url)
        results['tests']['silver'] = silver_result
        if silver_result['success']:
            print(f"Silver: {silver_result['data'].get('plan_count', 0)}", end=" ")
    
    # Test 3: Gold plans if available
    if categories.get('Gold', 0) > 0:
        gold_url = f"{API_BASE_URL}/zip/{zip_code}_Gold.json"
        gold_result = test_api_endpoint(gold_url)
        results['tests']['gold'] = gold_result
        if gold_result['success']:
            print(f"Gold: {gold_result['data'].get('plan_count', 0)}", end=" ")
    
    # Test 4: Bronze plans if available
    if categories.get('Bronze', 0) > 0 or categories.get('Expanded Bronze', 0) > 0:
        bronze_url = f"{API_BASE_URL}/zip/{zip_code}_Bronze.json"
        bronze_result = test_api_endpoint(bronze_url)
        results['tests']['bronze'] = bronze_result
        if bronze_result['success']:
            print(f"Bronze: {bronze_result['data'].get('plan_count', 0)}", end=" ")
    
    # Test 5: Platinum plans if available
    if categories.get('Platinum', 0) > 0:
        platinum_url = f"{API_BASE_URL}/zip/{zip_code}_Platinum.json"
        platinum_result = test_api_endpoint(platinum_url)
        results['tests']['platinum'] = platinum_result
        if platinum_result['success']:
            print(f"Platinum: {platinum_result['data'].get('plan_count', 0)}", end=" ")
    
    print()
    
    return results

def main():
    print("=" * 80)
    print("ACA API Comprehensive Test")
    print("=" * 80)
    print(f"Testing {ZIPS_PER_STATE} ZIP codes per state")
    print(f"Rate limit: {REQUESTS_PER_SECOND} requests/second")
    print(f"Retry attempts: {RETRY_ATTEMPTS}")
    print()
    
    # Load ZIP data
    print("Loading ZIP code data...")
    zip_data = load_zip_data()
    if not zip_data:
        print("❌ Failed to load ZIP data")
        return
    
    print(f"✓ Loaded {len(zip_data):,} ZIP codes")
    
    # Organize by state
    zips_by_state = get_zips_by_state(zip_data)
    print(f"✓ Found {len(zips_by_state)} states/territories")
    print()
    
    # Test states endpoint first
    print("Testing /states.json endpoint...")
    states_result = test_api_endpoint(f"{API_BASE_URL}/states.json")
    if states_result['success']:
        api_states = states_result['data']
        print(f"✓ API reports {api_states['state_count']} states, {api_states['total_plans']:,} total plans")
        print(f"  Response time: {states_result['elapsed_ms']}ms")
        
        # Get list of states with plans
        states_with_plans = set(s['abbrev'] for s in api_states['states'])
    else:
        print(f"❌ States endpoint failed: {states_result.get('error')}")
        states_with_plans = set()
    
    print()
    
    # Test each state
    all_results = {}
    total_tests = 0
    successful_tests = 0
    total_response_time = 0
    states_tested = 0
    
    # Sort states for consistent output
    sorted_states = sorted(states_with_plans) if states_with_plans else sorted(zips_by_state.keys())
    
    for state in sorted_states:
        if state not in zips_by_state:
            continue
        
        # Skip states not in API
        if states_with_plans and state not in states_with_plans:
            continue
        
        states_tested += 1
        print(f"{state}:")
        
        # Sample random ZIPs from this state
        state_zips = zips_by_state[state]
        sample_size = min(ZIPS_PER_STATE, len(state_zips))
        sampled_zips = random.sample(state_zips, sample_size)
        
        state_results = []
        for zip_code in sampled_zips:
            result = test_zip_code(zip_code)
            state_results.append(result)
            
            # Track stats
            total_tests += 1
            if result['tests']['all_plans']['success']:
                successful_tests += 1
                total_response_time += result['tests']['all_plans']['elapsed_ms']
        
        all_results[state] = state_results
        print()
    
    # Summary
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"States tested: {states_tested}")
    print(f"Total ZIP codes tested: {total_tests}")
    print(f"Successful tests: {successful_tests}/{total_tests} ({100*successful_tests/total_tests:.1f}%)")
    
    if successful_tests > 0:
        avg_response_time = total_response_time / successful_tests
        print(f"Average response time: {avg_response_time:.0f}ms")
    
    # Find states with no plans
    states_with_no_plans = []
    for state, results in all_results.items():
        all_zero = all(
            r['tests']['all_plans'].get('data', {}).get('plan_count', 0) == 0
            for r in results
            if r['tests']['all_plans']['success']
        )
        if all_zero:
            states_with_no_plans.append(state)
    
    if states_with_no_plans:
        print(f"\n⚠️  States with no plans found: {', '.join(states_with_no_plans)}")
        print("   (These may be state-based exchanges not in federal data)")
    
    # Count metal level test results
    metal_tests = defaultdict(int)
    for state_results in all_results.values():
        for result in state_results:
            for test_name in ['silver', 'gold', 'bronze', 'platinum']:
                if test_name in result['tests'] and result['tests'][test_name]['success']:
                    metal_tests[test_name] += 1
    
    if metal_tests:
        print(f"\nMetal level filter tests:")
        for metal, count in sorted(metal_tests.items()):
            print(f"  {metal.capitalize()}: {count} successful tests")
    
    print("\n✓ Test complete!")

if __name__ == '__main__':
    main()
