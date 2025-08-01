#!/usr/bin/env python3
"""Test PostgreSQL connection for all services."""

import psycopg2
import sys
import os
from urllib.parse import urlparse

def test_connection(service_name, connection_string):
    """Test connection to a specific database."""
    try:
        # Parse the connection string
        parsed = urlparse(connection_string)

        # Connect to the database
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remove leading slash
            user=parsed.username,
            password=parsed.password
        )

        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        print(f"✅ {service_name}: Connection successful")
        print(f"   Database: {parsed.path[1:]}")
        print(f"   User: {parsed.username}")
        print(f"   PostgreSQL version: {version.split(',')[0]}")
        return True

    except Exception as e:
        print(f"❌ {service_name}: Connection failed")
        print(f"   Error: {e}")
        return False

def main():
    """Test connections for all services."""
    print("🔍 Testing PostgreSQL connections for all services...\n")

    # Get admin credentials from environment variables
    postgres_user = os.getenv('POSTGRES_USER', 'postgres')
    postgres_password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
    postgres_port = os.getenv('POSTGRES_PORT', '5432')

    # Test connections using admin user (for migrations)
    connections = [
        ("User Service", f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/briefly_user"),
        ("Meetings Service", f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/briefly_meetings"),
        ("Shipments Service", f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/briefly_shipments"),
        ("Office Service", f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/briefly_office"),
        ("Chat Service", f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/briefly_chat"),
        ("Vector Service", f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/briefly_vector"),
    ]

    success_count = 0
    for service_name, connection_string in connections:
        if test_connection(service_name, connection_string):
            success_count += 1
        print()

    print("=" * 50)
    print(f"📊 Results: {success_count}/{len(connections)} services connected successfully")

    if success_count == len(connections):
        print("🎉 All services can connect to PostgreSQL!")
        print("\n📋 Next steps:")
        print("1. Update your service settings to use PostgreSQL URLs")
        print("2. Run migrations: ./scripts/run-migrations.sh")
        print("3. Test your applications")
    else:
        print("⚠️  Some services failed to connect. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
