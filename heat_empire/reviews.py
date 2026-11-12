from django.db.models import Avg, Count, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from .models import HeatingProduct, ProductReview


def refresh_product_ratings(product_ids):
    reviews = (
        ProductReview.objects.filter(product_id=OuterRef("pk"), published=True)
        .order_by()
        .values("product_id")
        .annotate(average=Avg("rating"), total=Count("pk"))
    )
    HeatingProduct.objects.filter(pk__in=product_ids).update(
        rating=Subquery(reviews.values("average")),
        review_count=Coalesce(Subquery(reviews.values("total")), Value(0)),
    )
