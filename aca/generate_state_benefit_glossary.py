#!/usr/bin/env python3
"""
Generate state-specific benefit glossary with cost-sharing values for that state only
This enables accurate query filtering by showing only values available in that state
"""

import psycopg2
import json
from collections import Counter
import sys

def generate_state_glossary(state_code):
    """Generate benefit glossary for specific state"""
    
    with open('/Users/andy/aca_overview_test/.db_password', 'r') as f:
        password = f.read().strip()
    
    conn = psycopg2.connect(
        f"host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com "
        f"dbname=aca_plans user=aca_admin password={password}"
    )
    cur = conn.cursor()
    
    print(f"\n{'='*120}")
    print(f"GENERATING {state_code} STATE-SPECIFIC BENEFIT GLOSSARY")
    print(f"{'='*120}\n")
    
    # Get all distinct benefit names for this state
    cur.execute("""
        SELECT DISTINCT b.benefit_name
        FROM benefits b
        JOIN plans p ON b.plan_id = p.plan_id
        WHERE p.state_code = %s
        ORDER BY b.benefit_name ASC
    """, (state_code,))
    
    state_benefits = [row[0] for row in cur.fetchall()]
    
    print(f"Total benefits in {state_code}: {len(state_benefits)}\n")
    
    # Get state name mapping (optional - we can add this later)
    state_names = {
        'FL': 'Florida',
        'NH': 'New Hampshire',
        'TX': 'Texas',
        'CA': 'California',
        'NY': 'New York',
        # Add more as needed
    }
    
    state_full_name = state_names.get(state_code, state_code)
    
    glossary_content = f"""# {state_full_name} ({state_code}) Benefit Glossary

**State:** {state_full_name} ({state_code})  
**Total Benefit Categories:** {len(state_benefits)}  
**Generated:** January 18, 2026

This glossary documents all benefit categories available in {state_full_name} with state-specific cost-sharing values.  
**Use this for query filtering** - all values shown are actually available in {state_code} plans.

---

"""
    
    # Process each benefit for this state
    for i, benefit_name in enumerate(state_benefits, 1):
        print(f"Processing {i}/{len(state_benefits)}: {benefit_name}")
        
        # Get stats for this benefit IN THIS STATE
        cur.execute("""
            SELECT COUNT(*) as plan_count,
                   COUNT(CASE WHEN b.is_covered = true THEN 1 END) as covered_count,
                   COUNT(CASE WHEN b.cost_sharing_details IS NOT NULL 
                              AND b.cost_sharing_details::text != '{}' THEN 1 END) as has_details
            FROM benefits b
            JOIN plans p ON b.plan_id = p.plan_id
            WHERE b.benefit_name = %s AND p.state_code = %s
        """, (benefit_name, state_code))
        
        stats = cur.fetchone()
        plan_count = stats[0]
        covered_count = stats[1]
        has_details = stats[2]
        
        glossary_content += f"## {i}. {benefit_name}\n\n"
        glossary_content += f"**Plans in {state_code} offering this benefit:** {plan_count:,}  \n"
        glossary_content += f"**Plans where covered:** {covered_count:,} ({covered_count/plan_count*100:.1f}%)  \n"
        glossary_content += f"**Plans with cost-sharing details:** {has_details:,} ({has_details/plan_count*100:.1f}%)  \n\n"
        
        # Get most common JSONB values FOR THIS STATE
        if has_details > 0:
            glossary_content += f"### {state_code}-Specific Cost-Sharing Values:\n\n"
            
            # Copay in-network tier 1 (STATE-SPECIFIC)
            cur.execute("""
                SELECT b.cost_sharing_details->>'copay_inn_tier1' as value, COUNT(*) as count
                FROM benefits b
                JOIN plans p ON b.plan_id = p.plan_id
                WHERE b.benefit_name = %s
                  AND p.state_code = %s
                  AND b.cost_sharing_details->>'copay_inn_tier1' IS NOT NULL
                GROUP BY value
                ORDER BY count DESC
                LIMIT 10
            """, (benefit_name, state_code))
            
            copay_results = cur.fetchall()
            if copay_results:
                glossary_content += f"**In-Network Copay (Tier 1):**  \n"
                glossary_content += f"*{len(copay_results)} unique values in {state_code}*\n\n"
                for val, cnt in copay_results:
                    pct = cnt / plan_count * 100
                    glossary_content += f"- `{val}` - {cnt:,} plans ({pct:.1f}%)\n"
                glossary_content += "\n"
            
            # Coinsurance in-network tier 1 (STATE-SPECIFIC)
            cur.execute("""
                SELECT b.cost_sharing_details->>'coins_inn_tier1' as value, COUNT(*) as count
                FROM benefits b
                JOIN plans p ON b.plan_id = p.plan_id
                WHERE b.benefit_name = %s
                  AND p.state_code = %s
                  AND b.cost_sharing_details->>'coins_inn_tier1' IS NOT NULL
                GROUP BY value
                ORDER BY count DESC
                LIMIT 10
            """, (benefit_name, state_code))
            
            coins_results = cur.fetchall()
            if coins_results:
                glossary_content += f"**In-Network Coinsurance (Tier 1):**  \n"
                glossary_content += f"*{len(coins_results)} unique values in {state_code}*\n\n"
                for val, cnt in coins_results:
                    pct = cnt / plan_count * 100
                    glossary_content += f"- `{val}` - {cnt:,} plans ({pct:.1f}%)\n"
                glossary_content += "\n"
            
            # Out-of-network copay (STATE-SPECIFIC)
            cur.execute("""
                SELECT b.cost_sharing_details->>'copay_oon' as value, COUNT(*) as count
                FROM benefits b
                JOIN plans p ON b.plan_id = p.plan_id
                WHERE b.benefit_name = %s
                  AND p.state_code = %s
                  AND b.cost_sharing_details->>'copay_oon' IS NOT NULL
                GROUP BY value
                ORDER BY count DESC
                LIMIT 10
            """, (benefit_name, state_code))
            
            oon_copay_results = cur.fetchall()
            if oon_copay_results:
                glossary_content += f"**Out-of-Network Copay:**  \n"
                glossary_content += f"*{len(oon_copay_results)} unique values in {state_code}*\n\n"
                for val, cnt in oon_copay_results:
                    pct = cnt / plan_count * 100
                    glossary_content += f"- `{val}` - {cnt:,} plans ({pct:.1f}%)\n"
                glossary_content += "\n"
            
            # Out-of-network coinsurance (STATE-SPECIFIC)
            cur.execute("""
                SELECT b.cost_sharing_details->>'coins_oon' as value, COUNT(*) as count
                FROM benefits b
                JOIN plans p ON b.plan_id = p.plan_id
                WHERE b.benefit_name = %s
                  AND p.state_code = %s
                  AND b.cost_sharing_details->>'coins_oon' IS NOT NULL
                GROUP BY value
                ORDER BY count DESC
                LIMIT 10
            """, (benefit_name, state_code))
            
            oon_coins_results = cur.fetchall()
            if oon_coins_results:
                glossary_content += f"**Out-of-Network Coinsurance:**  \n"
                glossary_content += f"*{len(oon_coins_results)} unique values in {state_code}*\n\n"
                for val, cnt in oon_coins_results:
                    pct = cnt / plan_count * 100
                    glossary_content += f"- `{val}` - {cnt:,} plans ({pct:.1f}%)\n"
                glossary_content += "\n"
            
            # Visit limits (STATE-SPECIFIC)
            cur.execute("""
                SELECT 
                    b.cost_sharing_details->>'has_quantity_limit' as has_limit,
                    b.cost_sharing_details->>'limit_quantity' as quantity,
                    b.cost_sharing_details->>'limit_unit' as unit,
                    COUNT(*) as count
                FROM benefits b
                JOIN plans p ON b.plan_id = p.plan_id
                WHERE b.benefit_name = %s
                  AND p.state_code = %s
                  AND b.cost_sharing_details->>'has_quantity_limit' = 'true'
                GROUP BY has_limit, quantity, unit
                ORDER BY count DESC
                LIMIT 10
            """, (benefit_name, state_code))
            
            limit_results = cur.fetchall()
            if limit_results:
                glossary_content += f"**Visit/Quantity Limits:**  \n"
                glossary_content += f"*{len(limit_results)} unique limits in {state_code}*\n\n"
                for has_limit, quantity, unit, cnt in limit_results:
                    pct = cnt / plan_count * 100
                    if quantity and unit:
                        glossary_content += f"- `{quantity} {unit}` - {cnt:,} plans ({pct:.1f}%)\n"
                glossary_content += "\n"
            
            # Sample full record (STATE-SPECIFIC)
            cur.execute("""
                SELECT b.cost_sharing_details
                FROM benefits b
                JOIN plans p ON b.plan_id = p.plan_id
                WHERE b.benefit_name = %s
                  AND p.state_code = %s
                  AND b.cost_sharing_details IS NOT NULL
                  AND b.cost_sharing_details::text != '{}'
                LIMIT 1
            """, (benefit_name, state_code))
            
            sample = cur.fetchone()
            if sample and sample[0]:
                glossary_content += "### Sample Cost-Sharing Details:\n\n"
                glossary_content += "```json\n"
                glossary_content += json.dumps(sample[0], indent=2)
                glossary_content += "\n```\n\n"
        
        glossary_content += "---\n\n"
    
    # Add state-specific summary
    glossary_content += "\n\n" + "="*120 + "\n"
    glossary_content += f"# {state_code} SUMMARY STATISTICS\n"
    glossary_content += "="*120 + "\n\n"
    
    # Most commonly covered in this state
    cur.execute("""
        SELECT 
            b.benefit_name,
            COUNT(*) as total_plans,
            COUNT(CASE WHEN b.is_covered = true THEN 1 END) as covered_plans,
            COUNT(CASE WHEN b.is_covered = true THEN 1 END)::float / COUNT(*)::float * 100 as coverage_pct
        FROM benefits b
        JOIN plans p ON b.plan_id = p.plan_id
        WHERE p.state_code = %s
        GROUP BY b.benefit_name
        HAVING COUNT(*) > 10
        ORDER BY coverage_pct DESC
        LIMIT 20
    """, (state_code,))
    
    coverage = cur.fetchall()
    glossary_content += f"## Most Commonly Covered Benefits in {state_code}\n\n"
    for benefit, total, covered, pct in coverage:
        glossary_content += f"- **{benefit}** - {covered:,}/{total:,} plans ({pct:.1f}%)\n"
    glossary_content += "\n---\n\n"
    
    # Least commonly covered
    cur.execute("""
        SELECT 
            b.benefit_name,
            COUNT(*) as total_plans,
            COUNT(CASE WHEN b.is_covered = true THEN 1 END) as covered_plans,
            COUNT(CASE WHEN b.is_covered = true THEN 1 END)::float / COUNT(*)::float * 100 as coverage_pct
        FROM benefits b
        JOIN plans p ON b.plan_id = p.plan_id
        WHERE p.state_code = %s
        GROUP BY b.benefit_name
        HAVING COUNT(*) > 10
        ORDER BY coverage_pct ASC
        LIMIT 20
    """, (state_code,))
    
    least = cur.fetchall()
    glossary_content += f"## Least Commonly Covered Benefits in {state_code}\n\n"
    for benefit, total, covered, pct in least:
        glossary_content += f"- **{benefit}** - {covered:,}/{total:,} plans ({pct:.1f}%)\n"
    glossary_content += "\n---\n\n"
    
    # Benefits with most variation in this state
    cur.execute("""
        SELECT 
            b.benefit_name,
            COUNT(DISTINCT b.cost_sharing_details->>'copay_inn_tier1') as unique_copays
        FROM benefits b
        JOIN plans p ON b.plan_id = p.plan_id
        WHERE p.state_code = %s
          AND b.cost_sharing_details->>'copay_inn_tier1' IS NOT NULL
        GROUP BY b.benefit_name
        ORDER BY unique_copays DESC
        LIMIT 15
    """, (state_code,))
    
    variation = cur.fetchall()
    glossary_content += f"## Benefits with Most Cost Variation in {state_code}\n\n"
    glossary_content += "*(Most unique copay amounts - use these for range queries)*\n\n"
    for benefit, unique_count in variation:
        glossary_content += f"- **{benefit}** - {unique_count} different copay amounts\n"
    glossary_content += "\n---\n\n"
    
    glossary_content += f"**End of {state_code} Glossary**\n"
    glossary_content += f"**Generated:** January 18, 2026\n"
    
    # Write to file
    output_file = f'/Users/andy/healthcare_plan_backends/aca/db_benefit_glossary-{state_code}.md'
    with open(output_file, 'w') as f:
        f.write(glossary_content)
    
    print(f"\n✅ {state_code} glossary saved to: {output_file}")
    print(f"   Generated {len(state_benefits)} benefits")
    
    conn.close()
    
    return len(state_benefits)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_state_benefit_glossary.py <STATE_CODE>")
        print("Example: python3 generate_state_benefit_glossary.py FL")
        sys.exit(1)
    
    state_code = sys.argv[1].upper()
    
    total = generate_state_glossary(state_code)
    
    print(f"\n{'='*120}")
    print(f"✅ COMPLETE: {state_code} benefit glossary with {total} benefits")
    print(f"{'='*120}\n")
