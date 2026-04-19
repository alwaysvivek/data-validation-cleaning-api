"""File I/O service — handles CSV and Excel uploads / downloads."""

from __future__ import annotations

import io
import logging
import os

import pandas as pd
from fastapi import UploadFile

from app.config import settings
from app.errors import EmptyDatasetError, FileTooLargeError, UnsupportedFileTypeError

logger = logging.getLogger(__name__)


class FileHandler:
    """Service class for reading and writing data files."""

    @staticmethod
    async def read_upload(file: UploadFile) -> pd.DataFrame:
        """Read an uploaded file into a DataFrame.

        Validates file size and extension before parsing.
        """
        # Validate extension
        filename = file.filename or ""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(ext, settings.ALLOWED_EXTENSIONS)

        # Read content and check size
        content = await file.read()
        if len(content) > settings.max_upload_bytes:
            raise FileTooLargeError(settings.max_upload_bytes, len(content))

        logger.info("Reading uploaded file '%s' (%d bytes)", filename, len(content))

        # Parse
        buf = io.BytesIO(content)
        if ext == ".csv":
            df = pd.read_csv(buf)
        elif ext in {".xlsx", ".xls"}:
            df = pd.read_excel(buf, engine="openpyxl")
        else:
            raise UnsupportedFileTypeError(ext, settings.ALLOWED_EXTENSIONS)

        if df.empty:
            raise EmptyDatasetError()

        logger.info("Parsed %d rows × %d columns from '%s'", *df.shape, filename)
        return df

    @staticmethod
    def to_csv(df: pd.DataFrame) -> io.BytesIO:
        """Write a DataFrame to an in-memory CSV buffer."""
        buf = io.BytesIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return buf

    @staticmethod
    def to_excel(df: pd.DataFrame) -> io.BytesIO:
        """Write a DataFrame to an in-memory Excel (.xlsx) buffer."""
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return buf
