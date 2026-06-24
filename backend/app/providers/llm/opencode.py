import json
import logging
import re
from typing import Any

import httpx

from app.providers.protocols import PRContext, ReviewFinding, Workspace

logger = logging.getLogger(__name__)

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


class OpenCodeLLMProvider:
    def __init__(
        self,
        server_url: str,
        username: str,
        password: str,
        agent: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self._server_url = server_url.rstrip("/")
        self._auth = (username, password) if password else None
        self._agent = agent
        self._model = model
        self._timeout = float(timeout_seconds)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._server_url,
            auth=self._auth,
            timeout=self._timeout,
        )

    async def run_review(
        self,
        workspace: Workspace,
        context: PRContext,
    ) -> list[ReviewFinding]:
        prompt = self._build_prompt(context)
        async with self._client() as client:
            session_id = await self._create_session(client, workspace)
            try:
                response_data = await self._send_prompt(client, session_id, prompt)
            finally:
                await self._delete_session(client, session_id)
        return self._parse_findings(response_data)

    async def _create_session(
        self, client: httpx.AsyncClient, workspace: Workspace
    ) -> str:
        payloads = [
            {"directory": str(workspace.path)},
            {"path": str(workspace.path)},
            {"cwd": str(workspace.path)},
        ]
        last_error: Exception | None = None
        for body in payloads:
            try:
                response = await client.post("/session", json=body)
                if response.status_code == 404:
                    response = await client.post("/api/session", json=body)
                response.raise_for_status()
                data = response.json()
                session_id = (
                    data.get("id")
                    or data.get("sessionID")
                    or data.get("data", {}).get("id")
                )
                if session_id:
                    return str(session_id)
            except Exception as exc:
                last_error = exc
                continue
        msg = f"Failed to create OpenCode session: {last_error}"
        raise RuntimeError(msg)

    async def _send_prompt(
        self,
        client: httpx.AsyncClient,
        session_id: str,
        prompt: str,
    ) -> dict[str, Any]:
        model_value: str | dict[str, str]
        if "/" in self._model:
            provider_id, model_id = self._model.split("/", 1)
            model_value = {"providerID": provider_id, "modelID": model_id}
        else:
            model_value = self._model
        body: dict[str, Any] = {
            "parts": [{"type": "text", "text": prompt}],
            "agent": self._agent,
            "model": model_value,
            "outputFormat": FINDINGS_JSON_SCHEMA,
        }
        paths = [
            f"/session/{session_id}/prompt",
            f"/api/session/{session_id}/prompt",
            f"/session/{session_id}/message",
            f"/api/session/{session_id}/message",
        ]
        last_error: Exception | None = None
        for path in paths:
            try:
                response = await client.post(path, json=body)
                if response.status_code >= 400:
                    alt_body = {
                        "prompt": prompt,
                        "agent": self._agent,
                        "outputFormat": FINDINGS_JSON_SCHEMA,
                    }
                    response = await client.post(path, json=alt_body)
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
                continue
        msg = f"Failed to send OpenCode prompt: {last_error}"
        raise RuntimeError(msg)

    async def _delete_session(
        self, client: httpx.AsyncClient, session_id: str
    ) -> None:
        for path in (f"/session/{session_id}", f"/api/session/{session_id}"):
            try:
                await client.delete(path)
                return
            except httpx.HTTPError:
                continue

    def _build_prompt(self, context: PRContext) -> str:
        meta = context.metadata
        ci_block = (
            f"\n\n## CI status\n{context.ci_summary}"
            if context.ci_summary
            else ""
        )
        return (
            f"Review pull request #{meta.pr_number}: {meta.title}\n"
            f"Author: {meta.author}\n"
            f"Base: {meta.base_ref} ({meta.base_sha[:7]})\n"
            f"Head: {meta.head_ref} ({meta.head_sha[:7]})\n"
            f"{ci_block}\n\n"
            "## Diff\n"
            f"{context.diff[:50000]}\n\n"
            "Return findings as JSON matching the outputFormat schema. "
            "Focus on bugs, security, performance, and missing tests."
        )

    def _parse_findings(self, data: dict[str, Any]) -> list[ReviewFinding]:
        raw_findings = self._extract_findings_list(data)
        if raw_findings is not None:
            return [self._to_finding(item) for item in raw_findings if item]

        text = self._extract_text(data)
        if text:
            return self._parse_findings_from_text(text)
        return []

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
        return [
            ReviewFinding(
                severity="info",
                title="Review summary",
                body=text[:4000],
            )
        ]

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
