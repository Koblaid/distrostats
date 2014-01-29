import gzip
import StringIO
import os
import sqlite3
import time
import traceback
from datetime import datetime

from dateutil import parser, rrule
import requests
import BeautifulSoup
from sqlalchemy import select

import model as m


FIRST_VALID_DAY = datetime(2005, 3, 12)


def get_valid_timestamps(interval_type, start, until=None):
    if not until:
        until = datetime.now()
    valid_timestamps = []
    html_cache = {}
    for dt in rrule.rrule(interval_type, dtstart=start, until=until):
        url = 'http://snapshot.debian.org/archive/debian/?year=%s&month=%s' % (dt.year, dt.month)
        html = html_cache.get(url)
        if not html:
            r = requests.get(url)
            html_cache[url] = r.text
            html = r.text

        doc = BeautifulSoup.BeautifulSoup(html)
        for a_tag in doc.findAll('a'):
            href = a_tag['href']
            if href.startswith(dt.strftime('%Y%m%dT')):
                valid_timestamps.append(href.strip('/'))
                break
        else:
            print 'No timestamp found for %s in %s' % (dt, url)
    return valid_timestamps


def write_timestamp_file(filepath, timestamps):
    with open(filepath, 'w') as f:
        for timestamp in timestamps:
            f.write(timestamp + '\n')


def read_timestamp_file(filepath):
    urls = []
    with open(filepath) as f:
        return f.read().strip().split('\n')


def get_filepath(path, archive, timestamp, dist, arch):
    filename = 'Packages_%s_%s_%s_main_binary-%s.txt' % (archive, timestamp, dist, arch)
    filepath = os.path.join(path, dist, filename)
    return filepath, filename


def download_from_snapshot_debian_org(path, timestamps, archive, dist, arch):
    counter = 0
    downloaded_counter = 0
    error_counter = 0
    skip_counter = 0

    for timestamp in timestamps:
        counter += 1
        print 'Downloading (% 3s/%s) %s... ' % (counter, len(timestamps), timestamp),
        outfile_path, filename = get_filepath(path, archive, timestamp, dist, arch)
        if os.path.exists(outfile_path):
            print 'file found, skip download'
            skip_counter += 1
            continue
        tmpfile_path = os.path.join(path, 'tmp', filename)

        url = 'http://snapshot.debian.org/archive/%s/%s/dists/%s/main/binary-%s/Packages.gz' % (archive, timestamp, dist, arch)
        try:
            r = requests.get(url)

            gzip_file = gzip.GzipFile(fileobj=StringIO.StringIO(r.content))
            with open(tmpfile_path, 'w') as tmpfile:
                tmpfile.write(gzip_file.read())
            print 'done'
        except Exception, e:
            print 'error when downloading %s' % url
            print traceback.format_exc()
            error_counter += 1
        else:
            os.rename(tmpfile_path, outfile_path)
            downloaded_counter += 1

    print '%s downloaded, %s skipped, %s errors' % (downloaded_counter, skip_counter, error_counter)


def parse_file(filepath):
    with open(filepath) as f:
        packages_info = f.read().strip('\n').split('\n\n')

    pkg_dict = {}
    for pkg_info in packages_info:
        lines = pkg_info.split('\n')
        properties = {}

        for line in lines:
            if line.startswith(' '):
                properties.setdefault('Long description', '')
                properties['Long description'] += line
            else:
                key, sep, value = line.partition(': ')
                properties[key] = value

        pkg_dict[properties['Package']] = properties

    return pkg_dict


def insert_file(conn, dist, timestamp, filesize, pkg_dict, pkg_id_cache):
    ts_text = parser.parse(timestamp).isoformat()
    res = conn.execute('SELECT id FROM snapshot WHERE snapshot_time = ?', (ts_text,)).fetchall()
    if res:
        ((snapshot_id,),) = res
    else:
        args = (ts_text, filesize)
        cur = conn.execute('INSERT INTO snapshot (snapshot_time, filesize) VALUES (?, ?)', args)
        snapshot_id = cur.lastrowid

    for pkg_name, properties in pkg_dict.iteritems():
        pkg_id = pkg_id_cache.get(pkg_name)
        if pkg_id is None:
            res = conn.execute('SELECT id FROM package WHERE name = ?', (pkg_name,)).fetchall()
            if res:
                ((pkg_id,),) = res
            else:
                cur = conn.execute('INSERT INTO package (name) VALUES (?)', (pkg_name,))
                pkg_id = cur.lastrowid
            pkg_id_cache[pkg_name] = pkg_id


        args = (snapshot_id, pkg_id, distributions[dist])
        conn.execute('INSERT INTO snapshot_content (snapshot_id, package_id, distribution_id) VALUES (?, ?, ?)', args)


def insert_file2(conn, dist, timestamp, filesize, pkg_dict, pkg_id_cache):
    trans = conn.begin()
    dt = parser.parse(timestamp)
    sel = select([m.snapshot.c.id]).where(m.snapshot.c.snapshot_time == dt)
    res = conn.execute(sel)
    if res.rowcount > 0:
        ((snapshot_id,),) = res
    else:
        res = conn.execute(m.snapshot.insert().values(snapshot_time=dt, filesize=filesize))
        snapshot_id = res.inserted_primary_key[0]
    c=0
    for pkg_name, properties in pkg_dict.iteritems():
        pkg_id = pkg_id_cache.get(pkg_name)
        if pkg_id is None:
            sel = select([m.package.c.id]).where(m.package.c.name == pkg_name)
            res = conn.execute(sel)
            if res.rowcount > 0:
                ((pkg_id,),) = res
            else:
                ins = m.package.insert().values(name=pkg_name)
                res = conn.execute(ins)
                pkg_id = res.inserted_primary_key[0]
            pkg_id_cache[pkg_name] = pkg_id

        ins = m.snapshot_content.insert().values(snapshot_id=snapshot_id, package_id=pkg_id, distribution_id=distributions[dist])
        conn.execute(ins)
        c+=1
        if c%1000==0:
            print c

    trans.commit()


db_filename = 'db.sqlite'
distributions = {
    'stable': 1,
    'testing': 2,
}

def connect_db():
    conn = sqlite3.connect(db_filename)
    curs = conn.execute('PRAGMA foreign_keys = ON')
    return conn


def create_schema(conn):
    sql = open('schema.sql').read()
    conn.executescript(sql)


def load_files_into_db(conn, path, timestamps, archive, dist, arch):
    pkg_id_cache = {}
    counter = 0
    for timestamp in timestamps:
        counter += 1
        filepath, filename = get_filepath(path, archive, timestamp, dist, arch)
        print 'Importing (% 3s/%s) %s ...' % (counter, len(timestamps), filename),
        if not os.path.exists(filepath):
            print 'file %s for timestamp %s not found, skipping' % (filepath, timestamp)
            continue

        filesize =  os.path.getsize(filepath)
        pkg_dict = parse_file(filepath)
        insert_file(conn, dist, timestamp, filesize, pkg_dict, pkg_id_cache)
        print 'done'
