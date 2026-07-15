import os, shutil
from typing import Protocol

class SaveableFileStream(Protocol):
    source_path: str | os.PathLike[str]
    
    def __init__(self, source_path: str | os.PathLike[str]):
        super().__init__()
        self.source_path = source_path

    def save(self, dst: str | os.PathLike[str], buffer_size: int = 16384) -> None:
        shutil.copy2(self.source_path, dst)