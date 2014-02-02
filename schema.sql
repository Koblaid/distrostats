CREATE TABLE distribution (
  id                SERIAL PRIMARY KEY,
  name              TEXT NOT NULL,
  UNIQUE(name)
);

CREATE TABLE snapshot (
  id                SERIAL PRIMARY KEY,
  snapshot_time     TEXT NOT NULL,      --ISO8601
  filesize          INTEGER NOT NULL,
  UNIQUE (snapshot_time)
);

CREATE TABLE dist_package (
  id                SERIAL PRIMARY KEY,
  name              TEXT NOT NULL,
  UNIQUE(name)
);

CREATE TABLE snapshot_content (
  id                SERIAL PRIMARY KEY,
  snapshot_id       INTEGER NOT NULL,
  package_id        INTEGER NOT NULL,
  distribution_id   INTEGER NOT NULL,
  FOREIGN KEY(snapshot_id)      REFERENCES snapshot(id),
  FOREIGN KEY(package_id)       REFERENCES    dist_package(id),
  FOREIGN KEY(distribution_id)  REFERENCES distribution(id),
  UNIQUE(snapshot_id, package_id, distribution_id)
);
CREATE INDEX snapshot_content__distribution_id__snapshot_id on snapshot_content(distribution_id, snapshot_id);


INSERT INTO distribution (id, name) VALUES (1, 'stable');
INSERT INTO distribution (id, name) VALUES (2, 'testing');
