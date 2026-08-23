# 05 · Migration与数据完整性报告

阶段7复用0008既有治理表，0020只增量增加可追溯关联、评分字段、幂等约束和索引，不重复建表。

- 正式库升级：`0019_stage6_recommendation_feedback → 0020_stage7_evaluation_release`；
- 升级前备份：`backend/backups/app-pre-stage7-0020-20260823.db`；
- 临时库往返：0020升级→0019降级→0020再升级通过；
- 阶段1～6核心业务数据摘要升级前后均为 `8b5b961352a1e6c58e91755e75b778b71bfdc1f476596b6d17912948153e1abd`；
- 正式库 `integrity_check=ok`，foreign_key_check错误0；
- 正式库草稿、Run、Case、三类Release和ReleaseAudit均为0，未注入虚构数据。
