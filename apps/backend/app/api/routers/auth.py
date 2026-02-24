"""
認証 API ルーター定義.

- Email signup/login/verify/reset/change
- セッションベースの `/auth/me` `/auth/logout`
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urljoin, urlparse

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.session import get_session
from app.api.schemas.auth import (
    EmailLoginRequest,
    EmailLoginResponse,
    EmailSignupRequest,
    EmailSignupResponse,
    EmailVerifyRequest,
    EmailVerifyResponse,
    LogoutResponse,
    PasswordChangeRequest,
    PasswordChangeResponse,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    PasswordResetRequestRequest,
    PasswordResetRequestResponse,
    SessionRefreshResponse,
    UserMeResponse,
)
from app.core.logging.config import get_logger
from app.core.settings import get_settings
from app.models.auth.user import User
from app.services.auth.auth_account_service import AuthConflictCode, AuthConflictError
from app.services.auth.auth_account_service import (
    change_email_password,
    issue_email_verification_token,
    issue_password_reset_token,
    resolve_entra_login,
    reset_password_by_token,
    resolve_email_login,
    signup_email_user,
    verify_email_by_token,
)
from app.services.auth.session_auth_service import (
    refresh_user_session,
    SessionAuthError,
    SessionAuthErrorCode,
    issue_user_session,
    resolve_user_by_session_token,
    revoke_session_by_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


def _validate_entra_settings() -> None:
    """
    Entra OIDC の必須設定値を検証する.

    Raises:
        HTTPException: 必須設定が不足している場合
    """
    settings = get_settings()
    required_values = {
        "ENTRA_TENANT_ID": settings.entra_tenant_id,
        "ENTRA_CLIENT_ID": settings.entra_client_id,
        "ENTRA_CLIENT_SECRET": settings.entra_client_secret,
        "ENTRA_REDIRECT_URI": settings.entra_redirect_uri,
    }
    missing_keys = [key for key, value in required_values.items() if not value]
    if missing_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "entra_configuration_missing",
                "message": f"Missing Entra settings: {', '.join(missing_keys)}",
            },
        )


@lru_cache(maxsize=1)
def _get_entra_oauth() -> OAuth:
    """
    Entra 用 OAuth クライアントを初期化して返す.

    Returns:
        OAuth: 初期化済み OAuth クライアント
    """
    settings = get_settings()
    oauth = OAuth()
    oauth.register(
        name="entra",
        client_id=settings.entra_client_id,
        client_secret=settings.entra_client_secret,
        server_metadata_url=(
            f"https://login.microsoftonline.com/"
            f"{settings.entra_tenant_id}/v2.0/.well-known/openid-configuration"
        ),
        client_kwargs={"scope": "openid profile email"},
    )
    return oauth


def _sanitize_redirect_path(path: str | None) -> str:
    """
    ログイン後リダイレクト先を相対パスに正規化する.

    Args:
        path: 入力パス

    Returns:
        str: 安全な相対パス
    """
    settings = get_settings()
    default_path = settings.auth_post_login_default_path
    if not path:
        return default_path
    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc:
        return default_path
    if not path.startswith("/"):
        return default_path
    return path


def _resolve_login_identifier(claims: dict[str, object]) -> tuple[str, str]:
    """
    Entra クレームから subject と UPN 相当メールを解決する.

    Args:
        claims: ID トークンクレーム

    Returns:
        tuple[str, str]: (subject, login_email)
    """
    subject = str(claims.get("oid") or claims.get("sub") or "")
    login_email = str(
        claims.get("preferred_username")
        or claims.get("upn")
        or claims.get("email")
        or ""
    ).strip()

    if not subject or not login_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "entra_claims_invalid",
                "message": "Required Entra claims (subject/email) are missing",
            },
        )
    return subject, login_email


def _validate_internal_domain(login_email: str) -> None:
    """
    Entra ログインユーザーのメールドメインを内部ドメイン一覧で検証する.

    Args:
        login_email: UPN / email

    Raises:
        HTTPException: 許可ドメイン外の場合
    """
    settings = get_settings()
    if not settings.entra_internal_domains:
        return
    domain = login_email.split("@")[-1].lower() if "@" in login_email else ""
    if domain not in settings.entra_internal_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "entra_domain_not_allowed",
                "message": "Entra account domain is not allowed",
            },
        )


def _to_user_me_response(user: User) -> UserMeResponse:
    """
    User モデルを `/auth/me` 用レスポンスへ変換する.

    Args:
        user: DB ユーザーモデル

    Returns:
        UserMeResponse: 返却用ユーザー情報
    """
    return UserMeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        user_type=user.user_type,
        is_active=user.is_active,
    )


def _set_session_cookie(response: Response, raw_token: str) -> None:
    """
    セッション Cookie をレスポンスへ設定する.

    Args:
        response: HTTP レスポンス
        raw_token: 生セッショントークン
    """
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_ttl_minutes * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    """
    セッション Cookie を削除する.

    Args:
        response: HTTP レスポンス
    """
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


def _raise_auth_error(error: AuthConflictError) -> None:
    """
    ドメインエラーを HTTP エラーへ変換して送出する.

    Args:
        error: サービス層の認証エラー
    """
    status_code_map: dict[AuthConflictCode, int] = {
        AuthConflictCode.WEAK_PASSWORD: status.HTTP_422_UNPROCESSABLE_ENTITY,
        AuthConflictCode.EMAIL_ACCOUNT_ALREADY_EXISTS: status.HTTP_409_CONFLICT,
        AuthConflictCode.ENTRA_ACCOUNT_ALREADY_EXISTS: status.HTTP_409_CONFLICT,
        AuthConflictCode.ENTRA_SUBJECT_CONFLICT: status.HTTP_409_CONFLICT,
        AuthConflictCode.EMAIL_NOT_VERIFIED: status.HTTP_403_FORBIDDEN,
        AuthConflictCode.EMAIL_ALREADY_VERIFIED: status.HTTP_409_CONFLICT,
        AuthConflictCode.EMAIL_ACCOUNT_LOCKED: status.HTTP_423_LOCKED,
        AuthConflictCode.INVALID_CREDENTIALS: status.HTTP_401_UNAUTHORIZED,
        AuthConflictCode.CURRENT_PASSWORD_INVALID: status.HTTP_401_UNAUTHORIZED,
        AuthConflictCode.PASSWORD_REUSE_NOT_ALLOWED: status.HTTP_422_UNPROCESSABLE_ENTITY,
        AuthConflictCode.EMAIL_VERIFICATION_TOKEN_INVALID: status.HTTP_400_BAD_REQUEST,
        AuthConflictCode.EMAIL_VERIFICATION_TOKEN_EXPIRED: status.HTTP_400_BAD_REQUEST,
        AuthConflictCode.PASSWORD_RESET_TOKEN_INVALID: status.HTTP_400_BAD_REQUEST,
        AuthConflictCode.PASSWORD_RESET_TOKEN_EXPIRED: status.HTTP_400_BAD_REQUEST,
        AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    }
    raise HTTPException(
        status_code=status_code_map.get(error.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": error.code.value, "message": error.message},
    )


def _raise_session_error(error: SessionAuthError) -> None:
    """
    セッションエラーを HTTP エラーへ変換して送出する.

    Args:
        error: セッション認証エラー
    """
    status_code_map: dict[SessionAuthErrorCode, int] = {
        SessionAuthErrorCode.SESSION_INVALID: status.HTTP_401_UNAUTHORIZED,
        SessionAuthErrorCode.SESSION_EXPIRED: status.HTTP_401_UNAUTHORIZED,
        SessionAuthErrorCode.USER_NOT_FOUND: status.HTTP_401_UNAUTHORIZED,
    }
    raise HTTPException(
        status_code=status_code_map.get(error.code, status.HTTP_401_UNAUTHORIZED),
        detail={"code": error.code.value, "message": error.message},
    )


async def _require_session_user(
    request: Request,
    session: AsyncSession,
) -> tuple[User, str]:
    """
    セッション Cookie から現在ユーザーを解決する.

    Args:
        request: 受信リクエスト
        session: DB セッション

    Returns:
        tuple[User, str]: 現在ユーザーと生セッショントークン
    """
    cookie_name = get_settings().session_cookie_name
    raw_token = request.cookies.get(cookie_name)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_missing", "message": "Session cookie is missing"},
        )
    try:
        user = await resolve_user_by_session_token(session, raw_token=raw_token)
    except SessionAuthError as error:
        _raise_session_error(error)
    return user, raw_token


@router.post("/email/signup", response_model=EmailSignupResponse)
async def post_email_signup(
    payload: EmailSignupRequest,
    session: AsyncSession = Depends(get_session),
) -> EmailSignupResponse:
    """Email サインアップを実行し、検証トークン発行状態を返す."""
    try:
        await signup_email_user(
            session,
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
        verification_token = await issue_email_verification_token(session, email=payload.email)
    except AuthConflictError as error:
        _raise_auth_error(error)

    debug_token = verification_token if get_settings().auth_debug_return_tokens else None
    return EmailSignupResponse(
        status="verification_required",
        debug_verification_token=debug_token,
    )


@router.get("/entra/login")
async def get_auth_entra_login(request: Request) -> Response:
    """Entra OIDC ログインへリダイレクトする."""
    _validate_entra_settings()
    settings = get_settings()
    return_to = _sanitize_redirect_path(request.query_params.get("return_to"))
    request.session["entra_post_login_path"] = return_to
    oauth = _get_entra_oauth()
    try:
        return await oauth.entra.authorize_redirect(
            request,
            redirect_uri=settings.entra_redirect_uri,
            prompt="select_account",
        )
    except OAuthError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "entra_authorize_failed", "message": str(error)},
        ) from error


@router.get("/entra/callback")
async def get_auth_entra_callback(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Entra OIDC コールバックを処理してアプリセッションを発行する."""
    _validate_entra_settings()
    oauth = _get_entra_oauth()
    try:
        token = await oauth.entra.authorize_access_token(request)
        claims = token.get("userinfo")
        if not claims:
            claims = await oauth.entra.parse_id_token(request, token)
    except OAuthError as error:
        logger.warning(
            "auth.audit.login.failure",
            method="entra",
            code="entra_callback_failed",
            client_ip=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "entra_callback_failed", "message": str(error)},
        ) from error

    subject, login_email = _resolve_login_identifier(claims)
    _validate_internal_domain(login_email)

    try:
        user = await resolve_entra_login(
            session,
            user_principal_name=login_email,
            entra_subject=subject,
            display_name=str(claims.get("name") or ""),
        )
        raw_token = await issue_user_session(
            session,
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthConflictError as error:
        logger.warning(
            "auth.audit.login.failure",
            method="entra",
            email=login_email,
            code=error.code.value,
            client_ip=request.client.host if request.client else None,
        )
        _raise_auth_error(error)

    settings = get_settings()
    post_login_path = _sanitize_redirect_path(request.session.pop("entra_post_login_path", None))
    target_url = urljoin(settings.frontend_base_url.rstrip("/") + "/", post_login_path.lstrip("/"))
    response = RedirectResponse(url=target_url, status_code=status.HTTP_302_FOUND)
    _set_session_cookie(response, raw_token)
    logger.info(
        "auth.audit.login.success",
        method="entra",
        user_id=str(user.id),
        email=user.email,
        client_ip=request.client.host if request.client else None,
    )
    return response


@router.post("/email/login", response_model=EmailLoginResponse)
async def post_email_login(
    payload: EmailLoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> EmailLoginResponse:
    """Email ログインを実行してセッション Cookie を発行する."""
    try:
        user = await resolve_email_login(
            session,
            email=payload.email,
            password=payload.password,
        )
        raw_token = await issue_user_session(
            session,
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthConflictError as error:
        logger.warning(
            "auth.audit.login.failure",
            method="email",
            email=payload.email,
            code=error.code.value,
            client_ip=request.client.host if request.client else None,
        )
        _raise_auth_error(error)

    _set_session_cookie(response, raw_token)
    logger.info(
        "auth.audit.login.success",
        method="email",
        user_id=str(user.id),
        email=user.email,
        client_ip=request.client.host if request.client else None,
    )
    return EmailLoginResponse(status="authenticated", user=_to_user_me_response(user))


@router.post("/email/verify", response_model=EmailVerifyResponse)
async def post_email_verify(
    payload: EmailVerifyRequest,
    session: AsyncSession = Depends(get_session),
) -> EmailVerifyResponse:
    """Email 検証トークンを消費して検証を完了する."""
    try:
        await verify_email_by_token(session, token=payload.token)
    except AuthConflictError as error:
        _raise_auth_error(error)
    return EmailVerifyResponse(status="verified")


@router.post("/password/reset/request", response_model=PasswordResetRequestResponse)
async def post_password_reset_request(
    payload: PasswordResetRequestRequest,
    session: AsyncSession = Depends(get_session),
) -> PasswordResetRequestResponse:
    """
    パスワードリセット要求を受け付ける.

    対象アカウントの存在有無にかかわらず、レスポンス形状は一定にする。
    """
    raw_token = await issue_password_reset_token(session, email=payload.email)
    debug_token = raw_token if get_settings().auth_debug_return_tokens else None
    return PasswordResetRequestResponse(status="accepted", debug_reset_token=debug_token)


@router.post("/password/reset/confirm", response_model=PasswordResetConfirmResponse)
async def post_password_reset_confirm(
    payload: PasswordResetConfirmRequest,
    session: AsyncSession = Depends(get_session),
) -> PasswordResetConfirmResponse:
    """リセットトークンでパスワード再設定を確定する."""
    try:
        await reset_password_by_token(
            session,
            token=payload.token,
            new_password=payload.new_password,
        )
    except AuthConflictError as error:
        _raise_auth_error(error)
    return PasswordResetConfirmResponse(status="password_reset")


@router.post("/password/change", response_model=PasswordChangeResponse)
async def post_password_change(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> PasswordChangeResponse:
    """現在パスワード確認つきでパスワード変更を行う."""
    user, _ = await _require_session_user(request, session)

    try:
        await change_email_password(
            session,
            email=user.email,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except AuthConflictError as error:
        _raise_auth_error(error)

    # パスワード変更時は全セッション失効ポリシーのため Cookie も削除する。
    _clear_session_cookie(response)
    return PasswordChangeResponse(status="password_changed")


@router.get("/me", response_model=UserMeResponse)
async def get_auth_me(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> UserMeResponse:
    """現在ログイン中のユーザー情報を返す."""
    user, _ = await _require_session_user(request, session)
    return _to_user_me_response(user)


@router.post("/logout", response_model=LogoutResponse)
async def post_auth_logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> LogoutResponse:
    """現在セッションを失効してログアウトする."""
    cookie_name = get_settings().session_cookie_name
    raw_token = request.cookies.get(cookie_name)
    if raw_token:
        try:
            await revoke_session_by_token(session, raw_token=raw_token)
        except SessionAuthError:
            # 既に失効済み/無効トークンでもログアウト成功として扱う。
            pass
    _clear_session_cookie(response)
    logger.info(
        "auth.audit.logout",
        has_session_cookie=bool(raw_token),
        client_ip=request.client.host if request.client else None,
    )
    return LogoutResponse(status="logged_out")


@router.post("/session/refresh", response_model=SessionRefreshResponse)
async def post_auth_session_refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> SessionRefreshResponse:
    """現在セッションをローテーションして新しい Cookie を発行する."""
    cookie_name = get_settings().session_cookie_name
    raw_token = request.cookies.get(cookie_name)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_missing", "message": "Session cookie is missing"},
        )
    try:
        user, new_token = await refresh_user_session(
            session,
            raw_token=raw_token,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except SessionAuthError as error:
        _raise_session_error(error)

    _set_session_cookie(response, new_token)
    logger.info(
        "auth.audit.session.refresh",
        user_id=str(user.id),
        client_ip=request.client.host if request.client else None,
    )
    return SessionRefreshResponse(status="refreshed", user=_to_user_me_response(user))
