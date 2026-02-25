"""
認証 API ルーター定義.

- Email signup/login/verify/reset/change
- セッションベースの `/auth/me` `/auth/logout`
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import NoReturn
from urllib.parse import urljoin, urlparse

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.idp.entra import (
    fetch_entra_me_profile,
    get_entra_oauth,
    refresh_entra_access_token,
    validate_entra_settings,
)
from app.adapters.postgres.session import get_session
from app.api.schemas.auth import (
    EmailLoginRequest,
    EmailLoginResponse,
    EmailSignupRequest,
    EmailSignupResponse,
    EmailVerifyRequest,
    EmailVerifyResponse,
    EntraGraphProfileResponse,
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
from app.core.security.token_cipher import decrypt_token, encrypt_token
from app.core.settings import get_settings
from app.models.auth.user import User
from app.repositories.auth.session_repository import update_entra_tokens_by_session_id
from app.services.auth.auth_account_service import (
    AuthConflictCode,
    AuthConflictError,
    change_email_password,
    issue_email_verification_token,
    issue_password_reset_token,
    reset_password_by_token,
    resolve_email_login,
    resolve_entra_login,
    signup_email_user,
    verify_email_by_token,
)
from app.services.auth.session_auth_service import (
    SessionAuthError,
    SessionAuthErrorCode,
    issue_user_session,
    refresh_user_session,
    resolve_active_session_by_token,
    resolve_user_by_session_token,
    revoke_session_by_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


def _sanitize_redirect_path(path: str | None) -> str:
    """
    ログイン後リダイレクト先を相対パスに正規化する.

    Args:
        path: 入力パス

    Returns:
        str: 安全な相対パス
    """
    settings = get_settings()
    # 安全側のフォールバック先。
    default_path = settings.auth_post_login_default_path
    if not path:
        # 未指定なら既定パスへ戻す。
        return default_path
    # URL として解釈し、外部URL混入（open redirect）を防ぐ。
    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc:
        return default_path
    # 相対パスのみ許可する（"/..." 以外は拒否）。
    if not path.startswith("/"):
        return default_path
    return path


def _resolve_entra_token_expires_at(token: dict[str, object]) -> datetime | None:
    """
    Authlib が返すトークン情報から有効期限を UTC datetime で解決する.
    """
    expires_at_raw = token.get("expires_at")
    if isinstance(expires_at_raw, (int, float)):
        return datetime.fromtimestamp(expires_at_raw, tz=timezone.utc)

    expires_in_raw = token.get("expires_in")
    if isinstance(expires_in_raw, (int, float)):
        return datetime.now(timezone.utc) + timedelta(seconds=int(expires_in_raw))

    return None


def _resolve_login_identifier(claims: dict[str, object]) -> tuple[str, str]:
    """
    Entra クレームから subject と UPN 相当メールを解決する.

    Args:
        claims: ID トークンクレーム

    Returns:
        tuple[str, str]: (subject, login_email)
    """
    # Entra の一意識別子（oid 優先、なければ sub）を解決する。
    subject = str(claims.get("oid") or claims.get("sub") or "")
    # ログイン識別メールは preferred_username を優先して順に解決する。
    login_email = str(
        claims.get("preferred_username")
        or claims.get("upn")
        or claims.get("email")
        or ""
    ).strip()

    # 認証処理に必要な最小クレームが欠けている場合は 400。
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
    # ドメイン制限が未設定なら全ドメイン許可。
    if not settings.entra_internal_domains:
        return
    # メールの @ 以降をドメインとして比較する。
    domain = login_email.split("@")[-1].lower() if "@" in login_email else ""
    if domain not in settings.entra_internal_domains:
        # 許可外ドメインは 403 で拒否。
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
    # アプリ全体で使うセッションCookieを発行する。
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
    # 同じ属性（path/samesite/secure）で削除しないと消えない場合があるため、
    # 発行時と揃えた属性で delete_cookie する。
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


def _raise_auth_error(error: AuthConflictError) -> NoReturn:
    """
    ドメインエラーを HTTP エラーへ変換して送出する.

    Args:
        error: サービス層の認証エラー
    """
    # ドメイン例外コードを HTTP ステータスへ対応付ける。
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
        AuthConflictCode.PASSWORD_REUSE_NOT_ALLOWED: (
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ),
        AuthConflictCode.EMAIL_VERIFICATION_TOKEN_INVALID: status.HTTP_400_BAD_REQUEST,
        AuthConflictCode.EMAIL_VERIFICATION_TOKEN_EXPIRED: status.HTTP_400_BAD_REQUEST,
        AuthConflictCode.PASSWORD_RESET_TOKEN_INVALID: status.HTTP_400_BAD_REQUEST,
        AuthConflictCode.PASSWORD_RESET_TOKEN_EXPIRED: status.HTTP_400_BAD_REQUEST,
        AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    }
    # API 返却は code/message 形式に統一する。
    raise HTTPException(
        status_code=status_code_map.get(error.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": error.code.value, "message": error.message},
    )


def _raise_session_error(error: SessionAuthError) -> NoReturn:
    """
    セッションエラーを HTTP エラーへ変換して送出する.

    Args:
        error: セッション認証エラー
    """
    # セッション関連の失敗は基本的に未認証扱い（401）。
    status_code_map: dict[SessionAuthErrorCode, int] = {
        SessionAuthErrorCode.SESSION_INVALID: status.HTTP_401_UNAUTHORIZED,
        SessionAuthErrorCode.SESSION_EXPIRED: status.HTTP_401_UNAUTHORIZED,
        SessionAuthErrorCode.USER_NOT_FOUND: status.HTTP_401_UNAUTHORIZED,
    }
    raise HTTPException(
        status_code=status_code_map.get(error.code, status.HTTP_401_UNAUTHORIZED),
        detail={"code": error.code.value, "message": error.message},
    )


def _raise_token_crypto_error(error: RuntimeError) -> NoReturn:
    """
    トークン暗号化/復号エラーを HTTP エラーへ変換して送出する.

    Args:
        error: トークン暗号化エラー
    """
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": "entra_token_crypto_error", "message": str(error)},
    ) from error


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
    # 設定済みのCookie名でセッショントークンを取得する。
    cookie_name = get_settings().session_cookie_name
    raw_token = request.cookies.get(cookie_name)
    if not raw_token:
        # Cookie 自体が無い場合は未ログイン。
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_missing", "message": "Session cookie is missing"},
        )
    try:
        # トークンからユーザーを解決（期限切れ/無効は例外）。
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
        # 1) ユーザー/アイデンティティを作成する。
        await signup_email_user(
            session,
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
        # 2) メール検証トークンを発行する。
        verification_token = await issue_email_verification_token(
            session, email=payload.email
        )
    except AuthConflictError as error:
        # 業務ルール違反は統一フォーマットでHTTPへ変換。
        _raise_auth_error(error)

    # ローカル検証時のみトークンをレスポンスに含める。
    debug_token = (
        verification_token if get_settings().auth_debug_return_tokens else None
    )
    return EmailSignupResponse(
        status="verification_required",
        debug_verification_token=debug_token,
    )


@router.post("/email/verify", response_model=EmailVerifyResponse)
async def post_email_verify(
    payload: EmailVerifyRequest,
    session: AsyncSession = Depends(get_session),
) -> EmailVerifyResponse:
    """Email 検証トークンを消費して検証を完了する."""
    try:
        # トークンを消費し、メール検証済みに更新する。
        await verify_email_by_token(session, token=payload.token)
    except AuthConflictError as error:
        _raise_auth_error(error)
    return EmailVerifyResponse(status="verified")


@router.post("/email/login", response_model=EmailLoginResponse)
async def post_email_login(
    payload: EmailLoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> EmailLoginResponse:
    """Email ログインを実行してセッション Cookie を発行する."""
    try:
        # 1) メール/パスワードでユーザーを認証する。
        user = await resolve_email_login(
            session,
            email=payload.email,
            password=payload.password,
        )
        # 2) 認証成功時に新しいセッションを発行する。
        raw_token = await issue_user_session(
            session,
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthConflictError as error:
        # 失敗監査ログ（理由コード付き）。
        logger.warning(
            "auth.audit.login.failure",
            method="email",
            email=payload.email,
            code=error.code.value,
            client_ip=request.client.host if request.client else None,
        )
        _raise_auth_error(error)

    # 成功時はセッションCookieを設定する。
    _set_session_cookie(response, raw_token)
    # 成功監査ログ。
    logger.info(
        "auth.audit.login.success",
        method="email",
        user_id=str(user.id),
        email=user.email,
        client_ip=request.client.host if request.client else None,
    )
    return EmailLoginResponse(status="authenticated", user=_to_user_me_response(user))


@router.post("/password/change", response_model=PasswordChangeResponse)
async def post_password_change(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> PasswordChangeResponse:
    """現在パスワード確認つきでパスワード変更を行う."""
    # セッションから現在ユーザーを解決する（未ログインなら 401）。
    user, _ = await _require_session_user(request, session)

    try:
        # 現在パスワードを検証し、新パスワードへ更新する。
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


@router.post("/password/reset/request", response_model=PasswordResetRequestResponse)
async def post_password_reset_request(
    payload: PasswordResetRequestRequest,
    session: AsyncSession = Depends(get_session),
) -> PasswordResetRequestResponse:
    """
    パスワードリセット要求を受け付ける.

    対象アカウントの存在有無にかかわらず、レスポンス形状は一定にする。
    """
    # アカウント有無を外部に漏らさない設計のため、内部的に token(None含む)を受け取る。
    raw_token = await issue_password_reset_token(session, email=payload.email)
    # デバッグ時のみ token を返す。
    debug_token = raw_token if get_settings().auth_debug_return_tokens else None
    return PasswordResetRequestResponse(
        status="accepted", debug_reset_token=debug_token
    )


@router.post("/password/reset/confirm", response_model=PasswordResetConfirmResponse)
async def post_password_reset_confirm(
    payload: PasswordResetConfirmRequest,
    session: AsyncSession = Depends(get_session),
) -> PasswordResetConfirmResponse:
    """リセットトークンでパスワード再設定を確定する."""
    try:
        # トークン検証後、パスワードを再設定する。
        await reset_password_by_token(
            session,
            token=payload.token,
            new_password=payload.new_password,
        )
    except AuthConflictError as error:
        _raise_auth_error(error)
    return PasswordResetConfirmResponse(status="password_reset")


@router.get("/entra/login")
async def get_auth_entra_login(request: Request) -> Response:
    """Entra OIDC ログインへリダイレクトする."""
    # Entra必須設定があるかを先に確認する。
    validate_entra_settings()
    settings = get_settings()
    # return_to は安全な相対パスへ正規化する。
    return_to = _sanitize_redirect_path(request.query_params.get("return_to"))
    # コールバック後に使えるよう、サーバーセッションへ一時保存する。
    request.session["entra_post_login_path"] = return_to
    # OIDC クライアントを取得して認可エンドポイントへリダイレクトする。
    oauth = get_entra_oauth()
    try:
        return await oauth.entra.authorize_redirect(
            request,
            redirect_uri=settings.entra_redirect_uri,
            prompt="select_account",
        )
    except OAuthError as error:
        # IdP 側連携失敗は 502 として返す。
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
    # 念のため設定不足を再チェックする。
    validate_entra_settings()
    oauth = get_entra_oauth()
    try:
        # 認可コードをアクセストークンに交換する。
        token = await oauth.entra.authorize_access_token(request)
        # userinfo があればそれを使用。なければ id_token を解析する。
        claims = token.get("userinfo")
        if not claims:
            claims = await oauth.entra.parse_id_token(request, token)
    except OAuthError as error:
        # コールバック失敗監査ログを残す。
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

    # クレームから subject とログインメールを取り出す。
    subject, login_email = _resolve_login_identifier(claims)
    # 許可ドメイン制限（設定時のみ）。
    _validate_internal_domain(login_email)

    try:
        # Entra優先ポリシーでユーザーを解決/統合する。
        user = await resolve_entra_login(
            session,
            user_principal_name=login_email,
            entra_subject=subject,
            display_name=str(claims.get("name") or ""),
        )
        # ログインセッションを新規発行する。
        raw_token = await issue_user_session(
            session,
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            entra_access_token=str(token.get("access_token") or "") or None,
            entra_refresh_token=str(token.get("refresh_token") or "") or None,
            entra_access_token_expires_at=_resolve_entra_token_expires_at(token),
        )
    except RuntimeError as error:
        _raise_token_crypto_error(error)
    except AuthConflictError as error:
        # 競合・業務ルール違反は監査ログを残してHTTP化する。
        logger.warning(
            "auth.audit.login.failure",
            method="entra",
            email=login_email,
            code=error.code.value,
            client_ip=request.client.host if request.client else None,
        )
        _raise_auth_error(error)

    settings = get_settings()
    # ログイン開始時に保存した return_to を取り出す（取り出し後は削除）。
    post_login_path = _sanitize_redirect_path(
        request.session.pop("entra_post_login_path", None)
    )
    # FRONTEND_BASE_URL + return_to で最終遷移先を組み立てる。
    target_url = urljoin(
        settings.frontend_base_url.rstrip("/") + "/", post_login_path.lstrip("/")
    )
    # フロントへ 302 リダイレクトする。
    response = RedirectResponse(url=target_url, status_code=status.HTTP_302_FOUND)
    # リダイレクトレスポンスにセッションCookieを付与する。
    _set_session_cookie(response, raw_token)
    # 成功監査ログ。
    logger.info(
        "auth.audit.login.success",
        method="entra",
        user_id=str(user.id),
        email=user.email,
        client_ip=request.client.host if request.client else None,
    )
    return response


@router.get("/me", response_model=UserMeResponse)
async def get_auth_me(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> UserMeResponse:
    """現在ログイン中のユーザー情報を返す."""
    # セッションからユーザーを引いて返すだけの読み取りAPI。
    user, _ = await _require_session_user(request, session)
    return _to_user_me_response(user)


@router.get("/entra/profile", response_model=EntraGraphProfileResponse)
async def get_auth_entra_profile(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> EntraGraphProfileResponse:
    """
    Entra 認証ユーザー向けに Graph API からプロフィールを返す.
    """
    user, raw_token = await _require_session_user(request, session)
    if user.user_type.value != "internal":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "entra_profile_forbidden",
                "message": "This endpoint is available for Entra users only",
            },
        )

    try:
        current_session = await resolve_active_session_by_token(
            session,
            raw_token=raw_token,
        )
    except SessionAuthError as error:
        _raise_session_error(error)

    try:
        access_token = decrypt_token(current_session.entra_access_token)
        refresh_token = decrypt_token(current_session.entra_refresh_token)
    except RuntimeError as error:
        _raise_token_crypto_error(error)
    access_token_expires_at = current_session.entra_access_token_expires_at
    token_expired = (
        access_token_expires_at is not None
        and access_token_expires_at <= datetime.now(timezone.utc)
    )
    if not access_token or token_expired:
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "entra_refresh_token_missing",
                    "message": "No Entra refresh token is available in the session",
                },
            )
        refreshed = await refresh_entra_access_token(refresh_token=refresh_token)
        new_access_token = str(refreshed.get("access_token") or "")
        new_refresh_token = str(refreshed.get("refresh_token") or "") or None
        access_token_expires_at = _resolve_entra_token_expires_at(refreshed)
        try:
            await update_entra_tokens_by_session_id(
                session,
                session_id=current_session.id,
                access_token=encrypt_token(new_access_token) or "",
                refresh_token=encrypt_token(new_refresh_token),
                access_token_expires_at=access_token_expires_at,
            )
        except RuntimeError as error:
            _raise_token_crypto_error(error)
        access_token = new_access_token

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "entra_access_token_missing",
                "message": "No Entra access token is available in the session",
            },
        )

    profile = await fetch_entra_me_profile(access_token=access_token)
    return EntraGraphProfileResponse(
        **profile,
        access_token_expires_at=access_token_expires_at,
    )


@router.post("/logout", response_model=LogoutResponse)
async def post_auth_logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> LogoutResponse:
    """現在セッションを失効してログアウトする."""
    cookie_name = get_settings().session_cookie_name
    # リクエストCookieから現在セッションを取得する。
    raw_token = request.cookies.get(cookie_name)
    if raw_token:
        try:
            # DB 側のセッションを失効させる。
            await revoke_session_by_token(session, raw_token=raw_token)
        except SessionAuthError:
            # 既に失効済み/無効トークンでもログアウト成功として扱う。
            pass
    # ブラウザ側Cookieも削除する。
    _clear_session_cookie(response)
    # ログアウト監査ログ。
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
    # 現在セッションCookieを取得する。
    raw_token = request.cookies.get(cookie_name)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_missing", "message": "Session cookie is missing"},
        )
    try:
        # 現在セッションを失効し、新トークンを発行してユーザーを返す。
        user, new_token = await refresh_user_session(
            session,
            raw_token=raw_token,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except SessionAuthError as error:
        _raise_session_error(error)

    # 新しいセッションCookieへ差し替える。
    _set_session_cookie(response, new_token)
    # セッション更新監査ログ。
    logger.info(
        "auth.audit.session.refresh",
        user_id=str(user.id),
        client_ip=request.client.host if request.client else None,
    )
    return SessionRefreshResponse(status="refreshed", user=_to_user_me_response(user))
