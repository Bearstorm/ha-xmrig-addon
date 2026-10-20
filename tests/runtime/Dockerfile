
# Isolated test image only.
# Never published or used as the HAOS add-on image.

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/xmrig

WORKDIR /opt/xmrig

# Copy the actual Python controller modules.
COPY xmrig_haos/rootfs/app/ /opt/xmrig/app/

# Copy isolated integration tests.
COPY tests/runtime/test_runtime_controller.py /opt/xmrig/tests/test_runtime_controller.py

# Run as an unprivileged user.
USER 65534:65534

# Run tests automatically when the container starts.
ENTRYPOINT ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_runtime_controller.py", "-v"]

