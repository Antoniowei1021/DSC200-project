UCSD 周边租房数据冻结快照

快照版本：ucsd_rentals_2026-11-16_102139_PT
采集开始（America/Los_Angeles）：2026-11-16T10:21:39.068444-08:00
采集完成（America/Los_Angeles）：2026-11-16T10:23:19.240148-08:00
采集日期：2026-11-16。UTC 时间另见 manifest.json。
数据来源：RentCast /v1/listings/rental/long-term
中心坐标：(32.8801, -117.2340)，近似校园参考点。
范围：10 英里直线半径；状态：Active。
最终冻结：2690 个不同 ID 的记录，等于全部请求返回的总量 2690。
请求数：7（六页完整采集 + 一次分页交界补查）。

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
保留全部 2690 条记录；缺失面积、异常价格及同一楼宇内不同房号均未删除。
挂牌租金尚未统一费用、优惠、家具、租期和整租/分租口径；这些属于后续清洗工作。
不同房号可能共享楼宇或坐标，统计上不一定独立。
公开发布原始数据前需另核对供应商许可。
