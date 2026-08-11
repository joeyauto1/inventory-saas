"""Square SDK adapter — pins square_client.py to the SDK actually installed.

Background: this module was written against the LEGACY Square Python SDK
(`retrieve_merchant`, `list_locations`, `body=` request wrappers, `.is_error()`,
`.body`) while requirements.txt pins `squareup==45.x`, the new generated SDK
where none of those exist. The first call in the OAuth callback —
`Square(access_token=..., environment="sandbox")` — raised
`TypeError: unexpected keyword argument 'access_token'`, surfacing to the
merchant as a 500 immediately after they clicked Allow.

These tests exist so the adapter can never silently drift from the installed
SDK again: they call the real constructor, and they pin the dict shape the
route handlers in auth.py / inventory.py / reports.py consume.
"""

from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from square.core.pagination import SyncPager
from square.types.batch_get_inventory_changes_response import (
    BatchGetInventoryChangesResponse,
)
from square.types.batch_get_inventory_counts_response import (
    BatchGetInventoryCountsResponse,
)
from square.types.get_merchant_response import GetMerchantResponse
from square.types.list_locations_response import ListLocationsResponse
from square.types.search_catalog_objects_response import SearchCatalogObjectsResponse

from app.config import settings
from app.services import square_client
from app.services.encryption import encrypt_token


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    """Real Fernet key — get_client decrypts for real, no mocking of crypto."""
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())


@pytest.fixture
def sandbox(monkeypatch):
    monkeypatch.setattr(settings, "SQUARE_SANDBOX", True)


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setattr(settings, "SQUARE_SANDBOX", False)


# --- get_client: the exact call that 500'd the OAuth callback -----------------


def test_get_client_constructs_against_installed_sdk(sandbox):
    """The regression test for the callback 500.

    Builds a client the same way /auth/callback does. Against squareup 45.x a
    legacy-style `access_token=` kwarg raises TypeError here, which is what the
    merchant saw as Internal Server Error.
    """
    client = square_client.get_client(encrypt_token("sq0atp-real-token"))

    assert client._client_wrapper.get_headers()["Authorization"] == "Bearer sq0atp-real-token"


def test_get_client_targets_sandbox_when_sandbox_flag_set(sandbox):
    client = square_client.get_client(encrypt_token("t"))

    assert client._client_wrapper.get_base_url() == "https://connect.squareupsandbox.com"


def test_get_client_targets_production_when_sandbox_flag_clear(production):
    """A string "production" is not a SquareEnvironment — this pins the enum."""
    client = square_client.get_client(encrypt_token("t"))

    assert client._client_wrapper.get_base_url() == "https://connect.squareup.com"


# --- response adapters: routes consume raw-Square-shaped dicts ----------------


def test_get_merchant_info_returns_square_shaped_dict():
    """auth.py reads merch_info["merchant"]["business_name"] via .get() chains."""
    client = SimpleNamespace(
        merchants=SimpleNamespace(
            get=lambda merchant_id: GetMerchantResponse.model_validate(
                {"merchant": {"id": "M1", "business_name": "Joe's Cafe", "country": "AU"}}
            )
        )
    )

    info = square_client.get_merchant_info(client)

    assert info["merchant"]["business_name"] == "Joe's Cafe"


def test_get_merchant_info_asks_for_the_authorised_merchant():
    """"me" resolves to whoever the token belongs to."""
    seen = {}

    def _get(merchant_id):
        seen["merchant_id"] = merchant_id
        return GetMerchantResponse.model_validate(
            {"merchant": {"id": "M1", "country": "AU"}}
        )

    client = SimpleNamespace(merchants=SimpleNamespace(get=_get))

    square_client.get_merchant_info(client)

    assert seen["merchant_id"] == "me"


def test_list_locations_returns_square_shaped_dict():
    """auth.py iterates locs.get("locations", []) and reads address/timezone."""
    client = SimpleNamespace(
        locations=SimpleNamespace(
            list=lambda: ListLocationsResponse.model_validate(
                {
                    "locations": [
                        {
                            "id": "L1",
                            "name": "Main St",
                            "timezone": "Australia/Brisbane",
                            "address": {"address_line_1": "1 Main St"},
                        }
                    ]
                }
            )
        )
    )

    locs = square_client.list_locations(client)

    assert locs["locations"][0]["address"]["address_line_1"] == "1 Main St"
    assert locs["locations"][0]["timezone"] == "Australia/Brisbane"


def test_list_catalog_items_returns_objects_with_variations():
    """inventory.py walks obj["item_data"]["variations"][n]["id"]."""
    client = SimpleNamespace(
        catalog=SimpleNamespace(
            search=lambda **kw: SearchCatalogObjectsResponse.model_validate(
                {
                    "objects": [
                        {
                            "type": "ITEM",
                            "id": "I1",
                            "item_data": {
                                "name": "Flat White",
                                "variations": [
                                    {
                                        "type": "ITEM_VARIATION",
                                        "id": "V1",
                                        "item_variation_data": {"name": "Regular"},
                                    }
                                ],
                            },
                        }
                    ]
                }
            )
        )
    )

    catalog = square_client.list_catalog_items(client)
    obj = catalog["objects"][0]

    assert obj["type"] == "ITEM"
    assert obj["item_data"]["variations"][0]["id"] == "V1"


def test_list_catalog_items_requests_only_items():
    seen = {}

    def _search(**kwargs):
        seen.update(kwargs)
        return SearchCatalogObjectsResponse.model_validate({"objects": []})

    client = SimpleNamespace(catalog=SimpleNamespace(search=_search))

    square_client.list_catalog_items(client, cursor="abc")

    assert seen["object_types"] == ["ITEM"]
    assert seen["cursor"] == "abc"


# --- pagination: batch_get_* return a SyncPager, not a flat response ----------


def _pager(pages):
    """Build a SyncPager chain over the given lists of raw count dicts."""
    def build(index):
        items = [
            BatchGetInventoryCountsResponse.model_validate({"counts": [c]}).counts[0]
            for c in pages[index]
        ]
        has_next = index + 1 < len(pages)
        return SyncPager(
            items=items,
            has_next=has_next,
            get_next=(lambda: build(index + 1)) if has_next else None,
            response=BatchGetInventoryCountsResponse.model_validate({"counts": pages[index]}),
        )

    return build(0)


def test_get_inventory_counts_drains_every_page():
    """The pager auto-paginates; a single-page read would silently truncate
    inventory for any merchant with more than one page of counts."""
    pages = [
        [{"catalog_object_id": "V1", "quantity": "5"}],
        [{"catalog_object_id": "V2", "quantity": "9"}],
    ]
    client = SimpleNamespace(
        inventory=SimpleNamespace(batch_get_counts=lambda **kw: _pager(pages))
    )

    data = square_client.get_inventory_counts(client, ["V1", "V2"])

    assert [c["catalog_object_id"] for c in data["counts"]] == ["V1", "V2"]
    assert data["counts"][1]["quantity"] == "9"


def test_get_inventory_counts_passes_filters_as_kwargs():
    """v45 takes real kwargs — a legacy body={...} dict is silently ignored."""
    seen = {}

    def _counts(**kwargs):
        seen.update(kwargs)
        return _pager([[]])

    client = SimpleNamespace(inventory=SimpleNamespace(batch_get_counts=_counts))

    square_client.get_inventory_counts(client, ["V1"], ["L1"])

    assert seen["catalog_object_ids"] == ["V1"]
    assert seen["location_ids"] == ["L1"]


def test_get_inventory_counts_omits_location_filter_when_absent():
    """Passing location_ids=None would filter to nothing rather than everything."""
    seen = {}

    def _counts(**kwargs):
        seen.update(kwargs)
        return _pager([[]])

    client = SimpleNamespace(inventory=SimpleNamespace(batch_get_counts=_counts))

    square_client.get_inventory_counts(client, ["V1"])

    assert "location_ids" not in seen


def test_get_inventory_changes_returns_changes_list():
    """inventory.py reads changes.get("changes", [])."""
    change = BatchGetInventoryChangesResponse.model_validate(
        {"changes": [{"type": "ADJUSTMENT"}]}
    ).changes[0]
    pager = SyncPager(
        items=[change],
        has_next=False,
        get_next=None,
        response=BatchGetInventoryChangesResponse.model_validate({"changes": []}),
    )
    client = SimpleNamespace(
        inventory=SimpleNamespace(batch_get_changes=lambda **kw: pager)
    )

    data = square_client.get_inventory_changes(client, ["V1"])

    assert data["changes"][0]["type"] == "ADJUSTMENT"
