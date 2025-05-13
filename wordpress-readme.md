# WordPress Docker Compose Example for MiniMan

This is an example Docker Compose configuration for running WordPress with MySQL, designed to be used with the MiniMan Docker management feature.

## Configuration Details

- **WordPress**: Latest version, accessible on port 8080
- **MySQL**: Version 5.7 for database storage
- **Volumes**: Persistent storage for both WordPress files and MySQL data
- **Network**: Dedicated network for service communication

## How to Use with MiniMan

### 1. Add the Configuration

1. Log in to your MiniMan interface
2. Navigate to the Docker management page by clicking on "Docker" in the navigation menu
3. Click on "Add Configuration"
4. Fill in the following details:
   - **Name**: WordPress
   - **Source URL**: URL to the raw wordpress-compose.yml file
   - **Description**: WordPress with MySQL database

### 2. Run the Containers

1. After adding the configuration, click on "View" to see the configuration details
2. Click on "Pull Images" to download the required Docker images
3. Once the images are pulled, click on "Run Compose" to start the containers

### 3. Access WordPress

1. Once the containers are running, WordPress will be accessible at:
   - http://[your-device-ip]:8080
   - If you're accessing it directly on the device running MiniMan: http://localhost:8080

2. You'll be presented with the WordPress setup page on first access
3. Follow the WordPress setup wizard to complete the installation

## Configuration Notes

### Default Credentials

The Docker Compose file includes the following default credentials:

- **Database Name**: wordpress
- **Database User**: wordpress
- **Database Password**: wordpress_password
- **Database Root Password**: wordpress_root_password

**Important**: For production use, you should change these default passwords.

### Customization

You can customize this configuration by:

1. Changing the port mapping (currently set to 8080:80)
2. Modifying database credentials
3. Adding additional WordPress plugins or themes through volumes

## Troubleshooting

If you encounter issues:

1. Check the container logs through the MiniMan interface
2. Verify that port 8080 is not being used by another service
3. Ensure Docker and Docker Compose are properly installed

## Updates

When new versions of WordPress or MySQL are released, you can:

1. Go to the configuration view in MiniMan
2. Click "Check for Updates" to see if updates are available
3. Click "Update Configuration" if updates are found
4. Restart the containers to apply the updates