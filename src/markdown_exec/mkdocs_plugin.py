"""This module contains an optional plugin for MkDocs."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, MutableMapping

from mkdocs.config import Config, config_options
from mkdocs.plugins import BasePlugin
from mkdocs.utils import write_file

from markdown_exec import formatter, formatters, validator
from markdown_exec.logger import patch_loggers
from markdown_exec.rendering import MarkdownConverter, markdown_config

if TYPE_CHECKING:
    from jinja2 import Environment
    from mkdocs.structure.files import Files

try:
    __import__("pygments_ansi_color")
except ImportError:
    ansi_ok = False
else:
    ansi_ok = True


class _LoggerAdapter(logging.LoggerAdapter):
    def __init__(self, prefix: str, logger: logging.Logger) -> None:
        super().__init__(logger, {})
        self.prefix = prefix

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
        return f"{self.prefix}: {msg}", kwargs


def _get_logger(name: str) -> _LoggerAdapter:
    logger = logging.getLogger(f"mkdocs.plugins.{name}")
    return _LoggerAdapter(name.split(".", 1)[0], logger)


patch_loggers(_get_logger)


class MarkdownExecPlugin(BasePlugin):
    """MkDocs plugin to easily enable custom fences for code blocks execution."""

    config_scheme = (("languages", config_options.Type(list, default=list(formatters.keys()))),)

    def on_config(self, config: Config, **kwargs: Any) -> Config:  # noqa: ARG002
        """Configure the plugin.

        Hook for the [`on_config` event](https://www.mkdocs.org/user-guide/plugins/#on_config).
        In this hook, we add custom fences for all the supported languages.

        We also save the Markdown extensions configuration
        into [`markdown_config`][markdown_exec.rendering.markdown_config].

        Arguments:
            config: The MkDocs config object.
            **kwargs: Additional arguments passed by MkDocs.

        Returns:
            The modified config.
        """
        self.languages = self.config["languages"]
        mdx_configs = config.setdefault("mdx_configs", {})
        superfences = mdx_configs.setdefault("pymdownx.superfences", {})
        custom_fences = superfences.setdefault("custom_fences", [])
        for language in self.languages:
            custom_fences.append(
                {
                    "name": language,
                    "class": language,
                    "validator": validator,
                    "format": formatter,
                },
            )
        markdown_config.save(config["markdown_extensions"], config["mdx_configs"])
        return config

    def on_env(self, env: Environment, *, config: Config, files: Files) -> Environment | None:  # noqa: ARG002,D102
        css_filename = "assets/_markdown_exec_ansi.css"
        css_content = Path(__file__).parent.joinpath("ansi.css").read_text()
        write_file(css_content.encode("utf-8"), os.path.join(config["site_dir"], css_filename))
        config["extra_css"].insert(0, css_filename)
        return env

    def on_post_build(self, *, config: Config) -> None:  # noqa: ARG002,D102
        MarkdownConverter.counter = 0
        markdown_config.reset()
