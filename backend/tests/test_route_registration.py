"""Regression guard: the API must expose its full public route surface.

WHY THIS EXISTS
---------------
The two tests in test_api_contracts.py assert that the app boots and that the
OpenAPI schema *generates*. Neither asserts anything about how much of the API
is actually reachable, so a change that silently drops routers — a failed
conditional import, a refactor of api/v1/api.py, a dependency that alters
include_router() semantics — would keep CI green while shrinking the product.

WHAT THIS MEASURES, AND WHY
---------------------------
Assertions here are made against the **OpenAPI path set**, i.e. the public
contract, and against real routing behaviour. They deliberately do NOT assert
on `len(app.routes)`.

That distinction matters. `len(app.routes)` is an internal detail that varies
by framework version: FastAPI 0.136.1 reports 166 while 0.140.13 reports 7 for
this identical application, because newer versions nest routes under a mounted
sub-router instead of flattening them. Both serve exactly the same 139 OpenAPI
paths and respond identically. Asserting on that counter would produce false
failures on a routine dependency bump.
"""
import pytest

from app.main import app

# Measured on the current application: 139 documented paths.
# The floor sits below that so ordinary feature work does not trip it, while a
# collapse of the router surface fails loudly.
MIN_OPENAPI_PATHS = 120


@pytest.fixture(scope="module")
def openapi_paths():
    return app.openapi().get("paths", {})


def test_openapi_documents_the_full_surface(openapi_paths):
    assert len(openapi_paths) >= MIN_OPENAPI_PATHS, (
        f"OpenAPI documents only {len(openapi_paths)} paths "
        f"(expected >= {MIN_OPENAPI_PATHS}). A router was probably dropped from "
        "app/api/v1/api.py, or an endpoint module failed to import."
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/health",
        "/api/v1/auth/login",
        "/api/v1/documents",
        "/api/v1/query/stream",
        "/api/v1/chats",
        "/api/v1/billing/status",
        "/api/v1/hr/jobs",
        "/api/v1/legal/contracts",
        "/api/v1/insights",
    ],
)
def test_representative_endpoints_are_documented(path, openapi_paths):
    """Spot-check endpoints spread across different include_router() calls.

    Each sits behind a different prefix, so losing any single router shows up
    here even when the aggregate count stays above the floor.
    """
    assert path in openapi_paths, (
        f"{path} is missing from the OpenAPI schema. "
        f"Its router is not reaching api_router."
    )


def test_every_workspace_router_is_mounted(openapi_paths):
    """All seven workspaces must be reachable, not just the first few."""
    prefixes = ["/api/v1/hr/", "/api/v1/legal/", "/api/v1/finance/",
                "/api/v1/study/", "/api/v1/research/", "/api/v1/exams/",
                "/api/v1/query/"]
    missing = [p for p in prefixes if not any(k.startswith(p) for k in openapi_paths)]
    assert not missing, f"No routes registered for workspace prefixes: {missing}"
