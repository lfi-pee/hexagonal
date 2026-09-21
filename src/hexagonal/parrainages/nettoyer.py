import csv
import re
import sys

from glom import Iter, glom

from hexagonal.utils.clean import date_francaise_vers_iso

MANDATS = {
    "député": "Députée?",
    "sénateur": "Sénat(eur|rice)",
    "député européen": "Représentante? française? au Parlement européen",
    "conseiller régional": "Conseill(er|ère) régionale?",
    "conseiller départemental": "Conseill(er|ère) départementale?",
    "président EPCI": "Présidente? d'un EPCI à fiscalité propre",
    "maire": "Maire",
    "maire délégué": "Maire déléguée? d'une commune associée ou d'une commune déléguée",
    "membre assemblée outremer": "Membre d'une assemblée d'une collectivité territoriale d'outre-mer à statut particulier",  # noqa: E501
    "membre assemblée corse": "Membre de l'Assemblée de Corse",
    "président Polynésie française": "Présidente? de la Polynésie française",
    "président Nouvelle-Calédonie": "Présidente? du gouvernement de la Nouvelle-Calédonie",  # noqa: E501
    "président conseil exécutif Martinique": "Présidente? du Conseil exécutif de Martinique",
    "conseiller Paris": "Conseill(er|ère) de Paris",
    "conseiller métropole Lyon": "Conseill(er|ère) métropolitaine? de Lyon",
    "maire arrondissement PLM": "Maire d'arrondissement",
    "conseiller AFE": "Conseill(er|ère) à l'Assemblée des Français de l'étranger",
    "président conseil consulaire": "Présidente? du conseil consulaire",
}

MANDATS = {k: re.compile(f"^{v}$") for k, v in MANDATS.items()}


def normaliser_mandat(mandat):
    return next(k for k, v in MANDATS.items() if v.match(mandat))


spec_parrainages = {
    "mandat": ("Mandat", normaliser_mandat),
    "nom": "Nom",
    "prenom": "Prénom",
    "sexe": ("Civilité", {"M.": "M", "Mme": "F"}.get),
    "circonscription_mandat": "Circonscription",
    "departement_mandat": "Département",
    "candidat": "Candidat",
    "date_publication": ("Date de publication", date_francaise_vers_iso),
}


def extraire(in_path, out_path):
    with (
        open(in_path, "r", newline="") as in_fd,
        open(out_path, "w", newline="") as out_fd,
    ):
        r = csv.DictReader(in_fd, delimiter=";")
        w = csv.DictWriter(out_fd, fieldnames=list(spec_parrainages.keys()))

        w.writeheader()
        w.writerows(glom(r, Iter(spec_parrainages)))


def run():
    in_path, out_path = sys.argv[1:]
    extraire(in_path, out_path)


if __name__ == "__main__":
    run()
