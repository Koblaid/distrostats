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



def get_valid_timestamps(archive, interval_type, start, until=None):
    if not until:
        until = datetime.now()
    valid_timestamps = []
    html_cache = {}
    for dt in rrule.rrule(interval_type, dtstart=start, until=until):
        url = 'http://snapshot.debian.org/archive/%s/?year=%s&month=%s' % (archive, dt.year, dt.month)
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
    filepath = os.path.join(path, archive, dist, filename)
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

        last_key = None
        for line in lines:
            if line.startswith(' '):
                properties[last_key] += line
            else:
                key, sep, value = line.partition(': ')
                properties[key] = value
                last_key = key
        pkg_dict[properties['Package']] = properties

    return pkg_dict


def get_static_ids(conn):
    id_cache = {}

    res = conn.execute('SELECT name, id from archive')
    id_cache['archive'] = dict(res)

    res = conn.execute('SELECT name, id from distribution')
    id_cache['distribution'] = dict(res)

    res = conn.execute('SELECT name, id from pkg_repository')
    id_cache['pkg_repository'] = dict(res)

    res = conn.execute('SELECT name, id from architecture')
    id_cache['architecture'] = dict(res)

    return id_cache


def insert_snapshots(conn, id_cache, archive, timestamps):
    print('insert snapshots...', end='')
    archive_id = id_cache['archive'][archive]
    cur = conn.cursor()
    for timestamp in timestamps:
        ts_text = parser.parse(timestamp).isoformat()
        stmt = 'INSERT INTO snapshot (archive_id, snapshot_time) VALUES (?, ?)'
        cur.execute(stmt, (archive_id, ts_text))
    print('done')


def connect_db(db_filename):
    conn = sqlite3.connect(db_filename)
    curs = conn.execute('PRAGMA foreign_keys = ON')
    return conn


def create_schema(conn):
    sql = open('schema.sql').read()
    conn.executescript(sql)


def load_files_into_db(conn, id_cache, path, timestamps, archive, dist, arch):
    counter = Counter(len(timestamps))
    for timestamp in timestamps:
        filepath, filename = get_filepath(path, archive, timestamp, dist, arch)
        counter.print_current(filename)
        if not os.path.exists(filepath):
            counter.not_found()
            continue

        filesize =  os.path.getsize(filepath)
        file_dict = parse_file(filepath)

        ts_text = parser.parse(timestamp).isoformat()
        stmt = 'SELECT id FROM snapshot WHERE snapshot_time = ? and archive_id = ?'
        res = conn.execute(stmt, (ts_text, id_cache['archive'][archive])).fetchall()
        ((snapshot_id,),) = res

        args = dict(
            snapshot_id=snapshot_id,
            distribution_id=id_cache['distribution'][dist],
            pkg_repository_id=id_cache['pkg_repository']['main'],
            architecture_id=id_cache['architecture'][arch],
            filepath=filepath,
            filesize=filesize,
        )
        args.update(stats(file_dict))
        values = ','.join(args)
        placeholders = ','.join((':%s'%k for k in args))
        stmt = 'INSERT INTO snapshot_file (%s) VALUES (%s)' % (values, placeholders)
        conn.execute(stmt, args)
        counter.success()

    counter.print_result()


def total_sum(file_dict, key):
    total_size = 0
    for pkg_dict in file_dict.itervalues():
        size = int(pkg_dict[key])
        total_size += size
    return total_size


def stats(file_dict):
    number_of_packages = len(file_dict)
    number_of_maintainers = len(set((d['Maintainer'] for d in file_dict.itervalues())))
    total_pkg_packed_size = total_sum(file_dict, 'Size')
    total_pkg_installed_size = total_sum(file_dict, 'Installed-Size') * 1024
    avg_size = 1. * total_pkg_packed_size / number_of_packages
    avg_installed_size = 1. * total_pkg_installed_size / number_of_packages
    avg_pack_ratio = 1.* total_pkg_packed_size / total_pkg_installed_size

    return dict(
        number_of_packages=number_of_packages,
        number_of_maintainers=number_of_maintainers,
        avg_size=avg_size,
        avg_installed_size=avg_installed_size,
        avg_pack_ratio=avg_pack_ratio
    )
