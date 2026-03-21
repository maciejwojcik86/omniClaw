from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import shlex
import subprocess
from uuid import uuid4

from fastapi import HTTPException

from omniclaw.config import Settings
from omniclaw.db.models import AgentTaskRetry, Node
from omniclaw.db.repository import KernelRepository
from omniclaw.runtime.retry_policy import RetryFailureClass, classify_llm_failure, compute_retry_decision
from omniclaw.runtime.schemas import RuntimeActionRequest
from omniclaw.runtime_integration import (
    DEFAULT_RUNTIME_INTEGRATION_FACTORY,
    RUNTIME_CALL_SOURCE_ENV,
    RUNTIME_DATABASE_URL_ENV,
    RUNTIME_INTEGRATION_FACTORY_ENV,
    RUNTIME_NODE_ID_ENV,
    RUNTIME_NODE_NAME_ENV,
    RUNTIME_OUTPUT_ROOT_ENV,
    RUNTIME_PROMPT_LOG_ROOT_ENV,
)


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

        if request.action == "process_due_retries":
            return self._process_due_retries()
        if request.action == "retry_now":
            return self._retry_now(request)
        if request.action == "cancel_retry":
            return self._cancel_retry(request)

        node = self._resolve_agent_node(request)

        if request.action == "gateway_start":
            return self._gateway_start(node=node, request=request)
        if request.action == "gateway_stop":
            return self._gateway_stop(node=node, request=request)
        if request.action == "gateway_status":
            return self._gateway_status(node=node, request=request)
        if request.action == "invoke_prompt":
            return self._invoke_prompt(node=node, request=request)

        raise HTTPException(status_code=400, detail=f"Unsupported runtime action '{request.action}'")

    def _gateway_start(self, *, node: Node, request: RuntimeActionRequest) -> dict[str, object]:
        workspace_root = self._resolve_workspace_root(node)
        config_path = self._resolve_runtime_config_path(node)
        artifact_paths = self._resolve_artifact_paths(workspace_root)
        gateway_command_args = self._build_gateway_command_args(
            host=request.gateway_host,
            port=request.gateway_port,
            workspace_root=workspace_root,
            config_path=config_path,
        )
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
        process = self._run_runtime_script(
            script=script,
            env_overrides=self._build_runtime_integration_env(node=node, artifact_paths=artifact_paths),
        )
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
        process = self._run_runtime_script(script=script)
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
        process = self._run_runtime_script(script=script)
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

    def _invoke_prompt(self, *, node: Node, request: RuntimeActionRequest) -> dict[str, object]:
        if not request.prompt:
            raise HTTPException(status_code=422, detail="prompt is required for invoke_prompt")
        workspace_root = self._resolve_workspace_root(node)
        config_path = self._resolve_runtime_config_path(node)
        artifact_paths = self._resolve_artifact_paths(workspace_root)
        command_args = self._build_agent_command_args(
            prompt=request.prompt,
            session_key=request.session_key,
            workspace_root=workspace_root,
            config_path=config_path,
            markdown=request.markdown,
            include_logs=request.include_logs,
        )
        command = shlex.join(command_args)
        started_at = datetime.now(timezone.utc)

        if self._mode == "mock":
            stdout = f"mock reply from {node.name}: {request.prompt[:160]}"
            finished_at = datetime.now(timezone.utc)
            usage_record = self._record_mock_usage(node=node, request=request, started_at=started_at, finished_at=finished_at)
            metadata_path = self._write_run_metadata(
                workspace_root=workspace_root,
                action="invoke_prompt",
                started_at=started_at,
                finished_at=finished_at,
                command=command,
                exit_code=0,
                stdout=stdout,
                stderr="",
                artifact_paths=artifact_paths,
                invocation_metadata={
                    "status": "completed",
                    "session_key": request.session_key,
                    "retry": None,
                },
            )
            refreshed_node = self._repository.get_agent_node(node_id=node.id)
            return {
                "action": "invoke_prompt",
                "node": self._serialize_node(refreshed_node or node),
                "invocation": {
                    "status": "completed",
                    "session_key": request.session_key,
                    "prompt": request.prompt,
                    "reply": stdout,
                    "exit_code": 0,
                    "command": command,
                    "artifact_paths": {**artifact_paths, "run_metadata": str(metadata_path)},
                    "mock_usage": usage_record,
                },
            }

        script = self._build_agent_invoke_script(command=command, artifact_paths=artifact_paths)
        process = self._run_runtime_script(
            script=script,
            env_overrides=self._build_runtime_integration_env(node=node, artifact_paths=artifact_paths),
        )
        finished_at = datetime.now(timezone.utc)
        metadata_path = self._write_run_metadata(
            workspace_root=workspace_root,
            action="invoke_prompt",
            started_at=started_at,
            finished_at=finished_at,
            command=command,
            exit_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
            artifact_paths=artifact_paths,
            invocation_metadata={
                "status": "completed" if process.returncode == 0 else "failed",
                "session_key": request.session_key,
                "retry": None,
            },
        )
        if process.returncode != 0:
            return self._handle_failed_prompt_invocation(
                node=node,
                request=request,
                command=command,
                process=process,
                started_at=started_at,
                finished_at=finished_at,
                artifact_paths=artifact_paths,
                metadata_path=metadata_path,
            )
        return {
            "action": "invoke_prompt",
            "node": self._serialize_node(node),
            "invocation": {
                "status": "completed",
                "session_key": request.session_key,
                "prompt": request.prompt,
                "reply": self._trim_output(process.stdout),
                "exit_code": process.returncode,
                "command": command,
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
        if not node.workspace_root:
            raise HTTPException(status_code=409, detail=f"node '{node.name}' has no workspace_root")
        workspace_root = Path(node.workspace_root).expanduser().resolve()
        if not workspace_root.exists():
            raise HTTPException(status_code=409, detail=f"workspace root does not exist: {workspace_root}")
        return workspace_root

    def _resolve_runtime_config_path(self, node: Node) -> Path:
        if not node.runtime_config_path:
            raise HTTPException(status_code=409, detail=f"node '{node.name}' has no runtime_config_path")
        config_path = Path(node.runtime_config_path).expanduser().resolve()
        if self._mode != "mock" and not config_path.exists():
            raise HTTPException(status_code=409, detail=f"runtime config does not exist: {config_path}")
        return config_path

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
            "prompt_logs_root": str((artifact_root / "prompt_logs").resolve()),
        }

    def _build_gateway_command_args(
        self,
        *,
        host: str,
        port: int,
        workspace_root: Path,
        config_path: Path,
    ) -> list[str]:
        template = self._settings.runtime_gateway_command_template
        try:
            rendered = template.format(
                runtime_bin=self._settings.runtime_command_bin,
                host=host,
                port=port,
                workspace_root=str(workspace_root),
                config_path=str(config_path),
            )
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

    def _build_agent_command_args(
        self,
        *,
        prompt: str,
        session_key: str,
        workspace_root: Path,
        config_path: Path,
        markdown: bool,
        include_logs: bool,
    ) -> list[str]:
        return [
            self._settings.runtime_command_bin,
            "agent",
            "--message",
            prompt,
            "--session",
            session_key,
            "--workspace",
            str(workspace_root),
            "--config",
            str(config_path),
            "--markdown" if markdown else "--no-markdown",
            "--logs" if include_logs else "--no-logs",
        ]

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

    def _build_agent_invoke_script(self, *, command: str, artifact_paths: dict[str, str]) -> str:
        output_root_q = shlex.quote(artifact_paths["output_root"])
        return (
            "set -euo pipefail\n"
            f"output_root={output_root_q}\n"
            "mkdir -p \"$output_root\"\n"
            f"{command}\n"
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

    def _run_runtime_script(
        self,
        *,
        script: str,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["bash", "-lc", script],
                capture_output=True,
                text=True,
                check=False,
                timeout=self._settings.runtime_command_timeout_seconds,
                env=self._build_runtime_env(env_overrides=env_overrides),
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=504,
                detail=f"runtime command timed out after {self._settings.runtime_command_timeout_seconds}s",
            ) from exc

    def _build_runtime_env(self, *, env_overrides: dict[str, str] | None = None) -> dict[str, str]:
        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)
        return env

    def _build_runtime_integration_env(
        self,
        *,
        node: Node,
        artifact_paths: dict[str, str],
    ) -> dict[str, str]:
        return {
            RUNTIME_INTEGRATION_FACTORY_ENV: DEFAULT_RUNTIME_INTEGRATION_FACTORY,
            RUNTIME_DATABASE_URL_ENV: self._settings.database_url,
            RUNTIME_NODE_ID_ENV: node.id,
            RUNTIME_NODE_NAME_ENV: node.name,
            RUNTIME_OUTPUT_ROOT_ENV: artifact_paths["output_root"],
            RUNTIME_PROMPT_LOG_ROOT_ENV: artifact_paths["prompt_logs_root"],
            RUNTIME_CALL_SOURCE_ENV: "omniclaw.runtime.service",
        }

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
        invocation_metadata: dict[str, object] | None = None,
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
        if invocation_metadata:
            metadata["invocation"] = invocation_metadata
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        return metadata_path

    def _retry_now(self, request: RuntimeActionRequest) -> dict[str, object]:
        task_key = (request.task_key or "").strip()
        if not task_key:
            raise HTTPException(status_code=422, detail="task_key is required for retry_now")
        record = self._repository.get_agent_task_retry(task_key=task_key)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Retry task '{task_key}' not found")
        updated = self._repository.update_agent_task_retry_status(
            task_key=task_key,
            status="pending",
            next_attempt_at=datetime.now(timezone.utc),
            claimed_at=None,
            completed_at=None,
        )
        assert updated is not None
        return {
            "action": "retry_now",
            "retry": {
                "task_key": updated.task_key,
                "status": updated.status,
                "next_attempt_at": updated.next_attempt_at.isoformat() if updated.next_attempt_at else None,
            },
        }

    def _cancel_retry(self, request: RuntimeActionRequest) -> dict[str, object]:
        task_key = (request.task_key or "").strip()
        if not task_key:
            raise HTTPException(status_code=422, detail="task_key is required for cancel_retry")
        record = self._repository.get_agent_task_retry(task_key=task_key)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Retry task '{task_key}' not found")
        updated = self._repository.update_agent_task_retry_status(
            task_key=task_key,
            status="cancelled",
            next_attempt_at=None,
            claimed_at=None,
            completed_at=datetime.now(timezone.utc),
        )
        assert updated is not None
        return {
            "action": "cancel_retry",
            "retry": {
                "task_key": updated.task_key,
                "status": updated.status,
                "completed_at": updated.completed_at.isoformat() if updated.completed_at else None,
            },
        }

    def _process_due_retries(self) -> dict[str, object]:
        due_before = datetime.now(timezone.utc)
        due_records = self._repository.list_due_agent_task_retries(due_before=due_before)
        processed: list[dict[str, object]] = []

        for record in due_records:
            claimed = self._repository.claim_agent_task_retry(task_key=record.task_key, claimed_at=due_before)
            if claimed is None:
                continue

            node = self._repository.get_agent_node(node_id=claimed.node_id)
            if node is None:
                self._repository.update_agent_task_retry_status(
                    task_key=claimed.task_key,
                    status="terminal",
                    claimed_at=due_before,
                    completed_at=due_before,
                    last_error_message="agent node not found for retry",
                )
                processed.append({
                    "task_key": claimed.task_key,
                    "status": "terminal",
                    "reason": "node_not_found",
                })
                continue

            if not claimed.last_error_message and not claimed.request_payload_json:
                self._repository.update_agent_task_retry_status(
                    task_key=claimed.task_key,
                    status="terminal",
                    claimed_at=due_before,
                    completed_at=due_before,
                    last_error_message="cannot resume retry without original request payload or error context",
                )
                processed.append({
                    "task_key": claimed.task_key,
                    "status": "terminal",
                    "reason": "missing_resume_payload",
                })
                continue

            retry_request = self._build_retry_request(node=node, record=claimed)
            result = self._invoke_prompt(node=node, request=retry_request)
            invocation = result.get("invocation", {}) if isinstance(result, dict) else {}
            status = invocation.get("status")
            if status == "completed":
                self._repository.update_agent_task_retry_status(
                    task_key=claimed.task_key,
                    status="completed",
                    claimed_at=claimed.claimed_at,
                    completed_at=datetime.now(timezone.utc),
                    next_attempt_at=None,
                )
            elif status == "deferred_retry":
                self._repository.update_agent_task_retry_status(
                    task_key=claimed.task_key,
                    status="pending",
                    claimed_at=None,
                )
            processed.append(
                {
                    "task_key": claimed.task_key,
                    "status": status,
                    "node_id": claimed.node_id,
                    "session_key": claimed.session_key,
                }
            )

        return {
            "action": "process_due_retries",
            "processed_count": len(processed),
            "processed": processed,
            "due_before": due_before.isoformat(),
        }

    def _handle_failed_prompt_invocation(
        self,
        *,
        node: Node,
        request: RuntimeActionRequest,
        command: str,
        process: subprocess.CompletedProcess[str],
        started_at: datetime,
        finished_at: datetime,
        artifact_paths: dict[str, str],
        metadata_path: Path,
    ) -> dict[str, object]:
        error_message = self._build_failure_message(process=process)
        failure_class = classify_llm_failure(error_message)
        task_key = self._build_task_key(node=node, request=request)
        retry_record = None
        retry_payload = None
        failure_event_written = False

        if failure_class != RetryFailureClass.TERMINAL:
            existing = self._repository.get_agent_task_retry(task_key=task_key)
            prior_attempts = existing.attempt_count if existing is not None else 0
            decision = compute_retry_decision(
                attempt_count=prior_attempts,
                failure_class=failure_class,
                reset_time_utc=self._company_reset_time_utc(),
                now=finished_at,
            )
            retry_record = self._repository.upsert_agent_task_retry(
                node_id=node.id,
                task_key=task_key,
                session_key=request.session_key,
                provider=self._provider_for_node(node),
                model=node.primary_model,
                failure_class=failure_class,
                status="pending" if decision.retryable else "exhausted",
                attempt_count=prior_attempts + 1,
                max_attempts=decision.max_attempts,
                next_attempt_at=decision.next_attempt_at,
                request_payload_json=self._serialize_retry_request_payload(request=request),
                last_error_message=error_message,
                last_run_id=metadata_path.stem,
                completed_at=None if decision.retryable else finished_at,
            )
            self._repository.insert_llm_failure_event(
                node_id=node.id,
                task_retry_id=retry_record.id,
                session_key=request.session_key,
                task_key=task_key,
                provider=self._provider_for_node(node),
                model=node.primary_model,
                failure_class=failure_class,
                error_message=error_message,
                occurred_at=finished_at,
            )
            failure_event_written = True
            retry_payload = {
                "retry_record_id": retry_record.id,
                "task_key": retry_record.task_key,
                "failure_class": failure_class.value,
                "attempt_count": retry_record.attempt_count,
                "max_attempts": retry_record.max_attempts,
                "next_attempt_at": retry_record.next_attempt_at.isoformat() if retry_record.next_attempt_at else None,
            }
            if decision.retryable:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata["invocation"] = {
                    "status": "deferred_retry",
                    "session_key": request.session_key,
                    "retry": retry_payload,
                    "failure_class": failure_class.value,
                    "error": error_message,
                }
                metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
                return {
                    "action": "invoke_prompt",
                    "node": self._serialize_node(node),
                    "invocation": {
                        "status": "deferred_retry",
                        "session_key": request.session_key,
                        "prompt": request.prompt,
                        "reply": None,
                        "exit_code": process.returncode,
                        "command": command,
                        "error": error_message,
                        "artifact_paths": {**artifact_paths, "run_metadata": str(metadata_path)},
                        "retry": retry_payload,
                    },
                }

        if not failure_event_written:
            self._repository.insert_llm_failure_event(
                node_id=node.id,
                task_retry_id=retry_record.id if retry_record is not None else None,
                session_key=request.session_key,
                task_key=task_key,
                provider=self._provider_for_node(node),
                model=node.primary_model,
                failure_class=failure_class,
                error_message=error_message,
                occurred_at=finished_at,
            )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["invocation"] = {
            "status": "terminal_failure",
            "session_key": request.session_key,
            "retry": retry_payload,
            "failure_class": failure_class.value,
            "error": error_message,
        }
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        raise HTTPException(
            status_code=500,
            detail=(
                "Prompt invocation failed: "
                f"exit_code={process.returncode}, classification={failure_class.value}, stderr={self._trim_output(process.stderr)}"
            ),
        )

    def _record_mock_usage(
        self,
        *,
        node: Node,
        request: RuntimeActionRequest,
        started_at: datetime,
        finished_at: datetime,
    ) -> dict[str, object]:
        prompt_tokens = max(1, len(request.prompt.split()))
        completion_tokens = max(1, len((request.prompt[:160] or "ok").split()))
        reasoning_tokens = 0
        total_tokens = prompt_tokens + completion_tokens + reasoning_tokens
        duration_ms = max(1, int((finished_at - started_at).total_seconds() * 1000))
        estimated_cost_usd = (Decimal(total_tokens) * Decimal("0.01")).quantize(Decimal("0.000001"))
        call = self._repository.insert_agent_llm_call(
            node_id=node.id,
            session_key=request.session_key,
            model=node.primary_model or "mock-model",
            provider="mock-runtime",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            start_time=started_at,
            end_time=max(finished_at, started_at + timedelta(milliseconds=1)),
            duration_ms=duration_ms,
        )
        budget = self._repository.get_budget(node_id=node.id)
        if budget is not None:
            updated_spend = Decimal(budget.current_spend) + estimated_cost_usd
            self._repository.upsert_budget(node_id=node.id, current_spend=updated_spend)
        return {
            "call_id": call.id,
            "provider": "mock-runtime",
            "model": node.primary_model or "mock-model",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "reasoning_tokens": reasoning_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": float(estimated_cost_usd),
            "duration_ms": duration_ms,
        }

    def _serialize_node(self, node: Node) -> dict[str, object]:
        manager = self._repository.get_manager_node(child_node_id=node.id)
        budget = self._repository.get_budget(node_id=node.id)
        return {
            "id": node.id,
            "name": node.name,
            "type": str(node.type.value).lower(),
            "status": node.status.value,
            "role_name": node.role_name,
            "linux_username": node.linux_username,
            "workspace_root": node.workspace_root,
            "runtime_config_path": node.runtime_config_path,
            "primary_model": node.primary_model,
            "deployed": bool(node.workspace_root and node.runtime_config_path),
            "gateway_running": bool(node.gateway_running),
            "gateway_pid": node.gateway_pid,
            "gateway_host": node.gateway_host,
            "gateway_port": node.gateway_port,
            "gateway_started_at": node.gateway_started_at.isoformat() if node.gateway_started_at else None,
            "gateway_stopped_at": node.gateway_stopped_at.isoformat() if node.gateway_stopped_at else None,
            "manager_node_id": manager.id if manager else None,
            "manager_name": manager.name if manager else None,
            "budget_mode": budget.budget_mode.value if budget else None,
            "current_spend_usd": float(budget.current_spend) if budget else None,
            "effective_daily_limit_usd": float(budget.daily_limit_usd) if budget else None,
            "remaining_budget_usd": float(max(budget.daily_limit_usd - budget.current_spend, 0)) if budget and budget.budget_mode.value == "metered" else None,
            "has_virtual_api_key": bool(budget and budget.virtual_api_key),
        }

    def _build_failure_message(self, *, process: subprocess.CompletedProcess[str]) -> str:
        stderr = self._trim_output(process.stderr)
        stdout = self._trim_output(process.stdout)
        if stderr and stdout:
            return f"{stderr} | stdout={stdout}"
        if stderr:
            return stderr
        if stdout:
            return stdout
        return f"runtime exited with code {process.returncode}"

    def _build_task_key(self, *, node: Node, request: RuntimeActionRequest) -> str:
        return f"invoke_prompt:{node.id}:{request.session_key}"

    def _build_retry_request(self, *, node: Node, record: AgentTaskRetry) -> RuntimeActionRequest:
        payload = self._deserialize_retry_request_payload(record.request_payload_json)
        if payload is not None:
            return RuntimeActionRequest(
                action="invoke_prompt",
                node_id=node.id,
                session_key=str(payload.get("session_key") or record.session_key or "cli:retry"),
                prompt=str(payload["prompt"]),
                markdown=bool(payload.get("markdown", False)),
                include_logs=bool(payload.get("include_logs", False)),
            )
        return RuntimeActionRequest(
            action="invoke_prompt",
            node_id=node.id,
            session_key=record.session_key or "cli:retry",
            prompt=(
                f"Retry previously failed task '{record.task_key}'. "
                f"Original failure: {record.last_error_message}"
            ),
        )

    def _serialize_retry_request_payload(self, *, request: RuntimeActionRequest) -> str:
        return json.dumps(
            {
                "prompt": request.prompt,
                "session_key": request.session_key,
                "markdown": request.markdown,
                "include_logs": request.include_logs,
            },
            sort_keys=True,
        )

    def _deserialize_retry_request_payload(self, raw_payload: str | None) -> dict[str, object] | None:
        if not raw_payload:
            return None
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            return None
        return payload

    def _provider_for_node(self, node: Node) -> str | None:
        primary_model = (node.primary_model or "").strip()
        if not primary_model:
            return None
        if "/" in primary_model:
            return primary_model.split("/", 1)[0]
        return primary_model

    def _company_reset_time_utc(self) -> str | None:
        budgeting = self._settings.company_section("budgeting")
        raw = budgeting.get("reset_time_utc") if isinstance(budgeting, dict) else None
        text = str(raw).strip() if raw is not None else ""
        return text or None

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
