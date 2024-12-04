# __init__.py

import os
import pathlib

import tomllib

settings_path = pathlib.Path(__file__).parent / "settings.toml"
with settings_path.open(mode="rb") as fp:
    config = tomllib.load(fp)

CONFIG_SECRETS_FILE = os.getenv("CONFIG_SECRETS_FILE")

if not CONFIG_SECRETS_FILE:
    secrets_path = pathlib.Path(__file__).parent / "secrets.toml"
else:
    secrets_path = pathlib.Path(CONFIG_SECRETS_FILE)

with secrets_path.open(mode="rb") as fp:
    secrets = tomllib.load(fp)
config.update(secrets)
