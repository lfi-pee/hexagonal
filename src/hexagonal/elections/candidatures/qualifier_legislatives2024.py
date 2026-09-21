import sys

import polars as pl

from hexagonal.files.spec import get_polars_dataframe


def extraire_candidats(
    candidats, sensibilite_nfp, nuances_lfi24, nuances_lfi25, destination
):
    candidats = get_polars_dataframe(candidats).with_columns(
        pl.col("profession").str.slice(1, 2)
    )

    sensibilite_nfp = pl.read_csv(sensibilite_nfp).select(
        "circonscription",
        "numero_panneau",
        "sensibilite",
    )

    nuances_lfi24 = pl.read_csv(nuances_lfi24).select(
        "circonscription",
        "numero_panneau",
        "nuance_lfi",
    )
    nuances_lfi25 = pl.read_csv(nuances_lfi25).select(
        "circonscription", "numero_panneau", "alliance", "parti"
    )

    candidats = candidats.join(
        nuances_lfi24, on=["circonscription", "numero_panneau"], how="left"
    )
    candidats = candidats.join(
        sensibilite_nfp,
        on=["circonscription", "numero_panneau"],
        how="left",
    )
    candidats = candidats.join(
        nuances_lfi25,
        on=["circonscription", "numero_panneau"],
        how="left",
    )

    candidats.write_csv(destination)


def run():
    extraire_candidats(*sys.argv[1:])


if __name__ == "__main__":
    run()
