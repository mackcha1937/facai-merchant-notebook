"""套餐卡用例编排。"""
from sqlalchemy.orm import Session

from app.application import serializers
from app.domain.errors import DomainError, NotFoundError
from app.domain.rules import validate_package_counts
from app.repositories import customers as customer_repo
from app.repositories import packages as package_repo
from app.repositories import services as service_repo
from app.schemas.package import PackageCreate, PackageUpdate

VALID_PACKAGE_STATUSES = {"active", "exhausted", "inactive"}


def create_package(db: Session, customer_id: int, data: PackageCreate) -> dict:
    customer = customer_repo.get_customer(db, customer_id)
    if customer is None:
        raise NotFoundError("客户不存在或已删除")
    service = service_repo.get_service(db, data.service_id)
    if service is None:
        raise NotFoundError("服务项目不存在或已删除")
    if service.status != "active":
        raise DomainError("已停用或删除的服务不能建立新套餐")

    total, _ = validate_package_counts(data.total_count, 0)
    package = package_repo.create_package(
        db, customer_id, service.id, total, 0, data.price_cents, data.purchased_on
    )
    package.service = service
    serializers.save(db)
    return serializers.package_to_dict(package)


def update_package(db: Session, package_id: int, data: PackageUpdate) -> dict:
    package = package_repo.get_package(db, package_id)
    if package is None:
        raise NotFoundError("套餐不存在或已删除")

    if data.service_id is not None and data.service_id != package.service_id:
        new_service = service_repo.get_service(db, data.service_id)
        if new_service is None:
            raise NotFoundError("服务项目不存在或已删除")
        if new_service.status != "active":
            raise DomainError("已停用或删除的服务不能用于套餐")
        package.service_id = new_service.id
        package.service = new_service

    total = data.total_count if data.total_count is not None else package.total_count
    used = data.used_count if data.used_count is not None else package.used_count
    total, used = validate_package_counts(total, used)
    package.total_count = total
    package.used_count = used

    if data.price_cents is not None:
        package.price_cents = data.price_cents
    if data.purchased_on is not None:
        package.purchased_on = data.purchased_on
    if data.status is not None:
        if data.status not in VALID_PACKAGE_STATUSES:
            raise DomainError("套餐状态只能是 active / exhausted / inactive")
        package.status = data.status

    serializers.save(db)
    return serializers.package_to_dict(package)


def delete_package(db: Session, package_id: int) -> dict:
    package = package_repo.get_package(db, package_id)
    if package is None:
        raise NotFoundError("套餐不存在或已删除")
    package_repo.soft_delete_package(db, package)
    serializers.save(db)
    return {"deleted": True, "id": package_id}


def restore_package(db: Session, package_id: int) -> dict:
    package = package_repo.get_package_any(db, package_id)
    if package is None:
        raise NotFoundError("套餐不存在")
    package_repo.restore_package(db, package)
    serializers.save(db)
    return serializers.package_to_dict(package)
