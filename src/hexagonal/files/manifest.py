from __future__ import annotations

import hashlib
import os
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import yaml

from hexagonal.files import CONFIG, DATA_DIR, ROOT_DIR

URL_PREFIX = "cache/files/md5"
CACHE_DIR = ROOT_DIR / ".dvc" / "cache" / "files" / "md5"
CHUNK_SIZE = 1024 * 1024

Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


@dataclass(frozen=True, order=True)
class DataFile:
    path: Path
    md5: str
    size: int

    @property
    def http_url(self) -> str:
        return f"{CONFIG['http_root']}/{URL_PREFIX}/{self.md5[:2]}/{self.md5[2:]}"

    @property
    def local_path(self) -> Path:
        return ROOT_DIR / self.path

    @property
    def cache_path(self) -> Path:
        return CACHE_DIR / self.md5[:2] / self.md5[2:]

    @property
    def section(self) -> str:
        return self.path.parts[1]

    def is_present(self) -> bool:
        return self.local_path.is_file() and self.local_path.stat().st_size == self.size


def _load_yaml(path: Path) -> dict:
    with path.open("rb") as fd:
        return yaml.load(fd, Loader=Loader) or {}


def _sources() -> list[DataFile]:
    files = []
    for dvc_path in DATA_DIR.rglob("*.dvc"):
        for out in _load_yaml(dvc_path).get("outs") or []:
            path = (dvc_path.parent / out["path"]).relative_to(ROOT_DIR)
            files.append(DataFile(path, out["md5"], out["size"]))
    return files


def _productions() -> list[DataFile]:
    lock_path = ROOT_DIR / "dvc.lock"
    if not lock_path.is_file():
        return []

    files = []
    for stage in (_load_yaml(lock_path).get("stages") or {}).values():
        for out in stage.get("outs") or []:
            if "md5" in out:
                files.append(DataFile(Path(out["path"]), out["md5"], out["size"]))
    return files


def load_manifest() -> dict[Path, DataFile]:
    files = {f.path: f for f in _sources()}
    files.update({f.path: f for f in _productions()})
    return dict(sorted(files.items()))


def _checksum(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as fd:
        while chunk := fd.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch_to_cache(file: DataFile) -> None:
    if file.cache_path.is_file():
        return

    file.cache_path.parent.mkdir(parents=True, exist_ok=True)
    # Plusieurs chemins peuvent partager un même contenu : le fichier temporaire doit
    # être unique pour que deux téléchargements concurrents ne s'écrasent pas.
    partial = file.cache_path.with_name(f"{file.cache_path.name}.{uuid4().hex}.part")

    try:
        url = urllib.request.urlopen(file.http_url)
        with url as response, partial.open("wb") as fd:
            shutil.copyfileobj(response, fd, CHUNK_SIZE)

        if _checksum(partial) != file.md5:
            raise ValueError(f"Somme de contrôle invalide pour {file.path}")

        if not file.cache_path.is_file():
            partial.replace(file.cache_path)
    finally:
        partial.unlink(missing_ok=True)


def download(file: DataFile) -> None:
    if file.is_present():
        return

    _fetch_to_cache(file)
    file.local_path.parent.mkdir(parents=True, exist_ok=True)

    if file.local_path.exists():
        file.local_path.unlink()

    try:
        os.link(file.cache_path, file.local_path)
    except OSError:
        shutil.copyfile(file.cache_path, file.local_path)
