#!/usr/bin/env python3
"""
Comprehensive exploration of ALL data available in HealthSherpa React props
Extract every field to understand what we can verify
"""

import re
import json
import html
from bs4 import BeautifulSoup
from collections import defaultdict

def explore_healthsherpa_structure(zip_code):
    """Extract and display ALL available fields from HealthSherpa"""
    html_file = f'/Users/andy/DEMOS_FINAL_SPRINT/sample_sites/healthsherpa/{zip_code}/all_plans.html'
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    elements = soup.find_all(attrs={'data-react-opts': True})
    
    if not elements:
        print(f"❌ No React data found for ZIP {zip_code}")
        return None
    
    react_data_raw = elements[0].get('data-react-opts')
    decoded = html.unescape(react_data_raw)
    react_data = json.loads(decoded)
    
    plans = react_data['state']['entities']['insurance_full_plans']
    
    print(f"\n{'='*120}")
    print(f"COMPLETE HEALTHSHERPA DATA STRUCTURE - ZIP {zip_code}")
    print(f"{'='*120}\n")
    
    # Analyze first plan in detail
    sample_plan = plans[0] if plans else None
    
    if not sample_plan:
        print("❌ No plans found")
        return None
    
    print(f"📋 SAMPLE PLAN (Plan 1 of {len(plans)}):")
    print(f"   ID: {sample_plan.get('hios_id', 'N/A')}")
    print(f"   Name: {sample_plan.get('name', 'N/A')[:70]}")
    print(f"\n" + "="*120)
    
    # Top-level fields
    print("\n🔹 TOP-LEVEL PLAN FIELDS:")
    print("-" * 120)
    top_fields = sorted([k for k in sample_plan.keys()])
    for field in top_fields:
        value = sample_plan.get(field)
        if not isinstance(value, (dict, list)):
            print(f"  {field:35s} = {str(value)[:70]}")
    
    # Benefits
    print(f"\n{'='*120}")
    print("🏥 BENEFITS DATA:")
    print("-" * 120)
    benefits = sample_plan.get('benefits', {})
    if isinstance(benefits, dict):
        benefit_fields = sorted(benefits.keys())
        print(f"\n  Total Benefit Fields: {len(benefit_fields)}\n")
        for field in benefit_fields:
            value = benefits.get(field)
            print(f"  {field:40s} = {str(value)[:70]}")
    
    # Cost Sharing
    print(f"\n{'='*120}")
    print("💵 COST SHARING DATA:")
    print("-" * 120)
    cost_sharing = sample_plan.get('cost_sharing', {})
    if isinstance(cost_sharing, dict):
        cs_fields = sorted(cost_sharing.keys())
        print(f"\n  Total Cost Sharing Fields: {len(cs_fields)}\n")
        for field in cs_fields:
            value = cost_sharing.get(field)
            print(f"  {field:40s} = {str(value)[:70]}")
    
    # Issuer data
    print(f"\n{'='*120}")
    print("🏢 ISSUER DATA:")
    print("-" * 120)
    issuer = sample_plan.get('issuer', {})
    if isinstance(issuer, dict):
        for field in sorted(issuer.keys()):
            value = issuer.get(field)
            print(f"  {field:40s} = {str(value)[:70]}")
    
    # Quality ratings
    print(f"\n{'='*120}")
    print("⭐ QUALITY RATINGS:")
    print("-" * 120)
    quality = sample_plan.get('quality', {})
    if isinstance(quality, dict):
        for field in sorted(quality.keys()):
            value = quality.get(field)
            print(f"  {field:40s} = {str(value)[:70]}")
    
    # Network data
    print(f"\n{'='*120}")
    print("🌐 NETWORK DATA:")
    print("-" * 120)
    network_adequacy = sample_plan.get('network_adequacy', {})
    if isinstance(network_adequacy, dict):
        for field in sorted(network_adequacy.keys()):
            value = network_adequacy.get(field)
            print(f"  {field:40s} = {str(value)[:70]}")
    
    # Premium details
    print(f"\n{'='*120}")
    print("💰 PREMIUM & FINANCIAL DATA:")
    print("-" * 120)
    financial_fields = ['premium', 'gross_premium', 'aptc', 'subsidy']
    for field in financial_fields:
        value = sample_plan.get(field)
        if value is not None:
            print(f"  {field:40s} = {value}")
    
    # Collect statistics across ALL plans
    print(f"\n{'='*120}")
    print(f"📊 FIELD AVAILABILITY ACROSS ALL {len(plans)} PLANS:")
    print("="*120)
    
    field_counts = defaultdict(int)
    benefit_counts = defaultdict(int)
    cost_sharing_counts = defaultdict(int)
    
    for plan in plans:
        # Top-level fields
        for field in plan.keys():
            if plan.get(field) is not None:
                field_counts[field] += 1
        
        # Benefits
        benefits = plan.get('benefits', {})
        if isinstance(benefits, dict):
            for field in benefits.keys():
                if benefits.get(field) is not None:
                    benefit_counts[field] += 1
        
        # Cost sharing
        cost_sharing = plan.get('cost_sharing', {})
        if isinstance(cost_sharing, dict):
            for field in cost_sharing.keys():
                if cost_sharing.get(field) is not None:
                    cost_sharing_counts[field] += 1
    
    print(f"\n🔹 TOP-LEVEL FIELDS (% of plans with data):")
    print("-" * 120)
    for field, count in sorted(field_counts.items(), key=lambda x: -x[1]):
        pct = (count / len(plans)) * 100
        print(f"  {field:40s} {count:4d}/{len(plans):4d} ({pct:6.1f}%)")
    
    print(f"\n🏥 BENEFIT FIELDS (% of plans with data):")
    print("-" * 120)
    for field, count in sorted(benefit_counts.items(), key=lambda x: -x[1]):
        pct = (count / len(plans)) * 100
        print(f"  {field:40s} {count:4d}/{len(plans):4d} ({pct:6.1f}%)")
    
    print(f"\n💵 COST SHARING FIELDS (% of plans with data):")
    print("-" * 120)
    for field, count in sorted(cost_sharing_counts.items(), key=lambda x: -x[1]):
        pct = (count / len(plans)) * 100
        print(f"  {field:40s} {count:4d}/{len(plans):4d} ({pct:6.1f}%)")
    
    return {
        'plans': plans,
        'field_counts': dict(field_counts),
        'benefit_counts': dict(benefit_counts),
        'cost_sharing_counts': dict(cost_sharing_counts),
    }

if __name__ == "__main__":
    import sys
    
    zip_codes = ['77447', '03031', '33433']
    
    if len(sys.argv) > 1:
        zip_codes = sys.argv[1:]
    
    for zip_code in zip_codes:
        result = explore_healthsherpa_structure(zip_code)
        if result:
            print(f"\n\n{'#'*120}")
            print(f"# Summary for ZIP {zip_code}")
            print(f"{'#'*120}\n")
            print(f"Total Plans: {len(result['plans'])}")
            print(f"Unique Benefit Fields: {len(result['benefit_counts'])}")
            print(f"Unique Cost Sharing Fields: {len(result['cost_sharing_counts'])}")
