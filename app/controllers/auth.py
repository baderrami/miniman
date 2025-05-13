from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from werkzeug.security import generate_password_hash
from functools import wraps

# Create blueprint
auth_bp = Blueprint('auth', __name__)

def admin_required(f):
    """Decorator for routes that require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('network.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.verify_password(password):
            login_user(user)
            next_page = request.args.get('next')
            if next_page is None or not next_page.startswith('/'):
                next_page = url_for('network.dashboard')
            return redirect(next_page)
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """Display user profile"""
    return render_template('profile.html')

@auth_bp.route('/users')
@login_required
@admin_required
def users():
    """List all users (admin only)"""
    users = User.query.all()
    return render_template('users.html', users=users)

@auth_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    """Add a new user (admin only)"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.add_user'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('auth.add_user'))

        # Create new user
        user = User(username=username, email=email, password=password, is_admin=is_admin)
        db.session.add(user)
        db.session.commit()

        flash('User created successfully.', 'success')
        return redirect(url_for('auth.users'))

    # Redirect to users page with the add user form
    return redirect(url_for('auth.users'))

@auth_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit a user (admin only)"""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form

        # Check if username is taken by another user
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user_id:
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.edit_user', user_id=user_id))

        # Check if email is taken by another user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user_id:
            flash('Email already exists.', 'danger')
            return redirect(url_for('auth.edit_user', user_id=user_id))

        # Update user
        user.username = username
        user.email = email
        if password:  # Only update password if provided
            user.password = password
        user.is_admin = is_admin

        db.session.commit()

        flash('User updated successfully.', 'success')
        return redirect(url_for('auth.users'))

    # For GET requests, redirect to users page
    # In a real application, you would render an edit form
    flash('Edit user functionality is not fully implemented.', 'warning')
    return redirect(url_for('auth.users'))

@auth_bp.route('/users/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    """Delete a user (admin only)"""
    user = User.query.get_or_404(id)

    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('auth.users'))

    db.session.delete(user)
    db.session.commit()

    flash('User deleted successfully.', 'success')
    return redirect(url_for('auth.users'))
