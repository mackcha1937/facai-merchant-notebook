# 05 · Migration与数据完整性报告

## 增量表审计

0007 已存在以下空表，0019 没有重复创建：

- `recommendation_rules`
- `recommendations`
- `message_drafts`
- `follow_up_feedback`

0019 只增补阶段6字段、外键、唯一约束和索引，并新增此前不存在的 `recommendation_action_audits`。Migration 同时兼容 ORM `create_all` 预建的空动作审计表：检测后补 tenant 外键、推荐外键、唯一约束和索引，不重复造表。该真实兼容场景已新增自动化回归。

## 正式数据库

- 升级：`0018_stage5_knowledge_rag → 0019_stage6_recommendation_feedback`。
- 核心数据 SHA-256 升级前后均为 `6e2e8fa5950779681cd725ce23afb46131a76dac7ce2ee6a4a8910494d25c115`。
- `PRAGMA integrity_check=ok`；`PRAGMA foreign_key_check` 无结果。
- 业务计数保持 customers 4、services 5、packages 3、ledger 4、facts 0、products 1、knowledge documents 0。
- 阶段6正式表保持 recommendation rules 0、recommendations 0、message drafts 0、feedback 0、action audits 0；未种虚构规则或推荐。

首次正式升级曾遇到 ORM 已预建空 `recommendation_action_audits`，Migration 因重复建表停止且 Alembic 仍为0018。核对业务哈希、integrity 和所有阶段6表均为0行后，删除失败留下的唯一空 `_alembic_tmp_recommendation_rules`，加固0019检测逻辑并续跑成功；没有删除或改写业务数据。

## 克隆库往返

正式库克隆执行 `0019 → 0018 → 0019`。三个检查点核心 SHA 均为上述值，`integrity_check=ok`、foreign key check 无错误，阶段6空表保持0行。临时克隆验证后已删除。

真实 `backend/.env` SHA-256 前后均为 `b83aadad2d9b8f3f3a8bbeb51b7385cefa7a54ad673154cbe3a25056ba35724b`，未修改。
