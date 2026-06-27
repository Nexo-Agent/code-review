import logging
from uuid import UUID

from app.repositories.llm_providers import LlmProviderRepository
from app.repositories.projects import ProjectRepository, ProjectRow
from app.repositories.teams import TeamRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.access_control import get_default_organization_id

logger = logging.getLogger(__name__)


async def _llm_provider_name(conn, llm_provider_id: UUID | None) -> str | None:
    if llm_provider_id is None:
        return None
    row = await LlmProviderRepository(conn).get(llm_provider_id)
    return row.name if row else None


async def _validate_llm_provider_for_org(
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


def to_project_response(
    row: ProjectRow,
    llm_provider_name: str | None,
) -> ProjectResponse:
    return ProjectResponse(
        id=row.id,
        team_id=row.team_id,
        name=row.name,
        description=row.description,
        llm_provider_id=row.llm_provider_id,
        llm_provider_name=llm_provider_name,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_projects(conn, team_id: UUID) -> list[ProjectResponse]:
    team = await TeamRepository(conn).get(team_id)
    if team is None:
        msg = "team not found"
        raise ValueError(msg)
    rows = await ProjectRepository(conn).list_for_team(team_id)
    result: list[ProjectResponse] = []
    for row in rows:
        name = await _llm_provider_name(conn, row.llm_provider_id)
        result.append(to_project_response(row, name))
    return result


async def get_project(conn, project_id: UUID) -> ProjectResponse:
    row = await ProjectRepository(conn).get(project_id)
    if row is None:
        msg = "project not found"
        raise ValueError(msg)
    name = await _llm_provider_name(conn, row.llm_provider_id)
    return to_project_response(row, name)


async def create_project(
    conn,
    team_id: UUID,
    payload: ProjectCreate,
) -> ProjectResponse:
    team = await TeamRepository(conn).get(team_id)
    if team is None:
        msg = "team not found"
        raise ValueError(msg)
    await _validate_llm_provider_for_org(conn, payload.llm_provider_id)
    row = await ProjectRepository(conn).create(
        team_id=team_id,
        name=payload.name,
        description=payload.description,
        llm_provider_id=payload.llm_provider_id,
    )
    llm_name = await _llm_provider_name(conn, row.llm_provider_id)
    logger.info("Created project %s in team %s", row.name, team_id)
    return to_project_response(row, llm_name)


async def update_project(
    conn,
    project_id: UUID,
    payload: ProjectUpdate,
) -> ProjectResponse:
    current = await ProjectRepository(conn).get(project_id)
    if current is None:
        msg = "project not found"
        raise ValueError(msg)
    if payload.llm_provider_id is not None:
        await _validate_llm_provider_for_org(conn, payload.llm_provider_id)
    row = await ProjectRepository(conn).update(
        project_id,
        name=payload.name,
        description=payload.description,
        llm_provider_id=payload.llm_provider_id,
        clear_llm_provider_id=payload.clear_llm_provider_id,
    )
    if row is None:
        msg = "project not found"
        raise ValueError(msg)
    llm_name = await _llm_provider_name(conn, row.llm_provider_id)
    return to_project_response(row, llm_name)


async def delete_project(conn, project_id: UUID) -> None:
    await ProjectRepository(conn).delete(project_id)
