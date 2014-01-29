from sqlalchemy import (Table, Column, Integer, String, DateTime, MetaData,
                        ForeignKey, UniqueConstraint, create_engine)
metadata = MetaData()

distribution = Table('distribution', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, nullable=False, unique=True),
)

snapshot = Table('snapshot', metadata,
    Column('id', Integer, primary_key=True),
    Column('snapshot_time', DateTime, nullable=False, unique=True),
    Column('filesize', Integer, nullable=False)
)

package = Table('package', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, nullable=False, unique=True),
)

snapshot_content = Table('snapshot_content', metadata,
    Column('id', Integer, primary_key=True),
    Column('snapshot_id', None, ForeignKey('snapshot.id'), nullable=False),
    Column('package_id', None, ForeignKey('package.id'), nullable=False),
    Column('distribution_id', None, ForeignKey('distribution.id'), nullable=False),
    UniqueConstraint('snapshot_id', 'package_id', 'distribution_id'),
)


def init_db(engine):
    metadata.create_all(engine)
    conn = engine.connect()
    conn.execute(distribution.insert(), [
        dict(id=1, name='stable'),
        dict(id=2, name='testing'),
    ])
