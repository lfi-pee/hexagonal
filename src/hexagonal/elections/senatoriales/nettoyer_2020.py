import click
import polars as pl

from hexagonal.codes import CORRESPONDANCE_CODE_DEPARTEMENT
from hexagonal.elections.algorithmes_electoraux import proportionnelle_dhondt
from hexagonal.elections.senatoriales.types import TypeElectionSenatoriale
from hexagonal.utils.polars import polars_large_to_long

PRENOM_RE = r"\p{Uppercase Letter}\p{Lowercase Letter}*"
PRENOMS_RE = rf"(?<prenom>{PRENOM_RE}(?:[ '-]{PRENOM_RE})*)"

NOM_RE = r"[\p{Uppercase Letter}()]+"
NOMS_RE = rf"(?<nom>{NOM_RE}(?: ?[ '-] ?{NOM_RE})*)"

CIVILITE_RE = r"(?<civilite>M.|Mme)"

TDL_RE = rf"^{CIVILITE_RE} {NOMS_RE} {PRENOMS_RE}$"


COLONNES_FIXES = {
    "type_scrutin": None,
    "code_departement": pl.String(),
    "nom_departement": None,
    "tour": None,
    "inscrits": pl.Int32(),
    "abstentions": pl.Int32(),
    "part_abstentions": None,
    "votants": pl.Int32(),
    "part_votants": None,
    "blancs": pl.Int32(),
    "part_blancs": None,
    "part_blancs_votants": None,
    "nuls": pl.Int32(),
    "part_nuls": None,
    "part_nuls_votants": None,
    "exprimes": pl.Int32(),
    "part_exprimes": None,
    "part_exprimes_votants": None,
}

COLONNES_VARIABLES_MAJ = {
    "numero_depot": pl.Int16(),
    "nuance": pl.String(),
    "sexe": pl.String(),
    "nom": pl.String(),
    "prenom": pl.String(),
    "voix": pl.Int32(),
    "part_voix_inscrits": None,
    "part_voix_exprimes": None,
}

COLONNES_VARIABLES_PROP = {
    "numero_depot": pl.Int16(),
    "nuance": pl.String(),
    "libelle_liste": pl.String(),
    "nom": pl.String(),
    "voix": pl.Int32(),
    "part_voix_inscrits": None,
    "part_voix_exprimes": None,
}

ORDRE_FINAL = [
    "code_departement",
    "type_scrutin",
    "inscrits",
    "abstentions",
    "votants",
    "blancs",
    "nuls",
    "exprimes",
    "numero_depot",
    "nuance",
    "libelle_liste",
    "nom",
    "prenom",
    "sexe",
    "voix",
    "elus",
]

NORMALISER_CODE_DEPARTEMENT = (
    pl.col("code_departement")
    .str.zfill(2)
    .replace(
        list(CORRESPONDANCE_CODE_DEPARTEMENT.keys()),
        list(CORRESPONDANCE_CODE_DEPARTEMENT.values()),
    )
)


def pretraiter(df):
    return df.with_columns(NORMALISER_CODE_DEPARTEMENT).filter(
        pl.col("numero_depot").is_not_null()
    )


@click.command()
@click.argument("fichier", type=click.Path(exists=True, readable=True))
@click.argument("nombre_senateurs", type=click.Path(exists=True, readable=True))
@click.argument("resultats", type=click.Path(writable=True, dir_okay=False))
def main(fichier, nombre_senateurs, resultats):
    nombre_senateurs = pl.read_csv(nombre_senateurs).select(
        "code_departement", pl.col("nombre").alias("nombre_senateurs")
    )

    maj_t1 = pl.read_excel(
        fichier, sheet_name="MAJ 1", read_options={"header_row": None, "skip_rows": 2}
    )
    maj_t1 = pretraiter(
        polars_large_to_long(maj_t1, COLONNES_FIXES, COLONNES_VARIABLES_MAJ)
    )
    maj_t1 = maj_t1.with_columns(
        type_scrutin=pl.lit("MAJORITAIRE_T1", dtype=TypeElectionSenatoriale),
        elus=(
            (pl.col("voix") / pl.col("exprimes") >= 0.5)
            & (pl.col("voix") / pl.col("inscrits") >= 0.25)
        ).cast(pl.Int16),
    )
    elus_t1 = maj_t1.group_by("code_departement").agg(
        pl.col("elus").sum().alias("elus_t1")
    )

    maj_t2 = pl.read_excel(
        fichier, sheet_name="MAJ 2", read_options={"header_row": None, "skip_rows": 2}
    )
    maj_t2 = pretraiter(
        polars_large_to_long(maj_t2, COLONNES_FIXES, COLONNES_VARIABLES_MAJ)
    )
    maj_t2 = (
        maj_t2.with_columns(
            type_scrutin=pl.lit("MAJORITAIRE_T2", dtype=TypeElectionSenatoriale),
        )
        .join(
            nombre_senateurs,
            on=["code_departement"],
            how="left",
        )
        .join(elus_t1, on=["code_departement"], how="left")
        .with_columns(
            elus=(
                pl.col("voix").rank(descending=True).over("code_departement")
                <= pl.col("nombre_senateurs") - pl.col("elus_t1")
            ).cast(pl.Int16)
        )
        .select(
            pl.all().exclude(["nombre_senateurs", "elus_t1"]),
        )
    )

    prop = pl.read_excel(
        fichier, sheet_name="PROP", read_options={"header_row": None, "skip_rows": 2}
    )
    prop = pretraiter(
        polars_large_to_long(prop, COLONNES_FIXES, COLONNES_VARIABLES_PROP)
    )
    prop = prop.with_columns(
        pl.lit("PROPORTIONNELLE", dtype=TypeElectionSenatoriale).alias("type_scrutin"),
        pl.col("nom").str.extract_groups(TDL_RE),
    ).with_columns(
        prenom=pl.col("nom").struct.field("prenom"),
        nom=pl.col("nom").struct.field("nom"),
        sexe=pl.col("nom")
        .struct.field("civilite")
        .replace_strict(["M.", "Mme"], ["M", "F"]),
    )

    prop = (
        prop.join(nombre_senateurs, on="code_departement", how="left")
        .group_by(["code_departement"])
        .map_groups(
            lambda g: g.with_columns(
                elus=proportionnelle_dhondt(
                    g["voix"].to_numpy(), g["nombre_senateurs"][0]
                )
            )
        )
        .select(pl.all().exclude("nombre_senateurs"))
    )

    res = (
        pl.concat([maj_t1, maj_t2, prop], how="diagonal_relaxed")
        .sort(["code_departement", "type_scrutin", "numero_depot"])
        .select(ORDRE_FINAL)
    )

    res.write_parquet(resultats)


if __name__ == "__main__":
    main()
