#!/usr/bin/env python3
import os
import sys
from app import create_app, db
from app.models.docker import DockerComposeConfig, DockerContainer

def init_docker_tables():
    """
    Initialize Docker-related tables in both development and production databases.
    """
    # Initialize tables in production database (default)
    app_prod = create_app()
    with app_prod.app_context():
        # Create tables for Docker models
        DockerComposeConfig.__table__.create(db.engine, checkfirst=True)
        DockerContainer.__table__.create(db.engine, checkfirst=True)
        print("Docker tables created in production database.")
    
    # Initialize tables in development database
    app_dev = create_app('development')
    with app_dev.app_context():
        # Create tables for Docker models
        DockerComposeConfig.__table__.create(db.engine, checkfirst=True)
        DockerContainer.__table__.create(db.engine, checkfirst=True)
        print("Docker tables created in development database.")
    
    print("Docker tables initialization complete.")
    return True

if __name__ == '__main__':
    success = init_docker_tables()
    sys.exit(0 if success else 1)