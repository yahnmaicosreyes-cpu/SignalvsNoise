# ============================================================
# timesheet_exporter.py
#
# Writes a rendered timesheet string to a .txt file on disk.
#
# Why this file exists:
#   render_timesheet() produces a string. That string is great for
#   printing in a terminal, but users need an actual file they can
#   save, email, print, or move around. This is the small adapter
#   between "string in memory" and "file on disk."
#
# Lives in src/engine/ because it operates on already-clean data
# (a string produced by the formatter). It performs I/O, but the
# I/O is bounded and validated.
#
# Security considerations:
#   - Path traversal: the resolved file path must stay INSIDE the
#     specified directory. We use os.path.realpath() to follow
#     symlinks and verify containment.
#   - File overwriting: we REFUSE to overwrite an existing file.
#     The caller must handle name collisions explicitly. This
#     prevents accidental data loss.
#   - Filename construction: the filename is generated entirely
#     by us (from the current date). The caller cannot influence
#     it. This eliminates a whole category of filename-injection
#     attacks.
#   - Input validation: we reject non-string content and bad
#     directory arguments at the door with TypeError / ValueError.
# ============================================================

import os
from datetime import date


# ----------------------------------------------------------------
# Filename rules
#
# Filenames are built by us, never derived from user input. This
# means we control every character that ends up in the file path.
# ----------------------------------------------------------------

# Prefix for every exported timesheet file. Chosen so files are
# easily findable when listed alongside other documents.
FILENAME_PREFIX = "timesheet_"

# File extension. .txt was the locked-in format choice.
FILENAME_EXTENSION = ".txt"


def _build_filename(today=None):
    """
    Construct a date-stamped filename.

    Args:
        today: Optional date object. Defaults to today's actual date.
               Passing an explicit date makes the function testable
               (otherwise tests would depend on what day they run).

    Returns:
        A filename string like "timesheet_2026-05-25.txt".

    Note: this function does NOT accept any user input. The filename
    is built from a date and our own constants. This is deliberate --
    user-influenced filenames are an injection risk.
    """
    if today is None:
        today = date.today()

    # ISO format YYYY-MM-DD is unambiguous and sorts correctly when
    # files are listed alphabetically. Safer than locale-specific
    # formats like "5/25/2026".
    date_str = today.isoformat()

    return f"{FILENAME_PREFIX}{date_str}{FILENAME_EXTENSION}"


def export_timesheet(timesheet_content, directory=".", today=None):
    """
    Write a rendered timesheet string to a .txt file.

    Args:
        timesheet_content (str): The string to write. Typically the
            return value of render_timesheet(events, issues).
        directory (str): The directory to write into. Defaults to the
            current working directory. The directory must already
            exist -- we do NOT create directories (avoids accidental
            structure creation if the path is wrong).
        today (date, optional): The date to use in the filename. If
            None (default), uses today's actual date. Mostly used for
            testing.

    Returns:
        The absolute path of the file that was written.

    Raises:
        TypeError: if timesheet_content isn't a string, or directory
            isn't a string.
        ValueError: if the directory doesn't exist, isn't a directory,
            or the resolved file path escapes the directory (path
            traversal attempt).
        FileExistsError: if a file with the target name already exists.
            We REFUSE to overwrite -- the caller must rename or
            delete first. Prevents silent data loss.
        OSError: any underlying I/O error (permission denied, disk
            full, etc.) propagates with its native error.
    """

    # ---- TYPE VALIDATION ----
    if not isinstance(timesheet_content, str):
        raise TypeError(
            f"timesheet_content must be a string, "
            f"got {type(timesheet_content).__name__}"
        )
    if not isinstance(directory, str):
        raise TypeError(
            f"directory must be a string, got {type(directory).__name__}"
        )

    # ---- DIRECTORY VALIDATION ----
    # Resolve the directory to an absolute, canonical path.
    # realpath() follows symlinks too, so we know exactly where
    # the file will end up.
    abs_directory = os.path.realpath(directory)

    # The directory must exist. We don't create directories
    # automatically -- that could mask typos (creating
    # "/home/usr/Documents" instead of "/home/user/Documents").
    if not os.path.exists(abs_directory):
        raise ValueError(f"directory does not exist: {directory}")
    if not os.path.isdir(abs_directory):
        raise ValueError(f"path is not a directory: {directory}")

    # ---- FILENAME + FULL PATH ----
    filename = _build_filename(today)
    full_path = os.path.join(abs_directory, filename)

    # ---- PATH TRAVERSAL DEFENSE ----
    # After building the full path, check that the resolved (real)
    # path is still inside the resolved directory. This catches:
    #   - Symlinks that point outside the target directory
    #   - Any weird path-manipulation surprises
    # We construct the filename ourselves so traversal via filename
    # shouldn't be possible, but this is belt-and-suspenders.
    resolved_full_path = os.path.realpath(full_path)
    if not resolved_full_path.startswith(abs_directory + os.sep) \
       and resolved_full_path != abs_directory:
        # The "+ os.sep" guards against the edge case where one
        # directory name is a prefix of another (e.g. "/tmp/foo"
        # being a prefix of "/tmp/foobar" -- we want only true
        # parent-child containment).
        raise ValueError(
            f"resolved path escapes target directory "
            f"(this should not happen with a generated filename)"
        )

    # ---- REFUSE TO OVERWRITE ----
    # If the file already exists, refuse rather than silently
    # destroying its contents. The caller decides what to do.
    if os.path.exists(full_path):
        raise FileExistsError(
            f"file already exists: {full_path}. "
            f"Delete or rename the existing file before re-exporting."
        )

    # ---- WRITE THE FILE ----
    # Open in "x" mode (exclusive create) as a second layer of
    # protection against overwriting. This is atomic: if another
    # process creates the file between our os.path.exists() check
    # above and this open(), the "x" mode will still refuse.
    # Encoding is explicit utf-8 so behavior is the same on every
    # platform (Windows defaults can vary).
    with open(full_path, "x", encoding="utf-8") as f:
        f.write(timesheet_content)

    return full_path
