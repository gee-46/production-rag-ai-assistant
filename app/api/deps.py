import uuid

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthError, PermissionError_
from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import ROLE_RANK, WorkspaceMembership, WorkspaceRole

DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    settings=Depends(get_settings),
) -> User:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            user = db.get(User, uuid.UUID(user_id)) if user_id else None
            if user and user.is_active:
                return user
        except TokenError as exc:
            if settings.auth_enabled:
                raise AuthError(f"Invalid token: {exc}") from exc

    if not settings.auth_enabled:
        # Enforce localhost restriction for unauthenticated demo mode if demo_local_only is active
        if getattr(settings, "demo_local_only", True):
            client_host = request.client.host if request.client else "localhost"
            allowed_hosts = {"127.0.0.1", "::1", "localhost", "testclient"}
            if client_host not in allowed_hosts:
                raise PermissionError_("Unauthenticated demo mode is restricted to localhost. Set AUTH_ENABLED=true for production deployment.")

        # Resolve or create the default demo user for frictionless local experience
        demo_user = db.get(User, DEMO_USER_ID)
        if demo_user is None:
            demo_user = db.query(User).filter(User.email == "demo@company.com").first()
        if demo_user is None:
            demo_user = User(
                id=DEMO_USER_ID,
                email="demo@company.com",
                full_name="Demo User",
                hashed_password="demo_password_hash",
                is_active=True,
                is_superuser=True,
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
        return demo_user

    raise AuthError("Missing or malformed Authorization header")


class RequireWorkspaceRole:
    """
    Dependency factory enforcing that the current user is a member of
    `workspace_id` (a path parameter) with at least `minimum` role.
    Returns the membership row so route handlers can also read the role.
    """

    def __init__(self, minimum: WorkspaceRole = WorkspaceRole.viewer):
        self.minimum = minimum

    def __call__(
        self,
        workspace_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        settings=Depends(get_settings),
    ) -> WorkspaceMembership:
        if current_user.is_superuser or not settings.auth_enabled:
            # Superusers and login-free demo users act as owner of the workspace.
            membership = (
                db.query(WorkspaceMembership)
                .filter(
                    WorkspaceMembership.workspace_id == workspace_id,
                    WorkspaceMembership.user_id == current_user.id,
                )
                .first()
            )
            if membership is None:
                membership = WorkspaceMembership(
                    workspace_id=workspace_id,
                    user_id=current_user.id,
                    role=WorkspaceRole.owner,
                )
            return membership

        membership = (
            db.query(WorkspaceMembership)
            .filter(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == current_user.id,
            )
            .first()
        )
        if membership is None:
            raise PermissionError_("You are not a member of this workspace")
        if ROLE_RANK[membership.role] < ROLE_RANK[self.minimum]:
            raise PermissionError_(f"Requires at least '{self.minimum.value}' role in this workspace")
        return membership


require_viewer = RequireWorkspaceRole(WorkspaceRole.viewer)
require_member = RequireWorkspaceRole(WorkspaceRole.member)
require_admin = RequireWorkspaceRole(WorkspaceRole.admin)

