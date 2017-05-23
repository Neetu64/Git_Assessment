import logging
from pyclowder.client import ClowderClient
from requests import HTTPError
from pyclowder.geostreams.sensors import SensorsApi


def test_version(caplog, host, key):
    caplog.setLevel(logging.DEBUG)
    client = ClowderClient(host=host, key=key)
    version = client.version()
    logging.info("Clowder version %s", version)
    assert len(version.keys()) != 0


def test_get_sensors(caplog, host, key):
    caplog.setLevel(logging.DEBUG)
    client = SensorsApi(host=host, key=key)
    response = client.sensors_get()
    sensors = response.json()
    logging.info("%s sensors found", len(sensors))
    assert response.status_code == 200 and len(sensors) != 0


def test_raise_for_status(caplog, host, key):
    client = ClowderClient(host=host, key=key)
    try:
        client.get_json("this_path_does_not_exist")
        assert False
    except HTTPError as e:
        logging.error(e.message)
        assert True