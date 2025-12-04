"""Progress tracking utilities."""

from typing import Optional, Iterable, Any
from tqdm import tqdm


def create_progress_bar(
    iterable: Optional[Iterable] = None,
    total: Optional[int] = None,
    desc: str = "Processing",
    unit: str = "items"
) -> tqdm:
    """
    Create a progress bar for tracking operations.

    Args:
        iterable: Iterable to track (optional)
        total: Total number of items (required if iterable is None)
        desc: Description text
        unit: Unit name for items

    Returns:
        tqdm progress bar instance
    """
    return tqdm(
        iterable=iterable,
        total=total,
        desc=desc,
        unit=unit,
        ncols=100,
        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
    )


def update_progress(pbar: tqdm, n: int = 1, desc: Optional[str] = None) -> None:
    """
    Update progress bar.

    Args:
        pbar: Progress bar instance
        n: Number of items to increment
        desc: Optional new description
    """
    if desc:
        pbar.set_description(desc)
    pbar.update(n)
