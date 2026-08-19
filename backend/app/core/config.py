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

    # 数据库连接串；留空则使用 backend/data/app.db
    database_url: str = ""

    # DeepSeek 模型配置
    deepseek_api_base_url: str = "https://api.deepseek.com"
    deepseek_model_id: str = "deepseek-v4-pro"
    deepseek_api_key: str = ""
    model_request_timeout_seconds: float = 60.0

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
            return self.database_url
        return f"sqlite:///{BACKEND_ROOT / 'data' / 'app.db'}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
