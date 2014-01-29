import os

from dateutil import rrule
from sqlalchemy import create_engine

import loader
import model as m



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


    pkg_dict = loader.parse_file('/media/ben/579781cd-f222-46b8-974b-e1741f7ceb61/distrostats/testing/Packages_debian_20050312T000000Z_testing_main_binary-i386.txt')
    pkg_id_cache = {}


    conn = loader.connect_db()
    loader.create_schema(conn)
    loader.insert_file1(conn, dist, '20050312T000000Z', 234234, pkg_dict, pkg_id_cache)

    conn.commit()
    conn.close()

    '''
    engine = create_engine('sqlite:///db2.sqlite', echo=False)
    m.init_db(engine)
    loader.insert_file2(engine.connect(), dist, '20050312T000000Z', 234234, pkg_dict, pkg_id_cache)
    '''
