from __future__ import annotations

import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import click

from hexagonal.files.manifest import DataFile, download, load_manifest

PRODUCTIONS = ("02_clean", "03_main")
WORKERS = 8


def _humanize(size: int) -> str:
    for unit in ("o", "ko", "Mo", "Go"):
        if size < 1024 or unit == "Go":
            return f"{size:.0f} {unit}" if unit == "o" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} Go"


def _select(motifs: tuple[str, ...], tout: bool) -> list[DataFile]:
    manifest = load_manifest()

    if motifs:
        selection = [
            f
            for f in manifest.values()
            if any(m in str(f.path) or str(f.path).startswith(m) for m in motifs)
        ]
    elif tout:
        selection = list(manifest.values())
    else:
        selection = [f for f in manifest.values() if f.section in PRODUCTIONS]

    return sorted(selection)


def _run_module(module: str, *args: str) -> None:
    result = subprocess.run([sys.executable, "-m", module, *args])
    if result.returncode:
        sys.exit(result.returncode)


@click.group()
def main() -> None:
    """Accès aux données électorales et administratives françaises."""


@main.command()
@click.argument("motifs", nargs=-1)
@click.option("--tout", is_flag=True, help="Inclure les sources brutes (~14 Go).")
def pull(motifs: tuple[str, ...], tout: bool) -> None:
    """Télécharge les données. Sans argument, récupère les productions (~360 Mo)."""
    selection = _select(motifs, tout)

    if not selection:
        raise click.ClickException("Aucun jeu de données ne correspond.")

    manquants = [f for f in selection if not f.is_present()]
    if not manquants:
        click.echo(f"{len(selection)} fichiers déjà à jour.")
        return

    total = sum(f.size for f in manquants)
    click.echo(f"Téléchargement de {len(manquants)} fichiers ({_humanize(total)}).")

    echecs = []
    with click.progressbar(length=len(manquants), label="Téléchargement") as barre:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            for echec in pool.map(_download_one, manquants):
                if echec:
                    echecs.append(echec)
                barre.update(1)

    click.echo(
        f"{len(manquants) - len(echecs)} fichiers récupérés dans {Path('data')}."
    )

    if echecs:
        click.echo(
            f"\n{len(echecs)} fichiers sont introuvables sur le serveur. Ils sont "
            f"référencés par le dépôt mais n'ont pas encore été publiés :",
            err=True,
        )
        for path, motif in echecs:
            click.echo(f"  {path} ({motif})", err=True)


def _download_one(file: DataFile) -> tuple[Path, str] | None:
    try:
        download(file)
    except Exception as exc:
        return file.path, str(exc)
    return None


@main.command(name="list")
@click.argument("motifs", nargs=-1)
@click.option("--tout", is_flag=True, help="Inclure les sources brutes.")
def lister(motifs: tuple[str, ...], tout: bool) -> None:
    """Liste les jeux de données disponibles."""
    selection = _select(motifs, tout)
    largeur = shutil.get_terminal_size().columns

    for file in selection:
        marque = "✓" if file.is_present() else " "
        taille = _humanize(file.size).rjust(9)
        click.echo(f"{marque} {taille}  {str(file.path)[: largeur - 14]}")

    total = sum(f.size for f in selection)
    presents = sum(1 for f in selection if f.is_present())
    click.echo(f"\n{len(selection)} fichiers, {_humanize(total)}, {presents} présents.")


@main.command()
@click.argument("cible", required=False)
def repro(cible: str | None) -> None:
    """Rejoue les traitements de données (nécessite l'extra « pipeline »)."""
    _require("dvc", "pipeline")
    args = [cible] if cible else ["--all-pipelines", "--recursive"]
    _run_module("dvc", "repro", *args)


@main.command()
def doc() -> None:
    """Régénère sources.md et productions.md (nécessite l'extra « pipeline »)."""
    _require("dvc", "pipeline")
    _run_module("hexagonal.files.update_specs")
    _run_module("hexagonal.documentation.build")


@main.command()
def push() -> None:
    """Publie les données vers S3 (mainteneurs, nécessite l'extra « maintainer »)."""
    _require("boto3", "maintainer")
    _run_module("hexagonal.release")


def _require(module: str, extra: str) -> None:
    from importlib.util import find_spec

    if find_spec(module) is None:
        raise click.ClickException(
            f"Cette commande nécessite des dépendances supplémentaires.\n"
            f"Installez-les avec : uv sync --extra {extra}"
        )


if __name__ == "__main__":
    main()
