"""生产进程启动前的只读检查；不迁移、不建表、不打印连接串。"""
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.core.config import BACKEND_ROOT, get_settings
from app.core.database import get_engine


def main() -> None:
    settings = get_settings()
    settings.validate_production_settings()

    config = Config(str(Path(BACKEND_ROOT) / "alembic.ini"))
    config.set_main_option("script_location", str(Path(BACKEND_ROOT) / "alembic"))
    expected = ScriptDirectory.from_config(config).get_current_head()
    with get_engine().connect() as connection:
        current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        connection.execute(text("SELECT 1"))
    if current != expected:
        raise SystemExit(f"数据库迁移未就绪：current={current or 'missing'} expected={expected}")
    print(f"生产只读预检通过：migration={current}; database=connected; secrets=not_printed")


if __name__ == "__main__":
    main()
