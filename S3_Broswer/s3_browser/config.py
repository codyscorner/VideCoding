import json
import os
import configparser
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "S3Browser"
CONFIG_PATH = APP_DIR / "config.json"
AWS_CREDENTIALS_PATH = Path.home() / ".aws" / "credentials"
AWS_CONFIG_PATH = Path.home() / ".aws" / "config"

DEFAULT_CONFIG = {
    "profile_name": "runpod-s3",
    "region": "us-ca-2",
    "endpoint_url": "https://s3api-us-ca-2.runpod.io",
    "bucket_name": "zyg8x1wtwr",
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            merged = dict(DEFAULT_CONFIG)
            merged.update(data)
            return merged
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def save_aws_credentials(profile_name: str, access_key: str, secret_key: str) -> None:
    AWS_CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    parser = configparser.ConfigParser()
    if AWS_CREDENTIALS_PATH.exists():
        parser.read(AWS_CREDENTIALS_PATH, encoding="utf-8")
    if not parser.has_section(profile_name):
        parser.add_section(profile_name)
    parser.set(profile_name, "aws_access_key_id", access_key)
    parser.set(profile_name, "aws_secret_access_key", secret_key)
    with open(AWS_CREDENTIALS_PATH, "w", encoding="utf-8") as f:
        parser.write(f)


def save_aws_config(profile_name: str, region: str) -> None:
    AWS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    parser = configparser.ConfigParser()
    if AWS_CONFIG_PATH.exists():
        parser.read(AWS_CONFIG_PATH, encoding="utf-8")
    section = profile_name if profile_name == "default" else f"profile {profile_name}"
    if not parser.has_section(section):
        parser.add_section(section)
    parser.set(section, "region", region)
    with open(AWS_CONFIG_PATH, "w", encoding="utf-8") as f:
        parser.write(f)


def has_credentials(profile_name: str) -> bool:
    if not AWS_CREDENTIALS_PATH.exists():
        return False
    parser = configparser.ConfigParser()
    parser.read(AWS_CREDENTIALS_PATH, encoding="utf-8")
    return parser.has_section(profile_name) and parser.has_option(profile_name, "aws_access_key_id")
