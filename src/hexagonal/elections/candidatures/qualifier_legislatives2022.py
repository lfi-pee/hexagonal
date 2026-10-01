import sys

import pandas as pd
from unidecode import unidecode

from hexagonal.codes import normaliser_code_circonscription
from hexagonal.files.spec import get_pandas_dataframe
from hexagonal.utils.clean import VRAI, FAUX

COLONNES_LEMONDE = {
    "Département": "departement",
    "Numéro Circonscription": "circonscription",
    "Numéro Panneau": "numero_panneau",
    "Nom": "nom_lemonde",
    "Nuance agrégée par Le Monde": "nuance_lemonde",
    "Parti agrégé par Le Monde": "parti_lemonde",
}

COLONNES_LEGIS_2022 = {
    "DEP": "departement",
    "panneau": "numero_panneau",
    "NCIRCO": "circonscription",
    "CODAGE_LEGIS2022": "nuance_legis_2022",
    "CODAGE_NUPES_ENSEMBLE_OUTREMER": "regroupement_om_legis_2022",
}


def normaliser_noms_villes(s):
    return (
        # éliminer les diacritiques (accents et autres cédilles)
        s.map(unidecode)
        # en majuscule
        .str.upper()
        # on remplace la ponctuation par des espaces
        .str.replace(r"[^A-Z]+", " ", regex=True)
        # on élimine tabulations et autres espace non standard, et on s'assure
        # qu'il n'y a pas d'espace double
        .str.replace(r"\s+", " ", regex=True)
        # on élimine les éventuels espaces avant et après
        .str.strip()
    )


def extraire_candidats(candidats, nuances_lemonde, nuances_legis_2022, destination):
    tour1 = get_pandas_dataframe(
        "data/02_clean/elections/2022-legislatives-1-circonscription.parquet"
    )
    tour2 = get_pandas_dataframe(
        "data/02_clean/elections/2022-legislatives-2-circonscription.parquet"
    )

    tour1["gagnant_premier_tour"] = (tour1["voix"] / tour1["inscrits"] > 0.25) & (
        tour1["voix"] / tour1["exprimes"] > 0.5
    )
    tour1["gagnant"] = tour1["gagnant_premier_tour"]

    rangs_candidats_tour2 = tour2.groupby("circonscription", observed=True)[
        "voix"
    ].rank(ascending=False)
    tour2["gagnant"] = rangs_candidats_tour2 == 1
    tour2["gagnant_premier_tour"] = False
    gagnants = pd.concat([tour2, tour1], ignore_index=True).drop_duplicates(
        ["circonscription", "numero_panneau"]
    )[["circonscription", "numero_panneau", "gagnant", "gagnant_premier_tour"]]

    candidats = get_pandas_dataframe(candidats)

    del candidats["departement"]

    nuances_lemonde = pd.read_csv(
        nuances_lemonde,
        usecols=list(COLONNES_LEMONDE),
        dtype=str,
    ).rename(columns=COLONNES_LEMONDE)
    nuances_lemonde["circonscription"] = normaliser_code_circonscription(
        nuances_lemonde["departement"].str.lstrip("0")
        + nuances_lemonde["circonscription"].str.zfill(2)
    )
    nuances_lemonde["numero_panneau"] = pd.to_numeric(nuances_lemonde["numero_panneau"])
    del nuances_lemonde["departement"]

    # 92-11 : le fichier du Monde place bien LÉVÊQUE (REC) au panneau 8 et ROLLOT (DXG)
    # au panneau 9, comme le ministère (candidatures et résultats), mais leurs nuances
    # Le Monde sont restées inversées (« LO » pour LÉVÊQUE, « Rec. » pour ROLLOT).
    inverses = (nuances_lemonde["circonscription"] == "92-11") & nuances_lemonde[
        "numero_panneau"
    ].isin([8, 9])
    if (
        nuances_lemonde.loc[inverses].set_index("numero_panneau")["nuance_lemonde"]
        == pd.Series({8: "LO", 9: "Rec."})
    ).all():
        colonnes = ["nuance_lemonde", "parti_lemonde"]
        nuances_lemonde.loc[inverses, colonnes] = nuances_lemonde.loc[
            inverses, colonnes
        ].to_numpy()[::-1]

    nuances_legis_2022 = pd.read_csv(
        nuances_legis_2022,
        usecols=list(COLONNES_LEGIS_2022),
        dtype=str,
    ).rename(columns=COLONNES_LEGIS_2022)
    nuances_legis_2022["circonscription"] = normaliser_code_circonscription(
        nuances_legis_2022["departement"]
        + nuances_legis_2022["circonscription"].str.zfill(2)
    )
    nuances_legis_2022["numero_panneau"] = pd.to_numeric(
        nuances_legis_2022["numero_panneau"]
    )
    del nuances_legis_2022["departement"]

    candidats = candidats.merge(nuances_lemonde, how="left")
    candidats = candidats.merge(nuances_legis_2022, how="left")

    candidats["nom"] = candidats["nom_lemonde"]
    del candidats["nom_lemonde"]

    candidats = candidats.merge(gagnants, how="left")
    for c in ["gagnant", "gagnant_premier_tour"]:
        candidats[c] = candidats[c].map(
            {
                True: VRAI,
                False: FAUX,
            }
        )

    candidats.to_csv(destination, index=False)


def run():
    extraire_candidats(*sys.argv[1:])


if __name__ == "__main__":
    run()
