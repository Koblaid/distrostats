import csv
from datetime import datetime

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


def get_table_data():
    cur = g.db.execute('''
    SELECT s.snapshot_time, d.name, r.name, a.name, sf.number_of_packages, sf.number_of_maintainers, sf.filesize, sf.filepath
    FROM snapshot s
        LEFT JOIN distribution d     ON sf.distribution_id = d.id
        LEFT JOIN pkg_repository r   ON sf.pkg_repository_id = r.id
        LEFT JOIN architecture a     ON sf.architecture_id = a.id
        LEFT JOIN snapshot_file sf   ON sf.snapshot_id = s.id
    WHERE
        a.name in ('i386', 'amd64')
        AND d.name in ('stable', 'testing')
        AND r.name = 'main'
    ORDER BY s.snapshot_time, d.name''')
    res = cur.fetchall()
    cols = 'snapshot_time distribution repository architecture number_of_packages number_of_maintainers filesize filepath'.split()

    data = []
    for row in res:
        d = dict(zip(cols, row))
        d['snapshot_time'] = d['snapshot_time'][:10]
        data.append(d)
    return data


@app.route('/json')
def json():
    sorted_data = {
        'stable': {
            'i386': {
                'pkg': [],
                'maintainer': [],
            },
            'amd64': {
                'pkg': [],
                'maintainer': [],
            },
        },
        'testing': {
            'i386': {
                'pkg': [],
                'maintainer': [],
            },
            'amd64': {
                'pkg': [],
                'maintainer': [],
            },
        }
    }

    data = get_table_data()
    for row in data:
        if not row['filepath']:
            continue
        ts = int(datetime.strptime(row['snapshot_time'], '%Y-%m-%d').strftime('%s'))*1000
        sorted_data[row['distribution']][row['architecture']]['pkg'].append((ts, row['number_of_packages']))
        sorted_data[row['distribution']][row['architecture']]['maintainer'].append((ts, row['number_of_maintainers']))

    out = [{
        'index': 0,
        'name': 'stable i386 pkg',
        'data': sorted_data['stable']['i386']['pkg'],
    }, {
        'index': 1,
        'name': 'stable amd64 pkg',
        'data': sorted_data['stable']['amd64']['pkg'],
    }, {
        'index': 2,
        'name': 'testing i386 pkg',
        'data': sorted_data['testing']['i386']['pkg']
    }, {
        'index': 3,
        'name': 'testing amd64 pkg',
        'data': sorted_data['testing']['amd64']['pkg']
    },{
        'index': 4,
        'name': 'stable i386 maintainer',
        'data': sorted_data['stable']['i386']['maintainer'],
    }, {
        'index': 5,
        'name': 'stable amd64 maintainer',
        'data': sorted_data['stable']['amd64']['maintainer'],
    }, {
        'index': 6,
        'name': 'testing i386 maintainer',
        'data': sorted_data['testing']['i386']['maintainer']
    }, {
        'index': 7,
        'name': 'testing amd64 maintainer',
        'data': sorted_data['testing']['amd64']['maintainer']
    }]
    return jsonify({'chart_data': out})


@app.route('/')
def index():
    data = get_table_data()
    total_filesize = sum((row['filesize'] for row in data if row['filepath']))
    number_of_files = len([row['filepath'] for row in data if row['filepath']])
    for row in data:
        if row['filepath']:
            row['filesize'] = '{:,}'.format(row['filesize'])
        else:
            row['filesize'] = ''
    return render_template('chart.html', table=data, number_of_files=number_of_files, total_filesize='{:,}'.format(total_filesize))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
