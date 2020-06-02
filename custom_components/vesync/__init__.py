"""Etekcity VeSync integration."""
import logging
import voluptuous as vol
from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD, CONF_TIME_ZONE)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery


_LOGGER = logging.getLogger(__name__)

DOMAIN = 'vesync'

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_TIME_ZONE): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the VeSync component."""
    conf = config.get(DOMAIN)

    if conf is None:
        return True

    if not configured_instances(hass):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data={
                    CONF_USERNAME: conf[CONF_USERNAME],
                    CONF_PASSWORD: conf[CONF_PASSWORD],
                },
            )
        )

    return True


async def async_setup_entry(hass, config_entry):
    """Set up Vesync as config entry."""
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]

    time_zone = str(hass.config.time_zone)

    manager = VeSync(username, password, time_zone)

    login = await hass.async_add_executor_job(manager.login)

    if not login:
        _LOGGER.error("Unable to login to the VeSync server")
        return False

    device_dict = await async_process_devices(hass, manager)

    forward_setup = hass.config_entries.async_forward_entry_setup

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][VS_MANAGER] = manager

    switches = hass.data[DOMAIN][VS_SWITCHES] = []

    hass.data[DOMAIN][VS_DISPATCHERS] = []

    if device_dict[VS_SWITCHES]:
        switches.extend(device_dict[VS_SWITCHES])
        hass.async_create_task(forward_setup(config_entry, "switch"))

    async def async_new_device_discovery(service):
        """Discover if new devices should be added."""
        manager = hass.data[DOMAIN][VS_MANAGER]
        switches = hass.data[DOMAIN][VS_SWITCHES]

        dev_dict = await async_process_devices(hass, manager)
        switch_devs = dev_dict.get(VS_SWITCHES, [])

        switch_set = set(switch_devs)
        new_switches = list(switch_set.difference(switches))
        if new_switches and switches:
            switches.extend(new_switches)
            async_dispatcher_send(hass, VS_DISCOVERY.format(VS_SWITCHES), new_switches)
            return
        if new_switches and not switches:
            switches.extend(new_switches)
            hass.async_create_task(forward_setup(config_entry, "switch"))

    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_DEVS, async_new_device_discovery
    )

    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    forward_unload = hass.config_entries.async_forward_entry_unload
    remove_switches = False
    if hass.data[DOMAIN][VS_SWITCHES]:
        remove_switches = await forward_unload(entry, "switch")

    if remove_switches:
        hass.services.async_remove(DOMAIN, SERVICE_UPDATE_DEVS)
        del hass.data[DOMAIN]
        return True

    return False

def setup(hass, config):
    """Set up the VeSync component."""
    from pyvesync.vesync import VeSync

    conf = config[DOMAIN]

    manager = VeSync(conf.get(CONF_USERNAME), conf.get(CONF_PASSWORD),
                     time_zone=conf.get(CONF_TIME_ZONE))

    if not manager.login():
        _LOGGER.error("Unable to login to VeSync")
        return

    manager.update()

    hass.data[DOMAIN] = {
        'manager': manager
    }

    # discovery.load_platform(hass, 'switch', DOMAIN, {}, config)
    discovery.load_platform(hass, 'fan', DOMAIN, {}, config)

    return True