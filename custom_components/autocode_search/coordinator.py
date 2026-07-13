"""Data coordinator for Autocode Search."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, TypedDict
from uuid import uuid4

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .adapters.base import IRAdapter
from .const import DOMAIN
from .engine import SearchEngine
from .memory import SuccessMemory, default_success_memory
from .models import SearchSession, SearchStatus
from .models.search_filter import SearchFilter
from .providers.base import CodeProvider
from .providers.composite import CompositeCodeProvider
from .storage import StorageBackend
from .success_workflow import (
    log_awaiting_confirmation,
    log_confirmed_success,
    log_rejected_result,
    remember_success,
    resolve_provider_name,
)

_LOGGER = logging.getLogger(__name__)


class AutocodeSearchData(TypedDict):
    """Represent the shared data exposed by the coordinator."""

    status: str
    adapter_available: bool | None
    device_info: dict[str, Any] | None
    session_id: str
    search_status: str
    codes_tested: int
    codes_total: int
    codes_after_filter: int
    filter_description: str
    filter_summary: str
    progress: float
    current_code: str | None
    current_manufacturer: str | None
    current_model: str | None
    elapsed_time: str
    search_rate: float | None
    paused: bool
    cancelled: bool
    providers_used: list[str]
    providers_completed: list[str]
    duplicates_removed: int
    provider_order: list[str]
    provider_ranking_reason: str
    success_count: int
    last_success: str
    awaiting_confirmation: bool
    last_provider: str | None
    last_tested_command: str | None


class AutocodeSearchCoordinator(DataUpdateCoordinator[AutocodeSearchData]):
    """Coordinate future IR-code searches and shared integration data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator from a Home Assistant config entry.

        Options override the original config-entry data so reconfiguration takes
        effect after the options flow reloads this integration.
        """
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self.config_entry = entry
        self.configuration: dict[str, Any] = {**entry.data, **entry.options}
        self.adapter: IRAdapter | None = None
        self.search_engine: SearchEngine | None = None
        self.success_memory: SuccessMemory = default_success_memory()
        self.storage_backend = StorageBackend(hass)
        self._last_search_filter: SearchFilter | None = None
        now = datetime.now(UTC)
        self.search_session = SearchSession(
            session_id=str(uuid4()),
            device_type="",
            brand="",
            command="",
            current_index=0,
            total_codes=0,
            status=SearchStatus.IDLE,
            started_at=None,
            last_update=now,
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Load persisted success memory and publish the initial coordinator data."""
        await self._async_load_success_memory()
        await super().async_config_entry_first_refresh()

    async def _async_load_success_memory(self) -> None:
        """Load success records from storage and bind persistence."""
        records = await self.storage_backend.async_load()
        self.success_memory.load_records(records)
        self.storage_backend.attach(self.success_memory)

    async def async_start_search(
        self,
        provider: CodeProvider,
        adapter: IRAdapter,
        session: SearchSession,
        search_filter: SearchFilter | None = None,
    ) -> SearchEngine:
        """Create, start, and retain the search engine for a new session."""
        _LOGGER.debug("Creating SearchEngine")
        engine = SearchEngine(provider, adapter, session)
        _LOGGER.debug("Calling engine.start()")
        await engine.start(search_filter)
        _sync_provider_statistics(provider, session)
        self.adapter = adapter
        self.search_session = session
        self.search_engine = engine
        self._last_search_filter = search_filter
        session.reset_confirmation_state()
        await self.async_publish_session()
        return engine

    async def async_pause_search(self) -> None:
        """Pause the active search session."""
        engine = self._require_search_engine()
        await engine.pause()
        await self.async_publish_session()

    async def async_resume_search(self) -> None:
        """Resume the paused search session."""
        engine = self._require_search_engine()
        await engine.resume()
        await self.async_publish_session()

    async def async_cancel_search(self) -> None:
        """Cancel the active search session."""
        engine = self._require_search_engine()
        last_code = engine.provider.current()
        last_provider = resolve_provider_name(
            engine.provider,
            last_code,
            fallback_provider=self.search_session.last_provider,
        )
        await engine.cancel()
        if last_code is not None and self.search_session.last_tested_code is None:
            self.search_session.capture_last_tested(last_code, last_provider)
        self._activate_confirmation_if_needed()
        await self.async_publish_session()

    async def async_finish_search(self) -> None:
        """Finish the active search session."""
        engine = self._require_search_engine()
        last_code = engine.provider.current()
        last_provider = resolve_provider_name(
            engine.provider,
            last_code,
            fallback_provider=self.search_session.last_provider,
        )
        await engine.finish()
        if last_code is not None and self.search_session.last_tested_code is None:
            self.search_session.capture_last_tested(last_code, last_provider)
        self._activate_confirmation_if_needed()
        await self.async_publish_session()

    async def async_confirm_success(self) -> None:
        """Remember the last tested code after user confirmation."""
        session = self.search_session
        if not session.awaiting_confirmation or session.last_tested_code is None:
            raise RuntimeError("No search result is awaiting confirmation")

        remember_success(
            self.success_memory,
            self._last_search_filter,
            session.last_tested_code,
            session.last_provider,
        )
        session.clear_confirmation()
        log_confirmed_success()
        await self.async_publish_session()

    async def async_reject_result(self) -> None:
        """Dismiss the pending confirmation without storing a success."""
        session = self.search_session
        if not session.awaiting_confirmation:
            raise RuntimeError("No search result is awaiting confirmation")

        session.clear_confirmation()
        log_rejected_result()
        await self.async_publish_session()

    async def async_publish_session(self) -> None:
        """Publish the latest session state to coordinator listeners."""
        if self.search_engine is not None:
            self._capture_last_tested_from_engine(self.search_engine)
            self._activate_confirmation_if_needed()
        data = await self._async_build_data()
        self.async_set_updated_data(data)

    async def _async_update_data(self) -> AutocodeSearchData:
        """Return the latest shared data for the integration."""
        return await self._async_build_data()

    async def _async_build_data(self) -> AutocodeSearchData:
        """Build the coordinator payload from adapter and session state."""
        session = self.search_session
        adapter_status = await self._async_get_adapter_status()
        return AutocodeSearchData(
            status=adapter_status["status"],
            adapter_available=adapter_status["adapter_available"],
            device_info=adapter_status["device_info"],
            session_id=session.session_id,
            search_status=session.status.value,
            codes_tested=session.codes_tested,
            codes_total=session.codes_total,
            codes_after_filter=session.codes_after_filter,
            filter_description=session.filter_description,
            filter_summary=session.filter_summary,
            progress=session.progress,
            current_code=session.current_code,
            current_manufacturer=session.current_manufacturer,
            current_model=session.current_model,
            elapsed_time=session.format_elapsed_time(),
            search_rate=session.search_rate(),
            paused=session.paused,
            cancelled=session.cancelled,
            providers_used=session.providers_used,
            providers_completed=session.providers_completed,
            duplicates_removed=session.duplicates_removed,
            provider_order=session.provider_order,
            provider_ranking_reason=session.provider_ranking_reason,
            success_count=self.success_memory.count(),
            last_success=self._format_last_success(),
            awaiting_confirmation=session.awaiting_confirmation,
            last_provider=session.last_provider,
            last_tested_command=self._format_last_tested_command(session),
        )

    async def _async_get_adapter_status(self) -> dict[str, Any]:
        """Return adapter availability data for the coordinator."""
        if self.adapter is None:
            return {
                "status": "adapter_not_configured",
                "adapter_available": None,
                "device_info": None,
            }

        return {
            "status": "ready",
            "adapter_available": await self.adapter.is_available(),
            "device_info": await self.adapter.get_device_info(),
        }

    def _require_search_engine(self) -> SearchEngine:
        """Return the active search engine or raise a runtime error."""
        if self.search_engine is None:
            raise RuntimeError("No active Autocode Search session")
        return self.search_engine

    def _format_last_success(self) -> str:
        """Return a compact label for the most recent success record."""
        record = self.success_memory.last_record()
        if record is None:
            return ""
        return self.success_memory.format_record_summary(record)

    def _format_last_tested_command(self, session: SearchSession) -> str | None:
        """Return the last tested command label for display."""
        if session.last_tested_code is None:
            return None
        return session.last_tested_code.name.strip().upper()

    def _capture_last_tested_from_engine(self, engine: SearchEngine) -> None:
        """Store the last tested code when a search has ended."""
        session = self.search_session
        if session.status not in (SearchStatus.FINISHED, SearchStatus.CANCELLED):
            return
        if session.last_tested_code is not None:
            return

        code = engine.provider.current()
        if code is None:
            return

        provider = resolve_provider_name(
            engine.provider,
            code,
            fallback_provider=session.last_provider,
        )
        session.capture_last_tested(code, provider)

    def _activate_confirmation_if_needed(self) -> None:
        """Enable confirmation when a finished search has a tested code."""
        session = self.search_session
        if session.status not in (SearchStatus.FINISHED, SearchStatus.CANCELLED):
            return
        if session.awaiting_confirmation or session.last_tested_code is None:
            return

        session.activate_confirmation()
        command = session.last_tested_code.name if session.last_tested_code else None
        log_awaiting_confirmation(session.last_provider, command)


def _sync_provider_statistics(provider: CodeProvider, session: SearchSession) -> None:
    """Copy multi-provider statistics into the session when available."""
    if isinstance(provider, CompositeCodeProvider):
        session.providers_used = list(provider.providers_used)
        session.providers_completed = list(provider.providers_completed)
        session.duplicates_removed = provider.duplicates_removed
        session.provider_order = list(provider.provider_order)
        session.provider_ranking_reason = provider.provider_ranking_reason
