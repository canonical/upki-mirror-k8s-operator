# Copyright Canonical Ltd.
# See LICENSE file for licensing details.

import os
import subprocess
import time
from pathlib import Path
from typing import Callable

import jubilant
import yaml
from pytest import fixture

from . import TRAEFIK


def _service_jsonpath(
    model_name: str,
    jsonpath: str,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    proc = run(
        [
            "/snap/bin/kubectl",
            "-n",
            model_name,
            "get",
            "service",
            f"{TRAEFIK}-lb",
            f"-o=jsonpath={jsonpath}",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout.strip()


def _traefik_service_ip(
    model_name: str,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleep: Callable[[float], None] = time.sleep,
    attempts: int = 24,
    delay: int = 5,
) -> str:
    for attempt in range(attempts):
        if ip_address := _service_jsonpath(
            model_name, "{.status.loadBalancer.ingress[0].ip}", run
        ):
            return ip_address

        if attempt < attempts - 1:
            sleep(delay)

    if ip_address := _service_jsonpath(model_name, "{.spec.clusterIP}", run):
        return ip_address

    raise RuntimeError(f"{TRAEFIK} service has no LoadBalancer IP or ClusterIP")


@fixture(scope="module")
def juju():
    with jubilant.temp_model() as juju:
        yield juju


@fixture(scope="module")
def upki_mirror_charm(request):
    """Upki mirror charm used for integration testing."""
    charm_file = request.config.getoption("--charm-path")
    if charm_file:
        return charm_file

    working_dir = os.getenv("SPREAD_PATH", Path("."))

    subprocess.run(
        ["/snap/bin/charmcraft", "pack", "--verbose"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=working_dir,
        check=True,
    )

    return next(Path.glob(Path(working_dir), "*.charm")).absolute()


@fixture(scope="module")
def upki_mirror_oci_image():
    if image := os.getenv("UPKI_OCI_IMAGE"):
        return image
    meta = yaml.safe_load(Path("./charmcraft.yaml").read_text())
    image = meta["resources"]["nginx-image"].get("upstream-source")
    if not image:
        raise RuntimeError("Set UPKI_OCI_IMAGE to a non-root image accessible to the Juju cluster")
    return image


@fixture(scope="module")
def traefik_lb_ip(juju: jubilant.Juju):
    model_name = juju.model
    assert model_name is not None
    return _traefik_service_ip(model_name)
