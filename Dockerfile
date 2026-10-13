# Isolated test image only. Never published or used as the HAOS add-on image.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/xmrig

WORKDIR /opt/xmrig
COPY xmrig_haos/rootfs/app/ /opt/xmrig/app/
COPY tests/runtime/test_runtime_controller.py /opt/xmrig/tests/test_runtime_controller.py

USER 65534:65534
ENTRYPOINT ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_runtime_controller.py", "-v"]
