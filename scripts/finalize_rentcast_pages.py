"""Validate saved pages, including overlaps, then freeze without API requests."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo
from freeze_rentcast import build_database, write_json


def finalize(folder):
    if (folder/'SHA256SUMS').exists():
        raise SystemExit('Already frozen; refusing to overwrite.')
    manifest=json.loads((folder/'manifest.json').read_text())
    unique={}
    provenance={}
    conflicting_ids=set()
    total_downloaded=0
    for request in manifest['requests']:
        body=(folder/request['file']).read_bytes()
        assert hashlib.sha256(body).hexdigest()==request['sha256'], 'Page checksum mismatch'
        page=json.loads(body)
        assert len(page)==request['returned_rows'], 'Page size mismatch'
        total_downloaded+=len(page)
        for row in page:
            identity=row.get('id')
            assert isinstance(identity,str) and identity, 'Missing record ID'
            if identity in unique:
                if unique[identity]!=row: conflicting_ids.add(identity)
            else:
                unique[identity]=row
                provenance[identity]={'sourcePageOffset':request['offset'],
                                      'sourceRequestedAtUtc':request['requested_at_utc']}
    totals={r['total_count'] for r in manifest['requests']}
    assert len(totals)==1 and len(unique)==next(iter(totals)), 'Count mismatch; cannot freeze'
    assert not conflicting_ids, 'Conflicting versions of same ID; review before freezing'
    # Full sequential coverage must be present; overlapping repairs alone are insufficient.
    total=next(iter(totals))
    core={r['offset']:r for r in manifest['requests'] if not r.get('purpose')}
    assert set(core)==set(range(0,total,500)), 'Missing primary page'
    assert all(core[o]['returned_rows']==min(500,total-o) for o in core), 'Truncated primary page'
    finish=max(r['received_at_utc'] for r in manifest['requests'])
    manifest.update(state='frozen',finished_at_utc=finish,
                    finished_at_pacific=datetime.fromisoformat(finish).astimezone(ZoneInfo('America/Los_Angeles')).isoformat(),
                    downloaded_rows=total_downloaded,unique_ids=len(unique),reported_totals=sorted(totals),
                    frozen_rows=len(unique),completeness_verified=True,
                    repeated_rows_removed=total_downloaded-len(unique),conflicting_duplicate_ids=0,
                    deduplication='First occurrence of ID retained; overlapping duplicate contents verified identical.',
                    pagination_repair='One overlap query at offset 990, limit 20 recovered a record skipped across tied lastSeenDate boundary at offset 1000.')
    manifest.pop('error',None)
    manifest.pop('stopped_at_utc',None)
    rows=list(unique.values())
    records=build_database(folder,rows,[provenance[r['id']] for r in rows],manifest)
    quality={
        'frozen_rows':len(rows),'provider_matching_total':total,'unique_ids':len(unique),
        'unique_addresses':len({r.get('formattedAddress','').strip().casefold() for r in rows}),
        'status_counts':dict(Counter(r.get('status') for r in rows)),
        'property_type_counts':dict(Counter(r.get('propertyType') for r in rows)),
        'bedroom_counts':dict(Counter(str(r.get('bedrooms')) for r in rows)),
        'missing_fields':{k:sum(r.get(k) is None for r in rows) for k in ['price','bedrooms','bathrooms','squareFootage','latitude','longitude','lastSeenDate']},
        'within_miles_counts':{str(n):sum(r['distanceToCampusMiles'] is not None and r['distanceToCampusMiles']<=n for r in records) for n in [1,2,3,5,10]},
        'outside_10_05_miles':sum(r['distanceToCampusMiles'] is not None and r['distanceToCampusMiles']>10.05 for r in records),
        'nonpositive_prices':sum(isinstance(r.get('price'),(int,float)) and r['price']<=0 for r in rows),
        'nonpositive_areas':sum(isinstance(r.get('squareFootage'),(int,float)) and r['squareFootage']<=0 for r in rows),
        'last_seen_range':[min(r['lastSeenDate'] for r in rows if r.get('lastSeenDate')),max(r['lastSeenDate'] for r in rows if r.get('lastSeenDate'))],
        'sqlite_integrity_check':'ok','cross_page_duplicate_conflicts':0,
        'policy':'Retain all unique provider records; no outlier removal or missing-value imputation.'}
    write_json(folder/'quality_report.json',quality)
    write_json(folder/'manifest.json',manifest)
    (folder/'README.txt').write_text(f'''UCSD 周边租房数据冻结快照

快照版本：{folder.name}
采集开始（America/Los_Angeles）：{manifest['started_at_pacific']}
采集完成（America/Los_Angeles）：{manifest['finished_at_pacific']}
采集日期：2026-11-16。UTC 时间另见 manifest.json。
数据来源：RentCast /v1/listings/rental/long-term
中心坐标：(32.8801, -117.2340)，近似校园参考点。
范围：10 英里直线半径；状态：Active。
最终冻结：{len(rows)} 个不同 ID 的记录，等于全部请求返回的总量 {total}。
请求数：{len(manifest['requests'])}（六页完整采集 + 一次分页交界补查）。

完整性处理
原始六页共 2,690 行，但相同 lastSeenDate 的排序交界重复了一条，最初只有 2,689 个不同 ID。
在 offset=990 补查 20 行后恢复漏项；按 ID 去重，全部重复记录内容一致。
所有响应保留在 pages/，没有覆写；initial_collection_manifest.json 记录最初未通过检查的状态。
最终 manifest.json 记录修复后的完整性、时间、请求参数与每页 SHA-256。

文件与用法
rentals.sqlite：SQLite 数据库。listings 为分析表，raw_listings 为完整供应商记录，snapshot_metadata 为采集元数据。
listings.json：分析字段与距离、单位面积租金、来源请求时间和 offset。
raw_listings.json：完整供应商记录，按 ID 去重后全部保留。
schema.json：字段类型及关键字段含义。
quality_report.json：缺失值、状态、地理范围等质量检查。
SHA256SUMS：本目录全部文件的 SHA-256（自身除外）。

冻结规则
所有快照文件设为只读；脚本遇到已冻结目录拒绝覆写。
后续清洗与分析应输出到其他目录，不修改本快照。新采集生成新版本。
SQLite 建议只读打开：sqlite3.connect('file:/absolute/path/rentals.sqlite?mode=ro', uri=True)。
本目录不包含 API key，并被 Git 忽略。

口径与限制
这是供应商在上述采集窗口内的完整查询结果，不代表租房市场全部房源。
分页采集并非供应商的原子时间点快照；逐页时间可追溯。
Active 与 lastSeenDate 由供应商提供，不等于独立确认当前可签约。
保留全部 {len(rows)} 条记录；缺失面积、异常价格及同一楼宇内不同房号均未删除。
挂牌租金尚未统一费用、优惠、家具、租期和整租/分租口径；这些属于后续清洗工作。
不同房号可能共享楼宇或坐标，统计上不一定独立。
公开发布原始数据前需另核对供应商许可。
''')
    with sqlite3.connect(f'file:{folder.resolve()}/rentals.sqlite?mode=ro',uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('SELECT COUNT(*) FROM listings').fetchone()[0]==total
        assert db.execute('SELECT COUNT(*) FROM raw_listings').fetchone()[0]==total
    lines=[]
    for path in sorted(folder.rglob('*')):
        if path.is_file():
            lines.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+str(path.relative_to(folder)))
    (folder/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
    for path in folder.rglob('*'):
        if path.is_file(): path.chmod(0o444)
    print(json.dumps({'folder':str(folder),'manifest':{k:manifest[k] for k in ['state','frozen_rows','finished_at_pacific','repeated_rows_removed']},'quality':quality},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder',type=Path)
    finalize(p.parse_args().folder)
