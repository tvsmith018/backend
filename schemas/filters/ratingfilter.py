from django_filters import FilterSet, NumberFilter, DateTimeFilter, OrderingFilter

from articles.models import Rating

class RatingFilter(FilterSet):
    article = NumberFilter(field_name="article__id")
    user = NumberFilter(field_name="user__id")

    min_value = NumberFilter(
        field_name="value",
        lookup_expr="gte",
    )
    max_value = NumberFilter(
        field_name="value",
        lookup_expr="lte",
    )

    created_after = DateTimeFilter(
        field_name="created",
        lookup_expr="gte",
    )

    order_by = OrderingFilter(
        fields=(
            ("created", "created"),
            ("article", "article"),
            ("user","user")
        )
    )
    class Meta:
        model = Rating
        fields = [
            "article",
            "user",
            "min_value",
            "max_value",
            "created_after",
        ]