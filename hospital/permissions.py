from django.contrib.auth import get_user_model
from rest_framework.permissions import SAFE_METHODS, BasePermission

User = get_user_model()


def _is_role(user, role: str) -> bool:
    return bool(user and user.is_authenticated and getattr(user, 'role', None) == role)


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return _is_role(request.user, User.Roles.ADMIN)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsDoctorRole(BasePermission):
    def has_permission(self, request, view):
        return _is_role(request.user, User.Roles.DOCTOR)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return _is_role(request.user, User.Roles.ADMIN)


class IsDoctorOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if _is_role(request.user, User.Roles.ADMIN):
            return True
        doctor = getattr(obj, 'doctor', None)
        if doctor and doctor.user_id == request.user.id:
            return True
        return False


class IsPatientSelfOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if _is_role(request.user, User.Roles.ADMIN):
            return True
        patient = getattr(obj, 'patient', None)
        if patient and patient.user_id == request.user.id:
            return True
        return False


class IsSelfOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if _is_role(request.user, User.Roles.ADMIN):
            return True
        return getattr(obj, 'id', None) == request.user.id
