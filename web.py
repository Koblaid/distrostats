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
    SELECT
        s.snapshot_time,
        d.name,
        r.name,
        a.name,
        sf.number_of_packages,
        sf.number_of_maintainers,
        sf.filesize,
        sf.filepath,
        sf.total_packed_size,
        sf.total_installed_size,
        sf.total_packed_size / (sf.total_installed_size * 1.0),
        sf.total_packed_size / (sf.number_of_packages * 1.0),
        sf.total_installed_size / (sf.number_of_packages * 1.0)
    FROM snapshot s
        LEFT JOIN distribution d     ON sf.distribution_id = d.id
        LEFT JOIN pkg_repository r   ON sf.pkg_repository_id = r.id
        LEFT JOIN architecture a     ON sf.architecture_id = a.id
        LEFT JOIN snapshot_file sf   ON sf.snapshot_id = s.id
    WHERE
        a.name in ('i386', 'amd64', 'kfreebsd-amd64')
        AND d.name in ('stable', 'testing')
        AND r.name = 'main'
    ORDER BY s.snapshot_time, d.name''')
    res = cur.fetchall()
    cols = 'snapshot_time distribution repository architecture number_of_packages number_of_maintainers filesize filepath total_packed_size total_installed_size avg_pack_ratio avg_packed_size avg_installed_size'.split()

    data = []
    for row in res:
        d = dict(zip(cols, row))
        d['snapshot_time'] = d['snapshot_time'][:10]
        data.append(d)
    return data


@app.route('/json')
def json():
    data = get_table_data()
    grouped_data = {}
    for row in data:
        if not row['filepath']:
            continue
        ts = int(datetime.strptime(row['snapshot_time'], '%Y-%m-%d').strftime('%s'))*1000
        d = grouped_data.setdefault(row['distribution'], {}).setdefault(row['architecture'], {})
        d.setdefault('pkg', []).append((ts, row['number_of_packages']))
        d.setdefault('maintainer', []).append((ts, row['number_of_maintainers']))
        d.setdefault('total_packed_size', []).append((ts, round(row['total_packed_size']/1024.**3,3)))
        d.setdefault('total_installed_size', []).append((ts, round(row['total_installed_size']/1024.**3,3)))
        d.setdefault('avg_pack_ratio', []).append((ts, row['avg_pack_ratio']))
        d.setdefault('avg_packed_size', []).append((ts, round(row['avg_packed_size']/1024.**2,3)))
        d.setdefault('avg_installed_size', []).append((ts, round(row['avg_installed_size']/1024.**2,3)))
    return jsonify({'metrics': grouped_data})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/table')
def table():
    data = get_table_data()
    total_filesize = sum((row['filesize'] for row in data if row['filepath']))
    number_of_files = len([row['filepath'] for row in data if row['filepath']])
    for row in data:
        if row['filepath']:
            row['filesize'] = '{:,}'.format(row['filesize'])
        else:
            row['filesize'] = ''
    return render_template('table.html', table=data, number_of_files=number_of_files, total_filesize='{:,}'.format(total_filesize))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
