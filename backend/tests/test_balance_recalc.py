"""权威余额重算测试：删除/恢复核销记录后余额自动回退/恢复。"""
from app.application import ledger_service
from app.repositories import customers as customer_repo
from app.repositories import packages as package_repo
from app.repositories import services as service_repo
from app.schemas.ledger import LedgerEntryCreate


def _setup(db):
    svc = service_repo.create_service(db, "面部清洁", "active")
    cust = customer_repo.create_customer(db, "小红", ["红姐"])
    pkg = package_repo.create_package(db, cust.id, svc.id, 5, 0, None, None)
    db.commit()
    return svc, cust, pkg


def test_delete_and_restore_consume_recalculates_balance(db_session):
    svc, cust, pkg = _setup(db_session)

    created = ledger_service.create_ledger_entry(
        db_session, cust.id,
        LedgerEntryCreate(entry_type="package_consumption", package_id=pkg.id, quantity=2),
    )
    assert package_repo.compute_used_count(db_session, pkg) == 2

    ledger_service.delete_ledger_entry(db_session, created["id"])
    assert package_repo.compute_used_count(db_session, pkg) == 0  # 回退

    ledger_service.restore_ledger_entry(db_session, created["id"])
    assert package_repo.compute_used_count(db_session, pkg) == 2  # 恢复


def test_opening_used_count_included(db_session):
    svc, cust, pkg = _setup(db_session)
    pkg.opening_used_count = 2
    db_session.commit()
    assert package_repo.compute_used_count(db_session, pkg) == 2
    assert package_repo.compute_used_count(db_session, pkg) == 2  # opening + 0 条核销记录
