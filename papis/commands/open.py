"""
The open command is a very important command in the papis workflow.
With it you can open documents, folders or marks.

Marks
^^^^^

One of special things about this command is the possibility of
creating marks for documents. As you would imagine, it is in general
difficult to create marks for any kind of data. For instance,
if our library consists of pdf files and epub files for instance,
we would like to define bookmarks in order to go back to them at
some later point.

How you define marks can be customized through the marks configuration
settings :ref:`here <marks-options>`.
The default way of doing it is just by defining a ``marks`` list in a document.
Let us look at a concrete example:

.. code:: yaml

    author: Isaiah Shavitt, Rodney J. Bartlett
    edition: '1'
    files: [book.pdf]
    isbn: 052181832X,9780521818322

    marks:
    - {name: Intermediates definition, value: 344}
    - {name: EOM equations, value: 455}

    publisher: Cambridge University Press
    ref: book:293288
    series: Cambridge Molecular Science
    title: 'Many-Body Methods in Chemistry and Physics'
    type: book
    year: '2009'

This book has defined two marks. Each mark has a name and a value.
If you tell the open command to open marks, then it will look for
the marks and open the value (page number). This is the default behaviour,
however if you go to the :ref:`configuration <marks-options>`
you'll see that you can change the convention to what it suits you.


Examples
^^^^^^^^
- Open a pdf file linked to a document matching the string ``bohm``

    ::

        papis open bohm

- Open the folder where this last document is stored

    ::

        papis open -d bohm

  Please notice that the file browser used will be also related to
  the :ref:`file-browser setting <config-settings-file-browser>`.

- Open a mark defined in the info file

    ::

        papis open --mark bohm


Cli
^^^
.. click:: papis.commands.open:cli
    :prog: papis open
"""
import papis
import papis.api
import papis.pick
import papis.utils
import papis.config
import papis.cli
import papis.database
import click
import logging
from papis.document import from_folder, Document, from_data
import papis.strings
from typing import Optional


def run(document: Document, opener: Optional[str] = None,
        folder: bool = False,
        mark: bool = False) -> None:
    logger = logging.getLogger('open:run')
    if opener is not None:
        papis.config.set("opentool", opener)

    if folder:
        # Open directory
        papis.api.open_dir(document.get_main_folder())
    else:
        if mark:
            logger.debug("Getting document's marks")
            marks = document[papis.config.get("mark-key-name")]
            if marks:
                logger.info("Picking marks")
                _mark_fmt = papis.config.get("mark-header-format")
                _mark_name = papis.config.get("mark-format-name")
                _mark_opener = papis.config.get("mark-opener-format")
                if not _mark_fmt:
                    raise Exception("No mark header format")
                if not _mark_name:
                    raise Exception("No mark name format")
                mark = papis.api.pick(
                    marks,
                    dict(
                        header_filter=lambda x: papis.utils.format_doc(
                            _mark_fmt, x, key=_mark_name),
                        match_filter=lambda x: papis.utils.format_doc(
                            _mark_fmt, x, key=_mark_name)))
                if mark:
                    if not _mark_opener:
                        raise Exception("mark-opener-format not set")
                    opener = papis.utils.format_doc(
                        _mark_opener, from_data(mark), key=_mark_name)
                    logger.info("Setting opener to '{0}'".format(opener))
                    papis.config.set("opentool", opener)
        files = document.get_files()
        if len(files) == 0:
            logger.error("The document chosen has no files attached")
            return
        file_to_open = papis.api.pick(
            files,
            pick_config=dict(
                header_filter=lambda x: x.replace(
                    document.get_main_folder(), "")))
        papis.api.open_file(file_to_open, wait=False)


@click.command("open")
@click.help_option('-h', '--help')
@papis.cli.query_option()
@papis.cli.sort_option()
@papis.cli.doc_folder_option()
@papis.cli.all_option()
@click.option(
    "--tool",
    help="Tool for opening the file (opentool)",
    default="")
@click.option(
    "-d",
    "--dir",
    "folder",
    help="Open directory",
    default=False,
    is_flag=True)
@click.option(
    "-m",
    "--mark/--no-mark",
    help="Open mark",
    default=lambda: True if papis.config.get('open-mark') else False)
def cli(query: str, doc_folder: str, tool: str, folder: bool,
        sort_field: Optional[str], sort_reverse: bool, _all: bool,
        mark: bool) -> None:
    """Open document from a given library"""
    if tool:
        papis.config.set("opentool", tool)
    logger = logging.getLogger('cli:run')

    if doc_folder:
        documents = [from_folder(doc_folder)]
    else:
        documents = papis.database.get().query(query)

    if sort_field:
        documents = papis.document.sort(documents, sort_field, sort_reverse)

    if not documents:
        logger.warning(papis.strings.no_documents_retrieved_message)
        return

    if not _all:
        documents = [papis.pick.pick_doc(documents)]
        documents = [d for d in documents if d]

    for document in documents:
        run(document, folder=folder, mark=mark)
