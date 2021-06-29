# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

"""
This script will update the catalogs using the information from the
`repository-map.yml` file.

This script will:
- Check `repository-map.yml` urls are valid.
- Update the crowdin.yml to match `repository-map.yml`
- Clone repos or fetch from origin  based on information from `repository-map.yml`
- Checkout the current version
- Create a `gettext` catalog (*.pot) or update an existing catalog using
  `jupyterlab-translate`
"""

# Standard library imports
import os
import subprocess
import sys
import time

# Third party imports
import click
import jupyterlab_translate.api as api
import yaml

# Constants
HERE = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(HERE)
REPOSITORIES_FOLDER = "repos"
LANGUAGE_PACKS_FOLDER = "language-packs"
REPO_MAP_FILE = "repository-map.yml"
CROWDIN_FILE = "crowdin.yml"


def load_repo_map() -> dict:
    """
    Load yaml file with mapping of package names to repo url and version.
    """
    fpath = os.path.join(REPO_ROOT, REPO_MAP_FILE)
    with open(fpath, "r") as fh:
        data = yaml.safe_load(fh.read())

    return data


def save_crowdin(data: dict):
    """
    Save crowdin `data`.
    """
    fpath = os.path.join(REPO_ROOT, CROWDIN_FILE)
    with open(fpath, "w") as fh:
        fh.write(yaml.safe_dump(data))


def load_crowdin() -> dict:
    """
    Load crowdin data.
    """
    fpath = os.path.join(REPO_ROOT, CROWDIN_FILE)
    with open(fpath, "r") as fh:
        data = yaml.safe_load(fh.read())

    return data


def update_crowdin_config():
    """
    Update crowdin configuration to match `repository-map.yml`.
    """
    data = load_repo_map()
    crowdin_data = load_crowdin()
    # _files = crowdin_data["files"]
    packages = [
        {
            "source": "/jupyterlab/locale/jupyterlab.pot",
            "translation": (
                f"/jupyterlab/locale/%locale_with_underscore%"
                f"/LC_MESSAGES/%file_name%.po"
            ),
        }
    ]
    for pkg_name in sorted(data):
        if pkg_name != "jupyterlab":
            pkg_name_norm = pkg_name.replace("-", "_")
            packages.append({
                "source": f"/extensions/{pkg_name_norm}/locale/{pkg_name_norm}.pot",
                "translation": (
                    f"/extensions/{pkg_name_norm}/locale"
                    f"/%locale_with_underscore%/LC_MESSAGES/%file_name%.po"
                ),
            })

    crowdin_data["files"] = packages
    save_crowdin(crowdin_data)


def update_repo(package_name: str, url: str, version: str):
    """
    Clone or update repo for given package and checkout `version` reference.
    """
    repos_path = os.path.join(REPO_ROOT, REPOSITORIES_FOLDER)
    clone_path = os.path.join(repos_path, package_name)
    os.makedirs(repos_path, exist_ok=True)

    if not os.path.isdir(clone_path):
        args = ["git", "clone", "--depth", "1", url + ".git", package_name, "--branch", version]
        subprocess.run(args, cwd=repos_path, check=True)
    else:
        args = ["git", "fetch", "--depth", "1", "origin", version]
        subprocess.run(args, cwd=repos_path, check=True)

    args = ["git", "checkout", version]
    subprocess.run(args, cwd=clone_path, check=True)

    if version in ["master", "main"]:
        args = ["git", "pull", "origin", version]
        subprocess.run(args, cwd=clone_path, check=True)


def update_catalog(package_name: str, version: str):
    """
    Create or update pot catalogs for package_name and version using
    `jupyterlab-translate`.

    TODO: version is ignored
    """
    package_repo_dir = os.path.join(REPO_ROOT, REPOSITORIES_FOLDER, package_name)
    api.extract_language_pack(package_repo_dir, REPO_ROOT, package_name)


if __name__ == "__main__":
    start_run_time = time.time()
    args = sys.argv[1:]
    data = load_repo_map()
    packages = []

    # Ensure repository map and crowdin config are in sync
    update_crowdin_config()

    if len(args) == 1:
        package_name = args[0]
        # Update package if found in the repository-map.yml
        if package_name in data:
            packages = [package_name]
    elif len(args) == 0:
        packages = sorted(data.keys())
    else:
        sys.exit(0)
    
    for package_name in packages:
        click.echo(click.style(f"\n\nUpdating catalog for \"{package_name}\"\n\n", fg="cyan"))
        url = data[package_name]["url"]
        version = data[package_name]["current-version-tag"]
        update_repo(package_name, url, version)
        update_catalog(package_name, version)

    delta = round(time.time() - start_run_time, 0)
    click.echo(
        click.style(
            f'\n\n\nCatalogs updated in {delta} seconds\n', fg="green"
        )
    )
