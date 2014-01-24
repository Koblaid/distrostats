import gzip
import StringIO
import os
import sqlite3
import time
import traceback
import random
from datetime import datetime

from dateutil import parser, rrule
import requests
import BeautifulSoup


FIRST_DAY = datetime(2005, 3, 12)


def get_urls_for_interval(interval_type):
    day_urls = []
    html_cache = {}
    for dt in rrule.rrule(interval_type, dtstart=FIRST_DAY, until=datetime.now()):
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
                day_urls.append(href.strip('/'))
                break
        else:
            print 'No url found for %s in %s' % (dt, url)
            #raise Exception('No url found for %s in %s' % (dt, url))

    return day_urls


def read_timestamp_file(filename):
    urls = []
    with open(filename) as f:
        return f.read().strip().split('\n')


def download_from_snapshot_debian_org(paths, dist):
    counter = 0
    downloaded_counter = 0
    error_counter = 0
    skip_counter = 0

    for url in paths:
        print 'Downloading (% 3s/%s) %s... ' % (counter, len(paths), url),
        counter += 1

        outfile_path = 'files/%s/Packages_%s' % (dist, url)
        if os.path.exists(outfile_path):
            print 'file found, skip download'
            skip_counter += 1
            continue
        tmpfile_path = 'files/tmp/Packages_%s_%s' % (url, random.randint(1, 10000))

        url = 'http://snapshot.debian.org/archive/debian/%s/dists/%s/main/binary-i386/Packages.gz' % (url, dist)
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
    ts_text = timestamp.isoformat()
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


def import_files(dist):
    path = 'files/%s' % dist
    pkg_id_cache = {}
    filenames = os.listdir(path)
    counter = 0
    for filename in filenames:
        counter += 1
        print 'Importing (% 3s/%s) %s ...' % (counter, len(filenames), filename),
        fullpath = os.path.join(path, filename)
        timestamp = parser.parse(filename.split('_')[1])
        filesize =  os.path.getsize(fullpath)
        pkg_dict = parse_file(fullpath)
        insert_file(conn, dist, timestamp, filesize, pkg_dict, pkg_id_cache)
        print 'done'



if __name__ == '__main__':
    #if os.path.exists(db_filename):
    #    os.unlink(db_filename)
    conn = connect_db()
    #create_schema(conn)

    dist = 'stable'
    timestamp_file = 'files/timestamps.txt'

    if not os.path.exists(timestamp_file):
        print 'Write timestamp file...',
        urls = get_urls_for_interval(rrule.WEEKLY)
        with open(timestamp_file, 'w') as f:
            for url in urls:
                url = 'http://snapshot.debian.org/archive/debian/'+url
                f.write(url + '\n')
        print 'done'


    #paths = read_timestamp_file('files/timestamps.txt')
    #download_from_snapshot_debian_org(paths, dist)
    #import_files(dist)


    #import_files('stable')
    #import_files('testing')
    #conn.commit()



    conn.close()
