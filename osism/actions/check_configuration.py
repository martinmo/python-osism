import logging

from pottery import Redlock

from osism import utils
from osism.plugins import routeros, routeros_testing


def for_device(name, parameters={}):

    device = utils.nb.dcim.devices.get(name=name)

    if "device_type" not in device.custom_fields or device.custom_fields["device_type"] != "switch":
        return

    if "Managed by OSISM" not in [str(x) for x in device.tags]:
        return

    if "deployment_enabled" in device.custom_fields and not bool(device.custom_fields["deployment_enabled"]):
        return

    if "deployment_type" not in device.custom_fields:
        return

    # Allow only one change per time
    lock = Redlock(key=f"lock_check_{name}", masters={utils.redis}, auto_release_time=120)
    lock.acquire()

    logging.info(f"Check configuration for device {device.name} with plugin {device.custom_fields['deployment_type']}")

    if device.custom_fields["deployment_type"] == "routeros":
        last_configuration = routeros.get_configuration(device)
    elif device.custom_fields["deployment_type"] == "routeros_testing":
        last_configuration = routeros_testing.get_configuration(device)
    else:
        logging.error(f"Deployment type x for device {device.name} not supported")
        last_configuration = None

    if last_configuration:
        for line in last_configuration.split('\n'):
            logging.info(f"configuration - {device.name}: {line}")

    lock.release()
