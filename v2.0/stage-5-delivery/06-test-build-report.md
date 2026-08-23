# 06 · 测试、构建与审计报告

## 自动测试

- 后端：253 passed（含阶段1—4全回归及阶段5知识、权限、版本、Migration、Embedding、检索、状态租户隔离与安全用例）。
- 前端：42 passed / 8 test files。
- 生产构建：Vite 通过，77 modules transformed。

阶段5重点覆盖：

- 当前实体 Top1、产品别名、服务知识、融合 3—5 条与文档去重；
- tenant / entity / confirmed / active / current version 强过滤；
- 跨 tenant、未确认、旧版、撤回、停用/合并实体零泄漏；
- 新版生效、旧证据可追溯；
- checksum 幂等、索引不重复、provider/model/dimension 隔离；
- 手机号、微信、邮箱、客户称呼、禁止字段、提示注入、脚本 HTML 门禁；
- title 与 content 同门禁，并在确认时复验防篡改；
- PII 查询不调用 EmbeddingAdapter；
- 适配器/索引失败安全降级；
- 确认前知识权威表零写入；
- 店主无知识写路由，管理员路由拒绝店主；
- Proposal 幂等、stale、跨店和事务边界；
- `0018 → 0017 → 0018` 与原数据完整性。
- 状态 API 四项计数全部限定当前 tenant；Chunk/Embedding 同时验证自身 tenant 与父 KnowledgeDocument tenant，异常错 tenant 子记录不计入。

## 外部调用

- DeepSeek：阶段5新增调用 0。
- 外部 Embedding：0。
- 模型下载：0。
- 自动测试全部使用本地确定性 Adapter 或网络替身/失败替身。

## 最终审计项目

- `git diff --check`
- Git 跟踪文件敏感信息扫描
- 后端 253 tests
- 前端 42 tests
- 生产构建 77 modules
- Migration 往返与 SQLite integrity/foreign key 检查
- Chromium 桌面和手机只读验收

最终命令结果同时记录于 `test-results.json`。
