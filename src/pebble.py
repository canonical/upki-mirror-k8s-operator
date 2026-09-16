#!/usr/bin/env python3
# Copyright Canonical Ltd.
# See LICENSE file for licensing details.

"""Utilities for running upki-mirror and nginx in Pebble."""

import os

import ops


def pebble_layer() -> ops.pebble.Layer:
    """Return a Pebble layer for managing upki mirroring."""
    proxy_env = {
        "HTTP_PROXY": os.environ.get("JUJU_CHARM_HTTP_PROXY", ""),
        "HTTPS_PROXY": os.environ.get("JUJU_CHARM_HTTPS_PROXY", ""),
    }
    return ops.pebble.Layer(
        {
            "services": {
                "mozilla-crlite": {
                    "override": "replace",
                    "summary": "mozilla-crlite",
                    # The sleep here is a bit of a hack, but prevents Pebble from thinking
                    # that the service exited too quickly in the case that it downloads
                    # files very fast.
                    "command": "bash -c '/bin/mozilla-crlite /var/www/html/revocation; sleep 2'",
                    "startup": "enabled",
                    # We expect this process to run and exit with exit code 0, but
                    # exiting should not be considered a failure.
                    "on-success": "ignore",
                    "environment": proxy_env,
                },
                "intermediates": {
                    "override": "replace",
                    "summary": "intermediates",
                    # The sleep here is a bit of a hack, but prevents Pebble from thinking
                    # that the service exited too quickly in the case that it downloads
                    # files very fast.
                    "command": "bash -c '/bin/intermediates /var/www/html/intermediates; sleep 2'",
                    "startup": "enabled",
                    # We expect this process to run and exit with exit code 0, but
                    # exiting should not be considered a failure.
                    "on-success": "ignore",
                    "environment": proxy_env,
                },
                "nginx": {
                    "after": ["mozilla-crlite", "intermediates"],
                    "override": "replace",
                    "summary": "nginx",
                    "command": "nginx -g 'daemon off;'",
                    "startup": "enabled",
                },
            },
            "checks": {
                "up": {
                    "override": "replace",
                    "level": "alive",
                    "period": "30s",
                    "tcp": {"port": 8080},
                    "startup": "enabled",
                },
                "fetch-mozilla-crlite": {
                    "override": "replace",
                    "level": "alive",
                    "period": "360m",
                    "exec": {
                        "command": "/bin/mozilla-crlite /var/www/html/revocation",
                        "environment": proxy_env,
                    },
                    "startup": "enabled",
                },
                "fetch-intermediates": {
                    "override": "replace",
                    "level": "alive",
                    "period": "360m",
                    "exec": {
                        "command": "/bin/intermediates /var/www/html/intermediates",
                        "environment": proxy_env,
                    },
                    "startup": "enabled",
                },
            },
        }
    )
