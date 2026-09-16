#!/usr/bin/env python3
# Copyright Canonical Ltd.
# See LICENSE file for licensing details.


from pathlib import Path
from urllib.request import urlopen

import jubilant
import pytest
import yaml

from . import UPKI_MIRROR, retry
from .helpers import assert_security_context, generate_container_securitycontext_map, get_pods

CONTAINERS_SECURITY_CONTEXT_MAP = generate_container_securitycontext_map(
    yaml.safe_load(Path("charmcraft.yaml").read_text())
)


def test_deploy(juju: jubilant.Juju, upki_mirror_charm, upki_mirror_oci_image):
    juju.deploy(
        upki_mirror_charm, app=UPKI_MIRROR, resources={"nginx-image": upki_mirror_oci_image}
    )
    juju.wait(jubilant.all_active)


@pytest.mark.parametrize("container_name", list(CONTAINERS_SECURITY_CONTEXT_MAP))
def test_container_security_context(juju: jubilant.Juju, container_name: str):
    """Verify the deployed pod identities after the charm reaches active status."""
    for pod in get_pods(juju.model, UPKI_MIRROR):
        assert_security_context(pod, container_name, CONTAINERS_SECURITY_CONTEXT_MAP)
    expected = CONTAINERS_SECURITY_CONTEXT_MAP[container_name]
    assert juju.ssh(f"{UPKI_MIRROR}/0", "id -u", container=container_name).strip() == str(
        expected["runAsUser"]
    )
    assert juju.ssh(f"{UPKI_MIRROR}/0", "id -g", container=container_name).strip() == str(
        expected["runAsGroup"]
    )


@retry(retry_num=10, retry_sleep_sec=3)
def test_revocation_manifest_was_fetched(juju: jubilant.Juju):
    output = juju.ssh(
        f"{UPKI_MIRROR}/0", "ls -l /var/www/html/revocation/manifest.json", container="nginx"
    ).strip()
    assert "/var/www/html/revocation/manifest.json" in output


@retry(retry_num=10, retry_sleep_sec=3)
def test_intermediates_manifest_was_fetched(juju: jubilant.Juju):
    output = juju.ssh(
        f"{UPKI_MIRROR}/0", "ls -l /var/www/html/intermediates/manifest.json", container="nginx"
    ).strip()
    assert "/var/www/html/intermediates/manifest.json" in output


@retry(retry_num=10, retry_sleep_sec=3)
def test_application_is_up(juju: jubilant.Juju):
    address = juju.status().apps[UPKI_MIRROR].units[f"{UPKI_MIRROR}/0"].address
    response = urlopen(f"http://{address}:8080/revocation/manifest.json")
    assert response.status == 200

    response = urlopen(f"http://{address}:8080/intermediates/manifest.json")
    assert response.status == 200
