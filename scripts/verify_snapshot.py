"""Offline checks for the project's frozen dataset. No API key required."""
import hashlib
import json
from pathlib import Path
import sqlite3

SNAPSHOT = Path(__file__).resolve().parent.parent / 'data/frozen/ucsd_rentals_2026-11-16_102139_PT'


def main():
    entries = (SNAPSHOT / 'SHA256SUMS').read_text().splitlines()
    expected_files = set()
    for entry in entries:
        digest, name = entry.split('  ', 1)
        path = SNAPSHOT / name
        expected_files.add(name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit(f'Checksum mismatch: {name}')
    actual_files = {str(p.relative_to(SNAPSHOT)) for p in SNAPSHOT.rglob('*') if p.is_file()}
    if actual_files != expected_files | {'SHA256SUMS'}:
        raise SystemExit('Snapshot contains missing or unexpected files.')
    manifest = json.loads((SNAPSHOT / 'manifest.json').read_text())
    if manifest['state'] != 'frozen' or not manifest['completeness_verified']:
        raise SystemExit('Snapshot completeness was not verified.')
    uri = (SNAPSHOT / 'rentals.sqlite').resolve().as_uri() + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise SystemExit('SQLite integrity check failed.')
        counts = db.execute('SELECT COUNT(*), COUNT(DISTINCT id), COUNT(DISTINCT formattedAddress) FROM listings').fetchone()
        if counts != (2690, 2690, 2690):
            raise SystemExit(f'Unexpected record counts: {counts}')
        if db.execute('SELECT COUNT(*) FROM raw_listings').fetchone()[0] != 2690:
            raise SystemExit('Raw and analysis record counts differ.')
        invalid = db.execute('SELECT COUNT(*) FROM listings WHERE status != ? OR status IS NULL OR distanceToCampusMiles > 10 OR distanceToCampusMiles IS NULL', ('Active',)).fetchone()[0]
        if invalid:
            raise SystemExit(f'{invalid} records fail status/geographic checks.')
    print(f'PASS: {len(entries)} file checksums; SQLite integrity; 2,690 unique records; Active status; 10-mile radius.')


if __name__ == '__main__':
    main()
