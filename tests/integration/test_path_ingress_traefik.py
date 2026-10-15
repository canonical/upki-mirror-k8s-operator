#!/usr/bin/env python3
# Copyright Canonical Ltd.
# See LICENSE file for licensing details.

import json
from urllib.request import Request, urlopen

import jubilant

from . import TRAEFIK, UPKI_MIRROR, retry


def test_deploy(juju: jubilant.Juju, upki_mirror_charm, upki_mirror_oci_image):
    """Test that upki-mirror can be related with Traefik for ingress."""
    apps = [UPKI_MIRROR, TRAEFIK]
    traefik_config = {"routing_mode": "path", "external_hostname": "foo.bar"}

    juju.deploy(
        upki_mirror_charm, app=UPKI_MIRROR, resources={"nginx-image": upki_mirror_oci_image}
    )
    juju.deploy(TRAEFIK, config=traefik_config, trust=True)
    juju.integrate(*apps)
    juju.wait(jubilant.all_active, timeout=360)


def test_ingress_setup(juju: jubilant.Juju):
    """Test that upki-mirror/Traefik are configured correctly."""
    result = juju.run(f"{TRAEFIK}/0", "show-external-endpoints")
    j = json.loads(result.results["external-endpoints"])

    model_name = juju.model
    assert model_name is not None
    assert j[UPKI_MIRROR] == {"url": f"http://foo.bar/{model_name}-{UPKI_MIRROR}"}


@retry(retry_num=24, retry_sleep_sec=5)
def test_ingress_functions_correctly(juju: jubilant.Juju, traefik_lb_ip):
    model_name = juju.model
    assert model_name is not None

    req = Request(f"http://{traefik_lb_ip}:80/{model_name}-{UPKI_MIRROR}/revocation/manifest.json")
    req.add_header("Host", "foo.bar")

    response = urlopen(req)
    assert response.status == 200
