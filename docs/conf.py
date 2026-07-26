from __future__ import annotations

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Mersal"
copyright = "2023, Abdulhaq Emhemmed"
author = "Abdulhaq Emhemmed"
release = "0.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinxcontrib.bibtex",
    "sphinxcontrib.mermaid",
    "sphinx_design",
    "sphinx_paramlinks",
    "sphinx_togglebutton",
]

templates_path = ["_templates"]
exclude_patterns = []

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
}

napoleon_google_docstring = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_attr_annotations = True

autoclass_content = "class"
autodoc_class_signature = "separated"
autodoc_member_order = "alphabetical"
autodoc_default_options = {
    "special-members": "__init__",
    "show-inheritance": True,
    "members": True,
}
autodoc_typehints_format = "short"

autosectionlabel_prefix_document = True

nitpicky = True
nitpick_ignore: list[tuple[str, str]] = [
    # TypeVars and TypeAliases - never resolvable as py:class targets
    ("py:class", "MessageT"),
    ("py:class", "MessageHandler"),
    ("py:class", "HandlerFactory"),
    ("py:class", "mersal.unit_of_work.config.UnitOfWorkT"),
    # autodoc_typehints_format="short" renders annotations without a module
    # prefix, which nitpicky can't resolve without a `py:module` context
    ("py:class", "InMemoryNetwork"),
    ("py:class", "AsyncSession"),
    ("py:class", "async_sessionmaker"),
    # TODO: no reference/*.rst page documents these modules yet
    ("py:class", "mersal.transport.file_system.FileSystemTransport"),
    ("py:class", "mersal.transport.base_transport.BaseTransport"),
    ("py:class", "mersal.pipeline.pipeline_invoker.PipelineInvoker"),
    ("py:class", "mersal.pipeline.message_context.MessageContext"),
    ("py:class", "pipeline.MessageContext"),
    ("py:class", "mersal.pipeline.send.set_default_headers_step.MessageIdGenerator"),
    ("py:class", "mersal.routing.router.Router"),
    ("py:class", "mersal.routing.default.config.DefaultRouterRegistrationConfig"),
    ("py:class", "mersal.workers.worker_factory.WorkerFactory"),
    ("py:class", "mersal.retry.RetryStrategySettings"),
    ("py:class", "mersal.retry.retry_strategy_settings.RetryStrategySettings"),
    ("py:class", "mersal.retry.error_tracking.error_tracker.ErrorTracker"),
    ("py:class", "mersal.retry.error_handling.error_handler.ErrorHandler"),
    ("py:class", "mersal.retry.fail_fast.fail_fast_checker.FailFastChecker"),
    ("py:class", "mersal.plugins.plugin.Plugin"),
    ("py:class", "mersal.sagas.config.SagaConfig"),
    ("py:class", "mersal.sagas.saga_storage.SagaStorage"),
    ("py:class", "mersal.serialization.serializers.Serializer"),
    ("py:class", "mersal.logging.config.LoggingConfig"),
    ("py:class", "mersal.logging.logger.Logger"),
    ("py:class", "mersal.messages.message_headers.MessageHeaders"),
    ("py:class", "mersal.messages.transport_message.TransportMessage"),
    ("py:class", "mersal.types.Empty"),
]

bibtex_bibfiles = ["refs.bib"]
# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
