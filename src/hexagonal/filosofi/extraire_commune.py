from pathlib import Path
from zipfile import Path as ZPath
from zipfile import ZipFile

import click
import pandas as pd

# base-cc-filosofi : format SDMX long (une ligne par commune × indicateur). On ne garde
# que le niveau communal et les indicateurs de niveau de vie. À la différence du fichier
# IRIS (communes ≥ 5000 hab.), cette base couvre toutes les communes.
MESURES = {
    "MED_SL": "revenu_median",  # médiane du niveau de vie (revenu disponible par UC, €)
    "PR_MD60": "taux_pauvrete",  # taux de pauvreté au seuil de 60 % (%)
    "D1_SL": "decile1",
    "D9_SL": "decile9",
    "IR_D9_D1_SL": "rapport_interdecile_9_1",
}


@click.command()
@click.argument(
    "archive_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.argument(
    "dest_path", type=click.Path(file_okay=True, dir_okay=False, path_type=Path)
)
def run(archive_path, dest_path):
    dest_path.parent.mkdir(exist_ok=True, parents=True)

    with ZipFile(archive_path) as archive:
        with (ZPath(archive) / "DS_FILOSOFI_CC_data.csv").open("r", newline="") as fd:
            df = pd.read_csv(
                fd,
                sep=";",
                decimal=".",
                usecols=["GEO", "GEO_OBJECT", "FILOSOFI_MEASURE", "OBS_VALUE"],
                dtype={"GEO": str},
            )

    com = df[(df["GEO_OBJECT"] == "COM") & df["FILOSOFI_MEASURE"].isin(MESURES)].copy()
    wide = (
        com.pivot_table(
            index="GEO",
            columns="FILOSOFI_MEASURE",
            values="OBS_VALUE",
            aggfunc="first",
        )
        .rename(columns=MESURES)
        .reset_index()
        .rename(columns={"GEO": "code_commune"})
    )
    wide.to_csv(dest_path, index=False)


if __name__ == "__main__":
    run()
