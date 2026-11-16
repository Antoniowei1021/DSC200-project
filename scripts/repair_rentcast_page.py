"""Save one targeted overlapping page; inspect pagination before running.

Reads RENTCAST_API_KEY from the environment. Makes one request, no retries.
Does not alter finalized snapshots or decide which boundary needs repair.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder', type=Path)
    p.add_argument('--offset', type=int, required=True)
    p.add_argument('--limit', type=int, default=20)
    args = p.parse_args()
    if args.offset < 0 or not 1 <= args.limit <= 500:
        p.error('Offset must be nonnegative and limit must be 1-500.')
    if (args.folder / 'SHA256SUMS').exists():
        p.error('Already frozen; refusing to modify.')
    key = os.environ.get('RENTCAST_API_KEY', '').strip()
    if not key:
        p.error('Missing RENTCAST_API_KEY; no request sent.')
    manifest_path = args.folder / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    base = 'https://api.rentcast.io/v1/listings/rental/long-term'
    if manifest.get('source') != base:
        p.error('Unexpected API source; no request sent.')
    query = {**manifest['query'], 'offset': args.offset, 'limit': args.limit, 'includeTotalCount': 'true'}
    url = base + '?' + urllib.parse.urlencode(query)
    timestamp = datetime.now(timezone.utc).isoformat()
    name = f'pages/repair_offset_{args.offset:05d}_limit_{args.limit}.json'
    if (args.folder / name).exists():
        p.error('Repair page already exists; refusing to overwrite.')
    request = urllib.request.Request(url, headers={'X-Api-Key': key, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
            status = response.status
            total = int(response.headers['X-Total-Count'])
    except urllib.error.HTTPError as error:
        raise SystemExit(f'HTTP {error.code}; stopped without retry.') from None
    page = json.loads(body)
    if not isinstance(page, list):
        raise SystemExit('Unexpected response schema; stopped.')
    (args.folder / name).write_bytes(body)
    manifest['requests'].append({
        'offset': args.offset, 'limit': args.limit, 'url': url,
        'requested_at_utc': timestamp, 'received_at_utc': datetime.now(timezone.utc).isoformat(),
        'http_status': status, 'total_count': total, 'returned_rows': len(page),
        'file': name, 'sha256': hashlib.sha256(body).hexdigest(),
        'purpose': 'Targeted overlapping page to resolve an inspected pagination boundary.'})
    manifest['state'] = 'validating_repair'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Saved {len(page)} rows. Provider total: {total}. Run offline validation before freezing.')


if __name__ == '__main__':
    main()
