from pathlib import Path
from typing import Any

from cookiecutter.generate import generate_files

from . import utils
from .utils.iohelper import AltTemporaryDirectory


def create(
    template_git_url: str,
    output_dir: Path = Path("."),
    config_file: Path | None = None,
    default_config: bool = False,
    extra_context: dict[str, Any] | None = None,
    extra_context_file: Path | None = None,
    no_input: bool = True,
    directory: str | None = None,
    checkout: str | None = None,
    overwrite_if_exists: bool = False,
    skip: list[str] | None = None,
) -> Path:
    """Expand a Git based Cookiecutter template into a new project on disk."""
    template_git_url = utils.cookiecutter.resolve_template_url(template_git_url)
    with AltTemporaryDirectory(directory) as cookiecutter_template_dir_str:
        cookiecutter_template_dir = Path(cookiecutter_template_dir_str)
        with utils.cookiecutter.get_cookiecutter_repo(
            template_git_url, cookiecutter_template_dir, checkout
        ) as repo:
            last_commit = repo.head.object.hexsha

            if directory:
                cookiecutter_template_dir = cookiecutter_template_dir / directory

            if extra_context_file:
                extra_context = utils.cookiecutter.get_extra_context_from_file(
                    extra_context_file
                )
            context = utils.cookiecutter.generate_cookiecutter_context(
                template_git_url,
                cookiecutter_template_dir,
                config_file,
                default_config,
                extra_context,
                no_input,
            )

        project_dir = Path(
            generate_files(
                repo_dir=cookiecutter_template_dir,
                context=context,
                overwrite_if_exists=overwrite_if_exists,
                output_dir=str(output_dir),
            )
        )

        cruft_content: dict[str, Any] = {
            "template": template_git_url,
            "commit": last_commit,
            "checkout": checkout,
            "context": context,
            "directory": directory,
        }

        if skip:
            cruft_content["skip"] = skip

        # After generating the project - save the cruft state
        # into the cruft file.
        (project_dir / ".cruft.json").write_text(utils.cruft.json_dumps(cruft_content))

        return project_dir
