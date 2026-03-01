"""サンプル待機ジョブ worker 起動スクリプト."""

from __future__ import annotations

from app.core.settings import get_settings
from app.workers.runtime import WorkerRuntimeConfig, run_worker_loop


def main() -> None:
    settings = get_settings()
    # 起動スクリプトは「どの queue をどの job_type として処理するか」だけを決める。
    run_worker_loop(
        config=WorkerRuntimeConfig(
            queue_name=settings.sample_wait_blob_queue_name,
            expected_job_type="sample_wait_blob",
        )
    )


if __name__ == "__main__":
    main()
