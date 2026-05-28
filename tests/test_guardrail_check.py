"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

import os
import re
import shlex
from pathlib import Path
from typing import Any, cast

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPENDABOT_CONFIG_PATH = REPO_ROOT / ".github" / "dependabot.yml"
REQUIRED_DEPENDABOT_ECOSYSTEMS = ("uv", "github-actions", "docker", "docker-compose")
REQUIRED_COOLDOWN_DAYS = 14
COMPOSE_FILE_NAMES = (
    "compose.yml",
    "compose.yaml",
    "docker-compose.yml",
    "docker-compose.yaml",
)
IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "cov",
    "htmlcov",
    "node_modules",
}

_REMOTE_ADD_PATTERN = re.compile(r"^\s*ADD\s+https?://", re.IGNORECASE)
_PIPE_TO_SHELL_PATTERN = re.compile(
    r"\b(?:curl|wget)\b[^\n]*\|\s*(?:sh|bash)\b",
    re.IGNORECASE,
)

pytestmark = pytest.mark.guardrail_check


def _walk_repo_files(repo_root: Path):
    for current_root, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [
            dirname for dirname in dirnames if dirname not in IGNORED_DIRECTORY_NAMES
        ]
        current_path = Path(current_root)
        for filename in filenames:
            yield current_path / filename


def _collect_dockerfiles(repo_root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in _walk_repo_files(repo_root)
            if path.name.startswith("Dockerfile")
        ),
        key=str,
    )


def _collect_compose_files(repo_root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in _walk_repo_files(repo_root)
            if path.name in COMPOSE_FILE_NAMES
        ),
        key=str,
    )


def _collect_docker_base_image_violations(file_path: Path) -> list[str]:
    stage_names: set[str] = set()
    violations: list[str] = []
    relative_path = file_path.relative_to(REPO_ROOT)

    for lineno, line in enumerate(
        file_path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        stripped = line.strip()
        if not stripped or not stripped.upper().startswith("FROM "):
            continue

        tokens = shlex.split(stripped, comments=False, posix=True)
        if not tokens or tokens[0].upper() != "FROM":
            continue

        token_index = 1
        while token_index < len(tokens) and tokens[token_index].startswith("--"):
            token_index += 1
        if token_index >= len(tokens):
            continue

        base_image = tokens[token_index]
        known_stage_names = set(stage_names)

        if token_index + 2 < len(tokens) and tokens[token_index + 1].upper() == "AS":
            stage_names.add(tokens[token_index + 2])

        if base_image == "scratch" or base_image in known_stage_names:
            continue
        if "@sha256:" not in base_image:
            violations.append(
                f"{relative_path}:{lineno} Docker base images must be pinned by digest"
            )

    return violations


def _collect_docker_remote_installer_violations(file_path: Path) -> list[str]:
    violations: list[str] = []
    relative_path = file_path.relative_to(REPO_ROOT)

    for lineno, line in enumerate(
        file_path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        if _REMOTE_ADD_PATTERN.search(line):
            violations.append(f"{relative_path}:{lineno} Remote URL ADD is not allowed")
        if _PIPE_TO_SHELL_PATTERN.search(line):
            violations.append(
                f"{relative_path}:{lineno} Pipe-to-shell installers must be hash verified"
            )

    return violations


def _collect_compose_image_digest_violations(file_path: Path) -> list[str]:
    relative_path = file_path.relative_to(REPO_ROOT)
    yaml = cast(Any, YAML(typ="safe"))
    loaded = cast(object, yaml.load(file_path.read_text(encoding="utf-8")))
    config = cast(dict[str, Any], loaded if isinstance(loaded, dict) else {})
    services = config.get("services")
    violations: list[str] = []

    if not isinstance(services, dict):
        return violations

    services_dict = cast(dict[object, object], services)
    for service_name_obj, service_obj_obj in services_dict.items():
        if not isinstance(service_name_obj, str) or not isinstance(
            service_obj_obj, dict
        ):
            continue
        service_obj = cast(dict[str, Any], service_obj_obj)
        if "build" in service_obj:
            continue
        image = service_obj.get("image")
        if not isinstance(image, str):
            continue
        if "@sha256:" not in image:
            violations.append(
                f"{relative_path}:{service_name_obj} External Compose images must be pinned by digest"
            )

    return violations


def _collect_dependabot_policy_violations(config_path: Path) -> list[str]:
    relative_path = config_path.relative_to(REPO_ROOT)
    yaml = cast(Any, YAML(typ="safe"))
    loaded = cast(object, yaml.load(config_path.read_text(encoding="utf-8")))
    config = cast(dict[str, Any], loaded if isinstance(loaded, dict) else {})
    violations: list[str] = []
    updates = config.get("updates")

    if config.get("version") != 2:
        violations.append(f"{relative_path} version must be set to 2")
    if not isinstance(updates, list):
        violations.append(f"{relative_path} updates must be a list")
        return violations

    updates_list = cast(list[object], updates)
    updates_by_ecosystem: dict[str, dict[str, Any]] = {}
    for raw_update_obj in updates_list:
        if not isinstance(raw_update_obj, dict):
            continue
        raw_update = cast(dict[str, Any], raw_update_obj)
        ecosystem = raw_update.get("package-ecosystem")
        if isinstance(ecosystem, str):
            updates_by_ecosystem[ecosystem] = raw_update

    for ecosystem in REQUIRED_DEPENDABOT_ECOSYSTEMS:
        update = updates_by_ecosystem.get(ecosystem)
        if update is None:
            violations.append(
                f"{relative_path} must define an update block for {ecosystem!r}"
            )
            continue

        cooldown_obj = update.get("cooldown")
        if not isinstance(cooldown_obj, dict):
            violations.append(f"{relative_path} must define cooldown for {ecosystem!r}")
            continue
        cooldown = cast(dict[str, Any], cooldown_obj)
        if cooldown.get("default-days") != REQUIRED_COOLDOWN_DAYS:
            violations.append(
                f"{relative_path} cooldown.default-days for {ecosystem!r} must be {REQUIRED_COOLDOWN_DAYS}"
            )

        if update.get("open-pull-requests-limit") == 0:
            violations.append(
                f"{relative_path} must not disable version updates for {ecosystem!r}"
            )

    return violations


def test_dockerfiles_pin_base_images_and_avoid_remote_installers():
    violations: list[str] = []
    for file_path in _collect_dockerfiles(REPO_ROOT):
        violations.extend(_collect_docker_base_image_violations(file_path))
        violations.extend(_collect_docker_remote_installer_violations(file_path))

    assert not violations, (
        "Supply-chain violations were found in Dockerfiles:\n" + "\n".join(violations)
    )


def test_compose_files_pin_images_by_digest():
    violations: list[str] = []
    for file_path in _collect_compose_files(REPO_ROOT):
        violations.extend(_collect_compose_image_digest_violations(file_path))

    assert not violations, (
        "Supply-chain violations were found in Compose files:\n" + "\n".join(violations)
    )


def test_dependabot_config_enforces_cooldown_policy():
    assert DEPENDABOT_CONFIG_PATH.exists(), (
        f"Dependabot configuration is missing: {DEPENDABOT_CONFIG_PATH.relative_to(REPO_ROOT)}"
    )

    violations = _collect_dependabot_policy_violations(DEPENDABOT_CONFIG_PATH)
    assert not violations, "Dependabot policy violations were found:\n" + "\n".join(
        violations
    )
