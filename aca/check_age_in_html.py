#!/usr/bin/env python3
"""
Check if age is embedded in HealthSherpa HTML React data
"""

import re
import json
import html
from bs4 import BeautifulSoup

ZIP_CODE = '77447'

html_file = f'/Users/andy/DEMOS_FINAL_SPRINT/sample_sites/healthsherpa/{ZIP_CODE}/all_plans.html'

with open(html_file, 'r', encoding='utf-8') as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, 'html.parser')
elements = soup.find_all(attrs={'data-react-opts': True})

if elements:
    react_data_raw = elements[0].get('data-react-opts')
    decoded = html.unescape(react_data_raw)
    react_data = json.loads(decoded)
    
    # Check household data for age
    if 'state' in react_data and 'household' in react_data['state']:
        household = react_data['state']['household']
        print("Household data found:")
        print(json.dumps(household, indent=2))
    
    # Check for quoter/applicant data
    if 'state' in react_data and 'quoters' in react_data['state']:
        quoters = react_data['state']['quoters']
        print("\nQuoters data found:")
        print(json.dumps(quoters, indent=2)[:1000])
else:
    print("No React data found")
