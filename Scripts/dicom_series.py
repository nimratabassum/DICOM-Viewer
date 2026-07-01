"""
dicom_series.py

Loads an entire DICOM series (a folder of .dcm files representing one
scan, e.g. 150 CT slices) into a single sorted 3D HU volume, instead of
processing one file at a time.

This is the difference between "renders one image" and "loads a scan" —
a real CT/MR study is a stack of slices, and they must be ordered
correctly (by physical position, not filename) before you can scroll
through them or do multi-planar reconstruction.
"""

import os
from dataclasses import dataclass
from typing import List

import numpy as np

from dicom_parser import (
    load_dicom_file,
    extract_metadata,
    extract_pixel_array,
    needs_inversion,
    DicomMetadata,
)
from processing_engine import apply_rescale


@dataclass
class DicomSeries:
    """A full loaded scan: one HU volume plus per-slice metadata."""
    volume_hu: np.ndarray              # shape: (num_slices, rows, cols), float32
    slice_metadata: List[DicomMetadata]  # one entry per slice, same order as volume_hu
    invert: bool                       # True if this series needs MONOCHROME1 inversion

    @property
    def num_slices(self) -> int:
        return self.volume_hu.shape[0]

    def get_slice_hu(self, index: int) -> np.ndarray:
        """Return the 2D HU array for a single slice by index."""
        if not (0 <= index < self.num_slices):
            raise IndexError(
                f"Slice index {index} out of range (series has {self.num_slices} slices)."
            )
        return self.volume_hu[index]


def _list_dcm_files(folder_path: str) -> List[str]:
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"'{folder_path}' is not a valid directory.")

    filepaths = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith(".dcm")
    ]
    if not filepaths:
        raise ValueError(f"No .dcm files found in '{folder_path}'.")
    return filepaths


def load_dicom_series(folder_path: str) -> DicomSeries:
    """
    Load every .dcm file in a folder as one ordered series/volume.

    Ordering strategy:
        Slices are sorted by ImagePositionPatient's z-coordinate (the
        physically correct way to order a scan), falling back to
        InstanceNumber if position data is missing. Sorting by filename
        alone is NOT reliable, since filenames don't always reflect
        acquisition/anatomical order.

    Note:
        This assumes all files in the folder belong to ONE series. A
        folder containing multiple series/studies mixed together should
        be filtered by SeriesInstanceUID before calling this — that's a
        straightforward extension if your test data ever has that shape.
    """
    filepaths = _list_dcm_files(folder_path)

    datasets = [load_dicom_file(fp) for fp in filepaths]
    metadatas = [extract_metadata(ds) for ds in datasets]

    # Sort datasets and metadata together by physical z-position.
    order = sorted(range(len(datasets)), key=lambda i: metadatas[i].image_position_z)
    datasets = [datasets[i] for i in order]
    metadatas = [metadatas[i] for i in order]

    invert = needs_inversion(metadatas[0])

    hu_slices = []
    for ds, meta in zip(datasets, metadatas):
        raw = extract_pixel_array(ds)
        hu = apply_rescale(raw, meta.rescale_slope, meta.rescale_intercept)
        hu_slices.append(hu)

    shapes = {s.shape for s in hu_slices}
    if len(shapes) > 1:
        raise ValueError(
            f"Inconsistent slice dimensions found in series: {shapes}. "
            f"This folder may contain more than one series mixed together."
        )

    volume = np.stack(hu_slices, axis=0)  # (num_slices, rows, cols)

    return DicomSeries(volume_hu=volume, slice_metadata=metadatas, invert=invert)