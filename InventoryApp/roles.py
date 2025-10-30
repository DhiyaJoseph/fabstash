
# Role definitions
ROLE_SUPERADMIN = 'superadmin'
ROLE_ADMIN = 'admin'
ROLE_USER = 'user'

VALID_ROLES = [ROLE_SUPERADMIN, ROLE_ADMIN, ROLE_USER]
DEFAULT_ROLE = ROLE_USER

# Role permissions hierarchy
ROLE_HIERARCHY = {
    ROLE_SUPERADMIN: ['superadmin', 'admin', 'user'],
    ROLE_ADMIN: ['admin', 'user'],
    ROLE_USER: ['user']
}

def normalize_role(role):
    """Normalize role string to match valid roles"""
    if not role:
        return DEFAULT_ROLE
    normalized = role.lower()
    return normalized if normalized in VALID_ROLES else DEFAULT_ROLE

def has_permission(user_role, required_role):
    """Check if user_role has permissions of required_role"""
    if user_role not in ROLE_HIERARCHY:
        return False
    return required_role in ROLE_HIERARCHY[user_role]