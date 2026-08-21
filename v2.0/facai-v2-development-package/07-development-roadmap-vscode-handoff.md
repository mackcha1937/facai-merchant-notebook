# 分阶段开发与VS Code交接说明

版本：v2.0-rc1  
状态：开发交接候选版·待用户最终确认  
日期：2026-08-21

## 1. 开发前指令

开发Agent必须先完整阅读本目录README和01～07号文档、contracts、data、prompts、eval；先审计现有V1代码和数据库Migration，不直接重写。

## 2. 阶段与停点

### 阶段0：代码审计与模型能力验证

- V1差异清单和数据备份；
- DeepSeek真实模型ID、JSON、工具调用、超时；
- Embedding候选适配器只做接口骨架和测试；
- 输出迁移计划，不改业务数据；
- 提供 `/verify/v2-stage-0` 后暂停。

### 阶段1：数据基础与权限

- CustomerFact、Product、KnowledgeVersion、Conversation、Recommendation、Release表；
- owner/admin RBAC；
- Migration、回滚、种子数据；
- V1账本回归；
- `/verify/v2-stage-1` 后暂停。

### 阶段2：双端应用壳与闭环

- 手机顶部今日事项、左侧精简入口、全部客户；
- Web左栏/主对话/右侧工作区；
- UI Block、ContextStack、返回、收起、草稿、系统返回键；
- 语音转写可见和等价操作接口；
- 使用Mock数据，不接推荐；
- `/verify/v2-stage-2` 后暂停。

### 阶段3：多日会话与统一Proposal

- Thread/Session/摘要/PendingAction/绝对日期；
- 一次统一确认、事务、幂等、跨设备冲突；
- 历史卡最新数据；
- `/verify/v2-stage-3` 后暂停。

### 阶段4：客户事实和产品实体

- 事实提取与确认；
- 产品exact/alias/fuzzy/embedding候选；
- 新产品草稿、合并、知识状态；
- 所有手动与语音闭环；
- `/verify/v2-stage-4` 后暂停。

### 阶段5：RAG知识链路

- 知识录入/确认/版本/文档/Embedding/索引；
- 混合检索、metadata过滤、注入防护、证据；
- 店主只读状态和管理员管理；
- `/verify/v2-stage-5` 后暂停。

### 阶段6：推荐、话术和反馈

- 三类候选、强制过滤、评分、Top3、红点/未处理；
- RAG解释、安全话术、复制/改写；
- 反馈提取、稍后、客户拒绝；
- 降级模板；
- `/verify/v2-stage-6` 后暂停。

### 阶段7：AI测评与管理员发布

- JSONL测评Runner；
- 工作簿人工记录导入/导出；
- 草稿→测评→发布→回滚；
- 安全门槛；
- `/admin/evaluations` 和 `/verify/v2-stage-7` 后暂停。

### 阶段8：完整联调

- 手机/微信WebView/电脑；
- 多日、多设备、网络、模型、索引、备份恢复；
- 性能、可访问性、安全；
- 完整测试报告和已知限制；
- 不自动公开部署。

## 3. 每阶段反馈格式

```text
阶段：
完成内容：
数据Migration：
自动测试：
AI测评：
手机验证地址：
电脑验证地址：
管理员验证地址（如适用）：
已知限制：
验收步骤：
当前已暂停，等待“阶段X确认通过”。
```

## 4. 给VS Code开发Agent的首条指令

```text
完整阅读 facai-v2-development-package。v2.0-rc1是V2候选基线，V1数据和已有代码不得删除、重置或覆盖。

本轮只做阶段0：审计现有代码、数据库和文档差异，验证模型与配置能力，输出迁移计划和风险。不要实现后续功能。不要把API Key写进代码、前端、日志或文档。完成后提供验证链接、测试结果并暂停。
```

## 5. 开发完成定义

代码、Migration、自动测试、AI测评、双端验证、异常/返回闭环、权限、安全、文档和备份说明全部满足才算完成。页面“看起来能用”不等于完成。

