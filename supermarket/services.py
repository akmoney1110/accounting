from collections import OrderedDict

from .models import CategoryAttribute


def get_category_chain(category):
    """
    Return category hierarchy from root -> selected category.

    Example:

        Electronics
            -> Phones
                -> Smartphones

    returns:

        [
            Electronics,
            Phones,
            Smartphones,
        ]

    Includes protection against accidental circular
    category relationships.
    """

    if not category:
        return []

    chain = []
    visited = set()

    current = category

    while current:

        if current.pk in visited:
            break

        visited.add(current.pk)

        chain.append(current)

        current = current.parent

    chain.reverse()

    return chain


def get_inherited_category_attributes(
    category,
    *,
    variant_only=False,
):
    """
    Return effective CategoryAttribute objects for a category,
    including attributes inherited from its ancestors.

    Child configuration overrides parent configuration for
    the same ProductAttribute.

    Example:

        Electronics:
            Color

        Phones:
            Storage

        Smartphones:
            RAM

    Smartphones receives:

        Color
        Storage
        RAM
    """

    if not category:
        return []

    category_chain = (
        get_category_chain(category)
    )

    if not category_chain:
        return []

    category_ids = [
        item.pk
        for item in category_chain
    ]

    queryset = (
        CategoryAttribute.objects
        .filter(
            category_id__in=category_ids,
            attribute__is_active=True,
        )
        .select_related(
            "category",
            "attribute",
        )
        .prefetch_related(
            "attribute__values",
        )
        .order_by(
            "order",
            "attribute__order",
            "attribute__name",
        )
    )

    if variant_only:
        queryset = queryset.filter(
            is_variant_attribute=True
        )

    # Group the records by their category.
    by_category = {}

    for item in queryset:

        by_category.setdefault(
            item.category_id,
            [],
        ).append(item)

    # Ordered dictionary means attributes retain
    # predictable ordering.
    effective = OrderedDict()

    # Walk root -> child.
    #
    # If a child defines the same attribute again,
    # it replaces the inherited parent definition.
    for category_item in category_chain:

        for item in by_category.get(
            category_item.pk,
            [],
        ):

            attribute_id = (
                item.attribute_id
            )

            if attribute_id in effective:
                del effective[
                    attribute_id
                ]

            effective[
                attribute_id
            ] = item

    return list(
        effective.values()
    )