"""Square API client — catalog, inventory, orders, merchant info.

Written against the generated Square SDK (`squareup` 45.x), whose surface
differs from the legacy SDK in four ways that matter here:

  * the constructor takes `token=` and a `SquareEnvironment` enum, not
    `access_token=` and a string;
  * methods are named for the resource (`merchants.get`, `locations.list`)
    rather than repeating it (`retrieve_merchant`, `list_locations`);
  * requests take real keyword arguments, not a `body={...}` wrapper;
  * responses are typed models that raise `ApiError` on failure — there is no
    `.is_error()` / `.body` pair to check.

Callers in routes/ consume plain dicts keyed exactly like Square's JSON, so
every function here returns `_as_dict()` output rather than leaking SDK models
into the route layer.
"""

from square.client import Square
from square.environment import SquareEnvironment

from app.config import settings
from app.services.encryption import decrypt_token


def _as_dict(model) -> dict:
    """Render an SDK model as the raw Square JSON shape the routes expect.

    `by_alias` keeps Square's own field names, and dropping None keeps the
    payload equivalent to what the REST API would have returned.
    """
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


def get_client(encrypted_token: str) -> Square:
    """Create a Square SDK client from an encrypted access token."""
    return Square(
        token=decrypt_token(encrypted_token),
        environment=(
            SquareEnvironment.SANDBOX
            if settings.SQUARE_SANDBOX
            else SquareEnvironment.PRODUCTION
        ),
    )


def list_catalog_items(client: Square, cursor: str = None) -> dict:
    """Pull one page of ITEM catalog objects."""
    kwargs = {"object_types": ["ITEM"]}
    if cursor:
        kwargs["cursor"] = cursor
    return _as_dict(client.catalog.search(**kwargs))


def get_inventory_counts(
    client: Square,
    catalog_object_ids: list[str],
    location_ids: list[str] = None,
) -> dict:
    """Retrieve current inventory counts for catalog objects, all pages.

    `batch_get_counts` returns a pager rather than a flat response; iterating it
    follows the cursor, so a merchant with more counts than fit in one page is
    not silently truncated.
    """
    kwargs = {"catalog_object_ids": catalog_object_ids}
    if location_ids:
        kwargs["location_ids"] = location_ids
    pager = client.inventory.batch_get_counts(**kwargs)
    return {"counts": [_as_dict(count) for count in pager]}


def get_inventory_changes(
    client: Square,
    catalog_object_ids: list[str],
    location_ids: list[str] = None,
) -> dict:
    """Retrieve inventory change history for catalog objects, all pages."""
    kwargs = {"catalog_object_ids": catalog_object_ids}
    if location_ids:
        kwargs["location_ids"] = location_ids
    pager = client.inventory.batch_get_changes(**kwargs)
    return {"changes": [_as_dict(change) for change in pager]}


def get_merchant_info(client: Square) -> dict:
    """Get basic merchant info. "me" resolves to the token's own merchant."""
    return _as_dict(client.merchants.get(merchant_id="me"))


def list_locations(client: Square) -> dict:
    """List all locations for a merchant."""
    return _as_dict(client.locations.list())
