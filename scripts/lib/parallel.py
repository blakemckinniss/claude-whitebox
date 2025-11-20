#!/usr/bin/env python3
"""
Parallel Execution Library
Provides high-performance batching with progress bars and error resilience.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Any, Tuple

# Try to import tqdm, gracefully degrade if not available
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    # Fallback: simple counter
    class tqdm:
        def __init__(self, iterable=None, total=None, desc="Processing", **kwargs):
            self.iterable = iterable
            self.total = total or (len(iterable) if iterable else 0)
            self.desc = desc
            self.n = 0

        def __iter__(self):
            return iter(self.iterable)

        def __enter__(self):
            print(f"{self.desc}: 0/{self.total}")
            return self

        def __exit__(self, *args):
            print(f"{self.desc}: {self.n}/{self.total} complete")

        def update(self, n=1):
            self.n += n

logger = logging.getLogger("Whitebox.Parallel")


def run_parallel(
    func: Callable,
    items: List[Any],
    max_workers: int = 10,
    desc: str = "Processing",
    fail_fast: bool = False
) -> List[Tuple[Any, Any, Exception]]:
    """
    Execute a function in parallel across multiple items with progress tracking.

    Args:
        func: Function to execute for each item. Should accept one argument (the item).
        items: List of items to process.
        max_workers: Maximum number of concurrent threads (default: 10).
        desc: Description for progress bar (default: "Processing").
        fail_fast: If True, stop on first error. If False, collect all errors (default: False).

    Returns:
        List of tuples: (item, result, error)
        - If successful: (item, result, None)
        - If failed: (item, None, Exception)

    Example:
        >>> def process_file(filepath):
        ...     with open(filepath) as f:
        ...         return len(f.read())
        ...
        >>> files = ['file1.txt', 'file2.txt', 'file3.txt']
        >>> results = run_parallel(process_file, files, desc="Reading files")
        >>> for item, result, error in results:
        ...     if error:
        ...         print(f"Failed {item}: {error}")
        ...     else:
        ...         print(f"Success {item}: {result}")
    """
    if not items:
        logger.warning("run_parallel called with empty items list")
        return []

    if not HAS_TQDM:
        logger.info(f"tqdm not installed, using simple progress tracking")

    results = []

    def _safe_execute(item):
        """Wrapper that catches exceptions so one failure doesn't crash the batch"""
        try:
            result = func(item)
            return (item, result, None)
        except Exception as e:
            logger.error(f"Error processing {item}: {e}")
            return (item, None, e)

    # Execute in parallel with progress bar
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_item = {executor.submit(_safe_execute, item): item for item in items}

        # Collect results with progress bar
        with tqdm(total=len(items), desc=desc, unit="item") as pbar:
            for future in as_completed(future_to_item):
                item, result, error = future.result()
                results.append((item, result, error))
                pbar.update(1)

                # Optionally fail fast
                if fail_fast and error:
                    logger.error(f"Failing fast due to error on {item}")
                    # Cancel remaining futures
                    for f in future_to_item:
                        f.cancel()
                    break

    # Log summary
    successes = sum(1 for _, _, error in results if error is None)
    failures = sum(1 for _, _, error in results if error is not None)
    logger.info(f"Batch complete: {successes} succeeded, {failures} failed")

    return results


def batch_map(
    func: Callable,
    items: List[Any],
    max_workers: int = 10,
    desc: str = "Processing"
) -> List[Any]:
    """
    Simpler interface: returns only successful results, logs errors.

    Args:
        func: Function to execute for each item.
        items: List of items to process.
        max_workers: Maximum number of concurrent threads.
        desc: Description for progress bar.

    Returns:
        List of results (errors are filtered out).

    Example:
        >>> results = batch_map(lambda x: x * 2, [1, 2, 3, 4, 5])
        >>> print(results)  # [2, 4, 6, 8, 10]
    """
    all_results = run_parallel(func, items, max_workers=max_workers, desc=desc, fail_fast=False)

    # Filter out errors
    successes = [(item, result) for item, result, error in all_results if error is None]

    return [result for _, result in successes]


def batch_filter(
    predicate: Callable[[Any], bool],
    items: List[Any],
    max_workers: int = 10,
    desc: str = "Filtering"
) -> List[Any]:
    """
    Filter items in parallel using a predicate function.

    Args:
        predicate: Function that returns True/False for each item.
        items: List of items to filter.
        max_workers: Maximum number of concurrent threads.
        desc: Description for progress bar.

    Returns:
        List of items where predicate returned True.

    Example:
        >>> def is_large_file(path):
        ...     return os.path.getsize(path) > 1000000
        ...
        >>> large_files = batch_filter(is_large_file, all_files)
    """
    all_results = run_parallel(predicate, items, max_workers=max_workers, desc=desc, fail_fast=False)

    # Return items where predicate was True
    return [item for item, result, error in all_results if error is None and result]


# Performance tuning helpers
def optimal_workers(item_count: int, io_bound: bool = True) -> int:
    """
    Calculate optimal number of workers for a given workload.

    Args:
        item_count: Number of items to process.
        io_bound: True for I/O-bound tasks (network, disk), False for CPU-bound.

    Returns:
        Recommended number of workers.
    """
    import os

    if io_bound:
        # I/O-bound: can use many threads
        return min(item_count, 50)
    else:
        # CPU-bound: limit to CPU count
        cpu_count = os.cpu_count() or 4
        return min(item_count, cpu_count)
