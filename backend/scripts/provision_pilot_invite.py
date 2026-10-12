"""为邀请内测创建店铺和一次性开通码。

邀请码只在命令成功时显示一次，数据库仅保存 HMAC 摘要。
"""
import argparse
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.application.auth_service import hash_invite_code
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.infrastructure.models import Invite, Tenant


def _utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    raw = "".join(secrets.choice(alphabet) for _ in range(12))
    return f"FC-{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def main() -> None:
    parser = argparse.ArgumentParser(description="创建发财邀请内测店铺和开通码")
    parser.add_argument("--tenant-slug", required=True, help="稳定店铺标识，如 xinglan-beauty")
    parser.add_argument("--tenant-name", required=True, help="店铺展示名")
    parser.add_argument("--role", choices=("owner", "admin"), default="owner")
    parser.add_argument("--expires-hours", type=int, default=72)
    args = parser.parse_args()
    settings = get_settings()
    settings.validate_production_settings()
    slug = args.tenant_slug.strip().lower()
    if not slug.replace("-", "").isalnum() or not 3 <= len(slug) <= 80:
        raise SystemExit("tenant-slug 只能使用 3—80 位字母、数字和短横线")
    code = _new_code()
    db = get_session_factory()()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
        if tenant is None:
            tenant = Tenant(slug=slug, display_name=args.tenant_name.strip(), status="active")
            db.add(tenant)
            db.flush()
        elif tenant.status != "active":
            raise SystemExit("店铺已停用，拒绝生成邀请码")
        db.add(Invite(
            tenant_id=tenant.id,
            code_hash=hash_invite_code(code, settings),
            role=args.role,
            expires_at=_utc_naive() + timedelta(hours=args.expires_hours),
        ))
        db.commit()
        print(f"店铺：{tenant.display_name} ({tenant.slug})")
        print(f"一次性邀请码：{code}")
        print(f"有效期：{args.expires_hours} 小时；兑换后立即失效")
    finally:
        db.close()


if __name__ == "__main__":
    main()
