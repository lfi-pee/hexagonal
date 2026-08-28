# Hexagonal

Ce dépôt agrège l'information électorale, administrative et géographique française
nécessaire pour faciliter l'analyse électorale.

- [Liste des fichiers mis à disposition](productions.md)
- [Liste des sources utilisées](sources.md)

Les données sont hébergées publiquement. **Aucun compte, aucune inscription et aucune
clé d'accès ne sont nécessaires pour les télécharger.**

---

## 1. Je veux juste les données

Ouvrez [productions.md](productions.md) et cliquez sur le fichier qui vous intéresse. Il
se télécharge directement, avec le bon nom et le bon format. Rien à installer.

En ligne de commande, sans rien installer non plus (`curl` est présent d'origine sur
Linux, macOS et Windows 10 ou plus récent) :

```bash
curl -OJ <URL du fichier copiée depuis productions.md>
```

## 2. Je veux travailler sur le dépôt

Deux outils à installer une seule fois. `uv` télécharge lui-même la bonne version de
Python : vous n'avez pas besoin d'installer Python.

**macOS**

```bash
xcode-select --install                              # fournit git
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Homebrew n'est pas nécessaire : `xcode-select --install` suffit à obtenir git.

**Linux**

```bash
sudo apt install git                                # ou dnf install git, pacman -S git
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**

```powershell
winget install --id Git.Git -e
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Ensuite, les mêmes commandes sur tous les systèmes :

```bash
git clone https://github.com/lfi-pee/hexagonal.git
cd hexagonal
uv run hexagonal pull
```

`uv run` installe les dépendances au premier appel (trois paquets, quelques secondes).
`hexagonal pull` récupère les données prêtes à l'emploi, soit environ 350 Mo.

### Les commandes

| Commande | Effet |
|---|---|
| `uv run hexagonal list` | Liste les jeux de données et indique ceux déjà présents |
| `uv run hexagonal list --tout` | Idem, sources brutes comprises |
| `uv run hexagonal pull` | Télécharge les productions (`02_clean` et `03_main`), ~350 Mo |
| `uv run hexagonal pull --tout` | Télécharge tout, sources brutes comprises, ~14 Go |
| `uv run hexagonal pull data/03_main/elections` | Télécharge seulement ce qui correspond |

Les téléchargements sont incrémentaux : un fichier déjà présent n'est jamais retéléchargé.

### Lire les données en Python

```bash
uv sync --extra pipeline
```

L'argument est le chemin du fichier dans `data`. L'exemple ci-dessous ouvre les adresses
des conseils régionaux, mais **n'importe quel autre jeu de données s'ouvre de la même
façon** :

```python
from hexagonal.files.spec import get_polars_dataframe

# Un exemple parmi d'autres : remplacez le chemin par celui du fichier voulu.
df = get_polars_dataframe("data/02_clean/annuaire/conseils_regionaux.csv")
```

Les fichiers sont rangés par étape de traitement — `data/01_raw/` pour les sources
brutes, `data/02_clean/` pour les données nettoyées et `data/03_main/` pour les données
prêtes à l'emploi (voir [Organisation du projet](#organisation-du-projet)). Pour trouver
le chemin qui vous intéresse :

- `uv run hexagonal list` en donne la liste complète, avec les tailles ;
- [productions.md](productions.md) les décrit un par un.

Les types de colonnes sont appliqués automatiquement à partir de la documentation du
jeu de données. `get_pandas_dataframe` fonctionne de la même manière.

## 3. Je veux modifier les traitements de données

Voir [CONTRIBUTING.md](CONTRIBUTING.md) : ajout et mise à jour des sources, écriture des
traitements, documentation et publication.

---

## Organisation du projet

Les données sont stockées dans le dossier `data` avec les sous-dossiers suivants :

- `01_raw/` : données brutes (téléchargées)
- `02_clean/` : données nettoyées (formatées, filtrées)
- `03_main/` : données prêtes à l'emploi par étude (_feature engineering_, jointures,
  agrégats, etc.)

Chaque jeu de données est accompagné d'un fichier `.toml` qui le documente. Les fichiers
de données eux-mêmes ne sont pas versionnés dans git : ils sont suivis par
[DVC](https://dvc.org), via des fichiers `.dvc` et le fichier `dvc.lock`, qui sont eux
versionnés.

## Environnements

Le projet définit trois niveaux d'installation, du plus léger au plus complet :

| Installation | Contenu | Pour |
|---|---|---|
| `uv sync` | `click`, `pyyaml` | Télécharger et lister les données |
| `uv sync --extra pipeline` | pandas, polars, geopandas, dvc… | Lire les données, rejouer les traitements |
| `uv sync --extra maintainer` | + boto3, dvc-s3 | Publier les données (mainteneurs) |

Ajoutez `--group dev` pour les outils de développement (pytest, ruff, jupyterlab).
