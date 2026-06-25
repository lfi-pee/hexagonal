release: repro push scaffold build_doc

# Commandes DVC
pull:
  uv run dvc pull

push:
  uv run dvc push -r s3
  uv run src/hexagonal/files/rewrite_s3_headers.py

repro:
  uv run dvc repro --all-pipelines --recursive

# Crée les fichiers de documentation sources et productions
scaffold:
  uv run src/hexagonal/files/update_specs.py

build_doc:
  uv run src/hexagonal/documentation/build.py
