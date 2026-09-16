# Copyright Canonical Ltd.
# See LICENSE file for licensing details.

import json
import subprocess


def generate_container_securitycontext_map(metadata: dict) -> dict:
    """Read expected workload identities and include the Juju charm identity."""
    contexts = {
        name: {"runAsUser": container["uid"], "runAsGroup": container["gid"]}
        for name, container in metadata["containers"].items()
    }
    contexts["charm"] = {"runAsUser": 170, "runAsGroup": 170}
    return contexts


def get_pods(model: str, application: str) -> list:
    """Fetch all application pods, failing on kubectl errors."""
    result = subprocess.run(
        [
            "/snap/bin/kubectl",
            "get",
            "pods",
            "-n",
            model,
            "-l",
            f"app.kubernetes.io/name={application}",
            "-o",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    pods = json.loads(result.stdout)["items"]
    assert pods, f"No pods found for {application} in {model}"
    return pods


def assert_security_context(pod: dict, container_name: str, contexts: dict) -> None:
    """Check the effective UID/GID, accounting for pod-level defaults."""
    container = next(c for c in pod["spec"]["containers"] if c["name"] == container_name)
    context = dict(pod["spec"].get("securityContext", {}))
    context.update(container.get("securityContext", {}))
    for key, value in contexts[container_name].items():
        assert context.get(key) == value, (pod["metadata"]["name"], container_name, context)
