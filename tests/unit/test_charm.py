# Copyright Canonical Ltd.
# See LICENSE file for licensing details.


import pytest
from ops.pebble import ServiceStatus
from ops.testing import (
    ActiveStatus,
    Container,
    Context,
    State,
    TCPPort,
)

from charm import UpkiMirrorCharm
from pebble import pebble_layer


@pytest.fixture
def charm():
    yield UpkiMirrorCharm


@pytest.fixture
def loaded_ctx(charm):
    ctx = Context(charm)
    container = Container(name="nginx", can_connect=True)
    return (ctx, container)


def test_nginx_pebble_ready(loaded_ctx):
    ctx, container = loaded_ctx
    state = State(containers=[container])

    result = ctx.run(ctx.on.pebble_ready(container=container), state)

    assert result.get_container("nginx").layers["nginx"] == pebble_layer()
    assert result.get_container("nginx").service_statuses == {
        "mozilla-crlite": ServiceStatus.ACTIVE,
        "intermediates": ServiceStatus.ACTIVE,
        "nginx": ServiceStatus.ACTIVE,
    }
    assert result.opened_ports == frozenset({TCPPort(8080)})
    assert result.unit_status == ActiveStatus()
