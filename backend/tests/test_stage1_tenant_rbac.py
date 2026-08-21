"""阶段1：租户隔离与 RBAC 测试。"""
import pytest

from app.core.rbac import require_admin, require_owner
from app.core.tenant import set_current_tenant_id
from app.domain.errors import DomainError
from app.repositories import customers as customer_repo
from app.repositories import services as service_repo


@pytest.fixture(autouse=True)
def _reset_tenant():
    yield
    set_current_tenant_id(1)


def test_cross_tenant_customer_isolation(db_session):
    set_current_tenant_id(1)
    cust_a = customer_repo.create_customer(db_session, "小红", ["红姐"])
    db_session.commit()

    set_current_tenant_id(2)
    cust_b = customer_repo.create_customer(db_session, "小明", [])
    db_session.commit()

    # 租户1 只能看到自己的客户
    set_current_tenant_id(1)
    customers = customer_repo.list_customers(db_session)
    assert len(customers) == 1
    assert customers[0].display_name == "小红"

    # 租户1 不能通过 ID 读取租户2 的客户（跨租户枚举被阻断）
    assert customer_repo.get_customer(db_session, cust_b.id) is None
    assert customer_repo.get_customer_any(db_session, cust_b.id) is None

    # 租户2 能读取自己的
    set_current_tenant_id(2)
    assert customer_repo.get_customer(db_session, cust_b.id) is not None


def test_cross_tenant_service_isolation(db_session):
    set_current_tenant_id(1)
    svc_a = service_repo.create_service(db_session, "面部清洁", "active")
    db_session.commit()

    set_current_tenant_id(2)
    svc_b = service_repo.create_service(db_session, "脱毛", "active")
    db_session.commit()

    set_current_tenant_id(1)
    assert service_repo.get_service(db_session, svc_a.id) is not None
    assert service_repo.get_service(db_session, svc_b.id) is None  # 跨租户阻断


def test_rbac_owner_vs_admin():
    # owner 可做业务操作
    require_owner("owner")
    require_owner("admin")
    # owner 不能管理 AI 配置
    with pytest.raises(DomainError):
        require_admin("owner")
    require_admin("admin")
    # 无角色拒绝
    with pytest.raises(DomainError):
        require_owner(None)
    with pytest.raises(DomainError):
        require_admin(None)


def test_default_tenant_is_one():
    from app.core.tenant import get_current_tenant_id

    set_current_tenant_id(1)
    assert get_current_tenant_id() == 1
