"""0018：阶段5知识版本、Chunk 与本地索引状态增量加固。

revision: 0018_stage5_knowledge_rag
down_revision: 0017_stage4_entity_hardening

复用 0005 已创建的知识版本、KnowledgeDocument 与 EmbeddingRecord；
本迁移只增加阶段5字段/索引，并创建此前不存在的 knowledge_chunks。
"""
from alembic import op
import sqlalchemy as sa


revision = "0018_stage5_knowledge_rag"
down_revision = "0017_stage4_entity_hardening"
branch_labels = None
depends_on = None


def _extend_version_table(table: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.add_column(sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"))
        batch.add_column(sa.Column("checksum", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("source_type", sa.String(length=30), nullable=True))
        batch.add_column(sa.Column("source_name", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("supersedes_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("withdrawn_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.create_unique_constraint(f"uq_{table}_tenant_entity_version", ["tenant_id", "entity_id", "version"])
    op.create_index(f"ix_{table}_current", table, ["tenant_id", "entity_id", "status", "version"])


def upgrade() -> None:
    _extend_version_table("product_knowledge_versions")
    _extend_version_table("service_knowledge_versions")

    with op.batch_alter_table("knowledge_documents") as batch:
        batch.add_column(sa.Column("source_type", sa.String(length=30), nullable=True))
        batch.add_column(sa.Column("source_name", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("withdrawn_at", sa.DateTime(), nullable=True))
        batch.create_unique_constraint(
            "uq_knowledge_documents_entity_version",
            ["tenant_id", "entity_type", "entity_id", "knowledge_version"],
        )
    op.create_index(
        "ix_knowledge_documents_retrieval",
        "knowledge_documents",
        ["tenant_id", "entity_type", "entity_id", "confirmed", "active", "knowledge_version"],
    )

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("knowledge_chunks"):
        op.create_table(
            "knowledge_chunks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("checksum", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_knowledge_chunks_tenant"),
            sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], name="fk_knowledge_chunks_document"),
            sa.UniqueConstraint("tenant_id", "document_id", "chunk_index", name="uq_knowledge_chunks_document_index"),
        )
    else:
        # 本地 create_all 可能在 Alembic 版本更新前预建空表；不重复造表，
        # 只补齐 Migration 要求的 tenant 外键，保留任何既有行。
        foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys("knowledge_chunks")
        if not any(fk.get("referred_table") == "tenants" and fk.get("constrained_columns") == ["tenant_id"] for fk in foreign_keys):
            with op.batch_alter_table("knowledge_chunks") as batch:
                batch.create_foreign_key("fk_knowledge_chunks_tenant", "tenants", ["tenant_id"], ["id"])
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("knowledge_chunks")}
    if "ix_knowledge_chunks_tenant_id_document" not in indexes:
        op.create_index("ix_knowledge_chunks_tenant_id_document", "knowledge_chunks", ["tenant_id", "document_id", "status"])

    with op.batch_alter_table("embedding_records") as batch:
        batch.add_column(sa.Column("chunk_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("knowledge_version", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"))
        batch.add_column(sa.Column("error_code", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key("fk_embedding_records_chunk", "knowledge_chunks", ["chunk_id"], ["id"])
        batch.create_unique_constraint(
            "uq_embedding_records_checksum_model",
            ["tenant_id", "document_id", "embedding_provider", "embedding_model", "checksum"],
        )
    op.create_index(
        "ix_embedding_records_active_dimension",
        "embedding_records",
        ["tenant_id", "status", "embedding_provider", "embedding_model", "dimension"],
    )


def _shrink_version_table(table: str) -> None:
    op.drop_index(f"ix_{table}_current", table_name=table)
    with op.batch_alter_table(table) as batch:
        batch.drop_constraint(f"uq_{table}_tenant_entity_version", type_="unique")
        for column in ("updated_at", "withdrawn_at", "supersedes_id", "source_name", "source_type", "checksum", "status"):
            batch.drop_column(column)


def downgrade() -> None:
    op.drop_index("ix_embedding_records_active_dimension", table_name="embedding_records")
    with op.batch_alter_table("embedding_records") as batch:
        batch.drop_constraint("uq_embedding_records_checksum_model", type_="unique")
        batch.drop_constraint("fk_embedding_records_chunk", type_="foreignkey")
        for column in ("updated_at", "error_code", "status", "knowledge_version", "chunk_id"):
            batch.drop_column(column)
    op.drop_index("ix_knowledge_chunks_tenant_id_document", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index("ix_knowledge_documents_retrieval", table_name="knowledge_documents")
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.drop_constraint("uq_knowledge_documents_entity_version", type_="unique")
        for column in ("withdrawn_at", "active", "confirmed", "source_name", "source_type"):
            batch.drop_column(column)
    _shrink_version_table("service_knowledge_versions")
    _shrink_version_table("product_knowledge_versions")
