from pydantic import BaseModel


class RolePermissionEntry(BaseModel):
    role_key: str
    action_key: str
    scope_key: str
    allowed: bool


class RolePermissionMatrixResponse(BaseModel):
    items: list[RolePermissionEntry]


class RolePermissionUpdate(BaseModel):
    role_key: str
    action_key: str
    scope_key: str
    allowed: bool


class RolePermissionBatchUpdate(BaseModel):
    updates: list[RolePermissionUpdate]


class RbacRoleResponse(BaseModel):
    key: str
    display_name: str
    scope_kind: str
    description: str


class RbacActionResponse(BaseModel):
    key: str
    display_name: str
    description: str


class RbacScopeResponse(BaseModel):
    key: str
    display_name: str
    description: str


class RbacCatalogResponse(BaseModel):
    roles: list[RbacRoleResponse]
    actions: list[RbacActionResponse]
    scopes: list[RbacScopeResponse]
