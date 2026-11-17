
from enum import Enum


class Role(str, Enum):
    PLATFORM_SUPER_ADMIN = "platform_super_admin"
    COMPANY_ADMIN = "company_admin"
    WORKFLOW_ADMIN = "workflow_admin"
    WORKER = "worker"


PERMISSIONS = {
    Role.PLATFORM_SUPER_ADMIN: {
        "company:create",
        "company:approve",
        "company:search",
        "company:deactivate",
        "company:branding",
    },
    Role.COMPANY_ADMIN: {
        "company:view",
        "company:manage",
        "workflow:create",
        "workflow:assign_admin",
        "worker:view",
        "worker:approve",
        "worker:transfer",
        "attendance:view",
        "attendance:correction_approve",
        "project:manage",
        "report:view",
    },
    Role.WORKFLOW_ADMIN: {
        "workflow:view_assigned",
        "worker:view_assigned",
        "worker:approve_assigned",
        "attendance:view_assigned",
        "attendance:correction_request",
        "project:view_assigned",
        "report:view_assigned",
    },
    Role.WORKER: {
        "attendance:submit_own",
        "attendance:view_own",
        "profile:view_own",
        "history:view_own",
    },
}


def has_permission(role: Role, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


def require_permission(role: Role, permission: str):
    if not has_permission(role, permission):
        raise PermissionError("You are not authorized to perform this action.")
