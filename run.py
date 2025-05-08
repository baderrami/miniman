#!/usr/bin/env python3
import os
from app import create_app, db
from app.models.user import User
from app.models.network import NetworkInterface

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.shell_context_processor
def make_shell_context():
    """
    Add database and models to shell context for easy access in shell
    """
    return dict(db=db, User=User, NetworkInterface=NetworkInterface)

@app.cli.command("init-db")
def init_db():
    """
    Initialize the database with tables and initial data
    """
    db.create_all()
    
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
        print('Admin user created.')
    else:
        print('Admin user already exists.')
    
    print('Database initialized.')

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