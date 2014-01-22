import gzip
import StringIO
import os
import sqlite3

import dateutil.parser
import requests
import BeautifulSoup



def find_first_timestamp_of_month(path):
    r = requests.get(path)
    doc = BeautifulSoup.BeautifulSoup(r.text)
    p_block = doc.p
    a_tag = p_block.a
    url = a_tag['href']
    return url


def iter_all_month_paths(year_overview_path):
    r = requests.get(year_overview_path)
    doc = BeautifulSoup.BeautifulSoup(r.text)
    for a_tag in doc.findAll('a'):
        href = a_tag['href']
        if href.startswith('./?year='):
            yield href


def download_from_snapshot_debian_org():
    for month_segment in iter_all_month_paths('http://snapshot.debian.org/archive/debian/'):
        url = find_first_timestamp_of_month('http://snapshot.debian.org/archive/debian/'+month_segment)
        url = url.strip('/')
        print 'Downloading %s... ' % url,

        outfile_name = 'files/Packages_%s' % url
        if os.path.exists(outfile_name):
            print 'file found, skip download'
            continue

        url = 'http://snapshot.debian.org/archive/debian/%s/dists/stable/main/binary-i386/Packages.gz' % url
        r = requests.get(url)
        gzip_file = gzip.GzipFile(fileobj=StringIO.StringIO(r.content))
        with open(outfile_name, 'w') as outfile:
            outfile.write(gzip_file.read())
        print 'done'


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


def insert_file(conn, timestamp, filesize, pkg_dict, pkg_id_cache):
    args = (timestamp.isoformat(), filesize)
    cur = conn.execute('INSERT INTO snapshot (snapshot_time, filesize) VALUES (?, ?)', args)
    snapshot_id = cur.lastrowid

    for pkg_name, properties in pkg_dict.iteritems():
        pkg_id = pkg_id_cache.get(pkg_name)
        if pkg_id is None:
            cur = conn.execute('INSERT INTO package (name) VALUES (?)', (pkg_name,))
            pkg_id = cur.lastrowid
            pkg_id_cache[pkg_name] = pkg_id

        args = (snapshot_id, pkg_id)
        conn.execute('INSERT INTO snapshot_content (snapshot_id, package_id) VALUES (?, ?)', args)


db_filename = 'db.sqlite'

def connect_db():
    conn = sqlite3.connect(db_filename)
    curs = conn.execute('PRAGMA foreign_keys = ON')
    return conn


def create_schema(conn):
    sql = open('schema.sql').read()
    conn.executescript(sql)


def import_files():
    if os.path.exists(db_filename):
        os.unlink(db_filename)
    conn = connect_db()
    create_schema(conn)

    path = 'files'
    pkg_id_cache = {}
    for filename in os.listdir(path):
        print 'Importing %s ...' % filename,
        fullpath = os.path.join(path, filename)
        timestamp = dateutil.parser.parse(filename.split('_')[1])
        filesize =  os.path.getsize(fullpath)
        pkg_dict = parse_file(fullpath)
        insert_file(conn, timestamp, filesize, pkg_dict, pkg_id_cache)
        print 'done'

    conn.commit()
    conn.close()


#download_from_snapshot_debian_org()
import_files()

