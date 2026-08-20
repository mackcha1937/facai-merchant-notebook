# 后端分层与分阶段开发文档

版本：v1.0  
状态：开发基线·已确认  
日期：2026-08-20

## 1. 文档目的

本文档约束后端的职责、分层、数据模型、Agent安全边界和分阶段交付方式。开发必须逐阶段完成，每一阶段都通过临时前端页面提供可见验证结果，并在用户确认后才能继续。

## 2. 技术边界

### 2.1 当前建议

- 前端：React；
- 后端：FastAPI；
- 数据库：SQLite；
- ORM与迁移工具：开发时选择与 FastAPI 兼容的成熟方案；
- 模型接口：由后端封装的 DeepSeek 适配器；
- 配置：环境变量加本地配置文件；
- 运行环境：用户电脑本地。

### 2.2 禁止事项

- 前端直接调用模型；
- API Key 出现在前端、代码、日志或版本库；
- Agent 直接访问数据库；
- 使用模型生成的余额作为权威值；
- 未经确认执行 Agent 写操作；
- 在当前测试版使用真实客户敏感资料。

## 3. 后端分层

建议目录职责如下，实际文件名可在不改变边界的情况下微调：

```text
backend/
  app/
    api/                  # HTTP 路由、请求与响应
    application/          # 用例编排：创建套餐、核销、查询、恢复
    domain/               # 业务实体、值对象和强制规则
    repositories/         # 数据访问接口
    infrastructure/       # SQLite实现、模型客户端、配置、日志
    agent/                # Agent结构、解析器、输出校验
    prompts/              # 系统提示词单一来源与历史版本
    schemas/              # API和Agent的结构化模型
    core/                 # 配置、错误处理、启动逻辑
    main.py
  tests/
  .env.example
```

### 3.1 API层

负责：

- 解析HTTP请求；
- 调用应用层用例；
- 返回统一响应；
- 将业务错误转换为可理解的中文错误。

不得负责：套餐余额计算、客户匹配决策、数据库SQL或模型提示词拼装。

### 3.2 应用层

负责组织完整用例：

- 新建客户；
- 创建套餐；
- 核销套餐；
- 记录一次性服务；
- 记录商品购买；
- 查询客户；
- 软删除和恢复；
- 生成预览并提交确认。

应用层调用领域规则和仓储接口，不依赖具体数据库实现。

### 3.3 领域层

负责不可绕过的规则：

- 次数必须为正整数；
- 剩余次数不能为负；
- 累计已用加剩余等于总次数；
- 多张同类卡不能自动选择；
- 一次性服务不改变套餐；
- 商品记录不改变库存；
- 已停用或删除的服务不能建立新套餐；
- 写入前必须重新校验目标数据状态。

这些规则不能只存在于系统提示词中。

### 3.4 仓储层

定义客户、服务、套餐、记录、回收站和提示词版本的数据访问接口。领域和应用层不直接编写SQLite查询。

### 3.5 Agent层

负责：

- 组装最少必要上下文；
- 加载当前系统提示词版本；
- 调用模型适配器；
- 解析和验证固定JSON；
- 返回操作建议或澄清问题。

不得负责：直接写库、删除、套餐选择、权威余额计算。

### 3.6 基础设施层

负责：

- SQLite连接和仓储实现；
- DeepSeek HTTP客户端；
- 环境变量；
- 日志脱敏；
- 数据库初始化和迁移。

## 4. 核心数据模型

### 4.1 Customer

| 字段 | 说明 |
|---|---|
| id | 内部ID |
| display_name | 客户化名，必填 |
| created_at / updated_at | 创建和更新时间 |
| deleted_at | 软删除时间，空表示有效 |

### 4.2 CustomerAlias

| 字段 | 说明 |
|---|---|
| id | 内部ID |
| customer_id | 所属客户 |
| alias | 搜索别名 |
| deleted_at | 软删除时间 |

### 4.3 Service

| 字段 | 说明 |
|---|---|
| id | 内部ID |
| name | 服务名称 |
| status | active / inactive |
| deleted_at | 软删除时间 |

### 4.4 Package

| 字段 | 说明 |
|---|---|
| id | 套餐卡ID |
| customer_id | 客户 |
| service_id | 服务项目 |
| total_count | 总次数 |
| opening_used_count | 首次导入纸质账本时的历史已用次数，默认0 |
| price | 可选价格，使用定点小数或整数分 |
| purchased_on | 可选购买日期 |
| status | active / exhausted / inactive |
| deleted_at | 软删除时间 |

`used_count` 和剩余次数不作为任意可写字段。权威累计已用由
`opening_used_count + SUM(未删除的 package_consumption.quantity)` 计算，剩余次数由
`total_count - used_count` 计算。这样删除或恢复核销记录时，余额会随有效账本事实自动回退或恢复。

套餐状态由权威余额派生：剩余为0时为 `exhausted`；被店主停用时为 `inactive`；否则为 `active`。如数据库缓存这些派生字段，必须在同一事务中更新并可由账本重建。

### 4.5 LedgerEntry

统一记录业务事实：

| 字段 | 说明 |
|---|---|
| id | 记录ID |
| customer_id | 客户 |
| entry_type | package_purchase / package_consumption / one_time_service / product_purchase |
| package_id | 套餐相关记录可填 |
| service_id | 服务相关记录可填 |
| product_name | 商品记录可填 |
| quantity | 次数或商品数量 |
| price | 可选价格 |
| occurred_on | 发生日期 |
| original_input | 原始自然语言，可选 |
| agent_prompt_version | 使用的提示词版本，可选 |
| deleted_at | 软删除时间 |

### 4.6 PromptVersion

| 字段 | 说明 |
|---|---|
| id | 版本ID |
| version | 递增版本号 |
| content | 提示词正文 |
| created_at | 保存时间 |
| is_active | 当前版本标记 |

### 4.7 AgentProposal

建议保留短期预览状态：

| 字段 | 说明 |
|---|---|
| id | 建议ID |
| original_input | 原始输入 |
| parsed_json | 通过结构校验的建议 |
| prompt_version | 提示词版本 |
| status | pending / confirmed / cancelled / expired |
| created_at | 创建时间 |
| confirmed_at | 确认写入时间，可选 |

确认写入时必须根据当前数据库状态重新校验，不直接相信旧预览。

### 4.8 客户查询读模型

为避免前端自行拼接余额和最后消费信息，后端提供专用读模型：

- `CustomerSummary`：客户ID、化名、别名、最后消费服务、最后消费日期、服务类型数量；
- `CustomerOverview`：客户基本信息、最后消费日期、服务类型摘要、有效套餐数量、最近动态；
- `CustomerServiceDetail`：当前服务信息、该服务的多张套餐卡、一次性服务标记和该服务历史。

“最后消费”只统计未删除的 `package_consumption` 与 `one_time_service`，按 `occurred_on` 和创建时间确定最新一条；`package_purchase` 与 `product_purchase` 不参与计算。从未消费的客户返回 `null`。

### 4.9 删除、编辑与恢复规则

- 账本事实采用软删除；删除套餐核销后，权威已用次数和剩余次数按未删除记录重新计算；
- 恢复核销记录前必须重新校验套餐、客户、服务及恢复后的余额，恢复会导致余额小于0时拒绝；
- 修改已入账的核销记录采用“软删除旧记录 + 创建更正记录”的事务方式，保留审计线索，不直接覆盖历史事实；
- 恢复父对象时不得自动恢复所有子对象，必须明确选择并通过关联校验；
- 所有余额变化、账本记录和关联状态更新必须在同一数据库事务中完成。

## 5. Agent结构化协议

建议顶层结构：

```json
{
  "customer_query": "小蓝",
  "customer_match": {
    "status": "exact|fuzzy|not_found|ambiguous",
    "candidate_ids": []
  },
  "actions": [
    {
      "type": "consume_service",
      "service_name": "面部清洁",
      "quantity": 1,
      "price": null
    }
  ],
  "needs_clarification": false,
  "clarification_question": null
}
```

后端必须忽略或拒绝白名单外字段和操作。客户候选、套餐候选及权威余额应由后端搜索和计算，不能仅采用模型生成的ID或数字。

## 6. API范围

### 6.1 健康与配置

- `GET /api/health`：后端状态；
- `GET /api/config/model-status`：只返回是否配置，不返回密钥；
- `POST /api/model/check`：执行最小连通性检查。

### 6.2 客户与别名

- `GET /api/customers?search=&sort=last_consumed_desc`：列表、别名搜索和最后消费排序；
- `POST /api/customers`；
- `GET /api/customers/{id}`；
- `GET /api/customers/{id}/overview`：客户概览读模型；
- `GET /api/customers/{id}/services`：该客户服务类型摘要；
- `GET /api/customers/{id}/services/{service_id}`：服务详情、多卡与服务历史；
- `PATCH /api/customers/{id}`；
- `DELETE /api/customers/{id}`：软删除；
- `POST /api/customers/{id}/restore`。

### 6.3 服务项目

- `GET /api/services`；
- `POST /api/services`；
- `PATCH /api/services/{id}`；
- `DELETE /api/services/{id}`；
- `POST /api/services/{id}/restore`。

### 6.4 套餐和账本

- `POST /api/customers/{id}/packages`；
- `PATCH /api/packages/{id}`；
- `DELETE /api/packages/{id}`；
- `POST /api/packages/{id}/restore`；
- `GET /api/customers/{id}/ledger`；
- `POST /api/customers/{id}/ledger`：手动新增一次性服务、商品购买或其他白名单内记录；
- `PATCH /api/ledger/{id}`：以更正事务处理，不直接覆盖原始账本事实；
- `DELETE /api/ledger/{id}`：软删除并重新计算受影响套餐余额；
- `POST /api/ledger/{id}/restore`。

### 6.5 Agent与确认

- `POST /api/agent/interpret`：生成建议，不写库；
- `GET /api/agent/proposals/{id}`：获取预览；
- `POST /api/agent/proposals/{id}/confirm`：重新校验并写入；
- `POST /api/agent/proposals/{id}/cancel`；
- `POST /api/customers/search-fuzzy`：候选匹配。

确认接口必须满足：

- 只允许确认 `pending` 状态的建议，同一建议只能成功确认一次；
- 有歧义的项目必须先解决或从建议中移除；
- 对建议中全部剩余操作先统一校验，再在单个数据库事务中写入；
- 任一操作失败时整组回滚，不允许部分成功；
- 返回每项实际入账结果、发生日期及后端计算的最新余额。

### 6.6 回收站

- `GET /api/trash`：按类型列出软删除数据；
- 具体恢复使用各资源恢复接口。

### 6.7 提示词管理

- `GET /api/settings/prompt`；
- `GET /api/settings/prompt/versions`；
- `POST /api/settings/prompt/versions`：保存新版本；
- `POST /api/settings/prompt/versions/{id}/activate`：切换或回退。

本地测试版可无账号，但这些接口在未来公开部署前必须加入仅管理员可用的权限控制。

## 7. 阶段开发与停点

## 阶段 0：项目骨架与模型连通性

### 目标

建立可运行的前后端骨架、SQLite连接和安全配置，验证模型 API 能否使用。

### 后端交付

- FastAPI启动；
- `/api/health`；
- `.env.example` 与 `.gitignore`；
- SQLite连接测试；
- DeepSeek适配器；
- 最小模型连通性检查；
- 日志不得输出API Key。

### 临时前端验证页

```text
http://127.0.0.1:5173/verify/stage-0
```

页面展示：前端状态、后端状态、数据库状态、模型配置状态和模型连通性结果，不展示密钥。

后端接口文档：

```text
http://127.0.0.1:8000/docs
```

### 验收停点

提供启动命令、验证地址和检查结果后暂停。若模型 ID 不被接受，停止并请用户核对。只有用户回复“阶段0确认通过”后进入阶段1。

## 阶段 1：基础账本、服务管理与回收站

### 目标

不依赖Agent，先验证数据模型和人工账本能够准确工作。

### 后端交付

- Customer、CustomerAlias、Service、Package、LedgerEntry；
- 客户、服务、套餐和记录CRUD；
- 客户搜索；
- 客户列表最后消费聚合与倒序；
- 客户概览、服务类型摘要和服务详情读模型；
- 套餐余额后端计算；
- 二次确认所需预检查；
- 软删除、回收站和恢复；
- 初始化化名数据导入脚本或种子数据。

### 临时前端验证页

```text
http://127.0.0.1:5173/verify/stage-1
```

页面提供客户列表、搜索、客户详情、服务管理、手动套餐编辑和回收站。

### 验收停点

至少验收：新增客户、创建套餐、编辑服务、删除恢复、余额一致。完成后暂停，只有用户回复“阶段1确认通过”后进入阶段2。

## 阶段 2：Agent解析、提示词管理与确认预览

### 目标

只验证“自然语言到结构化建议”，本阶段仍不允许Agent建议写入数据库。

### 后端交付

- 系统提示词加载；
- PromptVersion版本管理；
- 独立提示词管理API；
- Agent固定JSON结构；
- 模型输出校验；
- 允许操作白名单；
- 客户与服务模糊候选；
- 新客户识别；
- AgentProposal预览状态；
- 错误、澄清和无匹配状态。

### 临时前端验证页

```text
http://127.0.0.1:5173/verify/stage-2
```

页面支持输入测试表达并查看逐项解析结果，但确认按钮明确标记为“本阶段不写入”。

提示词管理页：

```text
http://127.0.0.1:5173/settings/prompt
```

### 验收停点

使用PRD中的10条表达测试，核对拆分、新客户、近似客户、服务近似匹配和澄清结果。完成后暂停，只有用户回复“阶段2确认通过”后进入阶段3。

## 阶段 3：确认写入、余额计算与查询

### 目标

打通完整的自然语言记账和查询闭环。

### 后端交付

- 预览逐项修改后的后端校验；
- Proposal确认和取消；
- 新客户确认创建；
- 套餐购买；
- 套餐核销；
- 一次性服务；
- 商品购买；
- 多项操作统一确认和整组事务回滚；
- Proposal幂等确认，防止重复入账；
- 多张同类卡人工选择；
- 余额不足保护；
- 模糊查询最多3位候选；
- 结果反馈文案所需结构化数据；
- 原始输入与提示词版本记录。

### 临时前端验证页

```text
http://127.0.0.1:5173/verify/stage-3
```

页面打通：输入 → 解析 → 修改 → 确认 → 写入 → 结果反馈 → 客户详情核对。

### 验收停点

逐条核对PRD验收场景，重点确认余额、多卡选择、新客户创建和一次性服务。完成后暂停，只有用户回复“阶段3确认通过”后进入阶段4。

## 阶段 4：联调、测试与本地验收

### 目标

修复阶段内缺陷，形成可供店主本地体验的测试版。

### 后端交付

- 领域规则单元测试；
- API集成测试；
- 10条自然语言回归样例；
- 异常输入和模型失败处理；
- 提示词版本回退测试；
- 软删除和恢复一致性测试；
- 删除、恢复核销记录后的余额重算测试；
- 最后消费口径和客户排序测试；
- 多项确认全部成功或全部回滚测试；
- 本地数据库备份说明；
- 启动、停止和配置说明。

### 临时前端验证页

```text
http://127.0.0.1:5173/verify/stage-4
```

页面提供完整验收入口和测试状态摘要。

### 最终停点

提供本地访问地址、启动方式、测试报告、已知限制和后续建议，然后暂停。用户确认前不得转入公开部署、邀请码或真实数据阶段。

## 8. 每阶段交付格式

开发任务在每阶段结束时必须按以下格式反馈：

```text
阶段：
完成内容：
未完成或已知限制：
自动测试结果：
前端验证地址：
后端接口地址：
启动方式：
请按以下步骤验收：
1.
2.
3.

当前已暂停，等待你回复“阶段X确认通过”。
```

## 9. 安全与数据保护

- `.env` 仅本地保存并加入 `.gitignore`；
- 提供 `.env.example`，只含变量名；
- 日志过滤认证头、API Key和完整模型请求；
- 模型只收到本次任务所需的化名上下文；
- Agent返回必须进行服务端结构校验；
- 提示词不是安全边界，白名单和领域规则为最终边界；
- SQLite文件放在明确的数据目录，提供本地备份方法；
- 公开部署前必须另做认证、HTTPS、权限、密钥轮换、审计和隐私评估。

## 10. 测试重点

### 10.1 领域规则测试

- 不能核销0次、负数或超过余额的次数；
- 多张同类卡不自动选择；
- 一次性服务不改变套餐；
- 软删除数据不出现在正常查询；
- 恢复后余额和关联不变。
- 删除核销记录后余额回退，恢复后余额重新扣减；
- 套餐购买和商品购买不改变“最后消费”；
- 多项确认中任一项失败时不得留下部分记录。

### 10.2 Agent协议测试

- 白名单外操作被拒绝；
- 非JSON或缺字段结果被拒绝；
- 多项服务正确拆分；
- 新客户不自动创建；
- “脸”建议匹配为面部清洁；
- 模糊客户查询最多返回3位；
- 提示词变化不能绕过后端规则。

### 10.3 安全测试

- 前端构建文件不包含API Key；
- 日志不包含API Key；
- 模型不可执行删除；
- 未确认的Proposal不改变数据库；
- 测试数据库只含化名数据。

## 11. 后续阶段（不在本次开发范围）

- 邀请码和正式身份认证；
- 公开部署及HTTPS；
- 手机和微信内体验验证；
- 真实客户数据的隐私与权限设计；
- 到店提醒；
- 在线表格导出或同步；
- 商品库存；
- 多店和多员工。
