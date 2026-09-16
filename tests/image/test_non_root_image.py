# Copyright Canonical Ltd.
# See LICENSE file for licensing details.

import os
import shutil
import subprocess

import pytest

IMAGE = os.environ.get("UPKI_TEST_IMAGE")
pytestmark = pytest.mark.skipif(not IMAGE, reason="Set UPKI_TEST_IMAGE to a locally loaded rock")


def test_non_root_image():
    """Check the default identity, real file writes, and Nginx without capabilities."""
    engine = None
    for candidate in ("docker", "podman"):
        if (
            shutil.which(candidate)
            and subprocess.run([candidate, "info"], capture_output=True).returncode == 0
        ):
            engine = candidate
            break
    assert engine is not None, "Neither Docker nor Podman is functional"
    subprocess.run(
        [
            engine,
            "run",
            "--rm",
            "--pull=never",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--sysctl=net.ipv4.ip_unprivileged_port_start=1024",
            "--entrypoint=sh",
            IMAGE,
            "-ec",
            """
            test "$(id -u)" = 584792
            test "$(id -g)" = 584792
            for path in /var/www/html /var/log/nginx /var/lib/nginx /run/nginx \
                        /opt/promtail /etc/promtail; do
                touch "$path/non-root-test"
                rm "$path/non-root-test"
            done
            mkdir -p /var/www/html/revocation /var/www/html/intermediates
            printf '{"non-root":true}' > /var/www/html/revocation/manifest.json
            nginx -t
            nginx
            trap 'nginx -s quit' EXIT
            bash -ec '
                exec 3<>/dev/tcp/127.0.0.1/8080
                printf "GET /revocation/manifest.json HTTP/1.0\\r\\n\\r\\n" >&3
                cat <&3 > /tmp/response
            '
            grep '200 OK' /tmp/response
            grep '"non-root":true' /tmp/response
            """,
        ],
        check=True,
    )
