import gzip
import shutil
import tempfile
from abc import abstractmethod
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import ContextManager, Optional


@contextmanager
def wrap_in_context_manager(value):
    yield value


@contextmanager
def decompress_to_temp_file(archive: Path):
    """Yields a path to the decompressed contents of a .gz file.

    The datasets are committed gzipped to keep the repository small; everything
    downstream of the reader only ever sees a plain .csv path.
    """
    with tempfile.NamedTemporaryFile(suffix=".csv") as handle:
        with gzip.open(archive, "rb") as source:
            shutil.copyfileobj(source, handle)
        handle.flush()
        yield Path(handle.name)


class FileReader:
    @abstractmethod
    def file(self, path_parts: list[str]) -> ContextManager[Optional[Path]]:
        """Given a path to a file, yields a single Path object to the file or None if the file does not exist."""
        raise NotImplementedError()


class FileSystemReader(FileReader):
    def __init__(self, root: Path) -> None:
        self._root = root

    def file(self, path_parts: list[str]) -> ContextManager[Optional[Path]]:
        file = self._root
        for part in path_parts:
            file = file / part

        if file.is_file():
            return wrap_in_context_manager(file)

        archive = file.with_suffix(file.suffix + ".gz")
        if archive.is_file():
            return decompress_to_temp_file(archive)

        return wrap_in_context_manager(None)


class PackageResourcesReader(FileReader):
    def file(self, path_parts: list[str]) -> ContextManager[Optional[Path]]:
        try:
            container = resources.files(
                f"prosperity4bt.resources.{'.'.join(path_parts[:-1])}")
            file = container / path_parts[-1]
            if not file.is_file():
                return wrap_in_context_manager(None)

            return resources.as_file(file)
        except Exception:
            return wrap_in_context_manager(None)
