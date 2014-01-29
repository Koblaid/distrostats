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
        distribution_id, strftime('%s', snapshot_time), count(*)
    FROM
        snapshot_content sc
        JOIN snapshot s ON sc.snapshot_id = s.id
    GROUP BY distribution_id, snapshot_id
    ORDER BY s.snapshot_time''')
    stable = []
    testing = []
    for distribution_id, unix_timestamp, count in cur:
        ts = int(unix_timestamp)*1000
        point = (ts, count)
        if distribution_id == 1:
            stable.append(point)
        else:
            testing.append(point)

    data = [{
        'index': 0,
        'name': 'stable',
        'data': stable,
    }, {
        'index': 1,
        'name': 'testing',
        'data': testing
    }]
    return jsonify({'chart_data': data})


def get_table_data():
    cur = g.db.execute('''
    SELECT *
    FROM snapshot s
        JOIN snapshot_file sf ON sf.snapshot_id = s.id
    ORDER BY s.snapshot_time, sf.distribution''')
    res = cur.fetchall()
    cols = [d[0] for d in cur.description]
    data = []
    for row in res:
        d = dict(zip(cols, row))
        d['snapshot_time'] = d['snapshot_time'][:10]
        data.append(d)
    return data


@app.route('/')
def index():
    data = get_table_data()
    return render_template('chart.html', table=data)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
