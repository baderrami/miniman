#!/usr/bin/env python3
import os
import sys
from app import create_app, db
from app.models.docker import DockerComposeConfig, DockerContainer

def test_docker_tables():
    """
    Test if Docker-related tables exist in the database.
    """
    # Create app with development configuration
    app = create_app('development')

    with app.app_context():
        # Check if tables exist
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        # Print all tables for debugging
        print("Database tables:", tables)

        # Check for Docker-related tables
        docker_tables = ['docker_compose_configs', 'docker_containers']
        missing_tables = [table for table in docker_tables if table not in tables]

        if missing_tables:
            print(f"Error: The following Docker-related tables are missing: {missing_tables}")
            return False
        else:
            print("Success: All Docker-related tables exist in the database.")
            return True

if __name__ == '__main__':
    success = test_docker_tables()
    sys.exit(0 if success else 1)
