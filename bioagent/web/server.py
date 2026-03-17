"""
BioAgent Web UI -- FastAPI backend with SSE streaming.

Wraps the Agent's execute() loop and emits structured SSE events
that a frontend can consume for real-time interaction.

Key design notes:
1. Agent.execute() is async but can have blocking operations
2. SSE (Server-Sent Events) provides real-time streaming to the browser
3. Multi-session support with persistent state storage
4. File upload and management capabilities
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import threading
import uuid
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

if TYPE_CHECKING:
    from bioagent.agent import Agent
    from bioagent.config import BioAgentConfig


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DONE = object()

_IMG_EXTS = frozenset((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"))


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _create_session_dir(base_dir: Path, session_id: Optional[str] = None) -> tuple[str, Path, Path]:
    """
    Create a per-session workspace directory.

    Returns:
        tuple: (session_id, workspace_dir, upload_subdir)
    """
    sid = session_id or uuid.uuid4().hex[:12]
    base = base_dir / sid
    uploads = base / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    return sid, base, uploads


def _safe_upload_name(dest_dir: Path, original_name: str) -> Path:
    """Generate a safe upload filename to avoid conflicts."""
    candidate = dest_dir / original_name
    if not candidate.exists():
        return candidate
    stem, ext = os.path.splitext(original_name)
    n = 1
    while True:
        candidate = dest_dir / f"{stem}_{n}{ext}"
        if not candidate.exists():
            return candidate
        n += 1


def _make_file_entry(abs_path: Path, workspace_dir: Path) -> Dict[str, Any]:
    """Create a file entry dictionary for frontend consumption."""
    ext = abs_path.suffix.lower()
    ftype = "image" if ext in _IMG_EXTS else "file"
    try:
        mtime = int(abs_path.stat().st_mtime * 1000)
    except OSError:
        mtime = int(time() * 1000)
    entry = {
        "path": str(abs_path),
        "name": abs_path.name,
        "type": ftype,
        "ext": ext,
        "timestamp": mtime,
    }
    try:
        entry["relativePath"] = str(abs_path.relative_to(workspace_dir))
    except ValueError:
        entry["relativePath"] = str(abs_path)
    return entry


def _is_subpath(path: Path, roots: List[Path]) -> bool:
    """Check if a path is within any of the root directories."""
    try:
        rp = path.resolve()
    except Exception:
        return False
    for root in roots:
        try:
            rr = root.resolve()
            if os.path.commonpath([rp, rr]) == rr:
                return True
        except Exception:
            continue
    return False


# ---------------------------------------------------------------------------
# Session State Management
# ---------------------------------------------------------------------------

class SessionManager:
    """Manages multiple agent sessions with persistent state."""

    def __init__(self, sessions_dir: Path):
        """
        Initialize session manager.

        Args:
            sessions_dir: Base directory for session storage
        """
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, Dict[str, Any]] = self._load_sessions()
        self.active_session_id: Optional[str] = self._get_most_recent_id()

    def _load_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Load all sessions from disk."""
        loaded = {}
        for session_dir in self.sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue
            json_path = session_dir / "session.json"
            if not json_path.exists():
                continue
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sid = data.get("id")
                if sid:
                    loaded[sid] = data
            except Exception:
                continue
        return loaded

    def _get_most_recent_id(self) -> Optional[str]:
        """Get ID of most recently created session."""
        if not self.sessions:
            return None
        return max(
            self.sessions.keys(),
            key=lambda k: self.sessions[k].get("created", 0)
        )

    def get_or_create(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get existing session or create a new one.

        Args:
            session_id: Optional existing session ID

        Returns:
            Session dictionary with state and metadata
        """
        if session_id and session_id in self.sessions:
            self.active_session_id = session_id
            return self.sessions[session_id]

        sid, workspace, uploads = _create_session_dir(self.sessions_dir, session_id)
        session = {
            "id": sid,
            "workspace": str(workspace),
            "upload_dir": str(uploads),
            "state": {
                "messages": [],
                "result_files": [],
                "uploaded_paths": set(),
            },
            "title": "New Task",
            "created": time(),
        }
        self.sessions[sid] = session
        self.active_session_id = sid
        self._save_session(session)
        return session

    def get_active(self) -> Dict[str, Any]:
        """Get currently active session."""
        sid = self.active_session_id
        if sid and sid in self.sessions:
            return self.sessions[sid]
        return self.get_or_create()

    def activate(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Switch to a different session.

        Args:
            session_id: Session ID to activate

        Returns:
            Session dictionary if found, None otherwise
        """
        if session_id not in self.sessions:
            return None
        self.active_session_id = session_id
        return self.sessions[session_id]

    def update(self, session_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Update session metadata.

        Args:
            session_id: Session ID to update
            **kwargs: Fields to update (e.g., title)

        Returns:
            Updated session dictionary if found, None otherwise
        """
        if session_id not in self.sessions:
            return None
        self.sessions[session_id].update(kwargs)
        self._save_session(self.sessions[session_id])
        return self.sessions[session_id]

    def delete(self, session_id: str) -> bool:
        """
        Delete a session and its workspace.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted, False if not found
        """
        if session_id not in self.sessions:
            return False

        workspace = self.sessions[session_id].get("workspace")
        del self.sessions[session_id]

        # Remove workspace from disk
        if workspace:
            try:
                shutil.rmtree(workspace)
            except Exception:
                pass

        # If deleted active one, switch to another
        if self.active_session_id == session_id:
            self.active_session_id = self._get_most_recent_id()

        return True

    def list_all(self) -> List[Dict[str, Any]]:
        """List all sessions sorted by creation time."""
        summaries = []
        for sid, session in self.sessions.items():
            msgs = session.get("state", {}).get("messages", [])
            title = session.get("title", "New Task")
            # Auto-derive title from first user message
            if title == "New Task" and msgs:
                for m in msgs:
                    if m.get("role") == "user":
                        raw = m.get("content", "").split("\n")[0].strip()
                        title = raw[:60] + ("..." if len(raw) > 60 else "")
                        session["title"] = title
                        break
            summaries.append({
                "id": sid,
                "title": title,
                "messageCount": len(msgs),
                "created": session.get("created", 0),
                "isActive": sid == self.active_session_id,
            })
        summaries.sort(key=lambda x: x["created"], reverse=True)
        return summaries

    def _save_session(self, session: Dict[str, Any]) -> None:
        """Save session state to disk."""
        try:
            workspace = Path(session["workspace"])
            workspace.mkdir(parents=True, exist_ok=True)
            data = {
                "id": session["id"],
                "title": session.get("title", "New Task"),
                "created": session.get("created", 0),
                "workspace": str(workspace),
                "upload_dir": session.get("upload_dir", ""),
                "state": {
                    "messages": session["state"].get("messages", []),
                    "result_files": session["state"].get("result_files", []),
                    "uploaded_paths": list(session["state"].get("uploaded_paths", [])),
                },
            }
            json_path = workspace / "session.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # best-effort


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------

def create_app(agent: Agent, config: BioAgentConfig) -> FastAPI:
    """
    Create FastAPI application for BioAgent web UI.

    Args:
        agent: BioAgent agent instance
        config: BioAgent configuration

    Returns:
        FastAPI application instance
    """
    app = FastAPI(title="BioAgent Web UI")

    # CORS middleware
    if config.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Session manager
    session_manager = SessionManager(config.sessions_dir)

    # ------------------------------------------------------------------
    # Session management endpoints
    # ------------------------------------------------------------------
    @app.get("/api/sessions")
    async def list_sessions():
        """Return all sessions sorted by creation time (newest first)."""
        summaries = session_manager.list_all()
        return JSONResponse({
            "sessions": summaries,
            "activeId": session_manager.active_session_id
        })

    @app.post("/api/sessions")
    async def create_session():
        """Create a new session and set it as active."""
        session = session_manager.get_or_create()
        return JSONResponse(session_manager.list_all()[0])  # Return new session summary

    @app.post("/api/sessions/{session_id}/activate")
    async def activate_session(session_id: str):
        """Switch active session."""
        session = session_manager.activate(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        st = session["state"]
        return JSONResponse({
            "id": session["id"],
            "title": session.get("title", "New Task"),
            "messageCount": len(st["messages"]),
            "created": session.get("created", 0),
            "isActive": True,
            "messages": st["messages"],
            "resultFiles": st.get("result_files", []),
        })

    @app.delete("/api/sessions/{session_id}")
    async def delete_session(session_id: str):
        """Delete a session and its workspace directory."""
        if not session_manager.delete(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        return JSONResponse({"ok": True})

    @app.patch("/api/sessions/{session_id}")
    async def update_session(session_id: str, request: Request):
        """Update session metadata (e.g. title)."""
        body = await request.json()
        updated = session_manager.update(session_id, **body)
        if not updated:
            raise HTTPException(status_code=404, detail="Session not found")
        return JSONResponse({
            "id": updated["id"],
            "title": updated.get("title", "New Task"),
            "messageCount": len(updated["state"]["messages"]),
            "created": updated.get("created", 0),
            "isActive": updated["id"] == session_manager.active_session_id,
        })

    # ------------------------------------------------------------------
    # SSE streaming endpoint
    # ------------------------------------------------------------------
    @app.post("/api/chat")
    async def chat_stream(request: Request):
        """
        Stream agent responses via Server-Sent Events.

        Request body:
            prompt: User query text
            sessionId: Optional session ID (uses active if not provided)
        """
        body = await request.json()
        prompt = body.get("prompt", "")
        req_sid = body.get("sessionId")

        sess = session_manager.get_or_create(req_sid) if req_sid else session_manager.get_active()
        workspace_dir = Path(sess["workspace"])
        conversation_state = sess["state"]

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        cancel_event = threading.Event()
        sess["_cancel"] = cancel_event

        def _put(evt: Dict[str, Any]) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, evt)

        def _producer() -> None:
            prev_cwd = os.getcwd()
            try:
                os.chdir(workspace_dir)
            except OSError:
                pass

            try:
                # Add user message to conversation state
                conversation_state["messages"].append({"role": "user", "content": prompt})
                result_files: List[Dict[str, Any]] = list(conversation_state.get("result_files", []))

                def emit(payload: Dict[str, Any]) -> None:
                    _put({"event": "message", "data": json.dumps(payload)})

                # Execute agent query
                t = time()

                # Initial status
                emit({"type": "status", "content": "Processing..."})
                emit({"type": "reasoning", "content": "Starting agent execution..."})

                # Stream from agent.execute()
                try:
                    # Note: agent.execute() is async, but we're in a thread
                    # We'll use asyncio.run_coroutine_threadsafe to handle this
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = loop.run_in_executor(
                            executor,
                            lambda: asyncio.run(agent.execute(prompt))
                        )
                        result = future.result(timeout=300)  # 5 minute timeout

                    # Add assistant response to conversation
                    conversation_state["messages"].append({"role": "assistant", "content": result})
                    emit({"type": "solution", "content": result})

                except Exception as exc:
                    error_msg = str(exc)
                    emit({"type": "error", "content": error_msg})
                    emit({"type": "done"})

                # Scan workspace for new files
                if os.path.isdir(workspace_dir):
                    try:
                        for entry in workspace_dir.iterdir():
                            if entry.name.startswith('.') or entry.name in ("uploads", "session.json"):
                                continue
                            if entry.is_dir():
                                for sub_entry in entry.rglob("*"):
                                    if sub_entry.is_file():
                                        path_str = str(sub_entry)
                                        if not any(f["path"] == path_str for f in result_files):
                                            result_files.append(_make_file_entry(sub_entry, workspace_dir))
                            elif entry.is_file():
                                path_str = str(entry)
                                if not any(f["path"] == path_str for f in result_files):
                                    result_files.append(_make_file_entry(entry, workspace_dir))
                    except PermissionError:
                        pass

                # Emit final files list
                if result_files != conversation_state.get("result_files", []):
                    conversation_state["result_files"] = result_files
                    emit({"type": "files", "files": result_files})

                # Persist session
                session_manager._save_session(sess)

                emit({"type": "done"})

            except Exception as exc:
                _put({"event": "message", "data": json.dumps({"type": "error", "content": str(exc)})})
                _put({"event": "message", "data": json.dumps({"type": "done"})})
            finally:
                sess.pop("_cancel", None)
                try:
                    os.chdir(prev_cwd)
                except OSError:
                    pass
                _put(_DONE)

        async def event_generator():
            thread = threading.Thread(target=_producer, daemon=True)
            thread.start()
            while True:
                item = await queue.get()
                if item is _DONE:
                    break
                yield item

        return EventSourceResponse(event_generator())

    # ------------------------------------------------------------------
    # Stop streaming
    # ------------------------------------------------------------------
    @app.post("/api/stop")
    async def stop_stream():
        """Signal running producer thread to stop."""
        sess = session_manager.get_active()
        cancel_ev = sess.get("_cancel")
        if cancel_ev and isinstance(cancel_ev, threading.Event):
            cancel_ev.set()
        return JSONResponse({"ok": True})

    # ------------------------------------------------------------------
    # File serving
    # ------------------------------------------------------------------
    @app.get("/api/files")
    async def get_file(path: str):
        """Serve a file from the active session workspace."""
        abs_path = Path(path)
        if not abs_path.is_absolute() or not abs_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        sess = session_manager.get_active()
        workspace = Path(sess["workspace"])
        roots = [workspace]

        if not _is_subpath(abs_path, roots):
            raise HTTPException(status_code=403, detail="Access denied")

        return FileResponse(abs_path, filename=abs_path.name)

    # ------------------------------------------------------------------
    # Directory listing
    # ------------------------------------------------------------------
    @app.get("/api/dir")
    async def list_dir(path: str):
        """List directory contents from the active session workspace."""
        abs_path = Path(path)
        if not abs_path.is_absolute() or not abs_path.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")

        sess = session_manager.get_active()
        workspace = Path(sess["workspace"])
        roots = [workspace]

        if not roots or not _is_subpath(abs_path, roots):
            raise HTTPException(status_code=403, detail="Access denied")

        entries = []
        try:
            for entry in sorted(abs_path.iterdir(), key=lambda e: (not e.is_dir(), e.name)):
                if entry.name.startswith('.'):
                    continue
                if entry.is_dir():
                    e_dict = {
                        "name": entry.name,
                        "path": str(entry),
                        "type": "directory",
                        "ext": ""
                    }
                    try:
                        e_dict["relativePath"] = str(entry.relative_to(workspace))
                    except ValueError:
                        e_dict["relativePath"] = str(entry)
                    entries.append(e_dict)
                elif entry.is_file():
                    ext = entry.suffix.lower()
                    e_dict = {
                        "name": entry.name,
                        "path": str(entry),
                        "type": "image" if ext in _IMG_EXTS else "file",
                        "ext": ext,
                        "timestamp": int(entry.stat().st_mtime * 1000),
                    }
                    try:
                        e_dict["relativePath"] = str(entry.relative_to(workspace))
                    except ValueError:
                        e_dict["relativePath"] = str(entry)
                    entries.append(e_dict)
        except PermissionError:
            pass
        return JSONResponse({"entries": entries, "path": str(abs_path)})

    # ------------------------------------------------------------------
    # File upload
    # ------------------------------------------------------------------
    @app.post("/api/upload")
    async def upload_file(file: UploadFile = File(...)):
        """Upload a file to the active session."""
        sess = session_manager.get_active()
        upload_dir = Path(sess["upload_dir"])

        original_name = file.filename or "file"
        dest = _safe_upload_name(upload_dir, original_name)

        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)

        uploaded_paths = sess["state"]["uploaded_paths"]
        if isinstance(uploaded_paths, set):
            uploaded_paths.add(str(dest))
        elif isinstance(uploaded_paths, list):
            uploaded_paths.append(str(dest))
        else:
            sess["state"]["uploaded_paths"] = [str(dest)]

        return JSONResponse({"path": str(dest), "name": original_name})

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------
    @app.get("/api/health")
    async def health():
        """Health check endpoint."""
        return JSONResponse({
            "status": "ok",
            "model": config.model,
            "sessionCount": len(session_manager.sessions)
        })

    # ------------------------------------------------------------------
    # Serve test page (fallback)
    # ------------------------------------------------------------------
    from fastapi.responses import HTMLResponse

    test_page_path = Path(__file__).parent / "test_page.html"
    if test_page_path.exists():
        @app.get("/")
        async def serve_test_page():
            """Serve a simple test page."""
            with open(test_page_path, "r", encoding="utf-8") as f:
                content = f.read()
            return HTMLResponse(content)

    return app
