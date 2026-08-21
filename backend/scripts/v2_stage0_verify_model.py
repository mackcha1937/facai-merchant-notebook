"""V2 阶段0：DeepSeek 模型能力验证脚本（严格版）。

用法：.venv/bin/python scripts/v2_stage0_verify_model.py
安全：API Key 只从 backend/.env 读取，输出脱敏，绝不打印 Key。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.application.stage0_verify import run_all_verifications  # noqa: E402
from app.core.config import get_settings  # noqa: E402

settings = get_settings()

if __name__ == "__main__":
    print(f"验证目标：base={settings.deepseek_api_base_url} model={settings.deepseek_model_id}")
    print(f"API Key 已配置: {settings.is_model_configured}")
    if not settings.is_model_configured:
        print("❌ 未配置 API Key，请在 backend/.env 填写 DEEPSEEK_API_KEY 后重试。")
        sys.exit(1)

    results = run_all_verifications(
        settings.deepseek_api_base_url.rstrip("/"),
        settings.deepseek_model_id,
        settings.deepseek_api_key,
    )
    passed = 0
    for r in results:
        print(f"\n[{r['name']}] {'✅ 通过' if r['ok'] else '❌ 失败'}")
        print(f"  {r['detail']}")
        if r["ok"]:
            passed += 1
    print(f"\n结果：{passed}/{len(results)} 通过。")
    sys.exit(0 if passed == len(results) else 1)
