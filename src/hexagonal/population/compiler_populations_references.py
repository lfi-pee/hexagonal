from pathlib import Path

import click
import polars as pl


@click.command()
@click.option(
    "--source",
    "sources",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    multiple=True,
)
@click.option("--output", type=click.Path(dir_okay=False, writable=True))
def main(sources, output):
    dfs = [pl.read_parquet(source) for source in sources]

    pl.concat(dfs, how="diagonal").select(
        "code_commune",
        pl.col("type_commune").fill_null("COM"),
        "nom_commune",
        "code_commune_parent",
        "population_municipale",
        "population_comptee_a_part",
        "population_totale",
    ).sort(["code_commune", "type_commune"]).write_parquet(output)


if __name__ == "__main__":
    main()
