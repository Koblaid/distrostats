import os

from dateutil import rrule

import loader



if __name__ == '__main__':
    dist = 'testing'
    archive = 'debian'
    arch = 'i386'

    file_directory = '/media/ben/579781cd-f222-46b8-974b-e1741f7ceb61/distrostats'
    timestamp_file = file_directory + '/timestamps.txt'

    if not os.path.exists(timestamp_file):
        print 'Write timestamp file...',
        timestamps = loader.get_valid_timestamps(rrule.WEEKLY, loader.FIRST_VALID_DAY)
        loader.write_timestamp_file(timestamp_file, timestamps)
        print 'done'


    timestamps = loader.read_timestamp_file(timestamp_file)
    #loader.download_from_snapshot_debian_org(file_directory, timestamps, archive, dist, arch)

    #if os.path.exists(db_filename):
    #    os.unlink(db_filename)
    conn = loader.connect_db()
    #loader.create_schema(conn)
    loader.load_files_into_db(conn, file_directory, timestamps, archive, dist, arch)

    #conn.commit()
    conn.close()
