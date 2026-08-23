# 05 · Migration 与数据完整性报告

## 正式数据库升级

- 升级前：`0017_stage4_entity_hardening`，`PRAGMA integrity_check=ok`。
- 升级后：`0018_stage5_knowledge_rag`，`PRAGMA integrity_check=ok`，`PRAGMA foreign_key_check` 无结果。
- 核心数据 dump SHA-256 升级前后均为：`544e357a801bde9765b4665526ec8747bf21fdc2875ba7bc7a23c010f5b7165b`。

升级前后业务计数一致：

- customers 4；services 5；packages 3；ledger_entries 4；
- customer_facts 0；products 1；product_aliases 0；agent_proposals 8；
- knowledge_documents 0；knowledge_chunks 0；embedding_records 0。

正式库没有装载浏览器验收的虚构知识数据。

## 克隆库往返

对正式库克隆执行：

1. `0017 → 0018`
2. `0018 → 0017`
3. `0017 → 0018`

三个检查点的核心数据 SHA-256 都与升级前一致，`integrity_check=ok`，`foreign_key_check` 无错误。阶段1—4客户、服务、套餐、账本、事实、产品、别名和 Proposal 数据未被修改。

## 增量表审计

`0018` 没有重复创建阶段1已有的知识版本、文档或 Embedding 表。对于本地 ORM `create_all` 可能先行创建的空 `knowledge_chunks`，Migration 会检测既有表、保留行并补 tenant 外键/索引，避免重复建表失败。
