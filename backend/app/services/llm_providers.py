import logging
from uuid import UUID

from app.repositories.llm_providers import LlmProviderRepository, LlmProviderRow
from app.repositories.organizations import OrganizationRepository
from app.schemas.llm_provider import (
    LlmProviderCreate,
    LlmProviderResponse,
    LlmProviderUpdate,
)
from app.services.provider_resolution import sync_opencode_config_from_db

logger = logging.getLogger(__name__)


def to_llm_provider_response(row: LlmProviderRow) -> LlmProviderResponse:
    return LlmProviderResponse(
        id=row.id,
        name=row.name,
        provider_id=row.provider_id,
        base_url=row.base_url,
        model=row.model,
        opencode_model=row.opencode_model,
        resolved_opencode_model=row.resolved_opencode_model,
        is_default=row.is_default,
        enabled=row.enabled,
        api_token_configured=bool(row.api_token),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_llm_providers(conn) -> list[LlmProviderResponse]:
    org = await OrganizationRepository(conn).get_default()
    org_id = org.id if org else None
    rows = await LlmProviderRepository(conn).list_all(organization_id=org_id)
    return [to_llm_provider_response(row) for row in rows]


async def create_llm_provider(conn, payload: LlmProviderCreate) -> LlmProviderResponse:
    org = await OrganizationRepository(conn).get_default()
    if org is None:
        msg = "organization not configured"
        raise ValueError(msg)
    repo = LlmProviderRepository(conn)
    row = await repo.create(
        organization_id=org.id,
        name=payload.name,
        provider_id=payload.provider_id,
        base_url=payload.base_url,
        api_token=payload.api_token,
        model=payload.model,
        opencode_model=payload.opencode_model,
        is_default=payload.is_default,
        enabled=payload.enabled,
    )
    await sync_opencode_config_from_db(conn)
    logger.info("Created LLM provider %s", row.name)
    return to_llm_provider_response(row)


async def update_llm_provider(
    conn,
    provider_id: UUID,
    payload: LlmProviderUpdate,
) -> LlmProviderResponse:
    repo = LlmProviderRepository(conn)
    data = payload.model_dump(exclude_unset=True)
    clear_api_token = "api_token" in data and data["api_token"] == ""
    row = await repo.update(
        provider_id,
        name=data.get("name"),
        provider_id_key=data.get("provider_id"),
        base_url=data.get("base_url"),
        api_token=data.get("api_token"),
        model=data.get("model"),
        opencode_model=data.get("opencode_model"),
        is_default=data.get("is_default"),
        enabled=data.get("enabled"),
        clear_api_token=clear_api_token,
    )
    await sync_opencode_config_from_db(conn)
    logger.info("Updated LLM provider %s", row.name)
    return to_llm_provider_response(row)


async def delete_llm_provider(conn, provider_id: UUID) -> None:
    await LlmProviderRepository(conn).delete(provider_id)
    await sync_opencode_config_from_db(conn)
    logger.info("Deleted LLM provider %s", provider_id)
