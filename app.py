#!/usr/bin/env python3
"""Flask AI Agent Marketplace Application."""

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from supabase import create_client, Client
import json

# Import services from the backend_examples
from backend_examples.python.services.agents import agent_service
from backend_examples.python.services.creators import creator_service
from backend_examples.python.models import SearchFilters
import asyncio

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth'

class User:
    def __init__(self, user_id, email=None):
        self.id = user_id
        self.email = email
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Routes
@app.route('/')
def homepage():
    """Homepage with hero section and featured agents."""
    return render_template('homepage.html')

@app.route('/explore')
def explore():
    """Explore agents with search and filters."""
    # Get filter parameters from URL
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    model = request.args.get('model', '')
    status = request.args.get('status', '')
    sort_by = request.args.get('sort_by', 'created_at')
    modalities = request.args.getlist('modalities')
    capabilities = request.args.getlist('capabilities')
    
    # Create filters object
    filters = SearchFilters(
        search=search,
        category=category,
        model=model,
        status=status,
        sort_by=sort_by,
        modalities=modalities,
        capabilities=capabilities
    )
    
    try:
        agents = agent_service.fetch_agents(filters)
    except Exception as e:
        flash(f'Error fetching agents: {str(e)}', 'error')
        agents = []
    
    return render_template('explore.html', 
                         agents=agents, 
                         filters=filters,
                         search=search,
                         category=category,
                         model=model,
                         sort_by=sort_by)

@app.route('/agent/<agent_id>')
def agent_detail(agent_id):
    """Agent detail page."""
    try:
        agent = agent_service.get_agent_by_id(agent_id)
        if not agent:
            flash('Agent not found', 'error')
            return redirect(url_for('explore'))
    except Exception as e:
        flash(f'Error fetching agent: {str(e)}', 'error')
        return redirect(url_for('explore'))
    
    return render_template('agent_detail.html', agent=agent)

@app.route('/creators')
def creators():
    """Creators page with leaderboard."""
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'reputation')
    
    try:
        all_creators = creator_service.fetch_creators()
        filtered_creators = creator_service.filter_and_sort_creators(all_creators, search, sort_by)
    except Exception as e:
        flash(f'Error fetching creators: {str(e)}', 'error')
        filtered_creators = []
    
    return render_template('creators.html', 
                         creators=filtered_creators,
                         search=search,
                         sort_by=sort_by)

@app.route('/submit')
@login_required
def creator_studio():
    """Creator studio for submitting agents."""
    return render_template('creator_studio.html')

@app.route('/submit', methods=['POST'])
@login_required
def submit_agent():
    """Handle agent submission."""
    try:
        # agent_data = {
        #     'name': request.form.get('name'),
        #     'description': request.form.get('description'),
        #     'category': request.form.get('category'),
        #     'model': request.form.get('model'),
        #     'tags': request.form.get('tags', '').split(',') if request.form.get('tags') else [],
        #     'github_url': request.form.get('github_url'),
        #     'dockerfile_url': request.form.get('dockerfile_url'),
        #     'status': 'pending',
        #     'created_at': datetime.utcnow(),
        #     'updated_at': datetime.utcnow()
        # }
        header_keys = request.form.getlist('header_keys[]')
        header_values = request.form.getlist('header_values[]')
        headers = {}
        for key, value in zip(header_keys, header_values):
            if key and value:  # Only add non-empty headers
                headers[key] = value
        
        # Process authentication
        auth_keys = request.form.getlist('auth_keys[]')
        auth_values = request.form.getlist('auth_values[]')
        authentication = {}
        for key, value in zip(auth_keys, auth_values):
            if key and value:  # Only add non-empty auth fields
                authentication[key] = value
        
        agent_data = {
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'category': request.form.get('category'),
            'base_url': request.form.get('base_url'),
            'headers': headers,
            'content_type': request.form.get('content_type'),
            'authentication': authentication,
            'data_format': request.form.get('data_format'),
            'data_structure': request.form.get('data_structure'),
            'tags': [tag.strip() for tag in request.form.get('tags', '').split(',')] if request.form.get('tags') else [],
            'status': 'pending',
            # 'created_at': datetime.utcnow(),
            # 'updated_at': datetime.utcnow()
        }
    
        print("Submitting agent data:", agent_data)

        print("Current user ID:", current_user)
        agent = asyncio.run(agent_service.create_agent(agent_data, current_user.id))
        
        print("Created agent:", agent)

        if agent:
            flash('Agent submitted successfully and is pending review!', 'success')
        else:
            flash('Failed to submit agent. Please try again.', 'error')
            
    except Exception as e:
        flash(f'Error submitting agent: {str(e)}', 'error')
    
    return redirect(url_for('creator_studio'))

@app.route('/auth')
def auth():
    """Authentication page."""
    if current_user.is_authenticated:
        return redirect(url_for('homepage'))
    return render_template('auth.html')




def _clean_email(v: str) -> str:
    return (v or "").strip().lower()

@app.route('/login', methods=['POST'])
def login():
    print("Supabase URL:", SUPABASE_URL)
    print("Supabase client:", supabase)
    email = _clean_email(request.form.get('email'))
    password = request.form.get('password') or ""

    if not email or not password:
        flash('Please fill in both email and password.', 'error')
        return redirect(url_for('auth'))

    try:
        auth = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if not auth.user or not auth.session:
            # This usually means email not confirmed or bad credentials
            flash('Invalid credentials or email not confirmed.', 'error')
            return redirect(url_for('auth'))

        # Persist tokens if you need to call Supabase on behalf of the user later
        session['sb_access_token'] = auth.session.access_token
        session['sb_refresh_token'] = auth.session.refresh_token

        user = User(user_id=auth.user.id, email=email)
        login_user(user)

        flash('Logged in successfully!', 'success')
        next_url = request.args.get('next') or url_for('homepage')
        return redirect(next_url)

    except Exception as e:
        # Optional: log e
        flash('Login failed. Please check your credentials.', 'error')
        return redirect(url_for('auth'))

@app.route('/register', methods=['POST'])
def register():
    email = _clean_email(request.form.get('email'))
    password = request.form.get('password') or ""
    confirm_password = request.form.get('confirm_password') or ""

    if not email or not password:
        flash('Please fill in all fields.', 'error')
        return redirect(url_for('auth'))
    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('auth'))
    if len(password) < 8:
        flash('Password must be at least 8 characters.', 'error')
        return redirect(url_for('auth'))

    try:
        # If your project requires email confirmation, this returns a user and sends a confirmation email
        auth = supabase.auth.sign_up({
            "email": email,
            "password": password,
            # After email confirmation, Supabase can redirect back here if you want:
            "options": {"email_redirect_to": url_for('auth', _external=True)}
        })

        if auth.user and not auth.session:
            # Email confirmation required; user must verify before they can sign in
            flash('Account created! Please check your email to confirm your address.', 'success')
            return redirect(url_for('auth'))

        # If email confirmation is disabled, you may get a session directly:
        if auth.user and auth.session:
            session['sb_access_token'] = auth.session.access_token
            session['sb_refresh_token'] = auth.session.refresh_token
            user = User(user_id=auth.user.id, email=email)
            login_user(user)
            flash('Account created successfully!', 'success')
            return redirect(url_for('homepage'))

        flash('Registration failed. Try a different email.', 'error')
        return redirect(url_for('auth'))

    except Exception as e:
        # Common: "User already registered"
        msg = str(e)
        if 'User already registered' in msg or 'already registered' in msg:
            flash('That email is already registered. Try logging in.', 'error')
        else:
            flash('Registration failed. Please try again.', 'error')
        return redirect(url_for('auth'))

@app.route('/logout', methods=['GET','POST'])
@login_required
def logout():
    try:
        # Optional: sign out from Supabase (mainly relevant if you’re using refresh token rotation)
        if session.get('sb_access_token'):
            supabase.auth.sign_out()
    except Exception:
        pass
    session.pop('sb_access_token', None)
    session.pop('sb_refresh_token', None)
    logout_user()
    flash('Logged out.', 'success')
    return redirect(url_for('auth'))


@app.route('/trending')
def trending():
    """Trending agents - redirect to explore with trending sort."""
    return redirect(url_for('explore', sort_by='popular'))

@app.route('/categories')
def categories():
    """Categories - redirect to explore."""
    return redirect(url_for('explore'))

# API endpoints for AJAX requests
@app.route('/api/agents')
def api_agents():
    """API endpoint for fetching agents."""
    # Get filter parameters
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    model = request.args.get('model', '')
    status = request.args.get('status', '')
    sort_by = request.args.get('sort_by', 'created_at')
    modalities = request.args.getlist('modalities')
    capabilities = request.args.getlist('capabilities')
    
    filters = SearchFilters(
        search=search,
        category=category,
        model=model,
        status=status,
        sort_by=sort_by,
        modalities=modalities,
        capabilities=capabilities
    )
    
    try:
        agents = agent_service.fetch_agents(filters)
        return jsonify([agent.dict() for agent in agents])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/creators')
def api_creators():
    """API endpoint for fetching creators."""
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'reputation')
    
    try:
        all_creators = creator_service.fetch_creators()
        filtered_creators = creator_service.filter_and_sort_creators(all_creators, search, sort_by)
        return jsonify([creator.dict() for creator in filtered_creators])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """404 error handler."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """500 error handler."""
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)