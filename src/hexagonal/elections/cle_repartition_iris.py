"""Clé de répartition des bureaux de vote dans les IRIS (étape 0).

À partir de la table des adresses géolocalisées du REU (une ligne par couple
adresse/bureau, pondérée par `nb_adresses`), on rattache chaque adresse à son IRIS par
jointure spatiale, puis on agrège par (bureau, IRIS). La colonne `part` (poids
normalisé à 1 par bureau) est la clé de répartition.

`nb_adresses` est un proxy imparfait du nombre d'électeurs (dédoublonnage et
anonymisation en amont) : la V1 remplacera ce poids par les comptages issus de l'OCR
des listes électorales, sans toucher au reste du calcul."""

from __future__ import annotations

from pathlib import Path

import click
import geopandas as gpd
import pandas as pd

CRS_IRIS = "EPSG:2154"


@click.command()
@click.argument("adresses_parquet", type=click.Path(exists=True, path_type=Path))
@click.argument("iris_gpkg", type=click.Path(exists=True, path_type=Path))
@click.argument("dest_path", type=click.Path(path_type=Path))
def run(adresses_parquet: Path, iris_gpkg: Path, dest_path: Path) -> None:
    adresses = pd.read_parquet(
        adresses_parquet,
        columns=["id_brut_bv_reu", "longitude", "latitude", "nb_adresses"],
    )
    points = gpd.GeoDataFrame(
        adresses[["id_brut_bv_reu", "nb_adresses"]],
        geometry=gpd.points_from_xy(adresses["longitude"], adresses["latitude"]),
        crs="EPSG:4326",
    ).to_crs(CRS_IRIS)

    iris = gpd.read_file(iris_gpkg, columns=["code_iris"]).to_crs(CRS_IRIS)
    rattachees = points.sjoin(iris, how="left", predicate="within")

    hors_iris = int(rattachees["code_iris"].isna().sum())
    click.echo(
        f"{len(points)} adresses, {hors_iris} hors IRIS "
        f"({hors_iris / len(points):.2%}), {points['id_brut_bv_reu'].nunique()} bureaux"
    )

    cle = (
        rattachees.dropna(subset=["code_iris"])
        .groupby(["id_brut_bv_reu", "code_iris"], as_index=False)["nb_adresses"]
        .sum()
        .rename(columns={"nb_adresses": "poids"})
    )
    total_bureau = cle.groupby("id_brut_bv_reu")["poids"].transform("sum")
    cle["part"] = cle["poids"] / total_bureau

    dest_path.parent.mkdir(exist_ok=True, parents=True)
    cle.to_parquet(dest_path, index=False)


if __name__ == "__main__":
    run()
