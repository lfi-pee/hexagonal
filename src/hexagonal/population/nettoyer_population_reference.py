import zipfile

import click
import polars as pl
import polars.selectors as cs

from hexagonal.files.spec import get_polars_dataframe


@click.command()
@click.option("--archive", type=click.Path(exists=True, dir_okay=False))
@click.option("--cog-communes", type=click.Path(exists=True, dir_okay=False))
@click.option("--output", type=click.Path(writable=True, dir_okay=False))
def main(archive, cog_communes, output):
    cog_communes = get_polars_dataframe(cog_communes).select(
        "code_commune", "code_commune_parent", "type_commune"
    )
    with zipfile.ZipFile(archive) as archive:
        with archive.open("donnees_communes.csv") as fd:
            pop_communes = pl.read_csv(
                fd,
                separator=";",
                columns=["COM", "Commune", "PMUN", "PCAP", "PTOT"],
                schema_overrides={"COM": pl.Utf8()},
            ).with_columns(
                COMP=pl.when(pl.col("COM").str.slice(0, 3) == "132")
                .then(pl.lit("13055"))
                .when(pl.col("COM").str.slice(0, 4) == "6938")
                .then(pl.lit("69123"))
                .when(pl.col("COM").str.slice(0, 3) == "751")
                .then(pl.lit("75056"))
            )

        with archive.open("donnees_communes_deleguees.csv") as fd:
            pop_communes_deleguees = pl.read_csv(
                fd,
                separator=";",
                columns=["COM", "Commune", "PMUN", "PCAP", "PTOT", "COMP"],
                schema_overrides={"COM": pl.Utf8(), "COMP": pl.Utf8()},
            )

        with archive.open("donnees_collectivites.csv") as fd:
            pop_collectivites = pl.read_csv(
                fd,
                separator=";",
                columns=["COM", "Commune", "PMUN", "PCAP", "PTOT"],
                schema_overrides={"COM": pl.Utf8()},
            )

    pop_plm = (
        pop_communes.filter(pl.col("COMP").is_not_null())
        .group_by("COMP")
        .agg(pl.col("PMUN").sum())
        .select(
            pl.col("COMP").alias("COM"),
            pl.col("COMP")
            .replace(["13055", "69123", "75056"], ["Marseille", "Lyon", "Paris"])
            .alias("Commune"),
            "PMUN",
        )
    )

    pop = (
        pl.concat(
            [pop_communes, pop_plm, pop_communes_deleguees, pop_collectivites],
            how="diagonal",
        )
        .select(
            code_commune="COM",
            nom_commune="Commune",
            population_municipale="PMUN",
            population_comptee_a_part="PCAP",
            population_totale="PTOT",
            code_commune_parent="COMP",
        )
        .join(
            cog_communes,
            on=["code_commune", "code_commune_parent"],
            how="left",
            nulls_equal=True,
        )
        .with_columns(cs.integer().cast(pl.Int32()))
    )

    pop.write_parquet(output)


if __name__ == "__main__":
    main()
