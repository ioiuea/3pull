from app.core.settings.config import AppSettings


def test_celery_task_modules_accepts_csv() -> None:
    # 目的: CELERY_TASK_MODULES の CSV 形式入力が
    # 設定オブジェクトで正規化されることを保証する。
    # 条件: カンマ区切り・空白入りの文字列を AppSettings に渡す。
    # 期待値: 余分な空白が除去された list[str] に変換される。
    settings = AppSettings(
        CELERY_TASK_MODULES="app.workers.audit_export_tasks, app.workers.example_tasks",
    )

    assert settings.celery_task_modules == [
        "app.workers.audit_export_tasks",
        "app.workers.example_tasks",
    ]
