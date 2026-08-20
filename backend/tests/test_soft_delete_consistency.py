"""软删除与恢复一致性测试：恢复后余额与关联保持不变。"""
from app.application import customer_service, package_service
from app.repositories import customers as customer_repo
from app.repositories import packages as package_repo
from app.repositories import services as service_repo
from app.schemas.package import PackageCreate


def _setup(db):
    svc = service_repo.create_service(db, "面部清洁", "active")
    cust = customer_repo.create_customer(db, "小红", ["红姐"])
    package_repo.create_package(db, cust.id, svc.id, 5, 2, 99900, None)
    db.commit()
    return svc, cust


def test_restore_customer_keeps_package_and_balance(db_session):
    svc, cust = _setup(db_session)

    customer_service.delete_customer(db_session, cust.id)
    assert customer_repo.get_customer(db_session, cust.id) is None

    customer_service.restore_customer(db_session, cust.id)
    restored = customer_repo.get_customer(db_session, cust.id)
    assert restored is not None
    packages = package_repo.list_packages_for_customer(db_session, cust.id)
    assert len(packages) == 1
    assert packages[0].total_count == 5
    assert packages[0].used_count == 2  # 余额未变


def test_restore_package_keeps_balance(db_session):
    svc, cust = _setup(db_session)
    pkg = package_repo.list_packages_for_customer(db_session, cust.id)[0]

    package_service.delete_package(db_session, pkg.id)
    assert package_repo.get_package(db_session, pkg.id) is None

    package_service.restore_package(db_session, pkg.id)
    restored = package_repo.get_package(db_session, pkg.id)
    assert restored is not None
    assert restored.total_count == 5
    assert restored.used_count == 2  # 余额未变


def test_deleted_service_not_in_list(db_session):
    svc, cust = _setup(db_session)
    from app.application import service_service

    service_service.delete_service(db_session, svc.id)
    names = [s["name"] for s in service_service.list_services(db_session)]
    assert "面部清洁" not in names
