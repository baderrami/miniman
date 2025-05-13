# Docker Tables Fix

## Issue
The Docker-related tables (`docker_compose_configs` and `docker_containers`) were not being created in the database when running `flask init-db`. This was causing errors when trying to use the Docker management feature.

## Root Cause
The issue was that the Docker models were not being properly registered with SQLAlchemy during database initialization. Additionally, the application uses two different databases (development and production), and the tables needed to be created in both.

## Solution
We've updated the `init_db` function in `run.py` to:
1. Explicitly create the Docker tables using `__table__.create()` to ensure they exist
2. Initialize tables in both the development and production databases, regardless of which configuration is being used

## How to Fix
1. Make sure you have the latest version of `run.py` with the updated `init_db` function
2. Run the following command to initialize the database:
   ```bash
   export FLASK_APP=run.py
   flask init-db
   ```
3. Verify that the Docker tables were created by running:
   ```bash
   python test_docker_tables.py
   ```
   You should see output indicating that all Docker-related tables exist in the database.

## Alternative Solutions
If you're still experiencing issues, you can use one of the following scripts to explicitly create the Docker tables:

1. `create_docker_tables.py`: Creates Docker tables in the default (production) database
2. `init_docker_tables.py`: Creates Docker tables in both the development and production databases

To use these scripts, simply run:
```bash
python create_docker_tables.py
# or
python init_docker_tables.py
```

## Technical Details
The Docker models are defined in `app/models/docker.py` and include:
- `DockerComposeConfig`: Stores Docker Compose configuration information
- `DockerContainer`: Stores information about Docker containers

These models are imported in `run.py` and included in the shell context processor, but they weren't being properly registered with SQLAlchemy during database initialization. The updated `init_db` function explicitly creates these tables to ensure they exist.