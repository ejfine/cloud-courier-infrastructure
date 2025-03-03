[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Checked with pyright](https://microsoft.github.io/pyright/img/pyright_badge.svg)](https://microsoft.github.io/pyright/)
[![Actions status](https://www.github.com/ejfine/cloud-courier-infrastructure/actions/workflows/ci.yaml/badge.svg?branch=main)](https://www.github.com/ejfine/cloud-courier-infrastructure/actions)
[![Open in Dev Containers](https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://www.github.com/ejfine/cloud-courier-infrastructure)


# Usage




# Development
## Using Pulumi
Run a Pulumi Preview: `uv run python -m cloud_courier_infrastructure.lib.pulumi_deploy --stack=dev`

## Updating from the template
This repository uses a copier template. To pull in the latest updates from the template, use the command:
`copier update --trust --conflict rej --defaults`
