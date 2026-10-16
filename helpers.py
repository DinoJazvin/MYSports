import sqlite3
from flask import render_template 

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
