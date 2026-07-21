"""Regression tests for DEBUG_MASTER_PLAN H-6.

With the default RAZORPAY_ENABLED=false, POST /billing/upgrade activated
any tier (including enterprise) for free — revenue bypass if deployed with
defaults. The sandbox path is now gated to non-production environments.
"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.billing import upgrade_plan, UpgradeRequest

FAKE_USER = {"id": "00000000-0000-0000-0000-000000000001", "email": "u@x.dev"}


@pytest.mark.asyncio
async def test_production_blocks_sandbox_upgrade(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with patch("app.api.v1.endpoints.billing.RAZORPAY_ENABLED", False):
        with pytest.raises(HTTPException) as exc_info:
            await upgrade_plan(UpgradeRequest(plan="enterprise"), FAKE_USER, db=None)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"] == "payments_disabled"


@pytest.mark.asyncio
async def test_razorpay_enabled_still_returns_402(monkeypatch):
    with patch("app.api.v1.endpoints.billing.RAZORPAY_ENABLED", True):
        with pytest.raises(HTTPException) as exc_info:
            await upgrade_plan(UpgradeRequest(plan="pro"), FAKE_USER, db=None)
    assert exc_info.value.status_code == 402


@pytest.mark.asyncio
async def test_dev_sandbox_upgrade_still_works(monkeypatch):
    """The dev convenience path must survive the gate (regression area)."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    activated = AsyncMock(return_value={"success": True, "plan": "plus",
                                        "billing_cycle": "monthly"})
    with patch("app.api.v1.endpoints.billing.RAZORPAY_ENABLED", False), \
         patch("app.api.v1.endpoints.billing._activate_plan", activated):
        result = await upgrade_plan(UpgradeRequest(plan="plus"), FAKE_USER, db=None)
    activated.assert_awaited_once()
    assert result["success"] is True
    assert "sandbox" in result["message"]
