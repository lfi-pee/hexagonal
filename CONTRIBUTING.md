# Contribuer à Hexagonal

Ce document s'adresse aux personnes qui modifient les sources ou les traitements de
données. Pour simplement récupérer les données, voir le [README](README.md).

## Installation

```bash
uv sync --extra pipeline --group dev
uv run hexagonal pull --tout          # les sources brutes sont nécessaires, ~14 Go
```

### Sous macOS

Le téléchargement des données et les traitements en Python fonctionnent nativement.
Deux binaires manquent pour rejouer l'ensemble des traitements :

```bash
brew install p7zip node     # 7z pour deux traitements, node pour mapshaper
npm install -g mapshaper
```

**Attention au traitement `nettoyer-2020-municipales-1`.** macOS fournit la version BSD
de `sed`, qui n'interprète pas l'échappement `\t` là où la version GNU y voit une
tabulation. Ce traitement de [dvc.yaml](dvc.yaml) s'appuie dessus : sous macOS il
n'échoue pas, mais **produit un résultat différent de celui obtenu sous Linux**. Ne le
rejouez pas depuis macOS ; utilisez le conteneur de développement.

Les scripts de [src/scripts/](src/scripts/) n'utilisent aucune fonctionnalité
postérieure à bash 3.2 : ils tournent avec le bash livré par Apple.

### Sous Windows

Le téléchargement des données fonctionne nativement. **En revanche, huit traitements sur
quarante-cinq ne peuvent pas tourner sous Windows** : cinq appellent les scripts de
[src/scripts/](src/scripts/), écrits en `bash`, deux dépendent du binaire `7z`, et le
dernier appelle directement `mapshaper`.

### Conteneur de développement

Sur les deux systèmes, le plus simple est d'ouvrir le dépôt dans un conteneur de
développement : il fournit Linux, bash, node, `mapshaper`, `p7zip` et le `sed` GNU déjà
installés, et les quarante-cinq traitements y tournent.

- **GitHub Codespaces** : bouton « Code » → « Codespaces » → « Create codespace ». Tout
  se passe dans le navigateur, rien à installer sur la machine.
- **VS Code en local** : extension « Dev Containers », puis « Reopen in Container ».

La configuration se trouve dans [.devcontainer/](.devcontainer/).

## Gestion des données sources

L'ensemble des données sources sont présentes dans le dossier `data/01_raw`. Les
fichiers sont organisés dans des dossiers correspondant aux éditeurs des données.

L'ensemble des fichiers sources est versionné avec DVC et non directement avec git. En
effet, git ne gère pas correctement les fichiers volumineux. En pratique, cela signifie
que les jeux de données ne sont jamais ajoutés directement dans le dépôt git (et le
fichier `.gitignore` exclut d'ailleurs la plupart des extensions correspondant à des
jeux de données). À chaque jeu de données correspond un fichier `.dvc` généré par DVC.
C'est ce dernier qui doit être ajouté dans git.

### Ajouter un jeu de données source

La démarche est différente selon qu'il s'agisse d'un jeu de données disponible sur
internet, ou non (par exemple s'il s'agit d'un jeu de données produit par la France
insoumise).

Dans les deux cas, la commande à utiliser crée un fichier `.dvc` qu'il faut
impérativement versionner avec git. Le fichier lui-même ne doit pas être versionné.

#### Depuis une URL externe

```bash
uv run dvc import-url <url> data/01_raw/<editeur>/<nom du fichier>
```

#### Sans URL externe

Le fichier doit être enregistré dans le dossier `data/01_raw/<editeur>/<nom fichier>`.
La commande `uv run dvc add data/01_raw/<editeur>/<nom fichier>` permet ensuite de
générer le fichier `.dvc`.

### Mettre à jour une source existante

Les sources ne sont pas mises à jour automatiquement. Pour les mises à jour, il y a
trois cas de figure.

#### Il n'y a pas d'URL externe

Il faut alors éditer le fichier directement, ou le remplacer par la nouvelle version.
Une fois que c'est fait, la commande `uv run dvc add` permet de mettre à jour le fichier
`.dvc` correspondant.

#### L'URL de la source ne change pas

Pour certains fichiers, l'URL de téléchargement renvoie un état actuel de la source de
données qui peut donc changer à n'importe quel moment. C'est par exemple le cas pour les
données de l'Assemblée nationale. Il suffit alors de faire tourner la commande :

```bash
uv run dvc update <chemin du fichier dans data/01_raw>
```

Cette commande interroge le serveur d'origine, télécharge la nouvelle version le cas
échéant, et met à jour le fichier `.dvc`.

#### L'URL de la source change

Pour d'autres fichiers, l'URL correspond à une édition particulière du fichier, et il
faut donc la changer pour mettre à jour le fichier. C'est par exemple le cas du COG.

```bash
uv run dvc import-url <nouvelle url> <chemin complet du fichier à mettre à jour>
```

## Traitements des données

Les traitements de données sont définis dans le fichier `dvc.yaml`
([voir la documentation de DVC](https://dvc.org/doc/user-guide/pipelines/defining-pipelines)).

### Reproduire les traitements de données

```bash
uv run hexagonal repro                  # tous les traitements qui ne sont plus à jour
uv run hexagonal repro <nom du stage>   # un seul traitement
```

S'il y en avait, le fichier `dvc.lock` est mis à jour en conséquence. Si c'est le cas,
il est impératif :

1. de versionner `dvc.lock` ;
2. de pousser les nouvelles versions des fichiers.

### Conventions à suivre pour ajouter de nouveaux traitements

De préférence, les traitements de données doivent être écrits en Python. Si nécessaire,
il est toutefois possible d'ajouter des traitements sous la forme de scripts bash.

#### Écrire un traitement de données en Python

1. Chaque traitement doit être un module Python exécutable dans le paquet `hexagonal` ;
   le fichier source doit donc se trouver dans le dossier `src/hexagonal`.
2. Sauf exception, le module exécutable doit prendre en argument les chemins vers les
   fichiers sources et les fichiers destination plutôt que d'accéder aux fichiers avec
   un chemin en dur. Il est possible d'utiliser la bibliothèque `click` pour faciliter
   le traitement des arguments.

#### Écrire un traitement de données en bash

1. Les scripts de traitements doivent se trouver dans le dossier `src/scripts`.
2. Sauf exception, le script doit prendre en argument les chemins vers les fichiers
   sources et les fichiers destination plutôt que d'accéder aux fichiers avec un chemin
   en dur, dans la mesure du possible.
3. Les scripts ne peuvent utiliser de dépendances externes qu'en cas de nécessité.

Un traitement écrit en bash ne tournera pas sous Windows : privilégiez Python quand
c'est possible.

#### Ajouter le traitement dans `dvc.yaml`

1. Donner un nom explicite au traitement, en s'assurant qu'il soit bien unique.
2. La liste des dépendances doit inclure aussi bien la source du traitement que les jeux
   de données utilisés.
3. Les variables `${src}`, `${raw}`, `${clean}` et `${main}` doivent être utilisées
   plutôt que les chemins complets.
4. Pour un traitement en python, le script doit être invoqué avec la syntaxe
   `${python} <nom.du.module>`.

## Documentation

L'ensemble des sources et des données produites sont documentés dans un fichier portant
le même nom que le fichier documenté, suivi de l'extension `.toml`.

```bash
uv run hexagonal doc
```

Cette commande crée une version initiale des fichiers `.toml` manquants, met à jour la
liste des dépendances à partir des pipelines DVC, puis régénère
[sources.md](sources.md) et [productions.md](productions.md).

### Documenter les sources

Pour une source, les propriétés suivantes peuvent être renseignées :

| Propriété | Description                                 |
|-----------|---------------------------------------------|
| `nom` | Une désignation complète du jeu de données  |
| `description` | Une description aussi complète que possible |
| `editeur` | L'éditeur du jeu de données                 |
| `date` | La date du jeu de données, si pertinent     |
| `info_url` | Une URL vers une documentation externe      |

### Documenter les productions

| Propriété     | Description                                         |
|---------------|-----------------------------------------------------|
| `nom`         | Une désignation complète du jeu de données          |
| `description` | Une description aussi complète que possible         |
| `section`     | La catégorie à laquelle appartient cette production |

Par ailleurs, pour les fichiers de type tabulaire (CSV ou parquet), il faut documenter
les différentes colonnes avec les propriétés suivantes :

| Propriété     | Description                                              |
|---------------|----------------------------------------------------------|
| `type`        | Le type de données de la colonne                         |
| `description` | Une description plus précise, lorsqu'elle est nécessaire |
| `nullable`    | Si la colonne admet des valeurs nulles.                  |

## Publier les données (mainteneurs)

C'est la **seule** étape du projet qui nécessite un accès AWS. Il faut me contacter pour
obtenir des droits en écriture sur le bucket S3, puis configurer un profil `hexagonal`
dans `~/.aws/credentials`.

```bash
uv sync --extra maintainer
uv run hexagonal push
```

Cette commande pousse le cache DVC vers S3, régénère la documentation, et réécrit les
en-têtes HTTP `Content-Type` et `Content-Disposition` des objets afin que les liens de
[sources.md](sources.md) et [productions.md](productions.md) se téléchargent avec le bon
nom et le bon format.
