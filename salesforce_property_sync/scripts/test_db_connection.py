#!/usr/bin/env python3
"""Test PostgreSQL database connection."""

import psycopg2
from psycopg2 import sql
import os

def test_connection():
    """Test the PostgreSQL connection and display basic information."""

    # Database credentials
    db_config = {
        'host': 'snappt-prod-fraud-db-01.cf42ig8y0oy4.us-west-2.rds.amazonaws.com',
        'port': 5432,
        'user': 'W9mKQBAB9FDaX6b8',
        'password': 'D47VKaEY,UVGPMui9kjnJpnugE,8ivbf',
        'database': 'oing9oa6eith_production'
    }

    try:
        # Connect to the database
        print(f"Connecting to PostgreSQL database at {db_config['host']}...")
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Test the connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✓ Successfully connected to PostgreSQL!")
        print(f"  Database version: {version[0]}")

        # Get current database name
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
        print(f"  Current database: {db_name}")

        # Get current user
        cursor.execute("SELECT current_user;")
        user = cursor.fetchone()[0]
        print(f"  Connected as user: {user}")

        # Get list of schemas
        cursor.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schema_name;
        """)
        schemas = cursor.fetchall()
        print(f"\n  Available schemas ({len(schemas)}):")
        for schema in schemas[:10]:  # Show first 10
            print(f"    - {schema[0]}")
        if len(schemas) > 10:
            print(f"    ... and {len(schemas) - 10} more")

        # Get table count
        cursor.execute("""
            SELECT schemaname, COUNT(*)
            FROM pg_tables
            WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
            GROUP BY schemaname
            ORDER BY schemaname;
        """)
        table_counts = cursor.fetchall()
        print(f"\n  Tables by schema:")
        for schema, count in table_counts:
            print(f"    - {schema}: {count} tables")

        cursor.close()
        conn.close()

        print("\n✓ Connection test successful!")
        return True

    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()
