#!/usr/bin/env python3
"""Flask AI Agent Marketplace Application."""

import os
import sys
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from supabase import create_client, Client
import json

# Ensure backend_examples can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import services from the backend_examples
from backend_examples.python.services.agents import agent_service
from backend_examples.python.services.creators import creator_service
from backend_examples.python.models import SearchFilters
from dotenv import load_dotenv
import asyncio

load_dotenv()

app = Flask(__name__, template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '../templates')))
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_backend: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth'

class User:
    def __init__(self, user_id=None, email=None):
        self.id = user_id
        self.email = email

    @property
    def is_authenticated(self):
        return self.id is not None

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return self.id is None

    def get_id(self):
        return str(self.id) if self.id else None


@login_manager.user_loader
def load_user(user_id):
    if not user_id:
        return None
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
    print("Filters applied:", filters)
    try:
        agents = asyncio.run(agent_service.fetch_agents(filters))
        print("Fetched agents:", agents)
    except Exception as e:
        flash(f'Error fetching agents: {str(e)}', 'error')
        agents = []
    
    return render_template('explore.html', 
                        agents=agents, 
                        filters=filters,
                        search=search,
                        category=category,
                        #  model=model,
                        sort_by=sort_by)

@app.route('/agent/<agent_id>')
def agent_detail(agent_id):
    """Agent detail page."""
    try:
        # agent = agent_service.get_agent_by_id(agent_id)
        agent = asyncio.run(agent_service.get_agent_by_id(agent_id))
        print("Fetched agent:", agent)
        if not agent:
            flash('Agent not found', 'error')
            return redirect(url_for('explore'))
    except Exception as e:
        flash(f'Error fetching agent: {str(e)}', 'error')
        return redirect(url_for('explore'))
    
    return render_template('agent_detail.html', agent=agent)

@app.route('/creators')
def creators():
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'reputation')
    try:
        # If fetch_creators is async, run it and get the list
        all_creators = asyncio.run(creator_service.fetch_creators())
        # If filter_and_sort_creators is async, run it too
        if asyncio.iscoroutinefunction(creator_service.filter_and_sort_creators):
            filtered_creators = asyncio.run(creator_service.filter_and_sort_creators(all_creators, search, sort_by))
        else:
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

@app.route('/dashboardk927498238409283490283409283409283094')
@login_required
def dashboard():
    return render_template('dashboard.html')


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
    
@app.route("/login/google")
def login_google():
    redirect_url = url_for("auth_callback", _external=True)
    oauth_url = f"{SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to={redirect_url}"
    return redirect(oauth_url)

@app.route("/auth/callback", methods=["GET", "POST"])
def auth_callback():
    # --- GET request: serve HTML with JS to extract tokens ---
    if request.method == "GET":
        return render_template("auth_callback.html")  # your JS in this page will POST the tokens

    # --- POST request: handle token sent from frontend ---
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not data:
            return {"error": "Expected JSON body"}, 400

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")

        if not access_token:
            return {"error": "Missing access_token"}, 400

        try:
            # --- Validate token with Supabase ---
            user_resp = supabase.auth.get_user(access_token)
            if not user_resp or not user_resp.user:
                return {"error": "Invalid token"}, 401

            user = user_resp.user

            # --- Save tokens in server-side session ---
            session["sb_access_token"] = access_token
            session["sb_refresh_token"] = refresh_token
            session["user_email"] = user.email

            # --- Ensure profile exists in 'profiles' table ---
            try:
                existing_profile = supabase.table("profiles").select("id").eq("id", user.id).execute()
                if not existing_profile.data:
                    profile_data = {
                        "id": user.id,  # same UUID as auth.users
                        "username": user.email.split("@")[0],  # default username
                        "full_name": user.user_metadata.get("full_name") or user.email,
                        "user_role": "user",  # default role
                        "primary_interest": None,
                        "portfolio_url": None,
                        "expertise": None
                    }
                    # Use service role key to bypass RLS, and handle duplicates gracefully
                    supabase_backend.table("profiles").upsert(profile_data, on_conflict="id").execute()
            except Exception as e:
                print("Error syncing profile:", e)

            # --- Log in the user with Flask-Login ---
            user_obj = User(user_id=user.id, email=user.email)
            login_user(user_obj)

            return {"message": "Logged in successfully"}

        except Exception as e:
            print("Error during Google login:", e)
            return {"error": "Login failed"}, 500

@app.route("/login/github")
def login_github():
    redirect_url = url_for("github_callback", _external=True)
    oauth_url = f"{SUPABASE_URL}/auth/v1/authorize?provider=github&redirect_to={redirect_url}"
    return redirect(oauth_url)

@app.route("/auth/github/callback")
def github_callback():
    # Supabase will redirect with #access_token in URL fragment
    return render_template("oauth_redirect.html")

@app.route("/auth/github/verify", methods=["POST"])
def github_verify():
    print("Verifying GitHub login...")
    data = request.get_json()
    access_token = data.get("access_token")
    print("Received GitHub access token:", access_token)
    if not access_token:
        return jsonify({"error": "Missing access token"}), 400

    try:
        user_info = supabase_backend.auth.get_user(access_token)
        github_user = user_info.data.user
        github_email = github_user.email
        github_profile_url = github_user.user_metadata.get("html_url", "")

        if not github_email:
            return jsonify({"error": "GitHub account has no email"}), 400

        # same insert/update logic ...
        profile_id = str(uuid.uuid4())
        # ...

        login_user(User(profile_id))
        return jsonify({"success": True, "redirect": url_for("homepage")})

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# You might have a helper for this already, if not, it's good practice
def _clean_email(email):
    return (email or "").lower().strip()

@app.route('/register', methods=['POST'])
def register():
    # --- 1. Get all form data ---
    email = _clean_email(request.form.get('email'))
    password = request.form.get('password') or ""
    confirm_password = request.form.get('confirm_password') or ""
    full_name = request.form.get('full_name') or ""
    username = request.form.get('username') or ""
    user_role = request.form.get('user_role') or ""
    
    # Role-specific fields
    portfolio_url = request.form.get('portfolio_url')
    expertise = request.form.get('expertise')
    primary_interest = request.form.get('primary_interest')

    # --- 2. Perform validation ---
    if not all([email, password, full_name, username, user_role]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('auth'))
    
    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('auth'))
    
    if len(password) < 8:
        flash('Password must be at least 8 characters long.', 'error')
        return redirect(url_for('auth'))

    # --- 3. Check for unique username before trying to create the user ---
    try:
        # Query your 'profiles' table to see if the username exists
        existing_user = supabase.table('profiles').select('id').eq('username', username).execute()
        if existing_user.data:
            flash('That username is already taken. Please choose another.', 'error')
            return redirect(url_for('auth'))
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('auth'))

    # --- 4. Attempt to sign up the user with Supabase Auth ---
    try:
        auth = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"email_redirect_to": url_for('auth', _external=True)}
        })

        if auth.user and not auth.user.identities:
            flash("That email is already registered. Try logging in.", "error")
            return redirect(url_for("auth"))

        # --- 5. If user auth is created, insert data into the profiles table ---
        if auth.user:
            profile_data = {
                'id': auth.user.id,  # Link to the auth.users table
                'username': username,
                'full_name': full_name,
                'user_role': user_role,
                'portfolio_url': portfolio_url if user_role == 'creator' else None,
                'expertise': expertise if user_role == 'creator' else None,
                'primary_interest': primary_interest if user_role == 'user' else None,
            }
            # Insert the new profile. Use a try-except block for safety.
            try:
                supabase.table('profiles').insert(profile_data).execute()
            except Exception as e:
                # This is a critical error. The auth user was created, but the profile failed.
                # You should log this error for manual review.
                # For the user, a generic error is okay for now.
                print(f"CRITICAL: Failed to create profile for user {auth.user.id}. Error: {e}")
                flash('Registration failed at the final step. Please contact support.', 'error')
                return redirect(url_for('auth'))


        # --- Handle session based on email confirmation settings ---
        if not auth.session: # Email confirmation required
            flash('Account created! Please check your email to confirm your address.', 'success')
            return redirect(url_for('auth'))
        
        if auth.session: # Email confirmation is disabled, user logged in directly
            session['sb_access_token'] = auth.session.access_token
            session['sb_refresh_token'] = auth.session.refresh_token
            # Your User model might need to be updated to load profile data
            user = User(user_id=auth.user.id, email=email) 
            login_user(user)
            flash('Account created successfully!', 'success')
            return redirect(url_for('homepage'))

        flash('An unknown error occurred during registration.', 'error')
        return redirect(url_for('auth'))

    except Exception as e:
        msg = str(e)
        if 'User already registered' in msg:
            flash('That email is already registered. Try logging in.', 'error')
        else:
            flash(f'Registration failed: {msg}', 'error')
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
    session.clear()
    return redirect(url_for('auth'))



from uuid import UUID

@app.route('/profile')
@login_required
def my_profile():
    """
    Displays the profile page for the currently logged-in user.
    Redirects to their public username-based URL.
    """
    try:
        # Ensure the ID is a proper UUID string
        user_id = str(UUID(str(current_user.id)))
        print("Current user ID:", user_id)

        # Supabase query
        user_profile_res = (
            supabase.table('profiles')
            .select('username')
            .eq('id', user_id)
            .execute()
        )


        print("User profile response:", user_profile_res.data)

        all_profiles_res = supabase.table('profiles').select('*').execute()
        print("All profiles:", all_profiles_res.data)

        if user_profile_res.data and len(user_profile_res.data) > 0:
            username = user_profile_res.data[0]['username']
            return redirect(url_for('view_profile', username=username))
        else:
            flash("Your profile has not been set up yet. Please contact support or re-register.", "error")
            return redirect(url_for('homepage'))

    except Exception as e:
        flash(f"An error occurred while fetching your profile: {e}", "error")
        return redirect(url_for('homepage'))





@app.route('/profile/<username>')
def view_profile(username):
    """
    Displays a user's public profile page, identified by their username.
    """
    try:
        # Fetch the profile data from Supabase using the username
        # REMOVED .single() to prevent a similar potential error
        profile_res = supabase.table('profiles').select('*').eq('username', username).execute()

        # If the data list is empty, the user does not exist
        if not profile_res.data:
            abort(404) # Renders a "Not Found" page

        # Since we are no longer using .single(), the result is a list. Get the first item.
        profile_data = profile_res.data[0]
        
        # Determine if the person viewing the page is the owner of the profile
        is_own_profile = False
        if current_user.is_authenticated and current_user.id == profile_data['id']:
            is_own_profile = True

        return render_template('profile.html', profile=profile_data, is_own_profile=is_own_profile)

    except Exception as e:
        flash(f"An error occurred while fetching the profile: {e}", "error")
        return redirect(url_for('homepage'))

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Allow the current user to edit their profile information.
    """
    # First, get the user's current profile data to populate the form
    try:
        profile_res = supabase.table('profiles').select('*').eq('id', current_user.id).execute()
        if not profile_res.data:
            flash("Your profile could not be found. Cannot edit.", "error")
            return redirect(url_for('homepage'))
        
        current_profile = profile_res.data[0]
    except Exception as e:
        flash(f"An error occurred while fetching your profile: {e}", "error")
        return redirect(url_for('homepage'))

    if request.method == 'POST':
        # Handle the form submission
        full_name = request.form.get('full_name') or ""
        username = request.form.get('username') or ""
        portfolio_url = request.form.get('portfolio_url')
        expertise = request.form.get('expertise')
        primary_interest = request.form.get('primary_interest')
        
        # --- Validation ---
        if not full_name or not username:
            flash("Full Name and Username are required.", "error")
            return render_template('edit_profile.html', profile=current_profile)

        # --- Unique Username Check (if it was changed) ---
        if username != current_profile['username']:
            try:
                existing_user = supabase.table('profiles').select('id').eq('username', username).execute()
                if existing_user.data:
                    flash('That username is already taken. Please choose another.', 'error')
                    submitted_data = current_profile.copy()
                    submitted_data.update({
                        'full_name': full_name, 'username': username,
                        'portfolio_url': portfolio_url, 'expertise': expertise,
                        'primary_interest': primary_interest
                    })
                    return render_template('edit_profile.html', profile=submitted_data)
            except Exception as e:
                flash(f'An error occurred while checking the username: {e}', 'error')
                return render_template('edit_profile.html', profile=current_profile)
        
        # --- Prepare data for update ---
        update_data = {
            'full_name': full_name, 'username': username,
            'portfolio_url': portfolio_url if current_profile['user_role'] == 'creator' else None,
            'expertise': expertise if current_profile['user_role'] == 'creator' else None,
            'primary_interest': primary_interest if current_profile['user_role'] == 'user' else None,
        }

        # --- Execute Update ---
        try:
            supabase.table('profiles').update(update_data).eq('id', current_user.id).execute()
            flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('view_profile', username=username))
        except Exception as e:
            flash(f'An error occurred while updating your profile: {e}', 'error')
            return render_template('edit_profile.html', profile=current_profile)

    # --- For GET request, just show the form ---
    return render_template('edit_profile.html', profile=current_profile)

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
import re
import ast

def parse_to_dict(raw: str):
    # Regex to capture key=value pairs (value can be quoted or unquoted)
    pattern = re.compile(r"(\w+)=((?:'[^']*')|(?:\[[^\]]*\])|(?:\{[^}]*\})|(?:\S+))")
    result = {}

    for match in pattern.finditer(raw):
        key, value = match.groups()

        # Try to safely evaluate Python literals (lists, dicts, numbers, booleans, None, strings)
        try:
            result[key] = ast.literal_eval(value)
        except Exception:
            # If not a pure literal (like datetime(...), Creator(...)), keep as string
            result[key] = value

    return result
import requests
import html
from pydantic.json import pydantic_encoder
def run_agent(user_input, agent_data):
    """
    Runs an agent by sending a POST request to the agent's base_url with the input payload.
    agent_data is expected to be a dict with at least 'base_url'.
    """
    
    print("==== USER INPUT ==== for now:",user_input)
    # agent_data = agent_data.dict()
    print("==== AGENT DATA ==== for now:",agent_data)
    agent_data = parse_to_dict(html.unescape(agent_data))
    print("==== AGENT DATA ==== for now:",agent_data)
    if not agent_data or not isinstance(agent_data, dict):
        return "Invalid agent data. Must be a dict."

    url = agent_data.get("base_url")
    if not url:
        return "Agent base_url not found."

    # Build the command/payload
    command = {}
    if isinstance(user_input, dict):
        command.update(user_input)
    else:
        command["user_input"] = user_input

    try:
        response = requests.post(url, json=user_input['body'])
        response.raise_for_status()  # raise if not 2xx
        return f"Agent processed: {response.text}"
    except requests.RequestException as e:
        return f"Agent request failed: {str(e)}"
    except Exception as e:
        return f"Agent processing failed: {str(e)}"


@app.route("/run-agent", methods=["POST"])
def run_agent_route():
    data = request.get_json(force=True) or {}
    user_input = data.get("input")
    agent_data = data.get("agent")
    result = run_agent(user_input, agent_data)
    agent_data = parse_to_dict(html.unescape(agent_data))
    agent_id = agent_data.get("id")
    # Fetch the latest agent from DB
    agent = asyncio.run(agent_service.get_agent_by_id(agent_id))
    if agent:
        new_total_runs = (agent.total_runs or 0) + 1
        asyncio.run(agent_service.update_agent_field(agent_id, "total_runs", new_total_runs))
    else:
        new_total_runs = None
    return jsonify({"response": result, "total_runs": new_total_runs})

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


# Agent stats update endpoints
from flask import request, jsonify

@app.route('/agent/<agent_id>/upvote', methods=['POST'])
def agent_upvote(agent_id):
    agent = asyncio.run(agent_service.get_agent_by_id(agent_id))
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    new_upvotes = (agent.upvotes or 0) + 1
    asyncio.run(agent_service.update_agent_field(agent_id, 'upvotes', new_upvotes))
    return jsonify({'upvotes': new_upvotes})

@app.route('/agent/<agent_id>/rate', methods=['POST'])
def agent_rate(agent_id):
    agent = asyncio.run(agent_service.get_agent_by_id(agent_id))
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    rating = request.json.get('rating', 0)
    # For demo: just set avg_rating to new rating (implement real average logic as needed)
    asyncio.run(agent_service.update_agent_field(agent_id, 'avg_rating', rating))
    return jsonify({'avg_rating': rating})

@app.route('/agent/<agent_id>/version', methods=['POST'])
def agent_version(agent_id):
    agent = asyncio.run(agent_service.get_agent_by_id(agent_id))
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    version = request.json.get('version', '1.0.0')
    asyncio.run(agent_service.update_agent_field(agent_id, 'version', version))
    return jsonify({'version': version})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
