"""阶段4产品实体仓储；所有读写在 SQL 层强制 tenant 边界。"""
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.tenant import get_current_owner_id, get_current_tenant_id
from app.domain.errors import DomainError, NotFoundError
from app.infrastructure.models import LedgerEntry, Product, ProductAlias


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def list_products(db: Session, *, include_inactive: bool = False) -> list[Product]:
    stmt = select(Product).where(
        Product.tenant_id == get_current_tenant_id(), Product.deleted_at.is_(None)
    )
    if not include_inactive:
        stmt = stmt.where(Product.lifecycle_status.in_(("draft", "active")))
    return list(db.scalars(stmt.order_by(Product.id)).all())


def get_product(db: Session, product_id: int, *, include_replaced: bool = False) -> Product | None:
    stmt = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == get_current_tenant_id(),
        Product.deleted_at.is_(None),
    )
    if not include_replaced:
        stmt = stmt.where(Product.lifecycle_status.in_(("draft", "active")))
    return db.scalar(stmt)


def list_aliases(db: Session, product_ids: list[int] | None = None) -> list[ProductAlias]:
    stmt = select(ProductAlias).where(
        ProductAlias.tenant_id == get_current_tenant_id(), ProductAlias.deleted_at.is_(None)
    )
    if product_ids is not None:
        if not product_ids:
            return []
        stmt = stmt.where(ProductAlias.product_id.in_(product_ids))
    return list(db.scalars(stmt.order_by(ProductAlias.id)).all())


def create_product(
    db: Session,
    *,
    canonical_name: str,
    brand: str | None = None,
    category: str | None = None,
    specification: str | None = None,
    lifecycle_status: str = "draft",
    knowledge_status: str = "incomplete",
) -> Product:
    product = Product(
        tenant_id=get_current_tenant_id(),
        owner_id=get_current_owner_id(),
        canonical_name=canonical_name.strip(),
        brand=brand.strip() if brand else None,
        category=category.strip() if category else None,
        specification=specification.strip() if specification else None,
        lifecycle_status=lifecycle_status,
        knowledge_status=knowledge_status,
        version=1,
    )
    db.add(product)
    db.flush()
    return product


def add_alias(
    db: Session, product: Product, alias: str, normalized_alias: str, source: str = "owner"
) -> ProductAlias | None:
    if product.tenant_id != get_current_tenant_id():
        raise DomainError("跨租户产品操作被拒绝")
    existing = db.scalar(
        select(ProductAlias).where(
            ProductAlias.tenant_id == get_current_tenant_id(),
            ProductAlias.product_id == product.id,
            ProductAlias.normalized_alias == normalized_alias,
            ProductAlias.deleted_at.is_(None),
        )
    )
    if existing:
        return None
    row = ProductAlias(
        tenant_id=get_current_tenant_id(), product_id=product.id, alias=alias.strip(),
        normalized_alias=normalized_alias, source=source,
    )
    db.add(row)
    db.flush()
    return row


def merge_products(db: Session, source_id: int, target_id: int) -> tuple[Product, Product, int]:
    if source_id == target_id:
        raise DomainError("不能把产品合并到自身")
    source = get_product(db, source_id)
    target = get_product(db, target_id)
    if source is None or target is None:
        raise NotFoundError("待合并产品不存在、已停用或已被合并")

    moved = db.execute(
        update(LedgerEntry)
        .where(
            LedgerEntry.tenant_id == get_current_tenant_id(),
            LedgerEntry.product_id == source.id,
        )
        .values(product_id=target.id)
    ).rowcount
    db.execute(
        update(ProductAlias)
        .where(
            ProductAlias.tenant_id == get_current_tenant_id(),
            ProductAlias.product_id == source.id,
        )
        .values(product_id=target.id)
    )
    source.lifecycle_status = "replaced"
    source.merged_into_id = target.id
    source.version += 1
    source.updated_at = _utcnow()
    target.version += 1
    target.updated_at = _utcnow()
    db.flush()
    return source, target, int(moved or 0)
