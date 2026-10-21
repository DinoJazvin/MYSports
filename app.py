from flask import Flask, redirect, render_template, request, session, flash, abort
from helpers import query_db, apology
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from sqlite3 import IntegrityError
import os, requests, redis, json
from dotenv import load_dotenv
# import requests
# from models import db

load_dotenv()
API_KEY = os.environ.get('SPORTS_API_KEY')
app = Flask(__name__)

cache = redis.Redis(host='localhost', port=6379, decode_responses=True)
CACHE_TIMEOUT = 43200 # 12 hours

# Configure session to use filesystem (CS50 style)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/")
def hello_world():
    return render_template('index.html')

@app.route("/register", methods=['GET', 'POST'])
def register():

    if request.method == "POST":
        # input validation
        if not request.form.get('username'):
            return apology('Must provide username', 400)

        if not request.form.get('password'):
            return apology('Must provide password', 400)

        if not request.form.get('confirmation') or request.form.get('confirmation') != request.form.get('password'):
            return apology('Passwords must match!', 400)

        # 1. add sql query to add row to users table
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            query_db('INSERT INTO users (user_name, hash) values (?, ?)', (username, generate_password_hash(password)))
        except IntegrityError:
            return apology('Username already exists!', 400)

         # 2. right before redirect, somehow send the 'user registered' message to '/'
        flash('Successfully registered!')

        return redirect("/")
    
    return render_template('register.html')


@app.route("/login", methods=['GET', 'POST'])
def login():

    # first logout any current user
    session.clear()

    if request.method == 'POST':
        # check input validation
        if not request.form.get('username'):
            return apology('please enter username', 400)

        if not request.form.get('password'):
            return apology('please enter password', 400)

        password = request.form.get('password')
        username = request.form.get('username')
        rows = query_db('SELECT * FROM users WHERE user_name = (?)', (username,))
       
        if len(rows) != 1 or not (check_password_hash(rows[0]['hash'], password)):
            return apology("invalid username and/or password", 400)
        
        session['user_id'] = rows[0]['id']
        
        return redirect('/')

    return render_template('login.html')

@app.route('/logout')
def logout():
    '''Log user out'''

    session.clear()

    return redirect('/')

@app.route('/standings')
def standings():

    # 1. Check if data already in db
    cached_data = cache.get("nfl_standings")

    # 2. If cache hit, parse string back into python array format and serve it! json.loads means 'load string'
    if cached_data:
        print("--- REDIS CACHE HIT: Serving lightning fast data ---")
        standings_data = json.loads(cached_data)
        return render_template("standings.html", response=standings_data["response"])

    
    # 4. IF CACHE MISS (or expired): hit the API
    print("--- REDIS CACHE MISS: Fetching fresh data from API-Sports ---")
    try:

        headers = {"x-apisports-key" : API_KEY}
        response = requests.get("https://v1.american-football.api-sports.io/standings?league=1&season=2024", headers=headers, timeout=5)
        response.raise_for_status()
        standings_data = response.json()

        # Save response to redis using 'setex' and turn dictionary into string using json.dumps()
        cache.setex("nfl_standings", CACHE_TIMEOUT, json.dumps(standings_data)) 

        return render_template("standings.html", response=standings_data["response"])

    except requests.exceptions.RequestException as e:
        print(f"API error occured: {e}")
        return abort(502, description="Failed to fetch live standings.")


@app.route('/scores')
def scores():

    # 1. Check if data already in db
    cached_data = cache.get("nfl_scores")

    # 2. If cache hit, parse string back into python array format and serve it! json.loads means 'load string'
    if cached_data:
        print("--- REDIS CACHE HIT: Serving lightning fast data ---")
        scores_data = json.loads(cached_data)
        return render_template("scores.html", response=scores_data["events"])

    # 4. IF CACHE MISS (or expired): hit the API
    print("--- REDIS CACHE MISS: Fetching fresh data from ESPN API ---")
    try:
        response = requests.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week=6", timeout=5)
        response.raise_for_status()
        scores_data = response.json()

        # Save response to redis using 'setex' and turn dictionary into string using json.dumps()
        cache.setex("nfl_scores", CACHE_TIMEOUT, json.dumps(scores_data)) 

        # print(scores_data['events'][0]['competitions'][0]['competitors'][0]['score'])
        # print(scores_data['events'][0]['competitions'][0]['competitors'][1]['score'])
        

        # return render_template("standings.html", scores_data=scores_data['events'])
        return render_template("scores.html")

    except requests.exceptions.RequestException as e:
        print(f"API error occured: {e}")
        return abort(502, description="Failed to fetch scores.")
