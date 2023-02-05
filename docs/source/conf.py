# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
import datetime

from sphinx_pyproject import SphinxConfig

sys.path.append(os.path.abspath('./src'))
sys.path.append(os.path.abspath('../../src'))

config = SphinxConfig("../../pyproject.toml")

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

project = config.name
author = config.author
version = config.version
project_copyright = f"{datetime.date.today().year}, {config.author}"

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode', 'sphinx_mdinclude', 'sphinx_rtd_theme']

templates_path = ['_templates']
smartquotes = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
