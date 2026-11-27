"""Local storage and backup utilities; independent of Qt."""
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
import os
import sqlite3
import tempfile


def data_folder(qt_folder, home, platform, override=None):
    if override is not None:
        return Path(override).expanduser().resolve()
    qt = Path(qt_folder).expanduser().resolve()
    if platform != 'darwin':
        return qt
    legacy = (Path(home) / 'Library/Application Support/DIDAR Connect').resolve()
    if qt != legacy and (qt/'didar.sqlite').exists() and (legacy/'didar.sqlite').exists():
        raise ValueError('Two possible DIDAR databases exist. Do not merge or overwrite them. Open the intended directory explicitly with --data-dir.')
    # Prefer the known V0.9 location unless Qt finds an existing database elsewhere.
    return qt if (qt/'didar.sqlite').exists() else legacy


def backups(folder):
    directory = Path(folder) / 'backups'
    return sorted((p for p in directory.glob('*.sqlite') if p.is_file()), key=lambda p:p.stat().st_mtime, reverse=True)


def create_backup(store, folder, label='manual'):
    if label not in ('manual','auto','before-restore'):
        raise ValueError('Invalid backup label')
    directory = Path(folder) / 'backups'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = directory / ('didar-'+label+'-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite')
    fd, name = tempfile.mkstemp(prefix='.backup-', suffix='.tmp', dir=directory)
    os.close(fd)
    temp = Path(name)
    try:
        store.backup(temp)
        with closing(sqlite3.connect(temp)) as db:
            if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Backup integrity check failed.')
        os.replace(temp, target)
        return target
    finally:
        temp.unlink(missing_ok=True)


def daily_backup(store, folder):
    prefix = 'didar-auto-'+date.today().strftime('%Y%m%d')+'-'
    if any(p.name.startswith(prefix) for p in backups(folder)):
        return None
    return create_backup(store, folder, 'auto')


def schema(db):
    return db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()


def restore_backup(store, folder, source):
    """Validate a same-database snapshot and preserve the live DB before restoring.

    Only current-schema snapshots of this database are accepted. A SQLite backup
    transaction replaces the live contents, without filesystem sidecar manipulation.
    The caller must ensure exclusive application access.
    """
    source = Path(source).expanduser().resolve(strict=True)
    live = (Path(folder)/'didar.sqlite').resolve()
    if source == live or source.samefile(live):
        raise ValueError('Select a backup, not the live database.')
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as candidate:
        candidate.execute('PRAGMA query_only=ON')
        candidate.execute('PRAGMA trusted_schema=OFF')
        candidate.execute('BEGIN')
        if candidate.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('The backup failed the SQLite integrity check.')
        if schema(candidate) != schema(store.db):
            raise ValueError('Backup schema differs. Restore only a compatible V0.9/V1.0 snapshot using this interface.')
        if candidate.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('The backup contains invalid relationships.')
        if candidate.execute("SELECT v FROM config WHERE k='salt'").fetchone() != store.db.execute("SELECT v FROM config WHERE k='salt'").fetchone():
            raise ValueError('This backup is from a different database.')
        check = candidate.execute("SELECT v FROM config WHERE k='check'").fetchone()
        if not check or store.key.decrypt(check[0]) != b'DIDAR':
            raise ValueError('The backup cannot be authenticated with this database passphrase.')
        for typ, name, _, _ in schema(store.db):
            if typ != 'table' or name == 'config':
                continue
            quoted = '"'+name.replace('"','""')+'"'
            for (payload,) in candidate.execute('SELECT payload FROM '+quoted):
                if not isinstance(store.dec(payload), dict):
                    raise ValueError('Invalid backup record.')
        safety = create_backup(store, folder, 'before-restore')
        candidate.backup(store.db)
        return safety
