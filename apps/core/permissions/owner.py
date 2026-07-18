from rest_framework.permissions import BasePermission

from apps.core.utils.permissions import user_owns_resource


class IsOwner(BasePermission):
    """Object-level permission for resources with owner_id / owner_type fields."""

    owner_id_field = "owner_id"
    owner_type_field = "owner_type"

    def has_object_permission(self, request, view, obj):
        owner_id = getattr(obj, self.owner_id_field, None)
        owner_type = getattr(obj, self.owner_type_field, None)
        return user_owns_resource(
            user=request.user, owner_id=owner_id, owner_type=owner_type
        )
