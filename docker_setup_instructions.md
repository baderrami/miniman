# Docker Management Feature Setup Instructions

## Overview
The Docker management feature allows you to define remote Docker Compose sources, install and run Docker containers, check for updates, and manage containers through an intuitive UI.

## Setup Instructions

### 1. Update Your Code
Make sure you have the latest version of the codebase with the Docker management feature.

### 2. Install Dependencies
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 3. Initialize the Database
The Docker management feature requires database tables to store configuration and container information. To initialize these tables:

```bash
# Set the Flask application
export FLASK_APP=run.py

# Initialize the database
flask init-db
```

This will create the necessary tables in the database:
- `docker_compose_configs`: Stores Docker Compose configuration information
- `docker_containers`: Stores information about Docker containers

### 4. Install Docker and Docker Compose
If you're using the provisioning script, Docker and Docker Compose will be installed automatically. If you're setting up manually, you'll need to install Docker and Docker Compose:

```bash
# Install prerequisites
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up the stable repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
sudo apt-get install -y docker-compose-plugin
```

### 5. Verify Setup
You can verify that the Docker management feature is set up correctly by running the test script:

```bash
python test_docker_tables.py
```

This script will check if the required database tables exist.

### 6. Access the Feature
Once everything is set up, you can access the Docker management feature through the web interface by clicking on the "Docker" link in the navigation menu.

## Troubleshooting

### Database Table Missing Error
If you see an error like "no such table: docker_compose_configs", it means the database hasn't been initialized with the Docker models. Run the database initialization command:

```bash
export FLASK_APP=run.py
flask init-db
```

### Docker Installation Issues
If you encounter issues with Docker installation, refer to the [official Docker documentation](https://docs.docker.com/engine/install/ubuntu/) for troubleshooting.

### Docker Compose Not Found
If you see an error about Docker Compose not being found, make sure you've installed the Docker Compose plugin:

```bash
sudo apt-get install -y docker-compose-plugin
```