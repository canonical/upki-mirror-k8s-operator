# Contributing

## Overview

This documents explains the processes and practices recommended for contributing enhancements to
this operator.

- Generally, before developing enhancements to this charm, you should consider [opening an issue
  ](https://github.com/canonical/upki-mirror-k8s-operator/issues) explaining your use case.
- If you would like to chat with us about your use-cases or proposed implementation, you can reach
  us [on Matrix](https://ubuntu.com/community/communications/matrix) or [Discourse](https://discourse.charmhub.io/).
- Familiarising yourself with the [Operator Framework](https://ops.readthedocs.io/en/latest/) library
  will help you a lot when working on new features or bug fixes.
- All enhancements require review before being merged. Code review typically examines
  - code quality
  - test coverage
  - user experience for Juju administrators this charm.
- Please help us out in ensuring easy to review branches by rebasing your pull request branch onto
  the `main` branch. This also avoids merge commits and creates a linear Git commit history.

## Developing

This project uses [`uv`](https://github.com/astral-sh/uv) for managing dependencies and virtual
environments.

You can create a virtual environment manually should you wish, though most of that is taken
care of automatically if you use the `Makefile` provided:

```bash
make format        # update your code according to linting rules
make lint          # code style
make unit          # unit tests

# The following exist, but should not be run directly without `spread`.
# See 'Running Tests' below.
❯ make integration   # run integration tests (run with `spread`)
```

To create the environment manually:

```bash
uv venv
source .venv/bin/activate
uv sync --all-extras
```

### Canonical Workshop

Alternatively, use [Canonical Workshop](https://github.com/canonical/workshop) to run the
development tools in an isolated environment. This definition uses
`confinement: virtual-machine` and requires host support for LXD virtual machines (including
KVM). Loading SDKs also requires LXD's support for shifted disk mounts in VMs, available in
LXD 6.10. LXD 6.9 can launch a VM without SDKs but refuses this definition. If your stable
channel still provides 6.9, use a suitable newer channel or wait for the stable release;
changing channels affects every LXD instance on the host, and downgrading is unsupported.

Workshop 0.9.7 requires enabling its experimental VM backend on the host before launch:

```bash
sudo snap set workshop workshop.experimental-vms=1
sudo snap restart workshop.workshopd
```

With Workshop installed and its host setup complete, run these commands from your checkout
(or the worktree you are developing in):

```bash
workshop launch dev
workshop actions dev
workshop run dev -- lint
workshop run dev -- unit
workshop run dev -- pytest tests/unit/test_charm.py -k pebble
workshop run dev -- format
workshop run dev -- pack-charm
workshop run dev -- pack-rock --verbose
workshop shell dev
```

`lint`, `format`, and `unit` reuse the Make targets above. The `pytest` action forwards its
arguments to pytest and excludes image and integration tests. The project SDK installs Make,
Git, build tools, Charmcraft, Rockcraft, LXD, and the locked Python dependencies.
The project is mounted at `/project`, with a separate virtual environment at
`/home/workshop/.venvs/upki-mirror` inside the workshop;
it does not share your host's `.venv`. Source edits and generated coverage files are visible
in your checkout.

After updating `uv.lock`, `workshop.yaml`, or the project SDK hooks in `.workshop/`, run:

```bash
workshop refresh dev
```

Workshop 0.9.7 requires recreating an existing workshop to change its confinement. This
discards files and build caches stored inside the old workshop; your mounted checkout is
preserved:

```bash
workshop remove dev
workshop launch dev
```

The VM's own LXD daemon runs managed build containers for the pack actions, which
forward arguments to Charmcraft and Rockcraft. Builds use their declared Ubuntu 24.04 bases;
the VM itself uses Ubuntu 26.04. Finished `.charm` and `.rock` files appear in your checkout.
The first build downloads its build image and dependencies, and ROCK builds compile the
upstream Rust tools, so allow additional time and disk space.

The VM runtime avoids the snapd/AppArmor failure seen with two levels of unprivileged LXD
containers ([LXD issue #14770](https://github.com/canonical/lxd/issues/14770)). Packing uses
normal managed builds, without destructive mode or access to the host's LXD daemon.

When packing the charm, use a regular clone rather than a linked Git worktree. The charm's
build hook runs `git describe`, and [Workshop cannot resolve linked worktree Git metadata
inside the container](https://documentation.ubuntu.com/canonical-workshop/latest/how-to/develop-with-workshops/use-git/#use-worktrees).
Lint, unit tests, and ROCK packing can still run from a linked worktree. Keep Git operations
on the host when using worktrees.

Continue to use the host workflows below for image checks (Docker or Podman) and integration
tests (Juju and Kubernetes via Spread). Those services are not provisioned in the workshop.

## Running tests

Unit tests can be run locally with no additional tools by running `make unit`. All of the project's unit tests are designed to run agnostic of machine and network, and shouldn't require any additional dependencies other than those injected by `uv run` and the `Make` target.

Integration testing is taken care of using `spread`. Currently, there are two supported backends -
tests can either be run in LXD virtual machines, or on a pre-provisioned server (such as a Github
Actions runner or development VM).

To show the available integration tests, you can:

```bash
$ charmcraft test --list lxd:
lxd:ubuntu-24.04:tests/spread/deploy:juju_3_6
lxd:ubuntu-24.04:tests/spread/ingress-path:juju_3_6
lxd:ubuntu-24.04:tests/spread/ingress:juju_3_6
lxd:ubuntu-24.04:tests/spread/observability-relations:juju_3_6
```

From there, you can either run all of the tests, or a selection:

```bash
# Run all of the tests
$ charmcraft test -v lxd:

# Run a particular test
$ charmcraft test -v lxd:ubuntu-24.04:tests/spread/deploy:juju_3_6
```

To run any of the tests on a locally provisioned machine, use the `github-ci` backend, e.g.

```bash
# List available tests
$ charmcraft test --list github-ci:

# Run all of the tests
$ charmcraft test -v github-ci:

# Run a particular test
$ charmcraft test -v github-ci:ubuntu-24.04:tests/spread/deploy:juju_3_6
```

### Troubleshooting Failing Tests

If you're working on a test that's failing, you can use `spread` to get an interactive shell inside the test environment on failure, which allows for easier debugging. To enable this, add `--debug` to your `charmcraft test` commands. For example:

```bash
❯ charmcraft test -v --debug lxd:ubuntu-24.04:tests/spread/functional/
```

If the above tests were to fail, you'd be dropped into an interactive shell before the machine is reaped.

## Build charm

Build the charm in this git repository using:

```bash
charmcraft pack
```

### Deploy

```bash
# Create a model
juju add-model dev
# Enable DEBUG logging
juju model-config logging-config="<root>=INFO;unit=DEBUG"
# Deploy the charm
juju deploy ./upki-mirror-k8s_amd64.charm \
  --resource nginx-image="$UPKI_OCI_IMAGE"
```

Set `UPKI_OCI_IMAGE` to the rebuilt non-root image accessible to your Kubernetes cluster.
The old upstream image runs as root and is incompatible with this charm's UID/GID.
Integration tests also read `UPKI_OCI_IMAGE`.

### Test the image locally

Build and load the ROCK without publishing it:

```bash
rockcraft pack
rockcraft.skopeo --insecure-policy copy oci-archive:upki-mirror_1.0.0_amd64.rock \
  docker-daemon:upki-mirror:non-root
UPKI_TEST_IMAGE=upki-mirror:non-root uv run --all-extras pytest tests/image -v
```

The image test checks UID/GID 584792, writes to workload and Promtail directories,
and serves a manifest through Nginx on port 8080 with all capabilities dropped.
It tries Docker first, then Podman if Docker is unavailable. For Podman, load the
ROCK using `rockcraft.skopeo copy` with a `containers-storage:` destination instead.
No image publication is needed for this test.
`--insecure-policy` permits loading this locally built, unsigned artifact without
requiring a system-wide Skopeo trust policy.
