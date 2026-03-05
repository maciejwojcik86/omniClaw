from __future__ import annotations

from datetime import datetime, timezone
import getpass
import json
from pathlib import Path
import shlex
import subprocess
from uuid import uuid4

from fastapi import HTTPException

from omniclaw.config import Settings
from omniclaw.db.models import Node
from omniclaw.db.repository import KernelRepository
from omniclaw.runtime.schemas import RuntimeActionRequest


class RuntimeService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: KernelRepository,
        mode: str,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._mode = mode

    def execute(self, request: RuntimeActionRequest) -> dict[str, object]:
        if request.action == "list_agents":
            return {
                "action": request.action,
                "agents": [self._serialize_node(node) for node in self._repository.list_agent_nodes()],
            }

        node = self._resolve_agent_node(request)

        if request.action == "gateway_start":
            return self._gateway_start(node=node, request=request)
        if request.action == "gateway_stop":
            return self._gateway_stop(node=node, request=request)
        if request.action == "gateway_status":
            return self._gateway_status(node=node, request=request)

        raise HTTPException(status_code=400, detail=f"Unsupported runtime action '{request.action}'")

    def _gateway_start(self, *, node: Node, request: RuntimeActionRequest) -> dict[str, object]:
        workspace_root = self._resolve_workspace_root(node)
        artifact_paths = self._resolve_artifact_paths(workspace_root)
        gateway_command_args = self._build_gateway_command_args(host=request.gateway_host, port=request.gateway_port)
        gateway_command = shlex.join(gateway_command_args)
        started_at = datetime.now(timezone.utc)

        if self._mode == "mock":
            pid = node.gateway_pid if node.gateway_running and node.gateway_pid else int(datetime.now(timezone.utc).timestamp())
            if node.gateway_running and not request.force_restart:
                status = "already_running"
                exit_code = 10
            else:
                status = "started"
                exit_code = 0
            updated = self._repository.mark_gateway_started(
                node_id=node.id,
                pid=pid,
                host=request.gateway_host,
                port=request.gateway_port,
            )
            finished_at = datetime.now(timezone.utc)
            metadata_path = self._write_run_metadata(
                workspace_root=workspace_root,
                action=request.action,
                started_at=started_at,
                finished_at=finished_at,
                command=gateway_command,
                exit_code=exit_code,
                stdout=status,
                stderr="",
                artifact_paths=artifact_paths,
            )
            return {
                "action": request.action,
                "node": self._serialize_node(updated),
                "gateway": {
                    "status": status,
                    "running": True,
                    "pid": pid,
                    "host": request.gateway_host,
                    "port": request.gateway_port,
                    "command": gateway_command,
                    "artifact_paths": {**artifact_paths, "run_metadata": str(metadata_path)},
                },
            }

        if request.force_restart and node.gateway_running:
            self._gateway_stop(node=node, request=request)

        script = self._build_start_script(
            workspace_root=workspace_root,
            gateway_command=gateway_command,
            artifact_paths=artifact_paths,
        )
        process = self._run_as_user(username=node.linux_username or "", script=script)
        finished_at = datetime.now(timezone.utc)

        if process.returncode not in {0, 10}:
            self._write_run_metadata(
                workspace_root=workspace_root,
                action=request.action,
                started_at=started_at,
                finished_at=finished_at,
                command=gateway_command,
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                artifact_paths=artifact_paths,
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    "Gateway start failed: "
                    f"exit_code={process.returncode}, stderr={self._trim_output(process.stderr)}"
                ),
            )

        status_token = self._first_line(process.stdout)
        pid = self._extract_pid(status_token)
        if pid is None and node.gateway_pid is not None:
            pid = node.gateway_pid
        if pid is None:
            raise HTTPException(status_code=500, detail="Gateway start did not return PID")

        if process.returncode == 0:
            status = "started"
            updated = self._repository.mark_gateway_started(
                node_id=node.id,
                pid=pid,
                host=request.gateway_host,
                port=request.gateway_port,
            )
        else:
            status = "already_running"
            updated = self._repository.reconcile_gateway_state(
                node_id=node.id,
                running=True,
                pid=pid,
                host=request.gateway_host,
                port=request.gateway_port,
            )

        metadata_path = self._write_run_metadata(
            workspace_root=workspace_root,
            action=request.action,
            started_at=started_at,
            finished_at=finished_at,
            command=gateway_command,
            exit_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
            artifact_paths=artifact_paths,
        )
        return {
            "action": request.action,
            "node": self._serialize_node(updated),
            "gateway": {
                "status": status,
                "running": True,
                "pid": pid,
                "host": request.gateway_host,
                "port": request.gateway_port,
                "command": gateway_command,
                "artifact_paths": {**artifact_paths, "run_metadata": str(metadata_path)},
            },
        }

    def _gateway_stop(self, *, node: Node, request: RuntimeActionRequest) -> dict[str, object]:
        del request  # currently unused
        workspace_root = self._resolve_workspace_root(node)
        artifact_paths = self._resolve_artifact_paths(workspace_root)
        started_at = datetime.now(timezone.utc)
        stop_command = "gateway_stop"

        if self._mode == "mock":
            status = "stopped" if node.gateway_running else "already_stopped"
            updated = self._repository.mark_gateway_stopped(node_id=node.id)
            finished_at = datetime.now(timezone.utc)
            metadata_path = self._write_run_metadata(
                workspace_root=workspace_root,
                action="gateway_stop",
                started_at=started_at,
                finished_at=finished_at,
                command=stop_command,
                exit_code=0 if status == "stopped" else 11,
                stdout=status,
                stderr="",
                artifact_paths=artifact_paths,
            )
            return {
                "action": "gateway_stop",
                "node": self._serialize_node(updated),
                "gateway": {
                    "status": status,
                    "running": False,
                    "pid": None,
                    "artifact_paths": {**artifact_paths, "run_metadata": str(metadata_path)},
                },
            }

        script = self._build_stop_script(artifact_paths=artifact_paths)
        process = self._run_as_user(username=node.linux_username or "", script=script)
        finished_at = datetime.now(timezone.utc)
        if process.returncode not in {0, 11}:
            self._write_run_metadata(
                workspace_root=workspace_root,
                action="gateway_stop",
                started_at=started_at,
                finished_at=finished_at,
                command=stop_command,
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                artifact_paths=artifact_paths,
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    "Gateway stop failed: "
                    f"exit_code={process.returncode}, stderr={self._trim_output(process.stderr)}"
                ),
            )

        status = "stopped" if process.returncode == 0 else "already_stopped"
        updated = self._repository.mark_gateway_stopped(node_id=node.id)
        metadata_path = self._write_run_metadata(
            workspace_root=workspace_root,
            action="gateway_stop",
            started_at=started_at,
            finished_at=finished_at,
            command=stop_command,
            exit_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
            artifact_paths=artifact_paths,
        )
        return {
            "action": "gateway_stop",
            "node": self._serialize_node(updated),
            "gateway": {
                "status": status,
                "running": False,
                "pid": None,
                "artifact_paths": {**artifact_paths, "run_metadata": str(metadata_path)},
            },
        }

    def _gateway_status(self, *, node: Node, request: RuntimeActionRequest) -> dict[str, object]:
        del request  # currently unused
        workspace_root = self._resolve_workspace_root(node)
        artifact_paths = self._resolve_artifact_paths(workspace_root)
        started_at = datetime.now(timezone.utc)
        status_command = "gateway_status"

        if self._mode == "mock":
            running = bool(node.gateway_running)
            pid = node.gateway_pid if running else None
            finished_at = datetime.now(timezone.utc)
            metadata_path = self._write_run_metadata(
                workspace_root=workspace_root,
                action="gateway_status",
                started_at=started_at,
                finished_at=finished_at,
                command=status_command,
                exit_code=0,
                stdout=f"running:{pid}" if running and pid else "stopped",
                stderr="",
                artifact_paths=artifact_paths,
            )
            return {
                "action": "gateway_status",
                "node": self._serialize_node(node),
                "gateway": {
                    "status": "running" if running else "stopped",
                    "running": running,
                    "pid": pid,
                    "artifact_paths": {**artifact_paths, "run_metadata": str(metadata_path)},
                },
            }

        script = self._build_status_script(artifact_paths=artifact_paths)
        process = self._run_as_user(username=node.linux_username or "", script=script)
        finished_at = datetime.now(timezone.utc)
        if process.returncode != 0:
            self._write_run_metadata(
                workspace_root=workspace_root,
                action="gateway_status",
                started_at=started_at,
                finished_at=finished_at,
                command=status_command,
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                artifact_paths=artifact_paths,
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    "Gateway status failed: "
                    f"exit_code={process.returncode}, stderr={self._trim_output(process.stderr)}"
                ),
            )

        token = self._first_line(process.stdout)
        running = token.startswith("running:")
        pid = self._extract_pid(token) if running else None
        updated = self._repository.reconcile_gateway_state(
            node_id=node.id,
            running=running,
            pid=pid,
        )
        metadata_path = self._write_run_metadata(
            workspace_root=workspace_root,
            action="gateway_status",
            started_at=started_at,
            finished_at=finished_at,
            command=status_command,
            exit_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
            artifact_paths=artifact_paths,
        )
        return {
            "action": "gateway_status",
            "node": self._serialize_node(updated),
            "gateway": {
                "status": "running" if running else "stopped",
                "running": running,
                "pid": pid,
                "artifact_paths": {**artifact_paths, "run_metadata": str(metadata_path)},
            },
        }

    def _resolve_agent_node(self, request: RuntimeActionRequest) -> Node:
        if not request.node_id and not request.node_name:
            raise HTTPException(status_code=422, detail="node_id or node_name is required")
        node = self._repository.get_agent_node(node_id=request.node_id, node_name=request.node_name)
        if node is None:
            raise HTTPException(status_code=404, detail="agent node not found")
        return node

    def _resolve_workspace_root(self, node: Node) -> Path:
        if not node.linux_username:
            raise HTTPException(status_code=409, detail=f"node '{node.name}' has no linux_username")
        if not node.workspace_root:
            raise HTTPException(status_code=409, detail=f"node '{node.name}' has no workspace_root")
        workspace_root = Path(node.workspace_root).expanduser().resolve()
        if not workspace_root.exists():
            raise HTTPException(status_code=409, detail=f"workspace root does not exist: {workspace_root}")
        return workspace_root

    def _resolve_artifact_paths(self, workspace_root: Path) -> dict[str, str]:
        boundary_rel = self._settings.runtime_output_boundary_rel.strip().strip("/")
        if not boundary_rel:
            raise HTTPException(status_code=500, detail="runtime_output_boundary_rel must not be empty")
        artifact_root = (workspace_root / boundary_rel).resolve()
        try:
            artifact_root.relative_to(workspace_root)
        except ValueError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"runtime output boundary escapes workspace: {artifact_root}",
            ) from exc

        return {
            "output_root": str(artifact_root),
            "gateway_pid_file": str(artifact_root / "gateway.pid"),
            "gateway_log_file": str(artifact_root / "gateway.log"),
        }

    def _build_gateway_command_args(self, *, host: str, port: int) -> list[str]:
        template = self._settings.runtime_gateway_command_template
        try:
            rendered = template.format(host=host, port=port)
        except KeyError as exc:
            raise HTTPException(status_code=500, detail=f"Invalid runtime gateway command template: {template}") from exc
        if not rendered.strip():
            raise HTTPException(status_code=500, detail="runtime gateway command resolved to empty string")
        try:
            args = shlex.split(rendered)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail="runtime gateway command template is not parseable") from exc
        if not args:
            raise HTTPException(status_code=500, detail="runtime gateway command resolved to empty argv")
        return args

    def _build_start_script(
        self,
        *,
        workspace_root: Path,
        gateway_command: str,
        artifact_paths: dict[str, str],
    ) -> str:
        workspace_q = shlex.quote(str(workspace_root))
        output_root_q = shlex.quote(artifact_paths["output_root"])
        pid_file_q = shlex.quote(artifact_paths["gateway_pid_file"])
        log_file_q = shlex.quote(artifact_paths["gateway_log_file"])
        return (
            "set -euo pipefail\n"
            f"workspace_root={workspace_q}\n"
            f"output_root={output_root_q}\n"
            f"pid_file={pid_file_q}\n"
            f"log_file={log_file_q}\n"
            "mkdir -p \"$output_root\"\n"
            "if [[ -f \"$pid_file\" ]]; then\n"
            "  pid=\"$(cat \"$pid_file\" || true)\"\n"
            "  if [[ -n \"$pid\" ]] && kill -0 \"$pid\" 2>/dev/null; then\n"
            "    echo \"already_running:$pid\"\n"
            "    exit 10\n"
            "  fi\n"
            "fi\n"
            "cd \"$workspace_root\"\n"
            f"nohup {gateway_command} >>\"$log_file\" 2>&1 &\n"
            "pid=$!\n"
            "echo \"$pid\" > \"$pid_file\"\n"
            "echo \"started:$pid\"\n"
        )

    def _build_stop_script(self, *, artifact_paths: dict[str, str]) -> str:
        output_root_q = shlex.quote(artifact_paths["output_root"])
        pid_file_q = shlex.quote(artifact_paths["gateway_pid_file"])
        return (
            "set -euo pipefail\n"
            f"output_root={output_root_q}\n"
            f"pid_file={pid_file_q}\n"
            "mkdir -p \"$output_root\"\n"
            "if [[ ! -f \"$pid_file\" ]]; then\n"
            "  echo \"already_stopped\"\n"
            "  exit 11\n"
            "fi\n"
            "pid=\"$(cat \"$pid_file\" || true)\"\n"
            "if [[ -z \"$pid\" ]]; then\n"
            "  rm -f \"$pid_file\"\n"
            "  echo \"already_stopped\"\n"
            "  exit 11\n"
            "fi\n"
            "if kill -0 \"$pid\" 2>/dev/null; then\n"
            "  kill \"$pid\" || true\n"
            "  sleep 1\n"
            "  if kill -0 \"$pid\" 2>/dev/null; then\n"
            "    kill -9 \"$pid\" || true\n"
            "  fi\n"
            "fi\n"
            "rm -f \"$pid_file\"\n"
            "echo \"stopped:$pid\"\n"
        )

    def _build_status_script(self, *, artifact_paths: dict[str, str]) -> str:
        output_root_q = shlex.quote(artifact_paths["output_root"])
        pid_file_q = shlex.quote(artifact_paths["gateway_pid_file"])
        return (
            "set -euo pipefail\n"
            f"output_root={output_root_q}\n"
            f"pid_file={pid_file_q}\n"
            "mkdir -p \"$output_root\"\n"
            "if [[ -f \"$pid_file\" ]]; then\n"
            "  pid=\"$(cat \"$pid_file\" || true)\"\n"
            "  if [[ -n \"$pid\" ]] && kill -0 \"$pid\" 2>/dev/null; then\n"
            "    echo \"running:$pid\"\n"
            "    exit 0\n"
            "  fi\n"
            "fi\n"
            "echo \"stopped\"\n"
        )

    def _run_as_user(self, *, username: str, script: str) -> subprocess.CompletedProcess[str]:
        if not username:
            raise HTTPException(status_code=409, detail="linux username is missing")

        if self._settings.runtime_use_sudo:
            command = ["sudo", "-n", "-u", username, "-H", "bash", "-lc", script]
        else:
            current_user = getpass.getuser()
            if current_user != username:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "runtime_use_sudo=false but target user differs from kernel user. "
                        "Set OMNICLAW_RUNTIME_USE_SUDO=true for cross-user runtime control."
                    ),
                )
            command = ["bash", "-lc", script]

        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=self._settings.runtime_command_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=504,
                detail=(
                    f"runtime command timed out after {self._settings.runtime_command_timeout_seconds}s "
                    f"for user '{username}'"
                ),
            ) from exc

    def _write_run_metadata(
        self,
        *,
        workspace_root: Path,
        action: str,
        started_at: datetime,
        finished_at: datetime,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        artifact_paths: dict[str, str],
    ) -> Path:
        output_root = Path(artifact_paths["output_root"]).expanduser().resolve()
        try:
            output_root.relative_to(workspace_root)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail="metadata output root escapes workspace") from exc

        run_id = str(uuid4())
        run_dir = output_root / "runs"
        run_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = run_dir / f"{started_at.strftime('%Y%m%dT%H%M%S')}-{action}-{run_id}.json"
        metadata = {
            "run_id": run_id,
            "action": action,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
            "command": command,
            "exit_code": exit_code,
            "stdout": self._trim_output(stdout),
            "stderr": self._trim_output(stderr),
            "artifact_paths": artifact_paths,
        }
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        return metadata_path

    def _serialize_node(self, node: Node) -> dict[str, object]:
        return {
            "id": node.id,
            "name": node.name,
            "status": node.status.value,
            "linux_username": node.linux_username,
            "workspace_root": node.workspace_root,
            "nullclaw_config_path": node.nullclaw_config_path,
            "primary_model": node.primary_model,
            "deployed": bool(node.linux_username and node.workspace_root and node.nullclaw_config_path),
            "gateway_running": bool(node.gateway_running),
            "gateway_pid": node.gateway_pid,
            "gateway_host": node.gateway_host,
            "gateway_port": node.gateway_port,
            "gateway_started_at": node.gateway_started_at.isoformat() if node.gateway_started_at else None,
            "gateway_stopped_at": node.gateway_stopped_at.isoformat() if node.gateway_stopped_at else None,
        }

    def _first_line(self, value: str) -> str:
        for line in value.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return ""

    def _extract_pid(self, token: str) -> int | None:
        if ":" in token:
            token = token.split(":", 1)[1]
        token = token.strip()
        if token.isdigit():
            return int(token)
        return None

    def _trim_output(self, value: str, *, limit: int = 4000) -> str:
        stripped = value.strip()
        if len(stripped) <= limit:
            return stripped
        return stripped[:limit] + "...<truncated>"
