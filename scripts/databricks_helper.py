#!/usr/bin/env python3
"""
Databricks Helper Script
Uses Databricks SDK to interact with workspace programmatically
"""

import os
import sys
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import sql

# Load config from .databrickscfg
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', '.databrickscfg')

# Initialize Databricks client
w = WorkspaceClient(
    host="https://dbc-9ca0f5e0-2208.cloud.databricks.com",
    token=os.getenv("DATABRICKS_TOKEN")
)

def list_dashboards():
    """List all SQL dashboards"""
    dashboards = w.dashboards.list()
    for dash in dashboards:
        print(f"Dashboard: {dash.name} (ID: {dash.id})")
        print(f"  URL: https://dbc-9ca0f5e0-2208.cloud.databricks.com/sql/dashboards/{dash.id}")
    return dashboards

def get_dashboard(dashboard_id):
    """Get dashboard details"""
    dashboard = w.dashboards.get(dashboard_id)
    print(f"Dashboard: {dashboard.name}")
    print(f"Widgets: {len(dashboard.widgets) if dashboard.widgets else 0}")
    return dashboard

def add_visualization_to_dashboard(dashboard_id, query_text, viz_name, viz_type="table"):
    """
    Add a visualization to a dashboard

    Args:
        dashboard_id: Dashboard ID
        query_text: SQL query
        viz_name: Name for the visualization
        viz_type: Type of visualization (table, counter, chart, etc.)
    """
    # This would require creating a query, then a visualization, then adding to dashboard
    # Databricks SDK for dashboards is limited - manual approach may be easier
    print("Note: Adding visualizations programmatically is complex.")
    print("Recommended approach: Use the web UI")
    print(f"\nQuery to add:\n{query_text}")

def list_queries():
    """List all saved queries"""
    queries = w.queries.list()
    for q in queries:
        print(f"Query: {q.name} (ID: {q.id})")
    return queries

def create_query(name, query_text, warehouse_id):
    """Create a new SQL query"""
    query = w.queries.create(
        name=name,
        query=query_text,
        data_source_id=warehouse_id
    )
    print(f"Created query: {query.name} (ID: {query.id})")
    return query

def list_warehouses():
    """List SQL warehouses"""
    warehouses = w.warehouses.list()
    for wh in warehouses:
        print(f"Warehouse: {wh.name} (ID: {wh.id})")
        print(f"  State: {wh.state}")
    return warehouses

if __name__ == "__main__":
    print("Databricks Helper Script")
    print("=" * 80)

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python databricks_helper.py list-dashboards")
        print("  python databricks_helper.py list-queries")
        print("  python databricks_helper.py list-warehouses")
        print("  python databricks_helper.py get-dashboard <dashboard_id>")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "list-dashboards":
            list_dashboards()

        elif command == "list-queries":
            list_queries()

        elif command == "list-warehouses":
            list_warehouses()

        elif command == "get-dashboard" and len(sys.argv) > 2:
            dashboard_id = sys.argv[2]
            get_dashboard(dashboard_id)

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
