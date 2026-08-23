"""阶段5知识入库/向量化门禁。知识始终视为不可信数据。"""
import html
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.stage4_model_service import contains_pii
from app.core.tenant import get_current_tenant_id
from app.domain.errors import DomainError
from app.infrastructure.models import Customer, CustomerAlias


_SCRIPT = re.compile(
    r"<\s*/?\s*(?:script|iframe|object|embed|style|svg|math)\b|"
    r"\bon(?:error|load|click|focus)\s*=|javascript\s*:", re.IGNORECASE,
)
_INJECTION = re.compile(
    r"ignore\s+(?:all\s+)?previous|system\s*prompt|developer\s*message|"
    r"忽略.{0,12}(?:指令|提示|上文)|系统提示词|开发者消息|"
    r"(?:泄露|显示|输出).{0,8}(?:密钥|api\s*key|prompt)", re.IGNORECASE,
)
_FORBIDDEN_DATA = re.compile(
    r"客户(?:姓名|画像|档案)|手机号|微信号|邮箱|账本|余额|购买日期|"
    r"system\s*prompt|api\s*key|secret", re.IGNORECASE,
)
_TAGS = re.compile(r"<[^>]{0,500}>")
_SPACE = re.compile(r"[ \t\r\f\v]+")


def sanitize_knowledge_text(value: str) -> str:
    raw = str(value or "").strip()
    if _SCRIPT.search(raw):
        raise DomainError("知识内容含脚本或危险 HTML，已拒绝")
    cleaned = html.unescape(_TAGS.sub(" ", raw))
    cleaned = _SPACE.sub(" ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if not cleaned:
        raise DomainError("知识内容不能为空")
    if len(cleaned) > 6000:
        raise DomainError("知识内容超过 6000 字")
    return cleaned


def validate_knowledge_input(db: Session, text: str, *, source_type: str, source_name: str) -> str:
    if source_type not in {"owner_confirmed", "published_policy", "imported_owner_document"}:
        raise DomainError("知识来源必须是店主确认资料或已发布规范，模型常识不能作为来源")
    if not source_name.strip() or len(source_name.strip()) > 200:
        raise DomainError("知识来源名称不能为空且不得超过 200 字")
    cleaned = sanitize_knowledge_text(text)
    if contains_pii(cleaned) or _FORBIDDEN_DATA.search(cleaned):
        raise DomainError("知识内容含禁止向量化的客户/PII/账本/秘密字段")
    if _INJECTION.search(cleaned):
        raise DomainError("知识内容含提示注入，已拒绝")
    names = list(db.scalars(select(Customer.display_name).where(
        Customer.tenant_id == get_current_tenant_id(), Customer.deleted_at.is_(None)
    )).all())
    names.extend(db.scalars(
        select(CustomerAlias.alias).join(Customer, Customer.id == CustomerAlias.customer_id).where(
            CustomerAlias.tenant_id == get_current_tenant_id(), CustomerAlias.deleted_at.is_(None),
            Customer.tenant_id == get_current_tenant_id(), Customer.deleted_at.is_(None),
        )
    ).all())
    if any(name and len(name.strip()) >= 2 and name.strip() in cleaned for name in names):
        raise DomainError("知识内容含当前店铺客户称呼，禁止进入知识向量")
    return cleaned


def safe_for_embedding_query(value: str) -> bool:
    raw = str(value or "")
    return bool(raw.strip()) and not (
        contains_pii(raw) or _SCRIPT.search(raw) or _INJECTION.search(raw) or _FORBIDDEN_DATA.search(raw)
    )
