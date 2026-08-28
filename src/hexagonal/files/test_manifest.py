from __future__ import annotations

from pathlib import Path

from hexagonal.files import ROOT_DIR
from hexagonal.files.manifest import DataFile, load_manifest

EXEMPLE = "data/02_clean/annuaire/conseils_regionaux.csv"


def test_manifest_couvre_sources_et_productions():
    manifest = load_manifest()
    sections = {file.section for file in manifest.values()}

    assert sections == {"01_raw", "02_clean", "03_main"}


def test_entree_de_manifest_est_complete():
    file = load_manifest()[Path(EXEMPLE)]

    assert (file.path, file.section, len(file.md5), file.size > 0) == (
        Path(EXEMPLE),
        "02_clean",
        32,
        True,
    )


def test_url_publique_derive_du_hash():
    file = DataFile(Path("data/03_main/exemple.csv"), "abcdef1234567890" * 2, 42)

    assert file.http_url.endswith("/cache/files/md5/ab/cdef1234567890abcdef1234567890")


def test_chemins_locaux_sont_dans_le_depot():
    file = load_manifest()[Path(EXEMPLE)]

    assert (file.local_path, file.cache_path.parent.name) == (
        ROOT_DIR / EXEMPLE,
        file.md5[:2],
    )
