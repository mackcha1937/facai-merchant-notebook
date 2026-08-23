# 03 · 备份恢复演练

对正式本地SQLite库执行只读源在线备份，恢复目标为全新临时文件 `/private/tmp/facai-stage8-restore-20260823.db`，未替换或写回正式库。

- Migration：`0020_stage7_evaluation_release`；
- integrity_check：ok；
- foreign_key_check：0错误；
- 30张核心表源摘要：`ecde1c6ea0836d80b51d49ed1fa3314757ef2bc24bfeb49a76a71fc47d66823d`；
- 恢复库摘要：同上；
- 覆盖保护：目标已存在时拒绝覆盖；
- 恢复库只用于阶段8只读性能和浏览器验收，结束后删除。

工具：`backend/scripts/stage8_restore_verify.py --source SOURCE --restored NEW_TARGET`。
