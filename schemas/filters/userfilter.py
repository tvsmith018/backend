from django_filters import CharFilter, FilterSet, NumberFilter, OrderingFilter
from users.models import Users

class UsersFilter(FilterSet):
    id = NumberFilter(field_name="id", lookup_expr="exact")

    firstname = CharFilter(
        field_name="firstname",
        lookup_expr="icontains",
    )

    lastname = CharFilter(
        field_name="lastname",
        lookup_expr="icontains",
    )

    email = CharFilter(
        field_name="email",
        lookup_expr="icontains",
    )

    order_by = OrderingFilter(
        fields=(
            ("email", "email"),
        )
    )

    class Meta:
        model = Users
        fields = [
            "id",
            "firstname",
            "lastname",
            "email",
        ]