"""
API Client for Production RAG AI Assistant.
Supports both Live FastAPI Backend (Docker / Remote) and
Pure Python Standalone Engine (No Docker required).
"""
from __future__ import annotations

import json
from typing import Any, Generator, Optional
import httpx

from frontend.standalone_engine import StandaloneEngine


class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000", token: Optional[str] = None, force_standalone: bool = False):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = token
        self.timeout = 25.0
        self.force_standalone = force_standalone
        self._standalone = StandaloneEngine.get_instance()

    def set_token(self, token: Optional[str]):
        self.token = token

    def _headers(self, extra: Optional[dict] = None) -> dict:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    def is_standalone(self) -> bool:
        if self.force_standalone:
            return True
        health = self.check_health()
        return health.get("status") != "ok"

    # --- Health & System ---
    def check_health(self) -> dict:
        if self.force_standalone:
            return {"status": "ok", "mode": "standalone", "data": {"status": "ok", "environment": "standalone_python"}}
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/health")
                if res.status_code == 200:
                    return {"status": "ok", "mode": "fastapi", "data": res.json()}
                return {"status": "error", "error": f"HTTP {res.status_code}"}
        except Exception:
            return {"status": "ok", "mode": "standalone", "data": {"status": "ok", "environment": "standalone_python"}}

    def health_check(self) -> dict:
        h = self.check_health()
        return {
            "status": h.get("status", "ok"),
            "mode": h.get("mode", "standalone"),
            "fastapi_online": h.get("mode") == "fastapi",
            "data": h.get("data", {}),
        }

    def get_metrics(self) -> dict:
        if not self.force_standalone:
            try:
                with httpx.Client(timeout=3.0) as client:
                    res = client.get(f"{self.base_url}/metrics")
                    if res.status_code == 200:
                        return {"status": "ok", "raw_text": res.text}
            except Exception:
                pass

        # Standalone Prometheus metrics formatting
        raw_prom = f"""# HELP http_requests_total Total HTTP requests handled
# TYPE http_requests_total counter
http_requests_total{{method="POST",path="/auth/login",status_code="200"}} {self._standalone.total_requests}
http_requests_total{{method="POST",path="/chat",status_code="200"}} {self._standalone.generation_count}
rag_retrieval_duration_seconds_count {self._standalone.query_count}
rag_generation_duration_seconds_count {self._standalone.generation_count}
"""
        return {"status": "ok", "raw_text": raw_prom}

    # --- Auth ---
    def register(self, email: str, password: str, full_name: Optional[str] = None) -> dict:
        if not self.force_standalone:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(
                        f"{self.base_url}/auth/register",
                        json={"email": email, "password": password, "full_name": full_name},
                    )
                    if res.status_code in (200, 201):
                        return {"success": True, "data": res.json()}
                    return {"success": False, "error": res.json().get("detail", res.text)}
            except Exception:
                pass
        return self._standalone.register(email, password, full_name)

    def login(self, email: str, password: str) -> dict:
        if not self.force_standalone:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(
                        f"{self.base_url}/auth/login",
                        json={"email": email, "password": password},
                    )
                    if res.status_code == 200:
                        data = res.json()
                        self.set_token(data.get("access_token"))
                        return {"success": True, "token": data.get("access_token")}
            except Exception:
                pass
        res = self._standalone.login(email, password)
        if res.get("success"):
            self.set_token(res.get("token"))
        return res

    # --- Workspaces ---
    def list_workspaces(self) -> list[dict]:
        if not self.force_standalone:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(f"{self.base_url}/workspaces", headers=self._headers())
                    if res.status_code == 200:
                        return res.json()
            except Exception:
                pass
        user = self._standalone.get_user_by_token(self.token)
        return self._standalone.list_workspaces(user.get("email") if user else None)

    def create_workspace(self, name: str) -> dict:
        if not self.force_standalone:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(
                        f"{self.base_url}/workspaces",
                        headers=self._headers(),
                        json={"name": name},
                    )
                    if res.status_code in (200, 201):
                        return {"success": True, "data": res.json()}
            except Exception:
                pass
        user = self._standalone.get_user_by_token(self.token)
        return self._standalone.create_workspace(name, user.get("email") if user else "lead.engineer@company.com")

    def invite_member(self, workspace_id: str, email: str, role: str = "member") -> dict:
        if not self.force_standalone:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(
                        f"{self.base_url}/workspaces/{workspace_id}/members",
                        headers=self._headers(),
                        json={"email": email, "role": role},
                    )
                    if res.status_code in (200, 201):
                        return {"success": True, "data": res.json()}
            except Exception:
                pass
        return self._standalone.invite_member(workspace_id, email, role)

    # --- Documents ---
    def list_documents(self, workspace_id: str) -> list[dict]:
        if not self.force_standalone:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(
                        f"{self.base_url}/workspaces/{workspace_id}/documents",
                        headers=self._headers(),
                    )
                    if res.status_code == 200:
                        return res.json()
            except Exception:
                pass
        return self._standalone.list_documents(workspace_id)

    def upload_document(
        self,
        workspace_id: str,
        filename: str,
        file_bytes: bytes,
        content_type: str = "application/octet-stream",
        visibility: str = "workspace",
    ) -> dict:
        if not self.force_standalone:
            try:
                files = {"file": (filename, file_bytes, content_type)}
                data = {"visibility": visibility}
                with httpx.Client(timeout=60.0) as client:
                    res = client.post(
                        f"{self.base_url}/workspaces/{workspace_id}/documents",
                        headers=self._headers(),
                        files=files,
                        data=data,
                    )
                    if res.status_code in (200, 202):
                        return {"success": True, "data": res.json()}
            except Exception:
                pass

        # Standalone extraction
        user = self._standalone.get_user_by_token(self.token)
        uploaded_by = user.get("id") if user else "user_id"
        doc = self._standalone.ingest_document(
            workspace_id=workspace_id,
            filename=filename,
            file_bytes=file_bytes,
            uploaded_by=uploaded_by,
            visibility=visibility,
            content_type=content_type,
        )
        return {"success": True, "data": {"document": doc, "message": "Document indexed successfully in local engine."}}

    def delete_document(self, workspace_id: str, document_id: str) -> dict:
        if not self.force_standalone:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.delete(
                        f"{self.base_url}/workspaces/{workspace_id}/documents/{document_id}",
                        headers=self._headers(),
                    )
                    if res.status_code == 204:
                        return {"success": True}
            except Exception:
                pass
        return self._standalone.delete_document(workspace_id, document_id)

    # --- Chat & Streaming ---
    def chat_stream(
        self,
        workspace_id: str,
        query: str,
        session_id: Optional[str] = None,
    ) -> Generator[dict, None, None]:
        if not self.force_standalone:
            try:
                payload: dict[str, Any] = {"query": query, "stream": True}
                if session_id:
                    payload["session_id"] = session_id

                with httpx.Client(timeout=120.0) as client:
                    with client.stream(
                        "POST",
                        f"{self.base_url}/workspaces/{workspace_id}/chat/stream",
                        headers=self._headers({"Content-Type": "application/json"}),
                        json=payload,
                    ) as response:
                        if response.status_code == 200:
                            current_event = "message"
                            for line in response.iter_lines():
                                line = line.strip()
                                if not line:
                                    continue
                                if line.startswith("event:"):
                                    current_event = line.replace("event:", "").strip()
                                elif line.startswith("data:"):
                                    data_str = line[5:].strip()
                                    try:
                                        data_obj = json.loads(data_str)
                                        if current_event == "session":
                                            yield {"event": "session", "session_id": data_obj.get("session_id")}
                                        elif current_event == "done":
                                            yield {
                                                "event": "done",
                                                "citations": data_obj.get("citations", []),
                                                "groundedness": data_obj.get("groundedness", {}),
                                                "retrieval_debug": data_obj.get("retrieval_debug", {}),
                                            }
                                        else:
                                            delta = data_obj.get("delta", "")
                                            yield {"event": "delta", "delta": delta}
                                    except Exception:
                                        pass
                                    current_event = "message"
                            return
            except Exception:
                pass

        # Fallback / Standalone generator
        yield from self._standalone.chat_stream(workspace_id, query, session_id)

    # --- Evaluation ---
    def ingest_benchmark_corpus(self, workspace_id: str) -> dict:
        return self._standalone.ingest_benchmark_corpus(workspace_id)

    def run_eval(self, workspace_id: str) -> dict:
        if not self.force_standalone:
            try:
                with httpx.Client(timeout=180.0) as client:
                    res = client.post(
                        f"{self.base_url}/workspaces/{workspace_id}/eval/run",
                        headers=self._headers(),
                    )
                    if res.status_code == 200:
                        return {"success": True, "data": res.json()}
            except Exception:
                pass
        return {"success": True, "data": self._standalone.run_eval(workspace_id)}
