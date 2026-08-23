# 04 · 本地性能基线

环境：127.0.0.1、恢复副本SQLite、单进程Uvicorn、真实模型关闭。每个接口40次顺序只读请求；该结果用于发现明显回退，不代表公网生产容量。

| 接口 | P50 | P95 | Max |
| --- | ---: | ---: | ---: |
| `/api/health` | 0.76ms | 1.11ms | 2.94ms |
| `/api/owner/customers` | 0.80ms | 0.96ms | 1.08ms |
| `/api/owner/today-tasks` | 0.78ms | 0.90ms | 0.98ms |
| `/api/v2-stage8/status` | 1.08ms | 1.37ms | 2.09ms |

限制：没有公网时延、PostgreSQL、并发压测、真实大数据量、队列或模型调用。本阶段不据此声称生产SLA。
