"""环境变量与配置集中管理。

API Key 只从 backend/.env 读取，绝不写入代码、日志、前端或版本库。
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录（config.py 位于 backend/app/core/config.py）
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "美容店智能客户账本"
    version: str = "0.1.0"
    log_level: str = "INFO"
    app_env: str = "local"  # local / test / production

    # 数据库连接串；留空则使用 backend/data/app.db
    database_url: str = ""
    # 默认由 Alembic 管理；仅隔离测试可显式开启 create_all。
    auto_create_schema: bool = False

    # DeepSeek 模型配置
    deepseek_api_base_url: str = "https://api.deepseek.com"
    deepseek_model_id: str = "deepseek-v4-pro"
    deepseek_api_key: str = ""
    model_request_timeout_seconds: float = 60.0

    # V2 真实模型付费调用独立开关；默认关闭，需获得授权后显式开启。
    enable_v2_real_model: bool = False

    # 阶段0 模型验证开关（会产生真实模型费用，仅开发环境显式开启）
    enable_stage0_verify: bool = False

    # 阶段1 验证状态接口开关（仅开发环境显式开启，生产默认关闭）
    enable_stage1_verify: bool = False

    # 阶段2 验证状态接口开关（仅开发环境显式开启，生产默认关闭）
    enable_stage2_verify: bool = False

    # 本地开发默认身份（正式登录未实现前）。生产环境应设为 False，缺失上下文时 fail closed。
    local_dev_owner_enabled: bool = True
    local_default_tenant_id: int = 1
    local_default_owner_id: int = 1
    local_default_owner_role: str = "owner"

    # 邀请内测认证。Secret 只能由后端环境变量注入。
    session_secret: str = ""
    session_cookie_name: str = "facai_session"
    session_ttl_hours: int = 168
    auth_max_failed_attempts: int = 5
    auth_lockout_minutes: int = 15
    cookie_secure: bool = False
    expose_api_docs: bool = True
    allowed_hosts: str = "127.0.0.1,localhost,testserver"

    # 前端开发服务器跨域来源（多个用英文逗号分隔）
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    @property
    def is_model_configured(self) -> bool:
        """是否已配置 API Key（只看是否非空，不读取或展示内容）。"""
        return bool(self.deepseek_api_key.strip())

    @property
    def effective_database_url(self) -> str:
        """返回实际使用的数据库连接串。"""
        if self.database_url.strip():
            url = self.database_url.strip()
            # 部分托管平台仍下发 postgres://；SQLAlchemy 2 使用明确的
            # psycopg v3 驱动，避免生产容器误选旧 psycopg2。
            if url.startswith("postgres://"):
                return "postgresql+psycopg://" + url.removeprefix("postgres://")
            if url.startswith("postgresql://"):
                return "postgresql+psycopg://" + url.removeprefix("postgresql://")
            return url
        return f"sqlite:///{BACKEND_ROOT / 'data' / 'app.db'}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def auth_secret(self) -> str:
        """返回认证 HMAC 密钥。

        本地开发可使用固定非生产值；生产环境必须显式注入随机 Secret。
        """
        if self.session_secret:
            return self.session_secret
        if not self.is_production:
            return "facai-local-development-only-session-secret"
        return ""

    def validate_production_settings(self) -> None:
        """生产启动前 fail closed，避免把本地便利配置带上线。"""
        if not self.is_production:
            return
        errors: list[str] = []
        if self.local_dev_owner_enabled:
            errors.append("LOCAL_DEV_OWNER_ENABLED 必须为 false")
        if len(self.session_secret) < 32:
            errors.append("SESSION_SECRET 必须是至少 32 字符的随机密钥")
        if not self.database_url.strip():
            errors.append("DATABASE_URL 必须显式配置")
        elif self.database_url.strip().lower().startswith("sqlite"):
            errors.append("生产环境不允许使用 SQLite")
        if self.auto_create_schema:
            errors.append("AUTO_CREATE_SCHEMA 必须为 false，生产结构只能由 Alembic 管理")
        if not self.cookie_secure:
            errors.append("COOKIE_SECURE 必须为 true")
        if not self.session_cookie_name.startswith("__Host-"):
            errors.append("SESSION_COOKIE_NAME 必须使用 __Host- 前缀")
        if self.expose_api_docs:
            errors.append("EXPOSE_API_DOCS 必须为 false")
        if not self.allowed_host_list or "*" in self.allowed_host_list:
            errors.append("ALLOWED_HOSTS 必须显式限定线上域名")
        if errors:
            raise RuntimeError("生产配置不安全；" + "；".join(errors))


@lru_cache
def get_settings() -> Settings:
    return Settings()
