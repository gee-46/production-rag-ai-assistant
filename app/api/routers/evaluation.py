import uuid
from pathlib import Path

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.services.embeddings.factory import get_embedding_provider
from app.services.evaluation.harness import load_golden_set, run_retrieval_eval
from app.services.llm.factory import get_llm_provider
from app.services.rag.orchestrator import RagOrchestrator
from app.services.retrieval.reranker import build_reranker

router = APIRouter(prefix="/workspaces/{workspace_id}/eval", tags=["evaluation"])

GOLDEN_SET_PATH = Path(__file__).resolve().parents[3] / "eval" / "golden_qa.json"


@router.post("/run")
def run_eval(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    _membership=Depends(require_admin),
    db=Depends(get_db),
):
    """
    Admin-only: runs the labeled golden set through the real retrieval +
    generation pipeline for this workspace and reports precision@k,
    recall@k, MRR, and the groundedness rate. Requires documents already
    ingested into the workspace that match eval/golden_qa.json's expected
    filenames.
    """
    settings = get_settings()
    orchestrator = RagOrchestrator(
        embedder=get_embedding_provider(),
        reranker=build_reranker(settings.reranker_provider, settings.reranker_model),
        llm=get_llm_provider(),
    )
    golden_set = load_golden_set(GOLDEN_SET_PATH)
    return run_retrieval_eval(
        db, golden_set=golden_set, workspace_id=workspace_id, user_id=current_user.id, orchestrator=orchestrator
    )
