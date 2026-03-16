"""
ORM モデルパッケージ.

- Alembic autogenerate 対象のモデルを import して登録する
"""

from app.models.audit.auth_audit_log import AuthAuditEventType, AuthAuditLog
from app.models.auth.auth_identity import AuthIdentity, AuthProvider
from app.models.auth.email_verification_token import EmailVerificationToken
from app.models.auth.password_reset_token import PasswordResetToken
from app.models.auth.session import UserSession
from app.models.auth.user import User, UserType
from app.models.jobs.async_job import AsyncJob, AsyncJobStatus, AsyncJobType
from app.models.jobs.async_job_artifact import AsyncJobArtifact, AsyncJobArtifactType

__all__ = [
    "AuthAuditEventType",
    "AuthAuditLog",
    "AuthIdentity",
    "AuthProvider",
    "EmailVerificationToken",
    "PasswordResetToken",
    "User",
    "UserSession",
    "UserType",
    "AsyncJob",
    "AsyncJobStatus",
    "AsyncJobType",
    "AsyncJobArtifact",
    "AsyncJobArtifactType",
    "load_all_models",
]


def load_all_models() -> tuple[
    type[AuthAuditLog],
    type[User],
    type[AuthIdentity],
    type[UserSession],
    type[EmailVerificationToken],
    type[PasswordResetToken],
    type[AsyncJob],
    type[AsyncJobArtifact],
]:
    """
    Alembic のモデル登録を確実にするために import 副作用を明示する.

    Returns:
        tuple[
            type[AuthAuditLog],
            type[User],
            type[AuthIdentity],
            type[UserSession],
            type[EmailVerificationToken],
            type[PasswordResetToken],
            type[AsyncJob],
            type[AsyncJobArtifact],
        ]:
            読み込まれたモデル
    """
    return (
        AuthAuditLog,
        User,
        AuthIdentity,
        UserSession,
        EmailVerificationToken,
        PasswordResetToken,
        AsyncJob,
        AsyncJobArtifact,
    )
