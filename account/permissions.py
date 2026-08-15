from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import User

class IsAdminUserRole(BasePermission):
    """Allows full access only to users with the ADMIN role."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Roles.ADMIN)


class IsVendorOrAdmin(BasePermission):
    """Allows access to Vendors or Admins."""
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and 
            (request.user.role == User.Roles.VENDOR or request.user.role == User.Roles.ADMIN)
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission to allow users to only view/edit their own data.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Roles.ADMIN:
            return True
        
        # Check if the object is tied to vendor or client
        if hasattr(obj, 'vendor'):
            return obj.vendor == request.user
        if hasattr(obj, 'client'):
            return obj.client == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False
