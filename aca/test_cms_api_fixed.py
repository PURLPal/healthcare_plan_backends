#!/usr/bin/env python3
"""
Fixed CMS API test - Get county FIPS first, then search plans.
"""

import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

CMS_API_KEY = os.getenv('CMS_API_KEY')
CMS_API_BASE_URL = os.getenv('CMS_API_BASE_URL', 'https://marketplace.api.healthcare.gov/api/v1')

def get_county_fips(zip_code):
    """Get county FIPS code for a ZIP code."""
    url = f"{CMS_API_BASE_URL}/counties/by/zip/{zip_code}?apikey={CMS_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and 'counties' in data and len(data['counties']) > 0:
                county = data['counties'][0]
                return county.get('fips'), county.get('state')
        return None, None
    except:
        return None, None

def test_plans(zip_code, state_code, county_fips):
    """Test plan search with proper county FIPS."""
    
    url = f"{CMS_API_BASE_URL}/plans/search?apikey={CMS_API_KEY}"
    
    payload = {
        "household": {
            "income": 52000,
            "people": [{"age": 27, "aptc_eligible": True, "gender": "Female", "uses_tobacco": False}]
        },
        "market": "Individual",
        "place": {
            "countyfips": county_fips,
            "state": state_code,
            "zipcode": zip_code
        },
        "year": 2026
    }
    
    headers = {'Content-Type': 'application/json'}
    
    print(f"\nTesting {state_code} ZIP {zip_code} (FIPS: {county_fips})")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            plans = data.get('plans', [])
            print(f"✅ SUCCESS: {len(plans)} plans found")
            if plans:
                sample = plans[0]
                print(f"   Sample: {sample.get('id')} - {sample.get('name')}")
            return True, len(plans)
        else:
            print(f"❌ ERROR {response.status_code}: {response.text[:200]}")
            return False, 0
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False, 0

def main():
    print("=" * 80)
    print("CMS MARKETPLACE API - DEFINITIVE TEST")
    print("=" * 80)
    
    # Test state-based exchanges
    print("\n### STATE-BASED EXCHANGES (Expected to FAIL) ###")
    
    for state, zip_code in [('MA', '02108'), ('CA', '90001')]:
        fips, api_state = get_county_fips(zip_code)
        if fips:
            print(f"\n{state} {zip_code}: Got FIPS {fips}")
            test_plans(zip_code, api_state, fips)
        else:
            print(f"\n{state} {zip_code}: ❌ No county data (state not in API)")
    
    # Test federal marketplace states
    print("\n\n### FEDERAL MARKETPLACE STATES (Expected to WORK) ###")
    
    for state, zip_code in [('FL', '33433'), ('TX', '75001'), ('NC', '27360')]:
        fips, api_state = get_county_fips(zip_code)
        if fips:
            print(f"\n{state} {zip_code}: Got FIPS {fips}, State: {api_state}")
            test_plans(zip_code, api_state, fips)
        else:
            print(f"\n{state} {zip_code}: ❌ Could not get county FIPS")
    
    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    print("If federal states work but MA/CA don't, then:")
    print("→ CMS API works correctly")
    print("→ CMS API does NOT include state-based exchanges")
    print("→ Need alternative data source for CA, NY, MA, PA, NJ")
    print("=" * 80)

if __name__ == '__main__':
    main()
