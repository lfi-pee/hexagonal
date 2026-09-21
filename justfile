# Ces recettes ne sont qu'un raccourci : tout est accessible via `uv run hexagonal`.

pull:
  uv run hexagonal pull

repro:
  uv run hexagonal repro

doc:
  uv run hexagonal doc

push:
  uv run hexagonal push

release: repro doc push
