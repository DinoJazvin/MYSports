import sqlite3, requests
from flask import render_template, abort
from datetime import datetime, time
from extensions import cache 
from zoneinfo import ZoneInfo
import json

# This is the only "boilerplate" we need. It just opens the file.
def query_db(query, args=()):
    # Connect to the exact file you created in the CLI
    conn = sqlite3.connect('database.db')
    # conn.row_factory = sqlite3.Row
    conn.row_factory = dict_factory
    
    cursor = conn.execute(query, args)
    rows = cursor.fetchall()
    
    conn.commit() # Saves changes if you do an INSERT/UPDATE
    conn.close()
    return rows

def dict_factory(cursor, row):
    """Converts SQLite row data into a standard Python dictionary."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

# Use it like this:
# db.row_factory = dict_factory


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def should_cache_refresh():

    ''' Return true if its monday at 9 PM AND the most recent refresh is NOT today during the 9 PM hour '''

    # get current time
    now_pst = datetime.now(ZoneInfo('America/Los_Angeles'))

    # convert/parse string format -> 
    current_day = now_pst.strftime("%A") # get current day 'Monday'
    current_hour = now_pst.hour # get current hour (0 - 23)

    # retrieve last_refreshed_time from cache
    last_refreshed_time = cache.get('last_refreshed_time')

    if not last_refreshed_time:
        return True
    # convert last_refreshed_time to datetime object
    last_refreshed_time_object = datetime.strptime(last_refreshed_time, "%Y-%m-%d %H:%M:%S")
    # Output: 2026-10-23 15:45:30

    last_refreshed_hour = last_refreshed_time_object.hour # hour of last refresh time  
    last_refreshed_date = last_refreshed_time_object.date() # date of last refresh time
    todays_date = now_pst.date # todays date                                          # day of last refresh day

    # if statement to check is it monday at 9 PM, and that we haven't already checked at 9 PM window today
    # last_refresh_day is not 

    # checking if its 9 PM on mon, wed, or sun, or if 2 or 5 pm on sunday (post regular games)
    is_time_right = (current_day in ['Monday', 'Thursday', 'Sunday'] and current_hour == 21) or (current_day == 'Sunday' and current_hour in [14, 17])

    # checking if we've haven't already refresh today
    is_not_already_done_today = current_hour != last_refreshed_hour or todays_date != last_refreshed_date

    if is_time_right and is_not_already_done_today:
        return True

    return False

def get_current_week():

    try:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard", timeout=5)
        response.raise_for_status()
        week_data = response.json()
        return week_data['week']['number']
    
    except requests.exceptions.RequestException as e:
        print(f"API error occured: {e}")
        return abort(502, description="Failed to fetch current week.")


def get_timeout_time():

    # if sunday between 10 AM - 9 PM set timeout to 10 min.
    # get current time
    now_pst = datetime.now(ZoneInfo('America/Los_Angeles'))

    # convert/parse string format 
    current_day = now_pst.strftime("%A") # get current day 'Monday'
    current_hour = now_pst.hour # get current hour (0 - 23)

    if current_day == 'Sunday' and (current_hour >= 10 and current_hour <= 21):
        return 600
    
    # if monday or thursday between 5 PM and 9 PM, set timeout to 10 min.
    if current_day in ['Monday', 'Thursday'] and (current_hour >= 17 and current_hour <= 21):
        return 600

    # otherwise, no need to refresh otherwise, 12 hrs by for now
    return 43200

def get_all_teams():

    # sql query to retreive all nfl teams
    all_teams_data = query_db('SELECT name FROM teams')
    return all_teams_data

def get_team_abv(user_id):

    # make SQL query to retreive array team abv objects
    team_abvs = query_db('SELECT abbreviation FROM (SELECT * FROM teams JOIN user_teams ON teams.id = user_teams.team_id) WHERE user_id = (?)', (user_id,))
    # print(team_abvs)

    # return abv
    return team_abvs

def add_teamdata_cache(abv):

    # 1. Check if data already in db
    cached_data = cache.get(abv)
    
    # If cache indeed hits, return data
    if cached_data:
        print("--- REDIS CACHE HIT: Fetching fresh Scores data Redis cache ---")
        abv_data = json.loads(cached_data)
        return abv_data
    
    # IF CACHE MISS (or expired): hit the API
    print("--- REDIS CACHE MISS: Fetching fresh Scores data from ESPN API ---")
    try:

        response = requests.get(f"http://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{abv}", timeout=5)
        response.raise_for_status()
        team_data = response.json()
        
        # Save response to redis using 'setex' and turn dictionary into string using json.dumps(), 
        # Change to shorter timeout later
        cache.setex(abv, 43200, json.dumps(team_data)) 

        return team_data

    except requests.exceptions.RequestException as e:
        print(f"API error occured: {e}")
        return abort(502, description="Failed to fetch team data.")