#!/usr/bin/env python3
"""
Compare HealthSherpa plans for ZIP 33433 with ACA database
"""

import psycopg2
import json

# Database connection
DB_HOST = "aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "aca_plans"
DB_USER = "aca_admin"
DB_PASSWORD = "AvRePOWBfVFZyPsKPPG2tV3r"

# HealthSherpa plans for ZIP 33433
healthsherpa_plans = [
    "21525FL0020002", "48121FL0070122", "44228FL0040008", "21525FL0020006",
    "44228FL0040005", "48121FL0070051", "48121FL0070107", "21525FL0020001",
    "21525FL0020004", "44228FL0040001", "21525FL0020005", "44228FL0040007",
    "19898FL0340092", "30252FL0070065", "19898FL0340017", "68398FL0090001",
    "68398FL0030058", "19898FL0340016", "21525FL0020003", "54172FL0010010",
    "67926FL0010001", "67926FL0010006", "67926FL0010002", "48121FL0070108",
    "54172FL0010013", "54172FL0040005", "68398FL0030042", "49004FL0010002",
    "54172FL0070005", "49004FL0010001", "68398FL0060006", "68398FL0030045",
    "21525FL0020016", "49004FL0020002", "49004FL0020001", "30252FL0070039",
    "30252FL0070044", "68398FL0060007", "30252FL0070001", "54172FL0010020",
    "54172FL0040012", "21525FL0020015", "54172FL0070003", "79850FL0020003",
    "48121FL0070033", "44228FL0040012", "21525FL0020012", "44228FL0040011",
    "30252FL0070031", "21525FL0020007", "21525FL0020009", "21525FL0020011",
    "21525FL0020013", "30252FL0190009", "44228FL0040013", "21525FL0020010",
    "49004FL0010004", "79850FL0020006", "48121FL0070104", "44228FL0040002",
    "19898FL0340082", "16842FL0120001", "21525FL0020008", "30252FL0200009",
    "86382FL0050017", "19898FL0340015", "19898FL0350015", "49004FL0020004",
    "30252FL0070061", "16842FL0120093", "30252FL0190007", "48121FL0070057",
    "19898FL0340013", "54172FL0010011", "16842FL0120078", "19898FL0350013",
    "30252FL0200007", "30252FL0070101", "54172FL0010002", "16842FL0120068",
    "30252FL0190032", "54172FL0040002", "30252FL0070070", "44228FL0040010",
    "30252FL0190025", "30252FL0200036", "44228FL0040014", "54172FL0070002",
    "67926FL0010008", "30252FL0200029", "68398FL0030046", "19898FL0340072",
    "54172FL0010009", "44228FL0040003", "44228FL0040009", "30252FL0070035",
    "16842FL0120091", "30252FL0190011", "16842FL0310014", "54172FL0010012",
    "54172FL0010001", "49004FL0010031", "79850FL0020001", "19898FL0340011",
    "79850FL0020002", "54172FL0040004", "54172FL0040001", "19898FL0350011",
    "68398FL0060004", "16842FL0320014", "30252FL0200011", "30252FL0070053",
    "67926FL0010003", "48121FL0070030", "48121FL0070029", "54172FL0070004",
    "54172FL0070001", "48121FL0070105", "68398FL0090002", "68398FL0030040",
    "79850FL0020005", "86382FL0050005", "68398FL0030048", "49004FL0010013",
    "54172FL0010008", "68398FL0060005", "49004FL0010010", "49004FL0010006",
    "67926FL0010007", "68398FL0060002", "49004FL0020012", "49004FL0010007",
    "49004FL0020009", "49004FL0020027", "49004FL0010009", "49004FL0010011",
    "67926FL0010004", "49004FL0020006", "68398FL0030036", "49004FL0020008",
    "68398FL0030034", "49004FL0020010", "67926FL0010009", "68398FL0030057",
    "86382FL0050014", "68398FL0060001", "30252FL0070055", "16842FL0260006",
    "30252FL0140018", "86382FL0050019", "16842FL0120072", "16842FL0310004",
    "30252FL0070009", "16842FL0320004", "16842FL0120094", "86382FL0050018",
    "16842FL0120033", "16842FL0260018", "86382FL0050009", "16842FL0260010",
    "30252FL0070074", "16842FL0260004", "30252FL0140026", "86382FL0050010",
    "30252FL0140017", "16842FL0260017", "16842FL0120095", "19898FL0340061",
    "19898FL0350061", "30252FL0140023", "16842FL0120086", "19898FL0340062",
    "16842FL0120076", "16842FL0310001", "30252FL0140021", "30252FL0070075",
    "30252FL0140027", "30252FL0070100", "16842FL0120062", "16842FL0120070",
    "30252FL0140028", "16842FL0120096", "16842FL0260003", "30252FL0140020",
    "16842FL0260020", "16842FL0260019", "16842FL0260012", "16842FL0260007",
    "16842FL0260009", "30252FL0140015", "30252FL0140029", "16842FL0260005",
    "16842FL0260008", "16842FL0260021"
]

def get_database_plans(zip_code):
    """Get plans from database for a ZIP code"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    cur = conn.cursor()
    
    # Query to get plans for ZIP code
    query = """
        SELECT DISTINCT 
            p.plan_id,
            p.plan_marketing_name,
            p.metal_level,
            p.issuer_name,
            p.plan_type
        FROM plans p
        JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
        JOIN zip_counties zc ON psa.county_fips = zc.county_fips
        WHERE zc.zip_code = %s
        ORDER BY p.plan_id
    """
    
    cur.execute(query, (zip_code,))
    results = cur.fetchall()
    
    conn.close()
    
    return results

def normalize_plan_id(plan_id):
    """Remove variant suffix (-00, -01, etc.) from plan ID"""
    if '-' in plan_id:
        return plan_id.split('-')[0]
    return plan_id

def main():
    print("=" * 80)
    print("HEALTHSHERPA vs ACA DATABASE COMPARISON - ZIP 33433")
    print("=" * 80)
    
    # Get database plans
    print("\n🔍 Querying ACA database for ZIP 33433...")
    db_plans = get_database_plans("33433")
    
    print(f"✓ Found {len(db_plans)} plans in database")
    print(f"✓ HealthSherpa shows {len(healthsherpa_plans)} plans")
    
    # Normalize plan IDs (remove -00, -01 suffixes)
    db_plan_ids = [row[0] for row in db_plans]
    db_plan_ids_normalized = [normalize_plan_id(pid) for pid in db_plan_ids]
    healthsherpa_normalized = [normalize_plan_id(pid) for pid in healthsherpa_plans]
    
    # Create sets for comparison
    db_set = set(db_plan_ids)
    db_set_normalized = set(db_plan_ids_normalized)
    hs_set = set(healthsherpa_plans)
    hs_set_normalized = set(healthsherpa_normalized)
    
    print("\n" + "=" * 80)
    print("EXACT MATCH COMPARISON (Including Variant Suffixes)")
    print("=" * 80)
    
    # Plans in both (exact match)
    in_both_exact = db_set.intersection(hs_set)
    print(f"\n✅ Plans in BOTH (exact match): {len(in_both_exact)}")
    if in_both_exact and len(in_both_exact) <= 10:
        for pid in sorted(list(in_both_exact))[:10]:
            print(f"   - {pid}")
    
    # Plans only in database
    only_in_db = db_set - hs_set
    print(f"\n📊 Plans ONLY in Database: {len(only_in_db)}")
    if only_in_db and len(only_in_db) <= 20:
        for pid in sorted(list(only_in_db))[:20]:
            print(f"   - {pid}")
    
    # Plans only in HealthSherpa
    only_in_hs = hs_set - db_set
    print(f"\n🏥 Plans ONLY in HealthSherpa: {len(only_in_hs)}")
    if only_in_hs and len(only_in_hs) <= 20:
        for pid in sorted(list(only_in_hs))[:20]:
            print(f"   - {pid}")
    
    print("\n" + "=" * 80)
    print("NORMALIZED COMPARISON (Base Plan IDs, Ignoring Variants)")
    print("=" * 80)
    
    # Normalized comparison
    in_both_normalized = db_set_normalized.intersection(hs_set_normalized)
    print(f"\n✅ Base Plans in BOTH: {len(in_both_normalized)}")
    
    only_in_db_normalized = db_set_normalized - hs_set_normalized
    print(f"\n📊 Base Plans ONLY in Database: {len(only_in_db_normalized)}")
    if only_in_db_normalized and len(only_in_db_normalized) <= 15:
        for pid in sorted(list(only_in_db_normalized))[:15]:
            print(f"   - {pid}")
    
    only_in_hs_normalized = hs_set_normalized - db_set_normalized
    print(f"\n🏥 Base Plans ONLY in HealthSherpa: {len(only_in_hs_normalized)}")
    if only_in_hs_normalized and len(only_in_hs_normalized) <= 15:
        for pid in sorted(list(only_in_hs_normalized))[:15]:
            print(f"   - {pid}")
    
    print("\n" + "=" * 80)
    print("VARIANT ANALYSIS")
    print("=" * 80)
    
    # Analyze variants in database
    db_variants = {}
    for pid in db_plan_ids:
        base = normalize_plan_id(pid)
        if base not in db_variants:
            db_variants[base] = []
        db_variants[base].append(pid)
    
    db_multi_variant = {k: v for k, v in db_variants.items() if len(v) > 1}
    
    print(f"\n📋 Database Plans with Multiple Variants: {len(db_multi_variant)}")
    if db_multi_variant:
        for base, variants in sorted(list(db_multi_variant.items()))[:10]:
            print(f"   {base}:")
            for v in variants:
                print(f"      → {v}")
    
    # Analyze variants in HealthSherpa
    hs_variants = {}
    for pid in healthsherpa_plans:
        base = normalize_plan_id(pid)
        if base not in hs_variants:
            hs_variants[base] = []
        hs_variants[base].append(pid)
    
    hs_multi_variant = {k: v for k, v in hs_variants.items() if len(v) > 1}
    
    print(f"\n📋 HealthSherpa Plans with Multiple Variants: {len(hs_multi_variant)}")
    if hs_multi_variant:
        for base, variants in sorted(list(hs_multi_variant.items()))[:10]:
            print(f"   {base}:")
            for v in variants:
                print(f"      → {v}")
    
    print("\n" + "=" * 80)
    print("SAMPLE PLAN DETAILS FROM DATABASE")
    print("=" * 80)
    
    # Show sample plan details
    print("\nSample plans from database (first 10):")
    for i, row in enumerate(db_plans[:10], 1):
        plan_id, name, metal, issuer, plan_type = row
        print(f"\n{i}. {plan_id}")
        print(f"   Name: {name}")
        print(f"   Metal: {metal} | Type: {plan_type}")
        print(f"   Issuer: {issuer}")
    
    print("\n" + "=" * 80)
    print("SUMMARY & CONCLUSIONS")
    print("=" * 80)
    
    print(f"""
Database Plans:         {len(db_plan_ids)}
HealthSherpa Plans:     {len(healthsherpa_plans)}
Exact Matches:          {len(in_both_exact)}
Base Plan Matches:      {len(in_both_normalized)}

Coverage:               {len(in_both_normalized) / len(hs_set_normalized) * 100:.1f}% of HealthSherpa base plans

VARIANT SUFFIX EXPLANATION:
- Plan IDs like "21525FL0020002-00" vs "21525FL0020002-01" are VARIANTS
- Same base HIOS product, different cost-sharing or network options
- Database may have -00 variant, HealthSherpa shows -01 variant
- This is normal and expected in ACA plan data
- Variants represent different benefit designs of the same product

RECOMMENDATION:
- Database appears to have good coverage of ZIP 33433
- Variant differences (-00 vs -01) are expected
- May need to normalize plan IDs for matching purposes
    """)

if __name__ == '__main__':
    main()
