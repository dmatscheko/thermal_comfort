"""Test the Thermal Comfort integration setup process."""

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.thermal_comfort import async_migrate_entry, async_setup_entry, async_unload_entry, async_update_options
from custom_components.thermal_comfort.const import DOMAIN, PLATFORMS
from custom_components.thermal_comfort.sensor import LegacySensorType, SensorType
from homeassistant.components.sensor import DOMAIN as PLATFORM_DOMAIN
from homeassistant.helpers import entity_registry as er

from .const import ADVANCED_USER_INPUT


async def test_setup_update_unload_entry(hass):
    """Test entry setup and unload."""

    hass.config_entries.async_forward_entry_setups = AsyncMock()
    with patch.object(hass.config_entries, "async_update_entry") as p:
        config_entry = MockConfigEntry(domain=DOMAIN, data=ADVANCED_USER_INPUT, entry_id="test", unique_id=None)
        await hass.config_entries.async_add(config_entry)
        assert p.called

    assert await async_setup_entry(hass, config_entry)
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]

    # check user input is in config
    for key in ADVANCED_USER_INPUT:
        if key in hass.data[DOMAIN][config_entry.entry_id]:
            assert hass.data[DOMAIN][config_entry.entry_id][key] == ADVANCED_USER_INPUT[key]

    hass.config_entries.async_forward_entry_setups.assert_called_with(config_entry, PLATFORMS)

    # ToDo test hass.data[DOMAIN][config_entry.entry_id][UPDATE_LISTENER]

    hass.config_entries.async_reload = AsyncMock()
    assert await async_update_options(hass, config_entry) is None
    hass.config_entries.async_reload.assert_called_with(config_entry.entry_id)

    # Unload the entry and verify that the data has been removed
    assert await async_unload_entry(hass, config_entry)
    assert config_entry.entry_id not in hass.data[DOMAIN]


async def test_sensor_migration(hass):
    """Test migration of legacy sensor types."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=ADVANCED_USER_INPUT,
        entry_id="test",
        version=1,
    )
    config_entry.add_to_hass(hass)

    # Mock entity registry with legacy sensor
    registry = er.async_get(hass)
    registry.async_get_or_create(
        domain=PLATFORM_DOMAIN,
        platform=DOMAIN,
        unique_id=f"uniqueid{LegacySensorType.THERMAL_PERCEPTION}",
        suggested_object_id="sensor.test_thermal_perception",
        config_entry=config_entry,  # Link entity to config_entry
    )

    assert await async_migrate_entry(hass, config_entry)
    assert config_entry.version == 2

    # Verify new unique ID
    entity_id = registry.async_get_entity_id(PLATFORM_DOMAIN, DOMAIN, f"uniqueid{SensorType.DEW_POINT_PERCEPTION}")
    assert entity_id is not None

    # Test migration with no legacy sensors
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=ADVANCED_USER_INPUT,
        entry_id="test2",
        version=1,
    )
    config_entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, config_entry)
    assert config_entry.version == 2
