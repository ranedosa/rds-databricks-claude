#!/usr/bin/env python3
"""
Test PostgreSQL database connections for all 7 MCP servers
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

# Database configurations from settings.local.json
databases = {
    "fraud_postgresql": {
        "host": "snappt-prod-fraud-db-01.cf42ig8y0oy4.us-west-2.rds.amazonaws.com",
        "database": "oing9oa6eith_production",
        "user": "W9mKQBAB9FDaX6b8",
        "password": "D47VKaEY,UVGPMui9kjnJpnugE,8ivbf",
        "port": 5432
    },
    "av_postgresql": {
        "host": "snappt-prod-av-cluster.cluster-ro-cf42ig8y0oy4.us-west-2.rds.amazonaws.com",
        "database": "automated_validation",
        "user": "postgres",
        "password": "!PFelaSuuj8azi<4O4GN4oiX[[jt",
        "port": 5432
    },
    "dp_iv_income_validation": {
        "host": "snappt-prod-document-processing-cluster.cluster-ro-cf42ig8y0oy4.us-west-2.rds.amazonaws.com",
        "database": "income_validation",
        "user": "postgres",
        "password": "mr:8F)n2F$9>rQeh]etxzIxdK.~6",
        "port": 5432
    },
    "dp_iv_ai_services": {
        "host": "snappt-prod-document-processing-cluster.cluster-ro-cf42ig8y0oy4.us-west-2.rds.amazonaws.com",
        "database": "ai_services",
        "user": "postgres",
        "password": "mr:8F)n2F$9>rQeh]etxzIxdK.~6",
        "port": 5432
    },
    "dp_iv_document_intelligence": {
        "host": "snappt-prod-document-processing-cluster.cluster-ro-cf42ig8y0oy4.us-west-2.rds.amazonaws.com",
        "database": "document_intelligence",
        "user": "postgres",
        "password": "mr:8F)n2F$9>rQeh]etxzIxdK.~6",
        "port": 5432
    },
    "dp_iv_inception_fraud": {
        "host": "snappt-prod-document-processing-cluster.cluster-ro-cf42ig8y0oy4.us-west-2.rds.amazonaws.com",
        "database": "inception_fraud",
        "user": "postgres",
        "password": "mr:8F)n2F$9>rQeh]etxzIxdK.~6",
        "port": 5432
    },
    "enterprise_postgresql": {
        "host": "snappt-prod-enterprise-db-02.cf42ig8y0oy4.us-west-2.rds.amazonaws.com",
        "database": "postgres",
        "user": "gRXRvWwqeVmB",
        "password": "p5lJqCwLwbXvJ3fTgHG.JcBy",
        "port": 5432
    }
}

def test_connection(name, config):
    """Test a single database connection"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Host: {config['host']}")
    print(f"Database: {config['database']}")
    print(f"User: {config['user']}")
    print(f"{'='*60}")

    try:
        # Attempt connection
        print("Connecting...")
        conn = psycopg2.connect(
            host=config['host'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            port=config['port'],
            connect_timeout=10
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        print("✅ Connection successful!")

        # Test query: Get PostgreSQL version
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"PostgreSQL Version: {version[:80]}...")

        # Test query: Simple SELECT
        cursor.execute("SELECT 1 as test;")
        result = cursor.fetchone()[0]
        print(f"Test query (SELECT 1): {result}")

        # Get table count
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema');
        """)
        table_count = cursor.fetchone()[0]
        print(f"Number of tables: {table_count}")

        # List first 5 tables
        cursor.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
            LIMIT 5;
        """)
        tables = cursor.fetchall()
        if tables:
            print(f"Sample tables:")
            for schema, table in tables:
                print(f"  - {schema}.{table}")

        cursor.close()
        conn.close()

        return True

    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {str(e)}")
        return False
    except psycopg2.Error as e:
        print(f"❌ Database error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def main():
    print("="*60)
    print("PostgreSQL Database Connection Tests")
    print("="*60)

    results = {}

    for name, config in databases.items():
        results[name] = test_connection(name, config)

    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    successful = sum(1 for v in results.values() if v)
    total = len(results)

    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{name:40} {status}")

    print(f"\nTotal: {successful}/{total} connections successful")

    if successful == total:
        print("\n🎉 All database connections are working!")
        return 0
    else:
        print(f"\n⚠️  {total - successful} connection(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
