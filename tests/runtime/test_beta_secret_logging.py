"""Step 50: reject MQTT/HA credentials exposure in supported error paths."""
import io
import logging
from contextlib import redirect_stderr
from unittest.mock import patch

from app.config import parse_config, ConfigError
from app.mqtt_service import BrokerSettings, MqttConfigError, parse_supervisor_service
from app.mqtt_runtime import load_mqtt_publisher
from app.mqtt_client import MqttPublisher

wallet="CI-WALLET-DO-NOT-LOG"
password="CI-MQTT-PASSWORD-DO-NOT-LOG"
token="CI-SUPERVISOR-TOKEN-DO-NOT-LOG"
settings=BrokerSettings("broker.invalid",1883,username="user",password=password)
assert password not in repr(settings)
config=parse_config({"wallet":wallet,"pool":"example.invalid"})
assert wallet not in repr(config)

logger=logging.getLogger("xmrig-mqtt")
stream=io.StringIO()
handler=logging.StreamHandler(stream)
logger.addHandler(handler)
old_level=logger.level
logger.setLevel(logging.INFO)
try:
    def fail_loader():
        raise MqttConfigError("MQTT service unavailable")
    assert load_mqtt_publisher(service_loader=fail_loader) is None
    data={"result":"error","message":password+token}
    try:
        parse_supervisor_service(data)
    except MqttConfigError as exc:
        assert password not in str(exc)
        assert token not in str(exc)
    else:
        raise AssertionError("service error was accepted")

    def bad_client():
        raise OSError(password+token)
    pub=MqttPublisher(settings,client_factory=bad_client)
    assert pub.start() is False
    assert not pub.connected

    try:
        parse_config({"wallet":wallet,"pool":"http://bad host"})
    except ConfigError as exc:
        assert wallet not in str(exc)
    else:
        raise AssertionError("bad pool was accepted")
finally:
    logger.removeHandler(handler)
    logger.setLevel(old_level)
text=stream.getvalue()
for secret in (wallet,password,token):
    assert secret not in text, "Sensitive value leaked in logs"
print("PASS: beta config, Supervisor MQTT and broker startup do not log sensitive values")
