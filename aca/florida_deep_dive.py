#!/usr/bin/env python3
"""
Deep investigation of Florida premium data
- Check premium values for different ages and tobacco status
- Identify what modifiers affect costs
- Match HealthSherpa values to database rows
"""

import re
import json
import html
import psycopg2
from bs4 import BeautifulSoup
from collections import defaultdict

def extract_florida_healthsherpa():
    """Extract Florida data from HealthSherpa"""
    html_file = '/Users/andy/DEMOS_FINAL_SPRINT/sample_sites/healthsherpa/33433/all_plans.html'
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    elements = soup.find_all(attrs={'data-react-opts': True})
    
    react_data_raw = elements[0].get('data-react-opts')
    decoded = html.unescape(react_data_raw)
    react_data = json.loads(decoded)
    
    household = react_data['state']['household']
    age = household['applicants'][0]['age']
    tobacco = household['applicants'][0]['smoker']
    
    plans = react_data['state']['entities']['insurance_full_plans']
    
    hs_plans = {}
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        
        hios_id = plan.get('hios_id', '')
        base_id = hios_id[:14]
        
        if not base_id:
            continue
        
        hs_plans[base_id] = {
            'hios_id': hios_id,
            'name': plan.get('name', ''),
            'issuer': plan.get('issuer', {}).get('name', ''),
            'premium': plan.get('gross_premium'),
        }
    
    return age, tobacco, hs_plans

def analyze_florida_rates():
    """Deep analysis of Florida rates"""
    
    print(f"\n{'='*120}")
    print(f"FLORIDA PREMIUM DEEP DIVE - ZIP 33433")
    print(f"{'='*120}\n")
    
    # Get HealthSherpa data
    hs_age, hs_tobacco, hs_plans = extract_florida_healthsherpa()
    
    print(f"📥 HealthSherpa Sample Data:")
    print(f"   Age: {hs_age}")
    print(f"   Tobacco: {hs_tobacco}")
    print(f"   Plans: {len(hs_plans)}")
    
    # Database connection
    with open('/Users/andy/aca_overview_test/.db_password', 'r') as f:
        password = f.read().strip()
    
    conn = psycopg2.connect(
        f"host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com "
        f"dbname=aca_plans user=aca_admin password={password}"
    )
    cur = conn.cursor()
    
    # Get sample plan - check all ages and tobacco variations
    sample_id = list(hs_plans.keys())[0]
    sample_plan = hs_plans[sample_id]
    
    print(f"\n{'='*120}")
    print(f"SAMPLE PLAN INVESTIGATION")
    print(f"{'='*120}")
    print(f"Plan: {sample_id}")
    print(f"Name: {sample_plan['name'][:80]}")
    print(f"HealthSherpa Premium (Age {hs_age}, {'Tobacco' if hs_tobacco else 'Non-Tobacco'}): ${sample_plan['premium']:.2f}")
    
    # Check ALL rate variations for this plan
    cur.execute("""
        SELECT 
            plan_id,
            age,
            individual_rate,
            individual_tobacco_rate
        FROM rates
        WHERE plan_id LIKE %s
        ORDER BY age
    """, (sample_id + '%',))
    
    all_rates = cur.fetchall()
    
    print(f"\n📊 Database Has {len(all_rates)} Age Variations")
    print(f"\n{'='*120}")
    print(f"RATE TABLE - ALL AGES FOR THIS PLAN")
    print(f"{'='*120}")
    print(f"{'Age':>5s} | {'Non-Tobacco':>15s} | {'Tobacco':>15s} | {'Tobacco Mult':>15s}")
    print("-" * 60)
    
    matching_rows = []
    
    for row in all_rates[:20]:  # Show first 20
        plan_id = row[0]
        age = row[1]
        non_tobacco = row[2]
        tobacco = row[3]
        mult = tobacco / non_tobacco if non_tobacco else 0
        
        # Check if this matches HealthSherpa
        match = ""
        if age == hs_age:
            if hs_tobacco and abs(tobacco - sample_plan['premium']) < 0.50:
                match = " ✅ MATCHES HS"
                matching_rows.append(('tobacco', age, tobacco, sample_plan['premium']))
            elif not hs_tobacco and abs(non_tobacco - sample_plan['premium']) < 0.50:
                match = " ✅ MATCHES HS"
                matching_rows.append(('non_tobacco', age, non_tobacco, sample_plan['premium']))
        
        print(f"{age:>5d} | ${non_tobacco:>14.2f} | ${tobacco:>14.2f} | {mult:>14.2f}x{match}")
    
    if len(all_rates) > 20:
        print(f"... ({len(all_rates) - 20} more ages)")
    
    # Check if HealthSherpa value matches ANY row
    print(f"\n{'='*120}")
    print(f"SEARCHING FOR HEALTHSHERPA VALUE MATCH")
    print(f"{'='*120}")
    print(f"Looking for: ${sample_plan['premium']:.2f}")
    
    cur.execute("""
        SELECT 
            plan_id,
            age,
            individual_rate,
            individual_tobacco_rate
        FROM rates
        WHERE plan_id LIKE %s
          AND (
            ABS(individual_rate - %s) < 0.50 
            OR ABS(individual_tobacco_rate - %s) < 0.50
          )
    """, (sample_id + '%', sample_plan['premium'], sample_plan['premium']))
    
    matches = cur.fetchall()
    
    if matches:
        print(f"\n✅ Found {len(matches)} matching value(s):")
        for match in matches:
            if abs(match[2] - sample_plan['premium']) < 0.50:
                print(f"   Age {match[1]}: Non-Tobacco Rate = ${match[2]:.2f}")
            if abs(match[3] - sample_plan['premium']) < 0.50:
                print(f"   Age {match[1]}: Tobacco Rate = ${match[3]:.2f}")
    else:
        print(f"\n❌ NO EXACT MATCH FOUND in database")
        print(f"   Checking closest values...")
        
        cur.execute("""
            SELECT 
                plan_id,
                age,
                individual_rate,
                individual_tobacco_rate,
                ABS(individual_rate - %s) as non_tobacco_diff,
                ABS(individual_tobacco_rate - %s) as tobacco_diff
            FROM rates
            WHERE plan_id LIKE %s
            ORDER BY LEAST(
                ABS(individual_rate - %s),
                ABS(individual_tobacco_rate - %s)
            )
            LIMIT 5
        """, (sample_plan['premium'], sample_plan['premium'], sample_id + '%', 
              sample_plan['premium'], sample_plan['premium']))
        
        closest = cur.fetchall()
        print(f"\n   Closest matches:")
        for row in closest:
            print(f"   Age {row[1]}:")
            print(f"      Non-Tobacco: ${row[2]:>10.2f} (diff: ${row[4]:>8.2f})")
            print(f"      Tobacco:     ${row[3]:>10.2f} (diff: ${row[5]:>8.2f})")
    
    # Test all Florida plans
    print(f"\n{'='*120}")
    print(f"TESTING ALL FLORIDA PLANS (First 10)")
    print(f"{'='*120}\n")
    
    test_count = 0
    match_count = 0
    
    for base_id in list(hs_plans.keys())[:10]:
        hs_plan = hs_plans[base_id]
        hs_prem = hs_plan['premium']
        
        # Check database
        cur.execute("""
            SELECT age, individual_rate, individual_tobacco_rate
            FROM rates
            WHERE plan_id LIKE %s
              AND age = %s
        """, (base_id + '%', hs_age))
        
        db_row = cur.fetchone()
        
        if db_row:
            db_non_tobacco = float(db_row[1]) if db_row[1] else None
            db_tobacco = float(db_row[2]) if db_row[2] else None
            
            expected = db_tobacco if hs_tobacco else db_non_tobacco
            diff = abs(hs_prem - expected) if expected else None
            matches = diff < 0.50 if diff else False
            
            if matches:
                match_count += 1
                status = "✅"
            else:
                status = "❌"
            
            print(f"{status} Plan {base_id[:14]}")
            print(f"   HealthSherpa: ${hs_prem:>10.2f}")
            if expected:
                print(f"   DB Expected:  ${expected:>10.2f} (Age {hs_age}, {'Tobacco' if hs_tobacco else 'Non-Tobacco'})")
                if diff:
                    print(f"   Difference:   ${diff:>10.2f}")
            else:
                print(f"   DB Expected:  N/A (missing rate)")
            print()
        else:
            print(f"❓ Plan {base_id[:14]}: Not found in database")
            print()
        
        test_count += 1
    
    print(f"{'='*120}")
    print(f"Match Rate: {match_count}/{test_count} ({match_count/test_count*100:.1f}%)")
    print(f"{'='*120}\n")
    
    # Analyze rating factors
    print(f"{'='*120}")
    print(f"RATING FACTORS ANALYSIS")
    print(f"{'='*120}\n")
    
    print("Factors that affect ACA premiums:")
    print("1. ✅ Age - Database has rate for every age (14-120)")
    print("2. ✅ Tobacco Use - Database has tobacco_rate column (typically 1.5x non-tobacco)")
    print("3. ✅ Geographic Area (Rating Area) - Different rates by ZIP/county")
    print("4. ❌ Household Size - Database does NOT have family rates")
    print("5. ❌ Income/Subsidies - HealthSherpa shows subsidized, DB has gross premium only")
    
    # Check if Florida plans have different rates by rating area
    print(f"\n{'='*120}")
    print(f"RATING AREA INVESTIGATION - Same Plan, Different ZIPs")
    print(f"{'='*120}\n")
    
    # Get sample plan and check if it has different rates in different FL counties
    cur.execute("""
        SELECT DISTINCT
            zc.zip_code,
            c.county_name,
            r.individual_rate
        FROM rates r
        JOIN plans p ON r.plan_id = p.plan_id
        JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
        JOIN zip_counties zc ON psa.county_fips = zc.county_fips
        JOIN counties c ON zc.county_fips = c.county_fips
        WHERE p.plan_id LIKE %s
          AND r.age = 40
          AND p.state_code = 'FL'
        ORDER BY r.individual_rate, zc.zip_code
        LIMIT 20
    """, (sample_id + '%',))
    
    rating_areas = cur.fetchall()
    
    if rating_areas:
        print(f"Sample Plan in Different Florida Locations (Age 40):")
        print(f"{'ZIP':>10s} | {'County':30s} | {'Premium':>12s}")
        print("-" * 60)
        
        unique_rates = set()
        for row in rating_areas:
            print(f"{row[0]:>10s} | {row[1]:30s} | ${row[2]:>11.2f}")
            unique_rates.add(row[2])
        
        if len(unique_rates) > 1:
            print(f"\n⚠️  DIFFERENT RATES by location: {len(unique_rates)} unique rates")
            print(f"   This plan has different premiums depending on ZIP/county (rating areas)")
        else:
            print(f"\n✅ SAME RATE across all locations")
    
    # Check tobacco multiplier consistency
    print(f"\n{'='*120}")
    print(f"TOBACCO MULTIPLIER ANALYSIS")
    print(f"{'='*120}\n")
    
    cur.execute("""
        SELECT 
            plan_id,
            age,
            individual_rate,
            individual_tobacco_rate,
            individual_tobacco_rate / NULLIF(individual_rate, 0) as multiplier
        FROM rates
        WHERE plan_id LIKE %s
          AND individual_rate > 0
        ORDER BY age
        LIMIT 10
    """, (sample_id + '%',))
    
    tobacco_data = cur.fetchall()
    multipliers = [row[4] for row in tobacco_data if row[4]]
    
    if multipliers:
        avg_mult = sum(multipliers) / len(multipliers)
        print(f"Average Tobacco Multiplier: {avg_mult:.4f}x")
        print(f"Range: {min(multipliers):.4f}x to {max(multipliers):.4f}x")
        print(f"\n💡 Tobacco users typically pay 1.5x the non-tobacco rate (ACA maximum)")
    
    conn.close()

if __name__ == "__main__":
    analyze_florida_rates()
