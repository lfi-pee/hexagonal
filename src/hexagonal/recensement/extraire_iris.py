"""Bases infracommunales (IRIS) du recensement INSEE 2021 : population/âge, CSP,
diplômes, logement. Les fichiers IRIS couvrent tout le territoire (une ligne par IRIS
pour les communes découpées, une ligne commune pour les autres).

On ne conserve que les comptages utiles ; les parts (% IRIS et % commune) sont calculées
en aval. Les comptages du recensement sont pondérés (flottants) : on arrondit à l'entier."""

from pathlib import Path
from zipfile import Path as ZPath
from zipfile import ZipFile

import click
import pandas as pd

POP = {
    "P21_POP": "pop",
    "P21_POP0014": "age_0014",
    "P21_POP1529": "age_1529",
    "P21_POP3044": "age_3044",
    "P21_POP4559": "age_4559",
    "P21_POP6074": "age_6074",
    "P21_POP75P": "age_75p",
    "C21_POP15P": "pop15p",
    "C21_POP15P_CS1": "cs_agri",
    "C21_POP15P_CS2": "cs_indep",
    "C21_POP15P_CS3": "cs_cadres",
    "C21_POP15P_CS4": "cs_interm",
    "C21_POP15P_CS5": "cs_employes",
    "C21_POP15P_CS6": "cs_ouvriers",
    "C21_POP15P_CS7": "cs_retraites",
    "C21_POP15P_CS8": "cs_autres",
}
ACT = {"P21_ACT1564": "act1564", "P21_CHOM1564": "chom1564"}
DIPL = {
    "P21_NSCOL15P": "nscol15p",
    "P21_NSCOL15P_DIPLMIN": "dipl_aucun",
    "P21_NSCOL15P_SUP2": "_sup2",
    "P21_NSCOL15P_SUP34": "_sup34",
    "P21_NSCOL15P_SUP5": "_sup5",
}
LOG = {
    "P21_RP": "rp",
    "P21_RP_PROP": "rp_prop",
    "P21_RP_LOC": "rp_loc",
    "P21_RP_LOCHLMV": "rp_hlm",
}


def _lire(zip_path: Path, cols: dict[str, str], avec_com: bool = False) -> pd.DataFrame:
    csv = next(n for n in ZipFile(zip_path).namelist() if n.lower().endswith(".csv"))
    usecols = ["IRIS", *cols] + (["COM"] if avec_com else [])
    with (ZPath(zip_path) / csv).open("r", newline="") as fd:
        df = pd.read_csv(fd, sep=";", usecols=usecols, dtype={"IRIS": str, "COM": str})
    return df.rename(columns={"IRIS": "code_iris", "COM": "code_commune", **cols})


@click.command()
@click.argument("pop_zip", type=click.Path(exists=True, path_type=Path))
@click.argument("activite_zip", type=click.Path(exists=True, path_type=Path))
@click.argument("diplomes_zip", type=click.Path(exists=True, path_type=Path))
@click.argument("logement_zip", type=click.Path(exists=True, path_type=Path))
@click.argument("dest_path", type=click.Path(path_type=Path))
def run(pop_zip, activite_zip, diplomes_zip, logement_zip, dest_path):
    dest_path.parent.mkdir(exist_ok=True, parents=True)
    df = _lire(pop_zip, POP, avec_com=True)
    for z, cols in ((activite_zip, ACT), (diplomes_zip, DIPL), (logement_zip, LOG)):
        df = df.merge(_lire(z, cols), on="code_iris", how="left")
    df["dipl_sup"] = df[["_sup2", "_sup34", "_sup5"]].sum(axis=1)
    df = df.drop(columns=["_sup2", "_sup34", "_sup5"])
    num = [c for c in df.columns if c not in ("code_iris", "code_commune")]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce").round(0)
    df.to_csv(dest_path, index=False)


if __name__ == "__main__":
    run()
