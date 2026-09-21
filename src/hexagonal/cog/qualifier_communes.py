from pathlib import Path

import click
import polars as pl

from hexagonal.cog.type_nom import TYPES_NOMS
from hexagonal.files.spec import get_polars_dataframe


@click.command()
@click.argument("chemin_communes", type=click.Path(exists=True, dir_okay=False))
@click.argument("chemin_population", type=click.Path(exists=True, dir_okay=False))
@click.argument("chemin_epci", type=click.Path(exists=True, dir_okay=False))
@click.argument("chemin_communes_epci", type=click.Path(exists=True, dir_okay=False))
@click.argument("dest", type=click.Path(dir_okay=False, path_type=Path))
def run(chemin_communes, chemin_population, chemin_epci, chemin_communes_epci, dest):
    communes = get_polars_dataframe(chemin_communes)

    # on ne garde que les communes de plein droit
    communes = communes.filter(pl.col("type_commune") == "COM")

    article = pl.col("type_nom").replace_strict(
        [t.code for t in TYPES_NOMS],
        [t.article for t in TYPES_NOMS],
        return_dtype=pl.String,
        default=None,
    )
    possessif = pl.col("type_nom").replace_strict(
        [t.code for t in TYPES_NOMS],
        [t.charniere for t in TYPES_NOMS],
        return_dtype=pl.String,
        default=None,
    )

    communes = communes.with_columns(
        nom=article + pl.col("nom"),
        forme_possessive=possessif + pl.col("nom"),
    ).select(
        pl.all().exclude(
            "type_commune",
            "type_nom",
            "code_commune_parent",
        )
    )

    population = get_polars_dataframe(chemin_population)

    population = population.filter(pl.col("type_commune") == "COM").select(
        "code_commune",
        "population_municipale",
    )

    communes = communes.join(population, how="left", on=["code_commune"]).sort(
        "code_commune"
    )

    epci = get_polars_dataframe(chemin_epci)
    communes_epci = get_polars_dataframe(chemin_communes_epci)

    communes = communes.join(
        communes_epci,
        on=["code_commune"],
        how="left",
    )
    communes = communes.join(
        epci.select("siren_epci", "nom_epci"),
        on=["siren_epci"],
        how="left",
    )

    dest.parent.mkdir(parents=True, exist_ok=True)
    communes.write_csv(dest)


if __name__ == "__main__":
    run()
