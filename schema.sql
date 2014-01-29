CREATE TABLE distribution (
  id                INTEGER PRIMARY KEY,
  name              TEXT NOT NULL,
  UNIQUE(name)
);


CREATE TABLE snapshot (
  id                    INTEGER PRIMARY KEY,
  snapshot_time         TEXT NOT NULL,      --ISO8601
  UNIQUE (snapshot_time)
);


CREATE TABLE snapshot_file (
  id                    INTEGER PRIMARY KEY,
  snapshot_id           INTEGER NOT NULL,
  filepath              TEXT NOT NULL,
  filesize              INTEGER NOT NULL,
  distribution          TEXT NOT NULL,
  archive               TEXT NOT NULL,
  architecture          TEXT NOT NULL,
  number_of_packages    INTEGER NOT NULL,
  number_of_maintainers INTEGER NOT NULL,
  FOREIGN KEY(snapshot_id)      REFERENCES snapshot(id),
  UNIQUE (filepath)
);
