"""Base Entity definition for SmartWeather Integration."""
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.device_registry as dr
from typing import Dict, List
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_FRIENDLY_NAME,
)
from .const import (
    DOMAIN,
    ATTR_BRAND,
    ATTR_SMARTWEATHER_STATION_ID,
    ATTR_UPDATED,
    CONF_STATION_ID,
    DEFAULT_BRAND,
    DEFAULT_ATTRIBUTION,
    DEVICE_TYPE_WEATHER,
)


class SmartWeatherEntity(Entity):
    """Base class for SmartWeather Entities."""

    def __init__(self, coordinator, entries, entity, server, fcst_coordinator):
        """Initialize the SmartWeather Entity."""
        super().__init__()
        self.coordinator = coordinator
        self.fcst_coordinator = fcst_coordinator
        self.entries = entries
        self.server = server

        self._entity = entity
        self._platform_serial = self.server["serial_number"]
        self._platform_id = self.server["station_type"]
        self._device_key = f"{self.entries[CONF_STATION_ID]}"
        if self._entity == DEVICE_TYPE_WEATHER:
            self._unique_id = self._device_key
        else:
            self._unique_id = f"{self._device_key}_{self._entity}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def _current(self):
        """Return Current Data."""
        return self.coordinator.data[0]

    @property
    def _forecast(self):
        """Return Forecast Data Array."""
        if self.fcst_coordinator is None:
            return None
        else:
            return self.fcst_coordinator.data[0]

    @property
    def device_info(self):
        return {
            "connections": {(dr.CONNECTION_NETWORK_MAC, self._device_key)},
            "manufacturer": DEFAULT_BRAND,
            "model": self._platform_id,
            "via_device": (DOMAIN, self._device_key),
        }

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def device_state_attributes(self) -> Dict:
        """Return SmartWeather specific attributes."""
        return {
            ATTR_ATTRIBUTION: DEFAULT_ATTRIBUTION,
            ATTR_SMARTWEATHER_STATION_ID: self._device_key,
        }

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

        self.async_on_remove(
            self.fcst_coordinator.async_add_listener(self.async_write_ha_state)
        )
