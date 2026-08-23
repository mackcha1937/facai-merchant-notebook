# 美容店智能客户账本 MVP 文档包

版本：v1.0  
状态：开发基线·已确认  
日期：2026-08-20

## 文档索引

1. [项目立项文档](./01-project-charter.md)
2. [产品需求文档（PRD）](./02-product-requirements.md)
3. [后端分层与分阶段开发文档](./03-backend-development-plan.md)
4. [系统提示词管理规范](./04-system-prompt-management.md)
5. [前端开发文档](./05-frontend-development-spec.md)
6. [已确认交互原型](./design-reference/minimal-chat-customer-flow.html)

## 使用说明

- 本文档包只定义项目目标、需求和开发方式，不代表已经开始开发。
- 当前版本是本地电脑测试版，不公开部署，不使用邀请码，不录入真实客户敏感信息。
- 五份项目文档均属于同一套v1.0开发基线；实现时不得使用旧原型覆盖文档中的最新规则。
- 正式开发必须在用户明确回复“确认开始开发”后才开始。
- 开发严格按阶段进行。每个阶段完成后，启动本地临时验证页面，提供验证地址和验收清单，然后暂停；只有用户确认通过后才能进入下一阶段。
- 当前阶段性地址均为本机地址，只能在运行项目的电脑上访问。未来如需手机或远程访问，需另行确认部署方案与安全要求。

## 当前模型配置（待连通性验证）

```text
API Base URL: https://api.deepseek.com
Model ID: deepseek-v4-pro
API Key: 仅保存在后端本地 .env 文件中，不进入文档、前端或版本库
V2 真实模型开关: `ENABLE_V2_REAL_MODEL=false`（默认关闭）
```

模型 ID 必须在开发第 0 阶段通过最小请求验证。若接口拒绝该模型 ID，应暂停并请用户核对，不得自行猜测或替换。

V2 主对话只有在 `DEEPSEEK_API_KEY` 已配置且
`ENABLE_V2_REAL_MODEL=true` 时才会构造真实 `DeepSeekAdapter`。该开关仅能在
获得单独付费调用授权后手动开启；配置 Key 本身不代表授权。
