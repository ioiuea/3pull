"""監査ログエクスポート worker 起動スクリプト."""

from __future__ import annotations

from app.core.settings import get_settings
from app.workers.runtime import WorkerRuntimeConfig, run_worker_loop


def main() -> None:
    settings = get_settings()
    # 実行ロジックは共通 runtime に寄せ、
    # この起動スクリプトでは対象キューの設定だけ渡す。
    run_worker_loop(
        config=WorkerRuntimeConfig(
            queue_name=settings.auth_audit_export_queue_name,
            expected_job_type="auth_audit_export",
        )
    )


if __name__ == "__main__":
    main()
