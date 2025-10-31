from rest_framework import permissions

class IsCRMOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['CRM', 'ADMIN']
