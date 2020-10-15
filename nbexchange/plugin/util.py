import os
import re
from collections import defaultdict

from nbgrader.utils import full_split


def contains_format(string):
    """
    Checks if a string has format markers
    :param string: the string to check
    :return: true if the string contains any {format} markers.
    """
    return re.search("([^{]|^){[^}]+}", string) is not None


def format_keys(string):
    """
    Find all format keys in a format string
    :param string: the string to look in
    :return: all format keys found in the format string
    """
    return [x.group(2) for x in re.finditer("([^{]|^){([^}]+)}", string)]


def maybe_format(string, **values):
    """
    This function applies all formats to a string that are available, leaving all other format strings in.

    :param string: the string to format
    :param values: the kwargs representing the values to format the string with
    :return: partially formatted string
    """
    try:
        formats = format_keys(string)
        return string.format(
            **{
                **{x: f"{{{x}}}" for x in formats if x not in values},
                **{x: y for x, y in values.items()},
            }
        )
    except KeyError:
        return string


def get_directory_structure(directory_structure, **kwargs):
    """
    A helper method that returns all files found in a particular directory structure. The directory structure
    can contain {format} specifiers, to indicate that multiple folders can match at that point. If the
    format specifiers are not specified in the kwargs, then multiple folders will be returned, otherwise
    the one specified in kwargs will be used.

    The files are returns as a list of dicts, where the dicts have the keys 'files' containing a
    list of all files found in a specific path, 'root' containing the path to the parent folder of the files,
    and the key 'details', which contains the details for
    those files (that is, any format keys that are not in kwargs will be passed back here).

    :param directory_structure: The directory structure
    :param kwargs: optional specifiers for which folders to look in.
    :return: All files matching criteria
    """
    structure = full_split(directory_structure)
    full_structure = []

    for part in structure:
        the_part = maybe_format(part, **kwargs)
        if (
            len(full_structure) > 0
            and not contains_format(the_part)
            and not contains_format(full_structure[-1])
        ):
            full_structure[-1] = os.path.join(full_structure[-1], the_part)
        else:
            full_structure.append(the_part)
    return full_structure


def group_by(key, entries):
    """
    Convenience method that groups a list of dicts by one of the keys in the dicts. If the key does not
    exist, the dict is ignored. Returns a dict, where each entry is a value of dict[key] -> list of dict with
    matching key->value pair.

    :param key: The key to group by
    :param entries: the list of dicts to group
    :return: dict[str, list[dict]]
    """
    ordered = defaultdict(list)
    for item in entries:
        if key in item.get("details", {}):
            ordered[item["details"][key]].append(item)
    return ordered


def get_files(root, structure=None, recursive=False, **kwargs):
    """
    Return all the files in the root directory that matches the structure, where the structure is a list of
    sub directories (as returned by the full_split function).

    The files are returns as a list of dicts, where the dicts have the keys 'files' containing a
    list of all files found in a specific path, 'root' containing the path to the parent folder of the files,
    and the key 'details', which contains the details for
    those files (that is, any format keys that are not in kwargs will be passed back here).

    :param root: The root path to look in
    :param structure: The structure as a list
    :param recursive: whether to recursively look for files (default: False)
    :param kwargs: specifiers
    :return: list of dicts for each folder found
    """
    if structure is None:
        structure = []
    if isinstance(structure, str):
        structure = get_directory_structure(structure, **kwargs)
    if isinstance(root, list):
        return get_files(root[0], root[1:] + structure, recursive=recursive, **kwargs)

    if len(structure) == 0:
        if os.path.isdir(root):
            if recursive:
                return [
                    {
                        "files": [
                            os.path.join(r, f) for r, _, fs in os.walk(root) for f in fs
                        ],
                        "root": root,
                        "details": kwargs,
                    }
                ]
            else:
                files = os.listdir(root)
                return [
                    {
                        "files": [os.path.join(root, f) for f in files],
                        "root": root,
                        "details": kwargs,
                    }
                ]
        else:
            return []

    if not contains_format(structure[0]):
        root = os.path.join(root, structure[0])
        return get_files(root, structure[1:], recursive=recursive, **kwargs)

    files = []
    # TODO: should we return error objects when files are missing?
    if os.path.exists(root):
        for filename in os.listdir(root):
            new_root = os.path.join(root, filename)
            detail_name = structure[0].strip("{}")
            if kwargs.get(detail_name, filename) != filename:
                continue
            kwargs[detail_name] = filename
            if os.path.isdir(new_root):
                files.extend(
                    get_files(new_root, structure[1:], recursive=recursive, **kwargs)
                )

    return files
