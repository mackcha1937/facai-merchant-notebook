"""初始化化名测试数据（幂等：已有数据时跳过）。

运行方式（在 backend 目录下）：
    .venv/bin/python -m app.seed
"""
from sqlalchemy import select

from app.core.database import get_session_factory, init_db
from app.infrastructure.models import Customer, CustomerAlias, Package, Service

SERVICES = ["面部清洁", "肩颈按摩", "身体护理", "清痘", "脱毛"]


def seed() -> None:
    init_db()
    db = get_session_factory()()
    try:
        if not db.scalars(select(Service).limit(1)).first():
            for name in SERVICES:
                db.add(Service(name=name, status="active"))
            db.flush()

        service_by_name = {s.name: s for s in db.scalars(select(Service)).all()}

        if not db.scalars(select(Customer).limit(1)).first():
            def add_customer(name, aliases, service_name, total, used, price_cents, purchased_on):
                customer = Customer(display_name=name)
                for alias in aliases:
                    customer.aliases.append(CustomerAlias(alias=alias))
                svc = service_by_name[service_name]
                customer.packages.append(
                    Package(
                        service_id=svc.id,
                        total_count=total,
                        used_count=used,
                        price_cents=price_cents,
                        purchased_on=purchased_on,
                        status="active",
                    )
                )
                db.add(customer)

            add_customer("小红", ["红姐"], "脱毛", 9, 2, 99900, "2026-05-10")
            add_customer("小黄", ["黄姐"], "面部清洁", 10, 7, 66600, "2026-03-01")
            add_customer("小蓝", ["蓝蓝"], "肩颈按摩", 3, 1, 29900, None)

        db.commit()
        print("种子数据已就绪（已存在则跳过）。")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
