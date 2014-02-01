-- Hierarchy for Debian:
--   Archive (debian, debian-backports, debian-security, ...)
--     Snapshot (2008-04-08 00:00:00, 2008-04-30 00:00:00, ...)
--       Distribution (stable, testing, unstable, experimental)
--         Repository (main, contrib, non-free)
--           Architecture (i386, amd64, ...


CREATE TABLE archive (
  id                    INTEGER PRIMARY KEY,
  name                  TEXT NOT NULL,
  UNIQUE (name)
);

CREATE TABLE snapshot (
  id                    INTEGER PRIMARY KEY,
  archive_id            INTEGER NOT NULL,
  snapshot_time         TEXT NOT NULL,      --ISO8601
  FOREIGN KEY (archive_id)  REFERENCES archive(id),
  UNIQUE (snapshot_time)
);

CREATE TABLE distribution (
  id                    INTEGER PRIMARY KEY,
  name                  TEXT NOT NULL,
  UNIQUE (name)
);

CREATE TABLE pkg_repository (
  id                    INTEGER PRIMARY KEY,
  name                  TEXT NOT NULL,
  UNIQUE (name)
);

CREATE TABLE architecture (
  id                    INTEGER PRIMARY KEY,
  name                  TEXT NOT NULL,
  UNIQUE (name)
);

CREATE TABLE snapshot_file (
  id                    INTEGER PRIMARY KEY,
  snapshot_id           INTEGER NOT NULL,
  distribution_id       INTEGER NOT NULL,
  pkg_repository_id     INTEGER NOT NULL,
  architecture_id       INTEGER NOT NULL,
  filepath              TEXT NOT NULL,
  filesize              INTEGER NOT NULL,
  number_of_packages    INTEGER NOT NULL,
  number_of_maintainers INTEGER NOT NULL,
  total_packed_size     INTEGER NOT NULL,
  total_installed_size  INTEGER NOT NULL,
  FOREIGN KEY(snapshot_id)          REFERENCES snapshot(id),
  FOREIGN KEY(distribution_id)      REFERENCES distribution(id),
  FOREIGN KEY(pkg_repository_id)    REFERENCES pkg_repository(id),
  FOREIGN KEY(architecture_id)      REFERENCES architecture(id),
  UNIQUE (filepath),
  UNIQUE (snapshot_id, distribution_id, pkg_repository_id, architecture_id)
);

INSERT INTO archive (name) VALUES ('debian');
INSERT INTO archive (name) VALUES ('debian-backports');
INSERT INTO archive (name) VALUES ('debian-security');

INSERT INTO distribution (name) VALUES ('experimental');
INSERT INTO distribution (name) VALUES ('unstable');
INSERT INTO distribution (name) VALUES ('testing');
INSERT INTO distribution (name) VALUES ('stable');

INSERT INTO pkg_repository (name) VALUES ('main');
INSERT INTO pkg_repository (name) VALUES ('contrib');
INSERT INTO pkg_repository (name) VALUES ('non-free');

INSERT INTO architecture (name) VALUES ('i386');
INSERT INTO architecture (name) VALUES ('amd64');
INSERT INTO architecture (name) VALUES ('kfreebsd-amd64');
