import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership, WorkspaceRole
from app.schemas.auth import MembershipInvite, WorkspaceCreate, WorkspaceOut

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceOut, status_code=201)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workspace:
    workspace = Workspace(name=payload.name, owner_id=current_user.id)
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=current_user.id, role=WorkspaceRole.owner))
    db.commit()
    db.refresh(workspace)
    return workspace


from app.core.config import Settings, get_settings


@router.get("", response_model=list[WorkspaceOut])
def list_my_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    workspaces = (
        db.query(Workspace)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .filter(WorkspaceMembership.user_id == current_user.id)
        .all()
    )
    if not workspaces and not settings.auth_enabled:
        demo_ws = Workspace(
            name="Demo Knowledge Base",
            owner_id=current_user.id,
        )
        db.add(demo_ws)
        db.flush()
        db.add(WorkspaceMembership(workspace_id=demo_ws.id, user_id=current_user.id, role=WorkspaceRole.owner))
        db.commit()
        db.refresh(demo_ws)
        return [demo_ws]
    return workspaces



@router.post("/{workspace_id}/members", status_code=201)
def invite_member(
    workspace_id: uuid.UUID,
    payload: MembershipInvite,
    _membership=Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        raise NotFoundError("No user with that email exists yet; they must register first")

    role = WorkspaceRole(payload.role)
    existing = (
        db.query(WorkspaceMembership)
        .filter(WorkspaceMembership.workspace_id == workspace_id, WorkspaceMembership.user_id == user.id)
        .first()
    )
    if existing:
        existing.role = role
    else:
        db.add(WorkspaceMembership(workspace_id=workspace_id, user_id=user.id, role=role))
    db.commit()
    return {"message": f"{payload.email} added to workspace with role {role.value}"}
