from flask import Flask, redirect, render_template, request, session, flash, abort
from helpers import query_db, apology, should_cache_refresh, get_current_week, get_timeout_time, get_all_teams, get_team_abv, add_teamdata_cache
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from sqlite3 import IntegrityError
import os, requests, json
from dotenv import load_dotenv
from datetime import datetime, time
from zoneinfo import ZoneInfo
from extensions import cache

# import requests
# from models import db
STANDINGS_CACHE_TIMEOUT = 43200
load_dotenv()
API_KEY = os.environ.get('SPORTS_API_KEY')
app = Flask(__name__)


# Configure session to use filesystem (CS50 style)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/")
def hello_world():

    if session.get('user_id'):
        # need a query to grab abvs of persons favorite teams
        # first contruct an array of all of the ids of the users favorite teams.
        abv_array = get_team_abv(session['user_id'])

        # start w retreiving all nfl scores, and grab
        favorites_data = []
        for team in abv_array:

            team_data = add_teamdata_cache(team['abbreviation'])
            favorites_data.append(team_data)

        final_data = []
        # final_data['teamName'] = []
        # final_data['game_details'] = []
        # final_data['teamName'] = []
        # iterate over favorites_data and append to a final array only the data we want to send to front end
        for ele in favorites_data:
            temp = {}

            # print(ele['team']['nextEvent'][0]['competitions'][0]['competitors'][1]['team']['displayName'])
            # print(ele["team"]["logos"][0]["href"])

            try:
                temp['name'] = ele['team']['nextEvent'][0]['competitions'][0]['competitors'][1]['team']['displayName']
                # temp['record'] = ele["team"]["nextEvent"][0]["competitions"][0]["competitors"][0]["record"][0]["displayValue"]
                temp['record'] = ele["team"]["record"]["items"][0]["summary"]
                temp['logo'] = ele["team"]["logos"][0]["href"]

                final_data.append(temp)

            except (KeyError, IndexError, TypeError):
                # Skip this team entirely, or log a warning
                print(final_data)
                print("Skipping team due to missing data paths.")

    # return render_template("index.html", teams_data=teams_data, game_details=game_details)    
    # print(final_data)
        return render_template('index.html', final_data=final_data)
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

    # 2. Check if its time for a refresh, if so 
    time_for_refresh = should_cache_refresh()

    # 2. If cached data AND not time for a refresh, parse string back into python array format and serve it! json.loads means 'load string'
    if cached_data and not time_for_refresh:
        print("--- REDIS CACHE HIT: Serving lightning fast Standings data ---")
        standings_data = json.loads(cached_data)

        return render_template("standings.html", response=standings_data["response"])

    
    # 4. IF CACHE MISS (or expired): hit the API
    print("--- REDIS CACHE MISS: Fetching fresh Standings data from API-Sports ---")
    try:

        headers = {"x-apisports-key" : API_KEY}
        response = requests.get("https://v1.american-football.api-sports.io/standings?league=1&season=2024", headers=headers, timeout=5)
        response.raise_for_status()
        standings_data = response.json()

        # get current time, then convert time to string (redis expects string)
        pst_zone = ZoneInfo('America/Los_Angeles')
        now_pst = datetime.now(pst_zone)
        timestamp_string = now_pst.strftime("%Y-%m-%d %H:%M:%S")

        # Save standings data and time of last refresh to redis using 'setex'
        cache.setex("nfl_standings", STANDINGS_CACHE_TIMEOUT, json.dumps(standings_data)) 
        cache.setex("last_refreshed_time", STANDINGS_CACHE_TIMEOUT, timestamp_string) 

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
        print("--- REDIS CACHE HIT: Serving lightning fast Scores data ---")
        scores_data = json.loads(cached_data)
        return render_template("scores.html", scores_data=scores_data["events"])

    # 4. IF CACHE MISS (or expired): hit the API
    print("--- REDIS CACHE MISS: Fetching fresh Scores data from ESPN API ---")
    try:
        week = get_current_week()
        response = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}", timeout=5)
        response.raise_for_status()
        scores_data = response.json()
        
        # Save response to redis using 'setex' and turn dictionary into string using json.dumps()
        cache.setex("nfl_scores", get_timeout_time(), json.dumps(scores_data)) 

        return render_template("scores.html", scores_data=scores_data['events'])

    except requests.exceptions.RequestException as e:
        print(f"API error occured: {e}")
        return abort(502, description="Failed to fetch scores.")

@app.route('/favorites', methods=['GET', 'POST'])
def favorites():

    teams_data = get_all_teams()

    if request.method == 'POST':
    
        # retrieve 'selected_team' data from form
        selected_team = request.form.get('favorite-team')
        print(selected_team)

        # first get team_id doing Select team_id where team_name == 'selected_team'
        team_id = query_db('SELECT id FROM teams WHERE name = (?)', (selected_team,))
    
        if not team_id:
            return apology('Team name does not exist!', 400)
        
        # get user_id from sessions
        user_id = session['user_id']
        team_id = team_id[0]['id']

        # make query adding selected team to user_teams table, make sure entry doesn't already exist for user
        try:
            query_db('INSERT INTO user_teams (user_id, team_id) values (?, ?)', (user_id, team_id))
        except IntegrityError:
            return apology('Team already a favorite!', 400)

        # add this only after submitting form
        flash('Team successfully added to favorites!')

        # maybe redirect to homepage
        return redirect('/')

    return render_template('favorites.html', teams_data = teams_data)

@app.cli.command('seed-teams')
def test_teams():

    # clear table to start
    try:
        query_db('DELETE FROM teams')
    except IntegrityError:
        return apology('Unable to clear teams table!', 400)

    # Get teams data from ESPN web api and populate teams table
    try:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/football/nfl/teams", timeout=5)
        response.raise_for_status()
        scores_data = response.json()
        scores_data = scores_data['sports'][0]['leagues'][0]['teams']

        for ele in scores_data:
            try:
                query_db('INSERT INTO teams (id, name, abbreviation) values (?, ?, ?)', (ele['team']['id'], ele['team']['displayName'], ele['team']['abbreviation']))
            except IntegrityError:
                return apology('Unable to add team to table!', 400)

    except requests.exceptions.RequestException as e:
        print(f"API error occured: {e}")
        return abort(502, description="Failed to fetch scores.")
