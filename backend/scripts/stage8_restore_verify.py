"""把SQLite在线备份恢复到一个全新文件并验证数据摘要、完整性和外键。"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


CORE_TABLES = (
    "tenants", "customers", "customer_aliases", "services", "packages", "ledger_entries",
    "customer_facts", "products", "product_aliases", "product_knowledge_versions",
    "service_knowledge_versions", "knowledge_documents", "knowledge_chunks", "embedding_records",
    "conversation_threads", "conversation_sessions", "messages", "message_blocks", "pending_actions",
    "recommendation_rules", "recommendations", "message_drafts", "follow_up_feedback",
    "ai_config_drafts", "evaluation_runs", "evaluation_case_results", "prompt_releases",
    "rag_releases", "recommendation_releases", "release_audits",
)


def _table_digest(connection: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    for table in CORE_TABLES:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,),
        ).fetchone()
        if not exists:
            continue
        digest.update(table.encode())
        cursor = connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid')
        digest.update(json.dumps([item[0] for item in cursor.description]).encode())
        for row in cursor:
            digest.update(json.dumps(row, ensure_ascii=False, default=str, separators=(",", ":")).encode())
    return digest.hexdigest()


def restore_and_verify(source: Path, restored: Path) -> dict:
    source = source.resolve()
    restored = restored.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"源数据库不存在：{source}")
    if restored.exists():
        raise FileExistsError(f"恢复目标已存在，拒绝覆盖：{restored}")
    restored.parent.mkdir(parents=True, exist_ok=True)

    source_connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    restored_connection = sqlite3.connect(restored)
    try:
        source_digest = _table_digest(source_connection)
        source_connection.backup(restored_connection)
        restored_connection.execute("PRAGMA foreign_keys=ON")
        integrity = restored_connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_errors = restored_connection.execute("PRAGMA foreign_key_check").fetchall()
        restored_digest = _table_digest(restored_connection)
        migration = restored_connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    finally:
        source_connection.close()
        restored_connection.close()

    result = {
        "status": "通过" if integrity == "ok" and not foreign_key_errors and source_digest == restored_digest else "失败",
        "migration": migration,
        "integrity": integrity,
        "foreign_key_errors": len(foreign_key_errors),
        "source_digest": source_digest,
        "restored_digest": restored_digest,
    }
    if result["status"] != "通过":
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--restored", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(restore_and_verify(args.source, args.restored), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
