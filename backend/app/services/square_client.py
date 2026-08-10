"""Square API client — catalog, inventory, orders, merchant info."""

from square.client import Client
from app.config import settings
from app.services.encryption import decrypt_token


def get_client(encrypted_token: str) -> Client:
    """Create a Square SDK client from an encrypted access token."""
    token = decrypt_token(encrypted_token)
    return Client(
        access_token=token,
        environment="sandbox" if settings.SQUARE_SANDBOX else "production",
    )


def list_catalog_items(client: Client, cursor: str = None) -> dict:
    """Pull all ITEM catalog objects with pagination."""
    body = {"object_types": ["ITEM"]}
    if cursor:
        body["cursor"] = cursor
    result = client.catalog.search_catalog_objects(body=body)
    if result.is_error():
        raise Exception(f"Square API error: {result.errors}")
    return result.body


def get_inventory_counts(
    client: Client,
    catalog_object_ids: list[str],
    location_ids: list[str] = None,
) -> dict:
    """Batch retrieve current inventory counts for catalog objects."""
    body = {"catalog_object_ids": catalog_object_ids}
    if location_ids:
        body["location_ids"] = location_ids
    result = client.inventory.batch_retrieve_inventory_counts(body=body)
    if result.is_error():
        raise Exception(f"Square API error: {result.errors}")
    return result.body


def get_inventory_changes(
    client: Client,
    catalog_object_ids: list[str],
    location_ids: list[str] = None,
) -> dict:
    """Batch retrieve inventory change history."""
    body = {"catalog_object_ids": catalog_object_ids}
    if location_ids:
        body["location_ids"] = location_ids
    result = client.inventory.batch_retrieve_inventory_changes(body=body)
    if result.is_error():
        raise Exception(f"Square API error: {result.errors}")
    return result.body


def get_merchant_info(client: Client) -> dict:
    """Get basic merchant info and locations."""
    merch = client.merchants.retrieve_merchant(merchant_id="me")
    if merch.is_error():
        raise Exception(f"Square API error: {merch.errors}")
    return merch.body


def list_locations(client: Client) -> dict:
    """List all locations for a merchant."""
    result = client.locations.list_locations()
    if result.is_error():
        raise Exception(f"Square API error: {result.errors}")
    return result.body
