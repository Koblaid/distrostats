import os

from dateutil import rrule

import loader



if __name__ == '__main__':
    dist = 'testing'
    archive = 'debian'
    arch = 'amd64'

    file_directory = '/media/ben/579781cd-f222-46b8-974b-e1741f7ceb61/distrostats'
    timestamp_file = '%s/%s/timestamps_%s.txt' % (file_directory, archive, archive)
    db_filename = 'db.sqlite'

    if not os.path.exists(timestamp_file):
        print 'Write timestamp file...',
        timestamps = loader.get_valid_timestamps(archive, rrule.WEEKLY, loader.FIRST_VALID_DAY)
        loader.write_timestamp_file(timestamp_file, timestamps)
        print 'done'


    timestamps = loader.read_timestamp_file(timestamp_file)
    #loader.download_from_snapshot_debian_org(file_directory, timestamps, archive, dist, 'amd64')
    #loader.download_from_snapshot_debian_org(file_directory, timestamps, archive, dist, 'i386')

    #if os.path.exists(db_filename):
    #    os.unlink(db_filename)
    conn = loader.connect_db(db_filename)
    #loader.create_schema(conn)
    id_cache = loader.get_static_ids(conn)
    #loader.insert_snapshots(conn, id_cache, archive, timestamps)
    loader.load_files_into_db(conn, id_cache, file_directory, timestamps, archive, dist, 'amd64')
    loader.load_files_into_db(conn, id_cache, file_directory, timestamps, archive, dist, 'i386')

    conn.commit()
    conn.close()

