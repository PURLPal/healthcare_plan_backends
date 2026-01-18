#!/usr/bin/env python3
"""
Add summary statistics to the end of the benefit glossary
"""

import psycopg2

def add_summary():
    """Add summary statistics to glossary"""
    
    with open('/Users/andy/aca_overview_test/.db_password', 'r') as f:
        password = f.read().strip()
    
    conn = psycopg2.connect(
        f"host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com "
        f"dbname=aca_plans user=aca_admin password={password}"
    )
    cur = conn.cursor()
    
    summary = "\n\n" + "="*120 + "\n"
    summary += "# GLOSSARY SUMMARY STATISTICS\n"
    summary += "="*120 + "\n\n"
    
    # 1. Total benefits
    cur.execute("SELECT COUNT(DISTINCT benefit_name) FROM benefits")
    total_benefits = cur.fetchone()[0]
    summary += f"**Total Unique Benefit Categories:** {total_benefits}\n\n"
    
    # 2. Most universal benefits (available in all 30 states)
    cur.execute("""
        SELECT b.benefit_name, COUNT(DISTINCT p.state_code) as state_count, COUNT(DISTINCT b.plan_id) as plan_count
        FROM benefits b
        JOIN plans p ON b.plan_id = p.plan_id
        GROUP BY b.benefit_name
        HAVING COUNT(DISTINCT p.state_code) = 30
        ORDER BY COUNT(DISTINCT b.plan_id) DESC
        LIMIT 20
    """)
    
    universal = cur.fetchall()
    summary += f"## Universal Benefits (Available in All 30 States)\n\n"
    summary += f"**Count:** {len(universal)} benefits\n\n"
    for benefit, states, plans in universal[:10]:
        summary += f"- **{benefit}** - {plans:,} plans\n"
    summary += "\n---\n\n"
    
    # 3. State-specific benefits (only 1-5 states)
    cur.execute("""
        SELECT b.benefit_name, COUNT(DISTINCT p.state_code) as state_count, COUNT(DISTINCT b.plan_id) as plan_count
        FROM benefits b
        JOIN plans p ON b.plan_id = p.plan_id
        GROUP BY b.benefit_name
        HAVING COUNT(DISTINCT p.state_code) <= 5
        ORDER BY COUNT(DISTINCT p.state_code), COUNT(DISTINCT b.plan_id) DESC
    """)
    
    state_specific = cur.fetchall()
    summary += f"## State-Specific Benefits (5 or fewer states)\n\n"
    summary += f"**Count:** {len(state_specific)} benefits\n\n"
    summary += f"{'Benefit':70s} | {'States':>8s} | {'Plans':>10s}\n"
    summary += "-" * 95 + "\n"
    for benefit, states, plans in state_specific[:20]:
        summary += f"{benefit[:68]:70s} | {states:>8d} | {plans:>10,d}\n"
    summary += "\n---\n\n"
    
    # 4. Most commonly covered benefits (by percentage)
    cur.execute("""
        SELECT 
            benefit_name,
            COUNT(*) as total_plans,
            COUNT(CASE WHEN is_covered = true THEN 1 END) as covered_plans,
            COUNT(CASE WHEN is_covered = true THEN 1 END)::float / COUNT(*)::float * 100 as coverage_pct
        FROM benefits
        GROUP BY benefit_name
        HAVING COUNT(*) > 1000
        ORDER BY coverage_pct DESC
        LIMIT 20
    """)
    
    coverage = cur.fetchall()
    summary += f"## Most Commonly Covered Benefits (>1000 plans)\n\n"
    for benefit, total, covered, pct in coverage:
        summary += f"- **{benefit}** - {covered:,}/{total:,} plans ({pct:.1f}%)\n"
    summary += "\n---\n\n"
    
    # 5. Least commonly covered benefits
    cur.execute("""
        SELECT 
            benefit_name,
            COUNT(*) as total_plans,
            COUNT(CASE WHEN is_covered = true THEN 1 END) as covered_plans,
            COUNT(CASE WHEN is_covered = true THEN 1 END)::float / COUNT(*)::float * 100 as coverage_pct
        FROM benefits
        GROUP BY benefit_name
        HAVING COUNT(*) > 1000
        ORDER BY coverage_pct ASC
        LIMIT 20
    """)
    
    least = cur.fetchall()
    summary += f"## Least Commonly Covered Benefits (>1000 plans)\n\n"
    for benefit, total, covered, pct in least:
        summary += f"- **{benefit}** - {covered:,}/{total:,} plans ({pct:.1f}%)\n"
    summary += "\n---\n\n"
    
    # 6. Benefits with most variation in copays
    cur.execute("""
        SELECT 
            benefit_name,
            COUNT(DISTINCT cost_sharing_details->>'copay_inn_tier1') as unique_copays
        FROM benefits
        WHERE cost_sharing_details->>'copay_inn_tier1' IS NOT NULL
        GROUP BY benefit_name
        ORDER BY unique_copays DESC
        LIMIT 15
    """)
    
    variation = cur.fetchall()
    summary += f"## Benefits with Most Cost Variation\n\n"
    summary += "*(Most unique copay amounts - indicates high price variation)*\n\n"
    for benefit, unique_count in variation:
        summary += f"- **{benefit}** - {unique_count} different copay amounts\n"
    summary += "\n---\n\n"
    
    # 7. Benefits with visit limits
    cur.execute("""
        SELECT 
            benefit_name,
            COUNT(*) as plans_with_limits,
            mode() WITHIN GROUP (ORDER BY cost_sharing_details->>'limit_quantity') as most_common_limit,
            mode() WITHIN GROUP (ORDER BY cost_sharing_details->>'limit_unit') as most_common_unit
        FROM benefits
        WHERE cost_sharing_details->>'has_quantity_limit' = 'true'
        GROUP BY benefit_name
        HAVING COUNT(*) > 100
        ORDER BY COUNT(*) DESC
        LIMIT 20
    """)
    
    limits = cur.fetchall()
    summary += f"## Benefits Most Commonly Subject to Visit/Quantity Limits\n\n"
    for benefit, plan_count, limit_qty, limit_unit in limits:
        summary += f"- **{benefit}** - {plan_count:,} plans (typical: {limit_qty} {limit_unit})\n"
    summary += "\n---\n\n"
    
    # 8. State coverage summary
    cur.execute("""
        SELECT p.state_code, COUNT(DISTINCT b.benefit_name) as benefit_count
        FROM benefits b
        JOIN plans p ON b.plan_id = p.plan_id
        GROUP BY p.state_code
        ORDER BY benefit_count DESC
    """)
    
    state_benefits = cur.fetchall()
    summary += f"## Benefits by State\n\n"
    summary += f"{'State':>8s} | {'Unique Benefits':>18s}\n"
    summary += "-" * 30 + "\n"
    for state, count in state_benefits:
        summary += f"{state:>8s} | {count:>18d}\n"
    summary += "\n---\n\n"
    
    summary += f"**End of Glossary**\n"
    summary += f"**Generated:** January 18, 2026\n"
    
    # Append to file
    with open('/Users/andy/healthcare_plan_backends/aca/db_benefit_glossary.md', 'a') as f:
        f.write(summary)
    
    print("✅ Summary statistics added to glossary")
    conn.close()

if __name__ == "__main__":
    add_summary()
