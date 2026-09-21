from pathlib import Path

import click
from glom import Coalesce, Iter, S, Spec

from hexagonal.utils.clean import iterate_ndjson, nettoyer_avec_spec


def code_departement(code_commune):
    if code_commune[:2] in ["97", "98"]:
        return code_commune[:3]
    return code_commune[:2]


def extraire_telephone(telephones):
    return "\n".join(
        f"{t['valeur']} ({t['description']})" if t["description"] else t["valeur"]
        for t in telephones
    )


def selection_adresse(type_adresse):
    return Spec(
        (
            "adresse",
            Coalesce(
                Iter().filter(lambda a: a["type_adresse"] == type_adresse).first(),
                default=None,
            ),
        ),
    )


def champs_adresses(prefixe, subspec):
    return {
        f"{prefixe}_numero_voie": (subspec, Coalesce("numero_voie", default="")),
        f"{prefixe}_complement1": (subspec, Coalesce("complement1", default="")),
        f"{prefixe}_complement2": (subspec, Coalesce("complement2", default="")),
        f"{prefixe}_service_distribution": (
            subspec,
            Coalesce("service_distribution", default=""),
        ),
        f"{prefixe}_code_postal": (subspec, Coalesce("code_postal", default="")),
        f"{prefixe}_commune": (subspec, Coalesce("nom_commune", default="")),
        f"{prefixe}_pays": (subspec, Coalesce("pays", default="")),
    }


def coordonnees(adresse):
    if adresse and adresse["longitude"] and adresse["latitude"]:
        return f"{adresse['longitude']},{adresse['latitude']}"


def ouverture(mairie):
    if "plage_ouverture" not in mairie:
        return None

    plages = []

    for p in mairie["plage_ouverture"]:
        deb_jour, fin_jour = p["nom_jour_debut"].lower(), p["nom_jour_fin"].lower()
        deb_hor1, fin_hor1 = p["valeur_heure_debut_1"], p["valeur_heure_fin_1"]
        deb_hor2, fin_hor2 = p["valeur_heure_debut_2"], p["valeur_heure_fin_2"]

        mention_jour = (
            deb_jour if deb_jour == fin_jour else f"du {deb_jour} au {fin_jour}"
        )

        mention_hor = f"{deb_hor1}-{fin_hor1}"
        if deb_hor2:
            mention_hor = f"{mention_hor} et {deb_hor2}-{fin_hor2}"

        plages.append(f"{mention_jour}, {mention_hor}")

    return "\n".join(plages)


contexte = S(
    adresse_physique=selection_adresse("Adresse"),
    adresse_postale=selection_adresse("Adresse postale"),
)


base_spec = {
    "id": "id",
    "code_departement": ("code_insee_commune", code_departement),
    "code_commune": "code_insee_commune",
    "siret": "siret",
    "nom": "nom",
    "emails": ("adresse_courriel", "\n".join),
    **champs_adresses("physique", S.adresse_physique),
    **champs_adresses(
        "postale",
        Coalesce(S.adresse_postale, S.adresse_physique, skip=None, default={}),
    ),
    "telephone": ("telephone", extraire_telephone),
    "coordonnees": (Coalesce(S.adresse_physique, default=None), coordonnees),
}


accessibilite_spec = {
    "type_accessibilite": Coalesce(
        S.adresse_physique["accessibilite"],
        default="",
    ),
    "details_accessibilite": Coalesce(
        S.adresse_physique["note_accessibilite"],
        default="",
    ),
    "ouverture": ouverture,
}


spec_mairies = (
    contexte,
    {
        **base_spec,
        **accessibilite_spec,
    },
)


spec_conseils_departementaux = (contexte, base_spec)

spec_conseils_regionaux = (contexte, base_spec)

spec_prefectures = (
    contexte,
    {
        **base_spec,
        **accessibilite_spec,
    },
)


FICHIERS = [
    ("mairies", spec_mairies),
    ("conseils_departementaux", spec_conseils_departementaux),
    ("conseils_regionaux", spec_conseils_regionaux),
    ("prefectures", spec_prefectures),
]


@click.command()
@click.argument(
    "src_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.argument(
    "dest_directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
)
def run(src_directory, dest_directory):
    dest_directory.mkdir(exist_ok=True, parents=True)

    for fichier, spec in FICHIERS:
        with iterate_ndjson(src_directory / f"{fichier}.json") as it:
            nettoyer_avec_spec(
                it,
                dest_directory / f"{fichier}.csv",
                spec,
                columns=list(spec[1].keys()),
            )


if __name__ == "__main__":
    run()
