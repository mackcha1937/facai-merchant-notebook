# 03 · Embedding、检索与安全报告

## 本地 Embedding 契约

- 独立 `EmbeddingAdapter` 与 `VectorStore` 接口；业务层不依赖具体供应商。
- MVP 实现：`facai-local / char-ngram-sha256-v1 / 32`。
- 字符与二元字符 n-gram 经 SHA-256 映射并归一化，完全确定性、可版本化、无网络、无模型下载、无费用。
- checksum、provider、model、dimension 全部入库；checksum 不变时重建返回 `checksum_unchanged`，不重复生成记录。
- 检索只读取当前 adapter 的 provider/model/dimension，错误维度记录不会混入。

## 向量输入白名单

只有已确认发布的产品/服务知识和已发布规范可以进入 Chunk/Embedding。下列内容禁止进入：

- 客户姓名或当前 tenant 客户别名；
- 手机号、明确标识的微信号、邮箱；
- 完整画像、账本、余额、购买日期、未确认事实；
- 系统提示词、API Key、秘密；
- 提示注入、脚本、危险 HTML 和事件处理器。

`title` 与 `content` 使用完全相同的门禁，创建 Proposal 和确认时各校验一次。安全 HTML 标签会被去除；脚本和危险 HTML 整体拒绝。PII 查询不会进入 EmbeddingAdapter。

## 混合检索与强过滤

每次检索先强制过滤：

- tenant；
- entity type/id（指定时）；
- confirmed=true；
- active=true；
- document status=published；
- 当前 knowledge version；
- 产品/服务实体本身仍为 active。

排序为实体当前精确 > 标准名/别名/关键词 > 本地向量。结果按 document 去重，通常返回 3—5 条；指定实体只有一条有效当前知识时宁可少于 3 条，也不会使用相似实体补位。

## 安全降级

- 无证据：`knowledge_insufficient`，evidence 为空。
- 不安全查询：跳过向量层，只允许安全的确定性路径。
- Embedding 或索引失败：保留当前已确认文档，降级到实体精确/关键词，返回已有证据；不得生成新内容。
- 指定产品无当前知识：零召回，不以相似产品替代。
- RAG 输出仅为不可信证据，不提供推荐、评分、提醒或营销话术。
