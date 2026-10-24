import sqlite3
from flask import render_template 
from datetime import datetime, time
from extensions import cache 
from zoneinfo import ZoneInfo

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

    # convert last_refreshed_time to datetime object
    last_refreshed_time_object = datetime.strptime(last_refreshed_time, "%Y-%m-%d %H:%M:%S")
    # Output: 2026-10-23 15:45:30

    last_refreshed_hour = last_refreshed_time_object.hour # hour of last refresh time  
    last_refreshed_date = last_refreshed_time_object.date() # date of last refresh time
    todays_date = now_pst.date # todays date                                          # day of last refresh day

    # if statement to check is it monday at 9 PM, and that we haven't already checked at 9 PM window today
    # last_refresh_day is not 
    if current_day == 'Monday' and current_hour == 21 and current_hour != last_refreshed_hour and todays_date != last_refreshed_date:
        return True

    return False
