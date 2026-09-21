import re
from itertools import chain
from pathlib import Path

import click
import pandas as pd
from glom import T, glom

from hexagonal.codes import outremers
from hexagonal.cog.type_nom import nom_complet_commune
from hexagonal.files.spec import get_pandas_dataframe

INITIAL_DIGITS = re.compile(r"^\d+")

TYPE_CIRCONSCRIPTIONS = {
    "député": "code_circonscription",
    "sénateur": "code_departement",
    "député européen": "",
    "conseiller régional": "code_departement",
    "conseiller départemental": "code_departement",
    "président EPCI": "nom_epci",
    "maire": "code_commune",
    "maire délégué": "code_commune",
    "membre assemblée outremer": "code_departement",
    "membre assemblée corse": "code_departement",
    "président Polynésie française": "code_departement",
    "président Nouvelle-Calédonie": "code_departement",
    "président conseil exécutif Martinique": "code_departement",
    "conseiller Paris": "code_departement",
    "conseiller métropole Lyon": "code_csp",
    "maire arrondissement PLM": "code_commune",
    "conseiller AFE": "liste_pays",
    "président conseil consulaire": "nom_consulat",
}

CORRECTIONS_NOMS = {
    "Montgaillard en Albret": "Montgaillard-en-Albret",
    "Bors-de-Baignes": "Bors (canton de Charente-Sud)",
}


def mapping_commune(cog_path):
    departements = get_pandas_dataframe(cog_path / "departements.csv")

    departements = dict(
        zip(departements["nom"], departements["code_departement"], strict=False)
    )

    departements.update({outremer.nom: outremer.code_insee for outremer in outremers})
    departements["Français de l'étranger"] = "ZZ"
    departements["Saint-Martin / Saint-Barthélémy"] = "ZX"
    departements["Wallis et Futuna"] = "986"

    # communes encore existantes
    communes_metro = get_pandas_dataframe(cog_path / "communes.csv")
    communes_com = get_pandas_dataframe(cog_path / "communes_com.csv")
    mouvements_com = get_pandas_dataframe(cog_path / "mouvements_communes.csv")

    # seuls les mouvements de communes après le mois où les parrainages ont été envoyés
    # nous intéressent
    apres_parrainages = mouvements_com["date_effet"] > pd.to_datetime("2022-02-01")

    # seuls les mouvements qui ont soit changé le nom, soit le code commune
    changement_nom_ou_code = mouvements_com["type_evenement"].isin(
        [
            "changement de nom",
            "création commune nouvelle",
            "fusion simple",
            "changement de département",
        ]
    )

    # pour ne garder qu'une seule ligne, on filtre sur les événements qui concernent des
    # communes au sens propre
    sur_communes = (mouvements_com["type_commune_avant"] == "COM") & (
        mouvements_com["type_commune_apres"] == "COM"
    )
    mouvements_pertinents = mouvements_com[
        apres_parrainages & changement_nom_ou_code & sur_communes
    ]

    communes_map = {}

    for com in chain(communes_metro.itertuples(), communes_com.itertuples()):
        libelle = nom_complet_commune(com.nom, com.type_nom).upper()
        communes_map[com.code_departement, libelle] = com.code_commune

    for mouvement in mouvements_pertinents.itertuples():
        libelle = nom_complet_commune(
            mouvement.nom_avant, mouvement.type_nom_avant
        ).upper()
        code_commune = mouvement.code_commune_avant
        code_departement = code_commune[:2]
        if code_departement in ("97", "98"):
            code_departement = code_commune[:3]

        communes_map[code_departement, libelle] = code_commune

    def mapper(parrainage):
        mandat = parrainage["mandat"]
        type_circonscription = TYPE_CIRCONSCRIPTIONS[mandat]

        if not type_circonscription:
            return ""

        if type_circonscription in ["nom_epci", "liste_pays", "nom_consulat"]:
            return parrainage["circonscription_mandat"]

        if type_circonscription == "code_csp":
            return "69M"

        code_departement = departements[parrainage["departement_mandat"]]

        if type_circonscription == "code_departement":
            return code_departement

        if type_circonscription == "code_circonscription":
            numero = (
                INITIAL_DIGITS.match(parrainage["circonscription_mandat"])
                .group(0)
                .zfill(2)
            )
            return f"{code_departement}-{numero}"

        if mandat == "maire arrondissement PLM":
            return {"75": "75056", "69": "69123", "13": "13055"}[code_departement]

        code_commune = communes_map.get(
            (
                code_departement,
                parrainage["circonscription_mandat"],
            )
        )
        if not code_commune:
            return ""

        if type_circonscription == "code_commune":
            return code_commune

        raise ValueError(f"Cas inconnu: ({mandat}, {type_circonscription})")

    return mapper


def qualifier_parrainages(parrainages_path, cog_path, dest_path):
    mapper = mapping_commune(cog_path)

    spec = {
        "mandat": "mandat",
        "nom": "nom",
        "prenom": "prenom",
        "sexe": "sexe",
        "type_code_circonscription": T["mandat"].map(TYPE_CIRCONSCRIPTIONS),
        "code_circonscription": T.apply(mapper, axis=1),
        "candidat": "candidat",
        "date_publication": "date_publication",
    }

    parrainages = get_pandas_dataframe(parrainages_path)

    articles_re = r"^(?P<nom>[^(]+) \((?P<article>[^)]{2,3})\)$"

    avec_articles = parrainages["circonscription_mandat"].str.extract(articles_re)
    avec_articles.loc[avec_articles["article"] != "L'", "article"] = (
        avec_articles["article"] + " "
    )
    parrainages.loc[avec_articles["article"].notnull(), "circonscription_mandat"] = (
        avec_articles["article"] + avec_articles["nom"]
    )

    corrections = parrainages["circonscription_mandat"].isin(CORRECTIONS_NOMS)

    parrainages.loc[
        corrections,
        "circonscription_mandat",
    ] = parrainages.loc[corrections, "circonscription_mandat"].map(CORRECTIONS_NOMS)

    # on met en majuscule pour éliminer les problèmes de casse
    parrainages["circonscription_mandat"] = parrainages[
        "circonscription_mandat"
    ].str.upper()

    res = pd.DataFrame(glom(parrainages, spec))

    res.to_csv(dest_path, index=False)


@click.command()
@click.argument(
    "parrainages_path",
    type=click.Path(exists=True, readable=True, file_okay=True, dir_okay=False),
)
@click.argument(
    "cog_path",
    type=click.Path(
        exists=True, readable=True, dir_okay=True, file_okay=False, path_type=Path
    ),
)
@click.argument("dest_path", type=click.Path(writable=True, dir_okay=False))
def run(parrainages_path, cog_path, dest_path):
    qualifier_parrainages(parrainages_path, cog_path, dest_path)


if __name__ == "__main__":
    run()
