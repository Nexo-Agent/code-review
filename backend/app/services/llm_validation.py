from uuid import UUID

from app.repositories.llm_providers import LlmProviderRepository
from app.services.access_control import get_default_organization_id


async def llm_provider_name(conn, llm_provider_id: UUID | None) -> str | None:
    if llm_provider_id is None:
        return None
    row = await LlmProviderRepository(conn).get(llm_provider_id)
    return row.name if row else None


async def validate_llm_provider_for_org(
    conn,
    llm_provider_id: UUID | None,
) -> None:
    if llm_provider_id is None:
        return
    org_id = await get_default_organization_id(conn)
    row = await LlmProviderRepository(conn).get(llm_provider_id)
    if row is None or row.organization_id != org_id:
        msg = "LLM provider not found in organization pool"
        raise ValueError(msg)
