from enum import StrEnum


class RoleKey(StrEnum):
    ORG_ADMIN = "org_admin"
    ORG_MEMBER = "org_member"
    TEAM_ADMIN = "team_admin"
    MEMBER = "member"
    VIEWER = "viewer"


class ActionKey(StrEnum):
    TEAM_CREATE = "team.create"
    TEAM_READ = "team.read"
    TEAM_UPDATE = "team.update"
    TEAM_DELETE = "team.delete"
    TEAM_MEMBER_READ = "team.member.read"
    TEAM_MEMBER_ADD = "team.member.add"
    TEAM_MEMBER_UPDATE_ROLE = "team.member.update_role"
    TEAM_MEMBER_REMOVE = "team.member.remove"
    REPO_READ = "repo.read"
    REPO_CREATE = "repo.create"
    REPO_UPDATE = "repo.update"
    REPO_DELETE = "repo.delete"
    REPO_CONFIGURE_CREDENTIALS = "repo.configure_credentials"
    REVIEW_READ = "review.read"
    REVIEW_RERUN = "review.rerun"
    REVIEW_FINDING_READ = "review.finding.read"
    USER_READ = "user.read"
    USER_ASSIGN_ORG_ADMIN = "user.assign_org_admin"
    USER_DEACTIVATE = "user.deactivate"
    SETTINGS_SSO_READ = "settings.sso.read"
    SETTINGS_SSO_UPDATE = "settings.sso.update"
    SETTINGS_LLM_READ = "settings.llm.read"
    SETTINGS_LLM_UPDATE = "settings.llm.update"
    SETTINGS_RBAC_READ = "settings.rbac.read"
    SETTINGS_RBAC_UPDATE = "settings.rbac.update"


class ScopeKey(StrEnum):
    ORGANIZATION = "organization"
    TEAM = "team"
    REPOSITORY = "repository"
    REVIEW = "review"
    USER = "user"
    SETTINGS = "settings"


ORG_SCOPED_ACTIONS: frozenset[ActionKey] = frozenset(
    {
        ActionKey.TEAM_CREATE,
        ActionKey.TEAM_DELETE,
        ActionKey.USER_READ,
        ActionKey.USER_ASSIGN_ORG_ADMIN,
        ActionKey.USER_DEACTIVATE,
        ActionKey.SETTINGS_SSO_READ,
        ActionKey.SETTINGS_SSO_UPDATE,
        ActionKey.SETTINGS_LLM_READ,
        ActionKey.SETTINGS_LLM_UPDATE,
        ActionKey.SETTINGS_RBAC_READ,
        ActionKey.SETTINGS_RBAC_UPDATE,
    }
)

TEAM_SCOPED_ACTIONS: frozenset[ActionKey] = frozenset(
    set(ActionKey) - ORG_SCOPED_ACTIONS
)

ACTION_DEFAULT_SCOPE: dict[ActionKey, ScopeKey] = {
    ActionKey.TEAM_CREATE: ScopeKey.ORGANIZATION,
    ActionKey.TEAM_READ: ScopeKey.TEAM,
    ActionKey.TEAM_UPDATE: ScopeKey.TEAM,
    ActionKey.TEAM_DELETE: ScopeKey.ORGANIZATION,
    ActionKey.TEAM_MEMBER_READ: ScopeKey.TEAM,
    ActionKey.TEAM_MEMBER_ADD: ScopeKey.TEAM,
    ActionKey.TEAM_MEMBER_UPDATE_ROLE: ScopeKey.TEAM,
    ActionKey.TEAM_MEMBER_REMOVE: ScopeKey.TEAM,
    ActionKey.REPO_READ: ScopeKey.TEAM,
    ActionKey.REPO_CREATE: ScopeKey.TEAM,
    ActionKey.REPO_UPDATE: ScopeKey.TEAM,
    ActionKey.REPO_DELETE: ScopeKey.TEAM,
    ActionKey.REPO_CONFIGURE_CREDENTIALS: ScopeKey.TEAM,
    ActionKey.REVIEW_READ: ScopeKey.TEAM,
    ActionKey.REVIEW_RERUN: ScopeKey.TEAM,
    ActionKey.REVIEW_FINDING_READ: ScopeKey.TEAM,
    ActionKey.USER_READ: ScopeKey.USER,
    ActionKey.USER_ASSIGN_ORG_ADMIN: ScopeKey.USER,
    ActionKey.USER_DEACTIVATE: ScopeKey.USER,
    ActionKey.SETTINGS_SSO_READ: ScopeKey.SETTINGS,
    ActionKey.SETTINGS_SSO_UPDATE: ScopeKey.SETTINGS,
    ActionKey.SETTINGS_LLM_READ: ScopeKey.SETTINGS,
    ActionKey.SETTINGS_LLM_UPDATE: ScopeKey.SETTINGS,
    ActionKey.SETTINGS_RBAC_READ: ScopeKey.SETTINGS,
    ActionKey.SETTINGS_RBAC_UPDATE: ScopeKey.SETTINGS,
}

TEAM_ASSIGNABLE_ROLES: frozenset[RoleKey] = frozenset(
    {RoleKey.TEAM_ADMIN, RoleKey.MEMBER, RoleKey.VIEWER}
)

ORG_ASSIGNABLE_ROLES: frozenset[RoleKey] = frozenset(
    {RoleKey.ORG_ADMIN, RoleKey.ORG_MEMBER}
)
