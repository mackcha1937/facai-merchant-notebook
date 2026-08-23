# 01 · 阶段4实现总结

版本：v2.0 阶段4

日期：2026-08-23

范围：客户事实和产品实体

## 1. 完成内容

- 客户事实从文本或语音转写中生成候选，展示证据、置信度、敏感等级和冲突；
- 事实在确认前不写库，确认后按类型版本化，旧值保留 `valid_to` 和 `superseded_by_id`；
- 删除已确认事实也必须经 Proposal，并保留撤销审计记录；
- 产品支持规范名、别名、品牌、规格、生命周期、知识完整度、版本和合并去向；
- 产品匹配依次返回精确、别名、模糊和本地名称语义候选，候选最多 3 个；
- 未识别产品先展示 ProductMatchCard，店主可选择已有产品或作为新产品；
- 新产品草稿、产品购买和同轮客户事实在一个数据库事务中提交；
- 产品新建和合并均先生成 Proposal，确认前不改变权威数据；
- 手动表单、文本和语音转写共用同一 Proposal、事务、幂等和冲突校验链路；
- 客户档案和管理页从后端权威读模型展示当前事实、产品和关联购买；
- `/verify/v2-stage-4` 提供只读匹配验证、实体状态和范围边界。

## 2. 安全边界

Agent 只生成候选和 Proposal。事实、产品、别名、产品购买与合并只能在店主确认、后端重新校验和数据库事务中写入。敏感事实单独展示，可在确认前移除。

## 3. 未扩大范围

本阶段没有建设知识文档、Chunk、EmbeddingRecord、向量库、RAG 检索或推荐算法。产品名称语义候选为请求内的本地字符特征计算，不落库、不读知识库，不属于 RAG。

## 4. 关键文件

- `backend/alembic/versions/0017_stage4_entity_hardening.py`
- `backend/app/application/fact_extraction_service.py`
- `backend/app/application/product_resolution_service.py`
- `backend/app/application/stage4_entity_service.py`
- `backend/app/application/confirmation_service.py`
- `backend/app/api/routes/v2_stage4.py`
- `frontend/src/pages/v2/VerifyV2Stage4.jsx`
- `frontend/src/components/v2/ProductMatchCard.jsx`
- `frontend/src/components/v2/ConfirmCard.jsx`

## 5. 停点

阶段4完成后暂停，等待人工验收。不得自动开始阶段5。
