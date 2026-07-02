import marko
from jinja2 import Environment, PackageLoader, select_autoescape
from marko.block import Heading
from marko.md_renderer import MarkdownRenderer
from rich.markdown import Heading
from slugify import slugify

from hexagonal.files.dvc_files import get_dvc_files
from hexagonal.files.spec import SourceSpec, load_all_specs


def slugify_filter(value):
    return slugify(value)


def url(path, specs):
    file = specs[path]
    base_file = "sources.md" if isinstance(file, SourceSpec) else "productions.md"
    fragment = str(path)
    return file.nom, f"{base_file}#{fragment}"


def prepare_deps(deps, specs):
    full_deps = [d for d in deps if d.path in specs]
    temp_deps = [d for d in deps if d.path not in specs]

    res = {url(d.path, specs): prepare_deps(d.deps, specs) for d in full_deps}
    for d in temp_deps:
        res.update(prepare_deps(d.deps, specs))

    return res


md = marko.Markdown(renderer=MarkdownRenderer)


def fix_titles(text):
    ds = md.parse(text)

    for c in ds.children:
        match c:
            case Heading():
                c.level += 3

    return md.render(ds)


def build(specs):
    env = Environment(
        loader=PackageLoader("hexagonal.documentation", "templates"),
        autoescape=select_autoescape(enabled_extensions=("html", "htm", "xml", "md")),
    )
    env.filters["slugify"] = slugify_filter

    dvc_files = get_dvc_files()

    sources_template = env.get_template("sources.md")
    productions_template = env.get_template("productions.md")

    sources = [f for f in specs.values() if isinstance(f, SourceSpec)]
    editeurs: dict[str, list[dict]] = {}
    for source in sources:
        file = dvc_files[source.path]
        props = source.props()
        for url in file.urls:
            props["URL d'origine"] = url

        props["URL de téléchargement"] = file.http_url

        source_dict = {
            "path": source.path,
            "nom": source.nom,
            "description": source.description,
            "props": props,
        }

        editeurs.setdefault(source.editeur, []).append(source_dict)

    with open("sources.md", "w") as fd:
        fd.write(sources_template.render(editeurs=sorted(editeurs.items())))

    productions = [f for f in specs.values() if not isinstance(f, SourceSpec)]
    sections = {}
    for prod in productions:
        file = dvc_files[prod.path]
        props = prod.props()
        props["URL de téléchargement"] = file.http_url

        prod_dict = {
            "path": prod.path,
            "nom": prod.nom,
            "description": fix_titles(prod.description),
            "props": props,
            "deps": prepare_deps(file.deps, specs),
            "colonnes": prod.colonnes,
        }

        sections.setdefault(prod.section, []).append(prod_dict)

    with open("productions.md", "w") as fd:
        fd.write(
            productions_template.render(
                sections=sorted(sections.items()), dvc_files=dvc_files
            ),
        )


if __name__ == "__main__":
    build(load_all_specs())
