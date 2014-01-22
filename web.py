import csv

import sqlite3
from flask import Flask, request, render_template, g, jsonify

app = Flask(__name__)


db_filename = 'db.sqlite'

def connect_db():
    conn = sqlite3.connect(db_filename)
    curs = conn.execute('PRAGMA foreign_keys = ON')
    return conn


@app.before_request
def before_request():
    g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


@app.route('/json')
def json():
    cur = g.db.execute('''
    SELECT
        strftime('%s', snapshot_time), count(*)
    FROM
        snapshot_content sc
        JOIN snapshot s ON sc.snapshot_id = s.id
    GROUP BY snapshot_id
    ORDER BY s.snapshot_time''')
    data = [(int(unix_timestamp)*1000, count) for unix_timestamp, count in cur]
    return jsonify({'chart_data': data})


@app.route('/')
def index():
    return render_template('chart.html')


if __name__ == '__main__':
    app.run(debug=True)
