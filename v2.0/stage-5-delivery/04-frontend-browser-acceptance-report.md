# 04 · 前端与真实浏览器验收报告

## 页面

- `/verify/v2-stage-5`：阶段5能力、运行时、Migration、测试状态与只读证据检索。
- `/app/manage` → “AI运行状态（只读）”：知识完整度、当前版本来源、索引和 RAG 状态。
- `/admin/knowledge`：管理员知识草稿、统一确认、版本历史、撤回 Proposal 和本地索引重建。

店主状态页没有知识/模型/Embedding/RAG 的输入框、开关、保存或重建按钮，也不返回 API Key 和提示词全文。管理员端只列出 active 实体用于新建知识 Proposal。

## 浏览器环境

使用隔离临时 SQLite 数据库和开发包 `knowledge-documents.jsonl` 的 5 条虚构资料。资料通过真实 Proposal → 管理员确认链路写入临时库：5 active Documents、5 Chunks、5 indexed EmbeddingRecords，`integrity_check=ok`。临时库不含真实客户资料，不影响正式数据库。

真实 Chromium 验收：

- 桌面 1440×1000：阶段5页加载 5 条当前知识；检索“净痘修护面霜”返回标准名精确 Top1 与本地向量补充证据；管理员页展示 version、source、checksum、provider/model/dimension 和索引状态。
- 店主桌面只读页：完整知识 5、indexed 5、failed 0、RAG available；右侧知识状态区输入控件 0、技术写按钮 0。
- 手机 390×844：阶段5验证页与店主只读页均无横向溢出，`scrollWidth=viewport=390`；版本、来源和索引状态可读。
- 浏览器验收没有点击知识发布、撤回或重建，只执行知识读取与只读检索；进入既有主应用时，阶段3页面按原逻辑自动写入了临时库的消息 `read_at` 阅读状态，该写入与知识/账本无关且随临时库删除。没有真实模型和外部 Embedding 请求。

## 结果

桌面、手机只读展示和本地证据检索通过。浏览器截图接口曾超时一次，但页面信息、语义树、实际输入/点击结果、视口和 DOM 控件审计均成功返回；不影响功能验收结论。
