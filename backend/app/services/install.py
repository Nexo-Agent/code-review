import logging

from app.repositories.system_install import SystemInstallRepository
from app.repositories.users import UserRepository
from app.schemas.install import InstallBootstrapRequest, InstallStatusResponse
from app.services.passwords import hash_password, verify_password

logger = logging.getLogger(__name__)


class SetupAlreadyCompletedError(Exception):
    pass


class SetupRequiredError(Exception):
    pass


async def get_install_status(conn) -> InstallStatusResponse:
    required = await SystemInstallRepository(conn).is_setup_required()
    return InstallStatusResponse(setup_required=required)


async def assert_setup_allowed(conn) -> None:
    if not await SystemInstallRepository(conn).is_setup_required():
        raise SetupAlreadyCompletedError


async def assert_setup_completed(conn) -> None:
    if await SystemInstallRepository(conn).is_setup_required():
        raise SetupRequiredError


async def bootstrap_install(conn, payload: InstallBootstrapRequest):
    install_repo = SystemInstallRepository(conn)
    if not await install_repo.is_setup_required():
        raise SetupAlreadyCompletedError

    user_repo = UserRepository(conn)
    if await user_repo.has_local_superuser():
        await install_repo.mark_completed()
        raise SetupAlreadyCompletedError

    email = (payload.email or f"{payload.username}@local").strip().lower()
    name = (payload.name or payload.username).strip()
    password_hash = hash_password(payload.password)

    user = await user_repo.create_local_superuser(
        username=payload.username,
        password_hash=password_hash,
        email=email,
        name=name,
    )
    await install_repo.mark_completed()
    logger.info("Initial superuser %s created", payload.username)
    return user


async def authenticate_local_user(conn, *, username: str, password: str):
    await assert_setup_completed(conn)

    normalized = username.strip().lower()
    creds = await UserRepository(conn).get_local_by_username(normalized)
    if creds is None:
        return None
    if not verify_password(creds.password_hash, password):
        return None
    return await UserRepository(conn).get(creds.id)
