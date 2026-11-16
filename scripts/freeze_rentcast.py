"""Capture all matching RentCast pages and build a versioned SQLite snapshot.

Reads RENTCAST_API_KEY from the process environment. No key is written to disk.
Never overwrites a snapshot. At most 20 requests; no automatic retries.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo('America/Los_Angeles')
ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://api.rentcast.io/v1/listings/rental/long-term'
QUERY = {'latitude': 32.8801, 'longitude': -117.2340, 'radius': 10,
         'status': 'Active', 'limit': 500, 'includeTotalCount': 'true'}


def now():
    return datetime.now(timezone.utc)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def distance(row):
    if row.get('latitude') is None or row.get('longitude') is None:
        return None
    a,b,c,d=map(math.radians,[QUERY['latitude'],QUERY['longitude'],row['latitude'],row['longitude']])
    h=math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return 3958.7613*2*math.asin(min(1,math.sqrt(h)))


def build_database(folder, rows, provenance, manifest):
    fields = ['id','formattedAddress','city','state','zipCode','latitude','longitude',
              'propertyType','bedrooms','bathrooms','squareFootage','price','status',
              'listedDate','lastSeenDate','daysOnMarket']
    records=[]
    for row, source in zip(rows,provenance):
        r={k:row.get(k) for k in fields}
        r.update(source)
        r['distanceToCampusMiles']=distance(row)
        area,price=row.get('squareFootage'),row.get('price')
        r['advertisedRentPerSqft']=round(price/area,6) if isinstance(price,(int,float)) and isinstance(area,(int,float)) and area>0 else None
        records.append(r)
    write_json(folder/'listings.json',records)
    write_json(folder/'raw_listings.json',rows)
    numeric={'latitude','longitude','bedrooms','bathrooms','squareFootage','price',
             'daysOnMarket','distanceToCampusMiles','advertisedRentPerSqft'}
    integer={'sourcePageOffset'}
    names=list(records[0])
    definitions=[f'"{k}" '+('TEXT PRIMARY KEY' if k=='id' else 'REAL' if k in numeric else 'INTEGER' if k in integer else 'TEXT') for k in names]
    db=sqlite3.connect(folder/'rentals.sqlite')
    try:
        with db:
            db.execute('CREATE TABLE listings ('+', '.join(definitions)+')')
            db.executemany('INSERT INTO listings VALUES ('+','.join('?' for _ in names)+')',
                           [tuple(r[k] for k in names) for r in records])
            db.execute('CREATE TABLE raw_listings (id TEXT PRIMARY KEY, record_json TEXT NOT NULL)')
            db.executemany('INSERT INTO raw_listings VALUES (?,?)',[(r['id'],json.dumps(r,ensure_ascii=False)) for r in rows])
            db.execute('CREATE TABLE snapshot_metadata (key TEXT PRIMARY KEY, value_json TEXT NOT NULL)')
            db.executemany('INSERT INTO snapshot_metadata VALUES (?,?)',[(k,json.dumps(v,ensure_ascii=False)) for k,v in manifest.items()])
            db.execute('CREATE INDEX idx_listings_zip ON listings(zipCode)')
            db.execute('CREATE INDEX idx_listings_bedrooms ON listings(bedrooms)')
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('SELECT COUNT(*) FROM listings').fetchone()[0]==len(rows)
        assert db.execute('SELECT COUNT(*) FROM raw_listings').fetchone()[0]==len(rows)
        schema={k:('number' if k in numeric or k in integer else 'string') for k in names}
        write_json(folder/'schema.json',{
            'tables':{'listings':schema,'raw_listings':{'id':'string','record_json':'complete provider record'},
                      'snapshot_metadata':{'key':'string','value_json':'JSON-encoded value'}},
            'definitions':{'price':'Advertised monthly rent in USD; not total housing cost.',
                           'squareFootage':'Provider living area in square feet; null means missing.',
                           'bedrooms':'0 means studio; null means missing.',
                           'distanceToCampusMiles':'Haversine straight-line distance from (32.8801, -117.2340); not commute distance.',
                           'advertisedRentPerSqft':'price / positive squareFootage; otherwise null.',
                           'sourcePageOffset':'Offset used to retrieve the original page.',
                           'sourceRequestedAtUtc':'UTC request timestamp for the original page.',
                           'lastSeenDate':'Provider last-seen timestamp, not collection time or independent availability verification.'}})
    finally:
        db.close()
    return records


def main():
    key=os.environ.get('RENTCAST_API_KEY','').strip()
    if not key:
        raise SystemExit('Missing RENTCAST_API_KEY; no request sent.')
    start=now()
    folder=ROOT/'data/frozen'/('ucsd_rentals_'+start.astimezone(PACIFIC).strftime('%Y-%m-%d_%H%M%S')+'_PT')
    folder.mkdir(parents=True,exist_ok=False)
    (folder/'pages').mkdir()
    manifest={'snapshot_id':folder.name,'state':'collecting','source':BASE,
              'started_at_utc':start.isoformat(),'started_at_pacific':start.astimezone(PACIFIC).isoformat(),
              'timezone':'America/Los_Angeles','query':QUERY,'requests':[],
              'max_requests':20,'snapshot_semantics':'Sequential API capture over the recorded time interval; not an atomic provider snapshot.'}
    rows=[]
    provenance=[]
    try:
        for offset in range(0,10000,500):
            url=BASE+'?'+urllib.parse.urlencode({**QUERY,'offset':offset})
            stamp=now()
            entry={'offset':offset,'url':url,'requested_at_utc':stamp.isoformat()}
            manifest['requests'].append(entry)
            write_json(folder/'manifest.json',manifest)
            request=urllib.request.Request(url,headers={'X-Api-Key':key,'Accept':'application/json'})
            try:
                with urllib.request.urlopen(request,timeout=90) as response:
                    body=response.read()
                    entry.update(http_status=response.status,total_count=int(response.headers['X-Total-Count']))
            except urllib.error.HTTPError as error:
                entry['http_status']=error.code
                try:
                    details=json.loads(error.read())
                    entry['api_error']=str(details.get('error','')).replace(key,'[REDACTED]')
                    entry['api_message']=str(details.get('message','')).replace(key,'[REDACTED]')
                except (ValueError,AttributeError):
                    pass
                raise RuntimeError(f'HTTP {error.code}; no automatic retry') from None
            page=json.loads(body)
            if not isinstance(page,list) or not all(isinstance(r,dict) for r in page):
                raise ValueError('Unexpected API response schema')
            name=f'pages/offset_{offset:05d}.json'
            (folder/name).write_bytes(body)
            entry.update(received_at_utc=now().isoformat(),returned_rows=len(page),file=name,
                         sha256=hashlib.sha256(body).hexdigest())
            rows.extend(page)
            provenance.extend({'sourcePageOffset':offset,'sourceRequestedAtUtc':stamp.isoformat()} for _ in page)
            write_json(folder/'manifest.json',manifest)
            print(json.dumps({'offset':offset,'page_rows':len(page),'accumulated_rows':len(rows),
                              'reported_total':entry['total_count'],'saved_to':str(folder)},ensure_ascii=False),flush=True)
            if offset+len(page)>=entry['total_count'] or len(page)<500:
                break
        totals={p['total_count'] for p in manifest['requests']}
        ids=[r.get('id') for r in rows]
        complete=(len(totals)==1 and len(rows)==next(iter(totals)) and
                  all(isinstance(i,str) and i for i in ids) and len(set(ids))==len(rows))
        finish=now()
        manifest.update(finished_at_utc=finish.isoformat(),finished_at_pacific=finish.astimezone(PACIFIC).isoformat(),
                        downloaded_rows=len(rows),unique_ids=len(set(ids)),reported_totals=sorted(totals),
                        completeness_verified=complete)
        if not complete:
            raise RuntimeError('Pagination completeness check failed; raw pages preserved, snapshot not frozen.')
        manifest['state']='frozen'
        records=build_database(folder,rows,provenance,manifest)
        quality={
            'rows':len(rows),'unique_ids':len(set(ids)),
            'unique_addresses':len({r.get('formattedAddress','').strip().casefold() for r in rows}),
            'status_counts':dict(Counter(r.get('status') for r in rows)),
            'property_type_counts':dict(Counter(r.get('propertyType') for r in rows)),
            'missing_fields':{k:sum(r.get(k) is None for r in rows) for k in ['price','bedrooms','bathrooms','squareFootage','latitude','longitude','lastSeenDate']},
            'within_miles_counts':{str(n):sum(r['distanceToCampusMiles'] is not None and r['distanceToCampusMiles']<=n for r in records) for n in [1,2,3,5,10]},
            'outside_10_05_miles':sum(r['distanceToCampusMiles'] is not None and r['distanceToCampusMiles']>10.05 for r in records),
            'nonpositive_prices':sum(isinstance(r.get('price'),(int,float)) and r['price']<=0 for r in rows),
            'nonpositive_areas':sum(isinstance(r.get('squareFootage'),(int,float)) and r['squareFootage']<=0 for r in rows),
            'last_seen_range':[min(r['lastSeenDate'] for r in rows if r.get('lastSeenDate')),max(r['lastSeenDate'] for r in rows if r.get('lastSeenDate'))],
            'sqlite_integrity_check':'ok',
            'policy':'All downloaded records retained; no outlier removal or missing-value imputation.'}
        write_json(folder/'quality_report.json',quality)
        write_json(folder/'manifest.json',manifest)
        readme=f'''UCSD 周边租房数据冻结快照

版本：{folder.name}
采集开始（洛杉矶时间）：{manifest['started_at_pacific']}
采集完成（洛杉矶时间）：{manifest['finished_at_pacific']}
来源：RentCast rental listings API
查询：中心 (32.8801, -117.2340)，半径 10 英里（直线），status=Active。
完整性：接口各页总量一致，下载 {len(rows)} 条、唯一 ID {len(set(ids))} 个；已通过完整性核对。
请求次数：{len(manifest['requests'])}，每页最多 500 条。

使用文件
rentals.sqlite：固定数据库。listings 是分析表；raw_listings 保留供应商完整原记录；snapshot_metadata 是采集元数据。
listings.json：分析字段及距离、单位面积租金、原始页码与时间。
raw_listings.json：完整记录集合，不改写供应商字段。
pages/：逐次响应原始字节；manifest.json 保存查询、时间、数量与页面 SHA-256。
schema.json：字段类型及关键字段含义。
quality_report.json：缺失值、地理范围、状态等检查结果。
SHA256SUMS：全部快照文件的校验值（自身除外）。

冻结规则
本目录是版本化的原始数据基线；后续清洗、填补、异常值排除和图表应写入另一个目录。
新采集会生成新版本，不覆盖本目录。可以通过 SHA256SUMS 检查文件是否改变。
SQLite 建议只读打开：sqlite3.connect('file:/absolute/path/rentals.sqlite?mode=ro', uri=True)。
没有删除缺失值、异常价格或同一公寓内不同房号；没有保存 API key。

范围与局限
这是该供应商在采集窗口内对本查询返回的完整记录，不代表租房市场上的全部房源。
分页采集不是供应商提供的原子时间点快照；各页采集时刻已记录。
Active 与 lastSeenDate 由供应商提供，不代表我们独立确认仍可租。
租金为挂牌价格，未统一费用、优惠、租期、家具以及整租/分租口径。
同一楼宇的不同房号可能共享坐标，在统计上未必独立。
API key 与数据目录已从 Git 默认跟踪范围排除；公开发布数据前另核实供应商许可。
'''
        (folder/'README.txt').write_text(readme)
        sums=[]
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                sums.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+str(path.relative_to(folder)))
        (folder/'SHA256SUMS').write_text('\n'.join(sums)+'\n')
        print(json.dumps({'state':'frozen','folder':str(folder),'quality':quality},indent=2,ensure_ascii=False),flush=True)
    except Exception as error:
        manifest.update(state='incomplete',error=str(error).replace(key,'[REDACTED]'),stopped_at_utc=now().isoformat())
        write_json(folder/'manifest.json',manifest)
        raise SystemExit(f'Collection stopped: {manifest["error"]}. Files: {folder}')


if __name__=='__main__':
    main()
