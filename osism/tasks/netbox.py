import os
import subprocess

from celery import Celery
from celery.signals import worker_process_init
import pynetbox
from redis import Redis

from osism import settings
from osism.actions import generate_configuration, manage_device
from osism.tasks import Config, ansible

app = Celery('kolla')
app.config_from_object(Config)

redis = None
nb = None


@worker_process_init.connect
def celery_init_worker(**kwargs):
    global nb
    global redis

    redis = Redis(host="redis", port="6379")
    nb = pynetbox.api(
        settings.NETBOX_URL,
        token=settings.NETBOX_TOKEN
    )

    if settings.IGNORE_SSL_ERRORS:
        import requests
        requests.packages.urllib3.disable_warnings()
        session = requests.Session()
        session.verify = False
        nb.http_session = session


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    pass


@app.task(bind=True, name="osism.tasks.netbox.run")
def run(self, action, arguments):
    pass


@app.task(bind=True, name="osism.tasks.netbox.import_device_types")
def import_device_types(self, vendors, library=False):
    global redis

    if library:
        env = {**os.environ, "BASE_PATH": "/devicetype-library/device-types/"}
    else:
        env = {**os.environ, "BASE_PATH": "/netbox/device-types/"}

    if vendors:
        p = subprocess.Popen(f"python3 /import/main.py --vendors {vendors}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    else:
        p = subprocess.Popen("python3 /import/main.py", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)

    p.communicate()


@app.task(bind=True, name="osism.tasks.netbox.states")
def states(self, data):
    result = manage_device.get_current_states(data)
    return result


@app.task(bind=True, name="osism.tasks.netbox.data")
def data(self, collection, device, state):
    result = manage_device.load_data_from_filesystem(collection, device, state)
    return result


@app.task(bind=True, name="osism.tasks.netbox.connect")
def connect(self, device=None, state=None, data={}, states={}, enforce=False):
    manage_device.run(device, state, data, states, enforce)


@app.task(bind=True, name="osism.tasks.netbox.disable")
def disable(self, name):
    global nb

    for interface in nb.dcim.interfaces.filter(device=name):
        if str(interface.type) in ["Virtual"]:
            continue

        if "Port-Channel" in interface.name:
            continue

        if not interface.connected_endpoint and interface.enabled:
            interface.enabled = False
            interface.save()

        if interface.connected_endpoint and not interface.enabled:
            interface.enabled = True
            interface.save()


@app.task(bind=True, name="osism.tasks.netbox.generate")
def generate(self, name, template=None):
    generate_configuration.for_device(name, template)


@app.task(bind=True, name="osism.tasks.netbox.deploy")
def deploy(self, name):
    return


@app.task(bind=True, name="osism.tasks.netbox.init")
def init(self, arguments):
    ansible.run.delay("netbox-local", "init", arguments)
