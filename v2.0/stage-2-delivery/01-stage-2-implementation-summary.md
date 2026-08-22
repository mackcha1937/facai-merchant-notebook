# 01 · 阶段2实现总结

版本：v2.0-rc1 阶段2
归档日期：2026-08-23
代码提交：`1cac323`
阶段1基线：`0c26bfb`

## 1. 阶段目标

阶段2按 `facai-v2-development-package/07-development-roadmap-vscode-handoff.md` 与
`stage-1-delivery/07-stage-2-plan.md` 实施，目标是建立双端应用壳和交互闭环基础：

- 手机端固定顶部、今日事项、左侧三个一级入口与全部客户；
- Web端固定左栏、持续主对话和右侧上下文工作区；
- 固定UI Block组件、ContextStack、逐层返回、草稿与列表状态恢复；
- SpeechToText Adapter接口和Mock转写流程；
- 全部使用合成Mock数据，不接真实推荐、RAG、Embedding或真实语音；
- 不修改V1权威账本数据，不进入阶段3的多日会话和统一Proposal实现。

## 2. 实际实现内容

### 2.1 后端

- 新增 `SpeechToTextAdapter` 抽象、转写结果和错误类型；
- 新增 `MockSpeechToTextAdapter`，支持成功、转写失败和网络失败演示；
- 新增 `/api/v2/stage2/status` 只读验证接口；
- 新增 `/api/v2/stage2/mock-speech` Mock转写接口；
- 两个接口都受 `ENABLE_STAGE2_VERIFY` 开关保护，默认关闭；
- 状态接口只返回表计数、摘要、Migration版本和能力边界，不返回客户身份字段或密钥；
- Mock语音只返回可编辑转写文本，不执行账本或其他业务写入。

### 2.2 前端

- 新增 `/app/chat`、`/app/customers`、`/app/manage` 三个V2路由；
- 新增手机顶部、左侧抽屉和电脑固定左栏；
- 新增桌面主对话＋右侧上下文工作区布局；
- 新增全部客户搜索、筛选、排序、客户档案和服务二级详情；
- 新增今日事项未处理数、未查看状态、逐条已读和处理状态的Mock逻辑；
- 新增文字输入、Mock语音、发送中、防重复和停止生成状态；
- 新增管理与设置分组和店主只读AI运行状态；
- 所有阶段2业务演示数据位于独立Mock fixture，并标记 `is_mock=true`。

## 3. 主要文件

### 3.1 后端

- `backend/app/api/routes/v2_stage2.py`
- `backend/app/infrastructure/stt/base.py`
- `backend/app/infrastructure/stt/mock.py`
- `backend/app/infrastructure/stt/__init__.py`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/tests/test_stage2.py`

### 3.2 前端应用壳与页面

- `frontend/src/pages/v2/AppShell.jsx`
- `frontend/src/pages/v2/ChatView.jsx`
- `frontend/src/pages/v2/VerifyV2Stage2.jsx`
- `frontend/src/main.jsx`
- `frontend/src/styles/stage2.css`

### 3.3 前端组件与状态

- `frontend/src/components/v2/TopBar.jsx`
- `frontend/src/components/v2/Drawer.jsx`
- `frontend/src/components/v2/LeftNav.jsx`
- `frontend/src/components/v2/ChatComposer.jsx`
- `frontend/src/components/v2/ConfirmCard.jsx`
- `frontend/src/components/v2/ReceiptCard.jsx`
- `frontend/src/components/v2/CustomerIndexCard.jsx`
- `frontend/src/components/v2/CustomerRecordCard.jsx`
- `frontend/src/components/v2/ServiceDetailCard.jsx`
- `frontend/src/components/v2/ProductMatchCard.jsx`
- `frontend/src/components/v2/TodayTaskCard.jsx`
- `frontend/src/lib/contextStack.js`
- `frontend/src/lib/todayTasks.js`
- `frontend/src/services/mockSpeech.js`
- `frontend/src/fixtures/mock/stage2.js`

## 4. 手机端与Web端应用壳

### 手机端

- 360～430px宽度下显示固定顶部；
- 顶部提供菜单和今日事项入口；
- 抽屉一级入口仅包含“对话、全部客户、管理与设置”；
- 上下文工作区以覆盖层显示，显式返回按钮可逐层返回；
- 输入区使用安全区底部间距，主对话保留在应用壳内。

### Web端

- 768px及以上显示固定左侧导航；
- 中间持续显示主对话；
- 客户、今日事项和管理详情显示在右侧工作区；
- 打开右侧工作区不会替换主对话组件。

## 5. UI Block与ContextStack

阶段2实现了以下固定组件形态：ConfirmCard、ReceiptCard、CustomerRecordCard、
ProductMatchCard、TodayTaskCard、CustomerIndexCard和ServiceDetailCard。

ContextStack保存视图类型、来源、查询、筛选、排序、滚动位置和输入草稿，显式按钮路径已支持：

```text
服务详情 → 客户档案 → 全部客户 → 对话
管理详情 → 管理与设置 → 对话
今日事项 → 来源工作区
```

当前组件集合尚未与 `contracts/ui-block.schema.json` 六类Block形成完整一一映射，
Recommendation、Undo等Block没有在阶段2实现；浏览器/系统返回键、焦点管理和客户档案收起也仍有缺口。
这些限制详见 `02-interaction-acceptance-report.md`，不得据此宣称阶段2已经具备完整生产交互能力。
