import os
import sys

def _jupyter_nbextension_paths():
    paths = []

    if sys.platform != 'win32':
        paths.append(
            dict(
                section="tree",
                src=os.path.join('nbextensions', 'nbexchange_history'),
                dest="nbexchange_history",
                require="nbexchange_history/main"
            )
        )

    return paths

def _jupyter_server_extension_paths():
    paths = [
        dict(module="nbexchange.server_extensions.exchange_history"),
    ]

    if sys.platform != 'win32':
        paths.append(dict(module="nbexchange.server_extensions.exchange_history"))

    return paths