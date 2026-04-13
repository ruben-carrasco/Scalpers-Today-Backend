import pytest
from unittest.mock import AsyncMock

from scalper_today.domain.entities.alerts import Alert, AlertCondition, AlertType, AlertStatus
from scalper_today.domain.dtos import CreateAlertRequest, UpdateAlertRequest
from scalper_today.domain.usecases.alerts import (
    CreateAlertUseCase,
    DeleteAlertUseCase,
    UpdateAlertUseCase,
)


def make_alert(user_id="user-1", name="Test Alert", alert_id="alert-1"):
    return Alert(
        id=alert_id,
        user_id=user_id,
        name=name,
        conditions=[AlertCondition(alert_type=AlertType.HIGH_IMPACT_EVENT, value=None)],
        status=AlertStatus.ACTIVE,
        push_enabled=True,
        trigger_count=0,
    )


# ── CreateAlertUseCase ──────────────────────────────


class TestCreateAlert:
    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        repo.create.side_effect = lambda alert: alert  # Return the alert as-is
        return repo

    @pytest.mark.asyncio
    async def test_create_valid_alert(self, mock_repo):
        use_case = CreateAlertUseCase(mock_repo)
        request = CreateAlertRequest(
            user_id="user-1",
            name="My Alert",
            description="Test",
            conditions=[{"alert_type": "high_impact_event"}],
            push_enabled=True,
        )
        result = await use_case.execute(request)

        assert result.name == "My Alert"
        assert result.user_id == "user-1"
        assert len(result.conditions) == 1
        assert result.conditions[0].alert_type == AlertType.HIGH_IMPACT_EVENT
        assert result.status == AlertStatus.ACTIVE
        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_country_condition(self, mock_repo):
        use_case = CreateAlertUseCase(mock_repo)
        request = CreateAlertRequest(
            user_id="user-1",
            name="Country Alert",
            conditions=[{"alert_type": "specific_country", "value": "United States"}],
        )
        result = await use_case.execute(request)

        assert result.conditions[0].alert_type == AlertType.SPECIFIC_COUNTRY
        assert result.conditions[0].value == "United States"

    @pytest.mark.asyncio
    async def test_create_with_no_conditions_fails(self, mock_repo):
        use_case = CreateAlertUseCase(mock_repo)
        request = CreateAlertRequest(
            user_id="user-1",
            name="Empty Alert",
            conditions=[],
        )
        with pytest.raises(ValueError, match="At least one condition"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_create_with_empty_name_fails(self, mock_repo):
        use_case = CreateAlertUseCase(mock_repo)
        request = CreateAlertRequest(
            user_id="user-1",
            name="   ",
            conditions=[{"alert_type": "high_impact_event"}],
        )
        with pytest.raises(ValueError, match="name is required"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_create_with_long_name_fails(self, mock_repo):
        use_case = CreateAlertUseCase(mock_repo)
        request = CreateAlertRequest(
            user_id="user-1",
            name="A" * 201,
            conditions=[{"alert_type": "high_impact_event"}],
        )
        with pytest.raises(ValueError, match="200 characters"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_create_country_without_value_fails(self, mock_repo):
        use_case = CreateAlertUseCase(mock_repo)
        request = CreateAlertRequest(
            user_id="user-1",
            name="Bad Alert",
            conditions=[{"alert_type": "specific_country"}],
        )
        with pytest.raises(ValueError, match="Value required"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_create_with_multiple_conditions(self, mock_repo):
        use_case = CreateAlertUseCase(mock_repo)
        request = CreateAlertRequest(
            user_id="user-1",
            name="Multi Alert",
            conditions=[
                {"alert_type": "high_impact_event"},
                {"alert_type": "specific_currency", "value": "USD"},
            ],
        )
        result = await use_case.execute(request)
        assert len(result.conditions) == 2


# ── DeleteAlertUseCase ──────────────────────────────


class TestDeleteAlert:
    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_owner_can_delete(self, mock_repo):
        alert = make_alert(user_id="user-1")
        mock_repo.get_by_id.return_value = alert
        mock_repo.delete.return_value = True

        use_case = DeleteAlertUseCase(mock_repo)
        result = await use_case.execute("alert-1", "user-1")

        assert result is True
        mock_repo.delete.assert_called_once_with("alert-1", soft_delete=True)

    @pytest.mark.asyncio
    async def test_non_owner_cannot_delete(self, mock_repo):
        alert = make_alert(user_id="user-1")
        mock_repo.get_by_id.return_value = alert

        use_case = DeleteAlertUseCase(mock_repo)
        with pytest.raises(PermissionError, match="permission"):
            await use_case.execute("alert-1", "user-2")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_alert(self, mock_repo):
        mock_repo.get_by_id.return_value = None

        use_case = DeleteAlertUseCase(mock_repo)
        with pytest.raises(ValueError, match="not found"):
            await use_case.execute("nonexistent", "user-1")


# ── UpdateAlertUseCase ──────────────────────────────


class TestUpdateAlert:
    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        repo.update.side_effect = lambda alert: alert
        return repo

    @pytest.mark.asyncio
    async def test_toggle_status(self, mock_repo):
        alert = make_alert(user_id="user-1")
        mock_repo.get_by_id.return_value = alert

        use_case = UpdateAlertUseCase(mock_repo)
        request = UpdateAlertRequest(
            alert_id="alert-1",
            user_id="user-1",
            status="paused",
        )
        result = await use_case.execute(request)

        assert result.status == AlertStatus.PAUSED
        mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_name(self, mock_repo):
        alert = make_alert(user_id="user-1")
        mock_repo.get_by_id.return_value = alert

        use_case = UpdateAlertUseCase(mock_repo)
        request = UpdateAlertRequest(
            alert_id="alert-1",
            user_id="user-1",
            name="Updated Name",
        )
        result = await use_case.execute(request)
        assert result.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_empty_name_fails(self, mock_repo):
        alert = make_alert(user_id="user-1")
        mock_repo.get_by_id.return_value = alert

        use_case = UpdateAlertUseCase(mock_repo)
        request = UpdateAlertRequest(
            alert_id="alert-1",
            user_id="user-1",
            name="",
        )
        with pytest.raises(ValueError, match="cannot be empty"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_non_owner_cannot_update(self, mock_repo):
        alert = make_alert(user_id="user-1")
        mock_repo.get_by_id.return_value = alert

        use_case = UpdateAlertUseCase(mock_repo)
        request = UpdateAlertRequest(
            alert_id="alert-1",
            user_id="user-2",
            name="Hacked",
        )
        with pytest.raises(PermissionError, match="permission"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_toggle_push_enabled(self, mock_repo):
        alert = make_alert(user_id="user-1")
        alert.push_enabled = True
        mock_repo.get_by_id.return_value = alert

        use_case = UpdateAlertUseCase(mock_repo)
        request = UpdateAlertRequest(
            alert_id="alert-1",
            user_id="user-1",
            push_enabled=False,
        )
        result = await use_case.execute(request)
        assert result.push_enabled is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_alert(self, mock_repo):
        mock_repo.get_by_id.return_value = None

        use_case = UpdateAlertUseCase(mock_repo)
        request = UpdateAlertRequest(
            alert_id="nonexistent",
            user_id="user-1",
            name="Whatever",
        )
        with pytest.raises(ValueError, match="not found"):
            await use_case.execute(request)
