"""Data ingestion module for downloading and organizing dataset files."""

from .downloader import HuggingFaceDownloader
from .organizer import DataOrganizer

__all__ = ['HuggingFaceDownloader', 'DataOrganizer']
