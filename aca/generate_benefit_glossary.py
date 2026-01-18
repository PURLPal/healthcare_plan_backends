#!/usr/bin/env python3
"""
Generate comprehensive benefit glossary with most common JSONB values
"""

import psycopg2
import json
from collections import Counter

def generate_glossary(limit=10):
    """Generate benefit glossary for first N benefits"""
    
    with open('/Users/andy/aca_overview_test/.db_password', 'r') as f:
        password = f.read().strip()
    
    conn = psycopg2.connect(
        f"host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com "
        f"dbname=aca_plans user=aca_admin password={password}"
    )
    cur = conn.cursor()
    
    # Get all distinct benefit names
    cur.execute("""
        SELECT DISTINCT benefit_name
        FROM benefits
        ORDER BY benefit_name ASC
    """)
    
    all_benefits = [row[0] for row in cur.fetchall()]
    
    print(f"\n{'='*120}")
    print(f"GENERATING BENEFIT GLOSSARY")
    print(f"{'='*120}")
    print(f"Total benefits: {len(all_benefits)}")
    print(f"Generating first {limit} benefits...\n")
    
    glossary_content = """# Database Benefit Glossary

**Total Benefit Categories:** {total}  
**Generated:** January 18, 2026

This glossary documents all benefit categories in our database with their most common cost-sharing values.

---

""".format(total=len(all_benefits))
    
    # Process first N benefits
    for i, benefit_name in enumerate(all_benefits[:limit], 1):
        print(f"Processing {i}/{limit}: {benefit_name}")
        
        # Get stats for this benefit
        cur.execute("""
            SELECT COUNT(*) as plan_count,
                   COUNT(CASE WHEN is_covered = true THEN 1 END) as covered_count,
                   COUNT(CASE WHEN cost_sharing_details IS NOT NULL 
                              AND cost_sharing_details::text != '{}' THEN 1 END) as has_details
            FROM benefits
            WHERE benefit_name = %s
        """, (benefit_name,))
        
        stats = cur.fetchone()
        plan_count = stats[0]
        covered_count = stats[1]
        has_details = stats[2]
        
        # Get state availability
        cur.execute("""
            SELECT DISTINCT p.state_code, COUNT(DISTINCT b.plan_id) as plan_count
            FROM benefits b
            JOIN plans p ON b.plan_id = p.plan_id
            WHERE b.benefit_name = %s
            GROUP BY p.state_code
            ORDER BY p.state_code
        """, (benefit_name,))
        
        state_data = cur.fetchall()
        states_list = [f"{state} ({count:,} plans)" for state, count in state_data]
        states_str = ", ".join(states_list) if states_list else "None"
        
        glossary_content += f"## {i}. {benefit_name}\n\n"
        glossary_content += f"**Plans offering this benefit:** {plan_count:,}  \n"
        glossary_content += f"**Plans where covered:** {covered_count:,} ({covered_count/plan_count*100:.1f}%)  \n"
        glossary_content += f"**Plans with cost-sharing details:** {has_details:,} ({has_details/plan_count*100:.1f}%)  \n"
        glossary_content += f"**States offering this benefit:** {len(state_data)} states  \n\n"
        glossary_content += f"**State availability:** {states_str}\n\n"
        
        # Get most common JSONB values
        if has_details > 0:
            glossary_content += "### Most Common Cost-Sharing Values:\n\n"
            
            # Copay in-network tier 1
            cur.execute("""
                SELECT cost_sharing_details->>'copay_inn_tier1' as value, COUNT(*) as count
                FROM benefits
                WHERE benefit_name = %s
                  AND cost_sharing_details->>'copay_inn_tier1' IS NOT NULL
                GROUP BY value
                ORDER BY count DESC
                LIMIT 5
            """, (benefit_name,))
            
            copay_results = cur.fetchall()
            if copay_results:
                glossary_content += "**In-Network Copay (Tier 1):**\n"
                for val, cnt in copay_results:
                    pct = cnt / plan_count * 100
                    glossary_content += f"- `{val}` - {cnt:,} plans ({pct:.1f}%)\n"
                glossary_content += "\n"
            
            # Coinsurance in-network tier 1
            cur.execute("""
                SELECT cost_sharing_details->>'coins_inn_tier1' as value, COUNT(*) as count
                FROM benefits
                WHERE benefit_name = %s
                  AND cost_sharing_details->>'coins_inn_tier1' IS NOT NULL
                GROUP BY value
                ORDER BY count DESC
                LIMIT 5
            """, (benefit_name,))
            
            coins_results = cur.fetchall()
            if coins_results:
                glossary_content += "**In-Network Coinsurance (Tier 1):**\n"
                for val, cnt in coins_results:
                    pct = cnt / plan_count * 100
                    glossary_content += f"- `{val}` - {cnt:,} plans ({pct:.1f}%)\n"
                glossary_content += "\n"
            
            # Out-of-network copay
            cur.execute("""
                SELECT cost_sharing_details->>'copay_oon' as value, COUNT(*) as count
                FROM benefits
                WHERE benefit_name = %s
                  AND cost_sharing_details->>'copay_oon' IS NOT NULL
                GROUP BY value
                ORDER BY count DESC
                LIMIT 5
            """, (benefit_name,))
            
            oon_copay_results = cur.fetchall()
            if oon_copay_results:
                glossary_content += "**Out-of-Network Copay:**\n"
                for val, cnt in oon_copay_results:
                    pct = cnt / plan_count * 100
                    glossary_content += f"- `{val}` - {cnt:,} plans ({pct:.1f}%)\n"
                glossary_content += "\n"
            
            # Out-of-network coinsurance
            cur.execute("""
                SELECT cost_sharing_details->>'coins_oon' as value, COUNT(*) as count
                FROM benefits
                WHERE benefit_name = %s
                  AND cost_sharing_details->>'coins_oon' IS NOT NULL
                GROUP BY value
                ORDER BY count DESC
                LIMIT 5
            """, (benefit_name,))
            
            oon_coins_results = cur.fetchall()
            if oon_coins_results:
                glossary_content += "**Out-of-Network Coinsurance:**\n"
                for val, cnt in oon_coins_results:
                    pct = cnt / plan_count * 100
                    glossary_content += f"- `{val}` - {cnt:,} plans ({pct:.1f}%)\n"
                glossary_content += "\n"
            
            # Visit limits
            cur.execute("""
                SELECT 
                    cost_sharing_details->>'has_quantity_limit' as has_limit,
                    cost_sharing_details->>'limit_quantity' as quantity,
                    cost_sharing_details->>'limit_unit' as unit,
                    COUNT(*) as count
                FROM benefits
                WHERE benefit_name = %s
                  AND cost_sharing_details->>'has_quantity_limit' = 'true'
                GROUP BY has_limit, quantity, unit
                ORDER BY count DESC
                LIMIT 5
            """, (benefit_name,))
            
            limit_results = cur.fetchall()
            if limit_results:
                glossary_content += "**Visit/Quantity Limits:**\n"
                for has_limit, quantity, unit, cnt in limit_results:
                    pct = cnt / plan_count * 100
                    if quantity and unit:
                        glossary_content += f"- `{quantity} {unit}` - {cnt:,} plans ({pct:.1f}%)\n"
                glossary_content += "\n"
            
            # Sample full record
            cur.execute("""
                SELECT cost_sharing_details
                FROM benefits
                WHERE benefit_name = %s
                  AND cost_sharing_details IS NOT NULL
                  AND cost_sharing_details::text != '{}'
                LIMIT 1
            """, (benefit_name,))
            
            sample = cur.fetchone()
            if sample and sample[0]:
                glossary_content += "### Sample Cost-Sharing Details:\n\n"
                glossary_content += "```json\n"
                glossary_content += json.dumps(sample[0], indent=2)
                glossary_content += "\n```\n\n"
        
        glossary_content += "---\n\n"
    
    # Write to file
    output_file = '/Users/andy/healthcare_plan_backends/aca/db_benefit_glossary.md'
    with open(output_file, 'w') as f:
        f.write(glossary_content)
    
    print(f"\n✅ Glossary saved to: {output_file}")
    print(f"   Generated {limit} of {len(all_benefits)} benefits")
    print(f"   Remaining: {len(all_benefits) - limit}")
    
    conn.close()
    
    return len(all_benefits)

if __name__ == "__main__":
    import sys
    
    limit = 10
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    
    total = generate_glossary(limit)
    
    print(f"\n{'='*120}")
    print(f"To generate all {total} benefits, run:")
    print(f"  python3 generate_benefit_glossary.py {total}")
    print(f"{'='*120}\n")
