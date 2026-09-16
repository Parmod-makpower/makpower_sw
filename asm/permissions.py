from rest_framework import permissions


class IsASM(permissions.BasePermission):
    """
    Allows access only to authenticated ASM users.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "ASM"
            and request.user.is_active
        )


class IsCRMOrAdminForASMAssignment(permissions.BasePermission):
    """
    Only CRM or ADMIN can manage ASM ↔ SS assignments.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role in ["CRM", "ADMIN"]
        )