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

    # Get current time
    pst_zone = ZoneInfo("America/Los_Angeles")
    now_pst = datetime.now(pst_zone)

    # Grab time string from redis cache
    cached_time_string = cache.get('last_refreshed_time')

    # If no recent cached time, return false
    if cached_time_string is None:
        return True

    # convert the time from string -> datetime object so we can perform calculations on it
    last_refreshed = datetime.strptime(cached_time_string, "%Y-%m-%d %H:%M:%S")
    last_refreshed = last_refreshed.replace(tzinfo=pst_zone)

    # Conditonnal logic to verify if cache refresh is necessary
    current_day = now_pst.strftime('%A') # get current day
    current_hour = now_pst.hour          # get current hour

    # check if its monday @ 9 and we haven't already cached
    if current_day == 'Monday' and current_hour == 21:

        # Did we already refresh during the 9 PM block?
        if not (last_refreshed.hour == 21 and last_refreshed.date == now_pst.date):
            return True

    return False