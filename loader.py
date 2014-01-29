from __future__ import print_function
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


FIRST_VALID_DAY = datetime(2005, 3, 12)



class Counter(object):
    def __init__(self, total):
        self._counters = {
            'success': 0,
            'skipped': 0,
            'not_found': 0,
            'error': 0,
        }
        self.total = total

    def _print(self, text, no_newline=False):
        if no_newline:
            print(text, end='')
        else:
            print(text)

    def _print_with_info(self, text, info):
        if info:
            text += ' (%s)' % info
        self._print(text)

    def _get_current_count(self):
        return sum(self._counters.values())

    def success(self, info=None):
        self._counters['success'] += 1
        self._print_with_info('done', info)

    def skipped(self, info=None):
        self._counters['skipped'] += 1
        self._print_with_info('skipped', info)

    def not_found(self, info=None):
        self._counters['not_found'] += 1
        self._print_with_info('file not found', info)

    def error(self, info=None):
        self._counters['error'] += 1
        self._print_with_info('error', info)
        self._print(traceback.format_exc())

    def print_current(self, label):
        current = self._get_current_count() + 1
        l = str(len(str(self.total)))
        text = 'Processing (% '+l+'s/% '+l+'s) %s... '
        self._print(text % (current, self.total, label), True)

    def print_result(self):
        if self._get_current_count() != self.total:
            self._print('Warning: %s should have been processed but only %s were counted' % (self.total, self._get_current_count()))
        self._print('%(success)s processed, %(skipped)s skipped, %(not_found)s not found, %(error)s errors' % self._counters)



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
            print('No timestamp found for %s in %s' % (dt, url))
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
    counter = Counter(len(timestamps))

    for timestamp in timestamps:
        counter.print_current(timestamp)
        outfile_path, filename = get_filepath(path, archive, timestamp, dist, arch)
        if os.path.exists(outfile_path):
            counter.skipped('file exists')
            continue
        tmpfile_path = os.path.join(path, 'tmp', filename)

        url = 'http://snapshot.debian.org/archive/%s/%s/dists/%s/main/binary-%s/Packages.gz' % (archive, timestamp, dist, arch)
        r = requests.get(url)
        if r.status_code != 200:
            counter.not_found('%s (HTTP %s)' % (url, r.status_code))
            continue

        try:
            gzip_file = gzip.GzipFile(fileobj=StringIO.StringIO(r.content))
            with open(tmpfile_path, 'w') as tmpfile:
                tmpfile.write(gzip_file.read())
        except Exception, e:
            counter.error('error while unzipping/writing %s' % url)
        else:
            os.rename(tmpfile_path, outfile_path)
            counter.success()

    counter.print_result()


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
    counter = Counter(len(timestamps))
    for timestamp in timestamps:
        filepath, filename = get_filepath(path, archive, timestamp, dist, arch)
        counter.print_current(filename)
        if not os.path.exists(filepath):
            counter.skipped()
            continue

        filesize =  os.path.getsize(filepath)
        pkg_dict = parse_file(filepath)
        insert_file(conn, dist, timestamp, filesize, pkg_dict, pkg_id_cache)
        counter.success()
    counter.print_result()
