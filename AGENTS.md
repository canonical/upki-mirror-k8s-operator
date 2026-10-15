# Repository instructions

## Scope and layout

This repository contains a Python Juju charm for mirroring and serving CRLite filters on
Kubernetes, and a ROCK definition that packages the upstream Rust upki tools with Nginx.
The Rust source lives upstream; this repository does not contain a Rust application workspace.

- `src/charm.py`: charm event handling, ingress, log forwarding, and workload setup.
- `src/pebble.py`: Pebble services, checks, and proxy environment for the upki tools.
- `tests/unit/`: isolated charm and helper tests using `ops.testing`.
- `tests/image/`: non-root image checks requiring a locally loaded ROCK and Docker or Podman.
- `tests/integration/`: Jubilant tests requiring Juju and Kubernetes.
- `tests/spread/` and `spread.yaml`: integration-test provisioning and orchestration.
- `lib/charms/`: vendored charm libraries; avoid editing them during ordinary feature work.
- `charmcraft.yaml` and `rockcraft.yaml`: charm and image packaging definitions.
- `workshop.yaml` and `.workshop/`: Canonical Workshop actions and project SDK setup hooks.

Read `README.md` and `CONTRIBUTING.md` for deployment and development details. Keep changes
focused on the requested task, preserve unrelated work, and leave generated artifacts and
caches out of commits.

## Workload constraints

- Keep the non-root identity consistent across charm, ROCK, and image tests: UID/GID 584792.
  Preserve narrowly scoped write permissions, including the Nginx and Promtail directories.
- Nginx listens on port 8080. Keep the ingress relation, opened port, Pebble health check,
  image configuration, and tests consistent when changing networking.
- `mozilla-crlite` and `intermediates` fetch data and exit successfully. Preserve their
  `on-success: ignore` behavior and the periodic fetch checks.
- Preserve Juju proxy forwarding to the upki tools and persistent data under `/var/www/html`.
- Use a rebuilt non-root image for deployment and integration tests; `UPKI_OCI_IMAGE` selects
  an image accessible to the Kubernetes cluster. `UPKI_TEST_IMAGE` selects a locally loaded
  image for `tests/image/`.

## Development and verification

Use `uv` with the dependencies in `pyproject.toml` and `uv.lock`. Follow the Ruff configuration
(99-character line length). Keep charm wiring in `src/charm.py` and service definitions in
`src/pebble.py`. Add or update focused tests for behavior changes and synchronize documentation
when commands or deployment behavior change. Do not weaken checks to hide failures.

The Workshop environment is the convenient isolated path for routine development:

```bash
workshop launch dev
workshop run dev -- lint
workshop run dev -- unit
workshop run dev -- pytest tests/unit/test_charm.py -k pebble
```

The project is mounted at `/project`; the Workshop virtual environment lives inside the
workshop, separate from the host's `.venv`. After changing SDK hooks or dependencies, run
`workshop refresh dev`. Keep hooks executable and install Python dependencies as the
`workshop` user. Workshop actions should reuse the existing Make targets where practical.

Equivalent host checks:

```bash
make lint
make unit
PYTHONPATH=.:lib:src uv run --all-extras pytest tests/unit/test_charm.py -v
```

Run `make format` (or `workshop run dev -- format`) when Python formatting is relevant and
review its diff. Select checks proportionate to the change. `make unit` also collects the
image test, which skips unless `UPKI_TEST_IMAGE` is set; the Workshop `pytest` action excludes
image and integration tests explicitly.

Use `charmcraft pack` and `rockcraft pack` for packaging checks, and run integration tests
through Spread with the `lxd` backend as documented in `CONTRIBUTING.md`. Packaging, image
testing, and integration infrastructure are not provisioned by this Workshop definition.
Check `spread.yaml` and `charmcraft test --list lxd:` for actual task names and backends before
running tests. Report the checks run and any validation that could not be completed.
