#!/usr/bin/env python3
import os
from app import create_app, db
from app.models.user import User
from app.models.network import NetworkInterface
from app.models.docker import DockerComposeConfig, DockerContainer, DockerImage, DockerVolume, DockerNetwork

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.shell_context_processor
def make_shell_context():
    """
    Add database and models to shell context for easy access in shell
    """
    return dict(db=db, User=User, NetworkInterface=NetworkInterface,
                DockerComposeConfig=DockerComposeConfig, DockerContainer=DockerContainer,
                DockerImage=DockerImage, DockerVolume=DockerVolume, DockerNetwork=DockerNetwork)

def initialize_database(config_name=None):
    """
    Helper function to initialize database tables and create admin user if needed

    Args:
        config_name (str): Configuration name to use, or None for current context
    """
    if config_name:
        app_instance = create_app(config_name)
        context_message = f"{config_name} database"
        with app_instance.app_context():
            _initialize_db_tables(context_message)
    else:
        _initialize_db_tables("default database")

def _initialize_db_tables(context_message):
    """
    Create database tables and admin user

    Args:
        context_message (str): Message to display for context
    """
    # Create all tables
    db.create_all()

    # Explicitly create Docker tables to ensure they exist
    DockerComposeConfig.__table__.create(db.engine, checkfirst=True)
    DockerContainer.__table__.create(db.engine, checkfirst=True)
    DockerImage.__table__.create(db.engine, checkfirst=True)
    DockerVolume.__table__.create(db.engine, checkfirst=True)
    DockerNetwork.__table__.create(db.engine, checkfirst=True)

    # Check if admin user exists
    if User.query.filter_by(username='admin').first() is None:
        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            password='admin',
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print(f'Admin user created in {context_message}.')
    else:
        print(f'Admin user already exists in {context_message}.')

@app.cli.command("init-db")
def init_db():
    """
    Initialize the database with tables and initial data
    """
    # Initialize current database
    initialize_database()

    # Initialize other database (development if in production, production if in development)
    other_config = 'development' if os.getenv('FLASK_CONFIG') != 'development' else 'production'
    initialize_database(other_config)

    print('Database initialization complete.')

@app.cli.command("create-user")
def create_user():
    """
    Create a new user interactively
    """
    import getpass

    username = input("Username: ")
    email = input("Email: ")
    password = getpass.getpass("Password: ")
    is_admin = input("Admin (y/n): ").lower() == 'y'

    # Check if user exists
    if User.query.filter_by(username=username).first() is not None:
        print(f"User '{username}' already exists.")
        return

    if User.query.filter_by(email=email).first() is not None:
        print(f"Email '{email}' already in use.")
        return

    # Create user
    user = User(
        username=username,
        email=email,
        password=password,
        is_admin=is_admin
    )
    db.session.add(user)
    db.session.commit()
    print(f"User '{username}' created successfully.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)