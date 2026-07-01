import asyncio
import json
import logging
import os
import re
from collections.abc import Callable
from typing import Any

from coreview_shared.agent.models import (
    AgentSetupArtifacts,
    LlmCallUsage,
    OpenCodeRunConfig,
    ReviewRunResult,
)
from coreview_shared.agent.opencode_config import materialize_opencode_config
from coreview_shared.review import PRContext, ReviewFinding
from coreview_shared.workspace.models import Workspace

logger = logging.getLogger(__name__)
STREAM_READ_SIZE = 64 * 1024

FINDINGS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "warning", "info", "suggestion"],
                    },
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "file_path": {"type": "string"},
                    "line_start": {"type": "integer"},
                    "line_end": {"type": "integer"},
                },
                "required": ["severity", "title", "body"],
            },
        }
    },
    "required": ["findings"],
}


class OpenCodeAgent:
    def __init__(
        self,
        *,
        config: OpenCodeRunConfig,
    ) -> None:
        self._config = config
        self._timeout = float(config.timeout_seconds)
        self._log_level = config.log_level.upper()
        self._setup_artifacts = AgentSetupArtifacts()
        self._llm_calls: list[LlmCallUsage] = []

    async def setup(self) -> None:
        config_path = materialize_opencode_config(self._config)
        self._setup_artifacts = AgentSetupArtifacts(config_path=config_path)

    async def teardown(self) -> None:
        config_path = self._setup_artifacts.config_path
        if config_path is not None:
            config_path.unlink(missing_ok=True)
        self._setup_artifacts = AgentSetupArtifacts()

    async def run_review(
        self,
        workspace: Workspace,
        context: PRContext,
    ) -> ReviewRunResult:
        if self._setup_artifacts.config_path is None:
            msg = "OpenCodeAgent.setup() must be called before run_review()"
            raise RuntimeError(msg)
        self._llm_calls = []
        prompt = self._build_prompt(context)
        stdout, stderr = await self._run_opencode_cli(workspace, prompt)
        if stderr.strip():
            logger.debug("opencode stderr tail:\n%s", stderr.strip())
        findings = self._parse_cli_output(stdout)
        return ReviewRunResult.from_findings(findings, self._llm_calls)

    def _build_command(self, workspace_path: str) -> list[str]:
        # Global flags (--print-logs, --log-level) must precede the subcommand.
        # --print-logs writes internal logs to stderr; --format json streams
        # NDJSON events to stdout (see opencode CLI docs).
        return [
            "opencode",
            "--log-level",
            self._log_level,
            "--print-logs",
            "run",
            "--agent",
            self._config.agent,
            "-m",
            self._config.model,
            "--dir",
            workspace_path,
            "--format",
            "json",
            "--dangerously-skip-permissions",
        ]

    async def _run_opencode_cli(
        self,
        workspace: Workspace,
        prompt: str,
    ) -> tuple[str, str]:
        env = os.environ.copy()
        env["OPENCODE_CONFIG"] = str(self._setup_artifacts.config_path)
        cmd = self._build_command(str(workspace.path))
        logger.info(
            "Running opencode CLI in %s (agent=%s model=%s log_level=%s)",
            workspace.path,
            self._config.agent,
            self._config.model,
            self._log_level,
        )
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace.path),
            env=env,
        )
        return await self._stream_subprocess_output(proc, prompt)

    async def _stream_subprocess_output(
        self,
        proc: asyncio.subprocess.Process,
        prompt: str,
    ) -> tuple[str, str]:
        if proc.stdin is None or proc.stdout is None or proc.stderr is None:
            msg = "opencode subprocess missing stdio pipes"
            raise RuntimeError(msg)

        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []

        async def pump_stderr() -> None:
            await self._pump_stream(
                proc.stderr,
                stderr_chunks,
                lambda text: logger.info("[opencode] %s", text),
            )

        async def pump_stdout() -> None:
            await self._pump_stream(
                proc.stdout,
                stdout_chunks,
                self._log_stdout_event,
            )

        proc.stdin.write(prompt.encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()

        try:
            await asyncio.wait_for(
                asyncio.gather(
                    pump_stdout(),
                    pump_stderr(),
                    proc.wait(),
                ),
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            msg = f"opencode run timed out after {self._timeout:.0f}s"
            raise RuntimeError(msg) from exc

        stdout = b"".join(stdout_chunks).decode("utf-8", errors="replace")
        stderr = b"".join(stderr_chunks).decode("utf-8", errors="replace")
        if proc.returncode != 0:
            msg = f"opencode run failed (exit {proc.returncode}): {stderr or stdout}"
            raise RuntimeError(msg)
        return stdout, stderr

    async def _pump_stream(
        self,
        reader: asyncio.StreamReader,
        chunks: list[bytes],
        handle_line: Callable[[str], None],
    ) -> None:
        buffer = bytearray()
        while True:
            chunk = await reader.read(STREAM_READ_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
            buffer.extend(chunk)
            while True:
                newline_index = buffer.find(b"\n")
                if newline_index < 0:
                    break
                line = bytes(buffer[: newline_index + 1])
                del buffer[: newline_index + 1]
                self._handle_stream_line(line, handle_line)

        if buffer:
            self._handle_stream_line(bytes(buffer), handle_line)

    def _handle_stream_line(
        self, line: bytes, handle_line: Callable[[str], None]
    ) -> None:
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            handle_line(text)

    def _log_stdout_event(self, text: str) -> None:
        try:
            event = json.loads(text)
        except json.JSONDecodeError:
            logger.info("[opencode:stdout] %s", text)
            return
        if isinstance(event, dict):
            usage = self._parse_step_finish_usage(event, len(self._llm_calls))
            if usage is not None:
                self._llm_calls.append(usage)
        event_type = str(event.get("type", "event"))
        summary = self._summarize_json_event(event)
        logger.info("[opencode:%s] %s", event_type, summary)

    @staticmethod
    def _parse_step_finish_usage(
        event: dict[str, Any],
        call_index: int,
    ) -> LlmCallUsage | None:
        if event.get("type") != "step_finish":
            return None
        part = event.get("part")
        if not isinstance(part, dict):
            return None
        tokens = part.get("tokens")
        if not isinstance(tokens, dict):
            logger.warning(
                "OpenCode step_finish missing tokens; recording zero usage "
                "(call_index=%d)",
                call_index,
            )
            return LlmCallUsage(
                call_index=call_index,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                reason=str(part.get("reason", "")),
            )
        input_tokens = _coerce_token_count(
            tokens.get("input"),
            tokens.get("input_tokens"),
            tokens.get("prompt"),
            tokens.get("prompt_tokens"),
        )
        output_tokens = _coerce_token_count(
            tokens.get("output"),
            tokens.get("output_tokens"),
            tokens.get("completion"),
            tokens.get("completion_tokens"),
        )
        total_tokens = _coerce_optional_token_count(
            tokens.get("total"),
            tokens.get("total_tokens"),
        )
        if total_tokens is None:
            total_tokens = input_tokens + output_tokens
        return LlmCallUsage(
            call_index=call_index,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            reason=str(part.get("reason", "")),
        )

    def _summarize_json_event(self, event: dict[str, Any]) -> str:
        for key in ("message", "text", "content", "output"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                snippet = value.strip().replace("\n", " ")
                return snippet[:200]
        part = event.get("part")
        if isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip().replace("\n", " ")[:200]
        return json.dumps(event, ensure_ascii=True)[:200]

    def _parse_cli_output(self, stdout: str) -> list[ReviewFinding]:
        text_parts: list[str] = []

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue

            findings = self._parse_findings(event)
            if findings:
                return findings

            if event.get("type") == "text":
                text = self._extract_text_from_event(event)
                if text.strip():
                    text_parts.append(text.strip())

        for text in reversed(text_parts):
            findings = self._parse_findings_from_text(text)
            if findings:
                return findings

        return []

    def _build_prompt(self, context: PRContext) -> str:
        """User message for this review run (PR context + output schema only).

        Behavioral instructions live in the agent system prompt (opencode.json).
        """
        meta = context.metadata
        return (
            f"Review pull request #{meta.pr_number}: {meta.title}\n"
            f"Repository: {meta.repo_full_name}\n"
            f"Author: {meta.author}\n"
            f"Base: {meta.base_ref} ({meta.base_sha[:7]})\n"
            f"Head: {meta.head_ref} ({meta.head_sha[:7]})\n\n"
            "The cloned repository is available in the session workspace directory.\n"
            f"Return JSON with this schema: {json.dumps(FINDINGS_JSON_SCHEMA)}"
        )

    def _parse_findings(self, data: dict[str, Any]) -> list[ReviewFinding]:
        raw_findings = self._extract_findings_list(data)
        if raw_findings is not None:
            return [self._to_finding(item) for item in raw_findings if item]

        text = self._extract_text_from_event(data)
        if text:
            return self._parse_findings_from_text(text)
        return []

    def _extract_text_from_event(self, event: dict[str, Any]) -> str:
        part = event.get("part")
        if isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str):
                return text
        return self._extract_text(event)

    def _extract_findings_list(self, data: Any) -> list[dict[str, Any]] | None:
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return None
        for key in ("findings", "items", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        for key in ("content", "text", "message", "output"):
            nested = data.get(key)
            if isinstance(nested, dict):
                found = self._extract_findings_list(nested)
                if found is not None:
                    return found
            if isinstance(nested, str):
                parsed = self._try_parse_json(nested)
                if parsed is not None:
                    return self._extract_findings_list(parsed)
        parts = data.get("parts")
        if isinstance(parts, list):
            for part in parts:
                if isinstance(part, dict) and part.get("type") == "text":
                    parsed = self._try_parse_json(str(part.get("text", "")))
                    if parsed is not None:
                        return self._extract_findings_list(parsed)
        return None

    def _extract_text(self, data: Any) -> str:
        if isinstance(data, str):
            return data
        if not isinstance(data, dict):
            return ""
        for key in ("text", "content", "message", "output"):
            value = data.get(key)
            if isinstance(value, str):
                return value
        parts = data.get("parts")
        if isinstance(parts, list):
            texts = [
                str(part.get("text", ""))
                for part in parts
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            return "\n".join(texts)
        return ""

    def _parse_findings_from_text(self, text: str) -> list[ReviewFinding]:
        parsed = self._try_parse_json(text)
        if parsed is not None:
            raw = self._extract_findings_list(parsed)
            if raw is not None:
                return [self._to_finding(item) for item in raw if item]
        return []

    def _try_parse_json(self, text: str) -> Any | None:
        text = text.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None

    def _to_finding(self, item: dict[str, Any]) -> ReviewFinding:
        return ReviewFinding(
            severity=str(item.get("severity", "info")),
            title=str(item.get("title", "Finding")),
            body=str(item.get("body", "")),
            file_path=item.get("file_path") or item.get("file"),
            line_start=item.get("line_start") or item.get("line"),
            line_end=item.get("line_end"),
        )


def _coerce_token_count(*values: object) -> int:
    parsed = _coerce_optional_token_count(*values)
    return 0 if parsed is None else parsed


def _coerce_optional_token_count(*values: object) -> int | None:
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, float):
            return max(int(value), 0)
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    return None
