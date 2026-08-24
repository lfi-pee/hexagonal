import click
from dvc.repo import Repo

from hexagonal.documentation.build import build as build_doc
from hexagonal.files.rewrite_s3_headers import rewrite_metadata
from hexagonal.files.spec import load_all_specs


@click.command()
def release():
    spec = load_all_specs()
    r = Repo(".")
    r.push(remote="s3")
    build_doc(spec)
    rewrite_metadata()


if __name__ == "__main__":
    release()
