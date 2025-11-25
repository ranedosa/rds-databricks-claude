"""
Extract database schemas from all MCP-connected PostgreSQL databases
and save them as JSON files for ERD generation.
"""
import json
from pathlib import Path

# Schema query to extract all table structures
SCHEMA_QUERY = """
SELECT
    c.table_name,
    c.column_name,
    c.ordinal_position,
    c.data_type,
    c.character_maximum_length,
    c.is_nullable,
    c.column_default,
    tc.constraint_type,
    kcu.constraint_name
FROM information_schema.columns c
LEFT JOIN information_schema.key_column_usage kcu
    ON c.table_name = kcu.table_name
    AND c.column_name = kcu.column_name
    AND c.table_schema = kcu.table_schema
LEFT JOIN information_schema.table_constraints tc
    ON kcu.constraint_name = tc.constraint_name
    AND kcu.table_schema = tc.table_schema
WHERE c.table_schema = 'public'
ORDER BY c.table_name, c.ordinal_position;
"""

# Placeholder - actual queries would be executed via MCP tools
# For now, storing the fraud schema data we already retrieved

fraud_schema = [
    # The large JSON response from the first query
    # This would be populated from the mcp__snappt-postgres__query tool
]

# Save to file
output_dir = Path("/Users/danerosa/rds_databricks_claude/database_erd")
output_dir.mkdir(exist_ok=True)

# Process each database
databases = [
    "fraud_postgresql",
    "av_postgresql",
    "dp_income_validation",
    "dp_ai_services",
    "dp_document_intelligence",
    "dp_inception_fraud",
    "enterprise_postgresql"
]

print("Schema extraction script prepared.")
print(f"Will extract schemas from {len(databases)} databases.")
print(f"Output directory: {output_dir}")
