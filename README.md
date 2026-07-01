#  Development of a Medical Image Processing Pipeline for DICOM Data

##  Introduction

Medical imaging data significantly differs from standard consumer image formats. DICOM files function as comprehensive datasets, encapsulating high-depth pixel arrays (typically 12-bit or 16-bit), spatial coordinate mapping, and extensive hardware-specific metadata.

The objective of this semester project was to develop a resilient backend infrastructure to automate the extraction and rendering of these files. The system was designed with defensive programming principles to gracefully handle common real-world anomalies—such as missing metadata tags, proprietary data compression, and variable photometric interpretations—ensuring mathematically rigorous outputs.

---

##  Theoretical Framework and Mathematical Models

The pipeline relies on fundamental principles of medical imaging physics and linear algebra to accurately render diagnostic data. The core transformations applied to the 2D discrete matrices are defined as follows:

###  Hounsfield Units (HU) Derivation

Computed Tomography (CT) scanners record radiodensity based on the linear attenuation coefficient, $\mu$, of the scanned tissue. To standardize these density measurements across different proprietary hardware, raw values are mapped to the Hounsfield scale. The theoretical definition of a Hounsfield Unit is:

$$HU = 1000 \times \frac{\mu - \mu_{water}}{\mu_{water} - \mu_{air}}$$

In practice, the DICOM standard pre-calculates the necessary slope and intercept for this conversion. Let $P_{raw}$ be the matrix of raw 16-bit pixel values from the scanner. The mathematical conversion to the standardized HU matrix, $H$, is a linear transformation:

$$H(x, y) = m \cdot P_{raw}(x, y) + b$$

Where $m$ represents the `RescaleSlope` and $b$ represents the `RescaleIntercept` embedded in the file's metadata.

###  Windowing and Leveling (Grayscale Mapping)

A standard CT scan may contain density values spanning over 4,000 units, whereas standard monitors display only 256 discrete intensity levels (8-bit depth). Windowing acts as a contrast-enhancing transfer function that maps a specific continuous sub-range of $H$ to the discrete $[0, 255]$ spectrum.

Let $c$ denote the `WindowCenter` (level) and $w$ denote the `WindowWidth`. The lower bound $L$ and upper bound $U$ of the window are defined as:

$$L = c - \frac{w}{2}$$

$$U = c + \frac{w}{2}$$

A piecewise normalization function, $N(x, y)$, maps the $H$ values into a continuous range between 0 and 1:

$$N(x, y) = \begin{cases} 0 & \text{if } H(x, y) \le L \\ \frac{H(x, y) - L}{w} & \text{if } L < H(x, y) < U \\ 1 & \text{if } H(x, y) \ge U \end{cases}$$

The final 8-bit display matrix, $D(x, y)$, is derived by scaling the normalized array:

$$D(x, y) = \lfloor N(x, y) \cdot 255 \rfloor$$

### Photometric Interpretation and Inversion

Standard radiological convention (`MONOCHROME2`) assumes higher density values (e.g., bone) map to higher intensity outputs (white). Certain datasets utilize `MONOCHROME1`, which represents an inverse relationship. To algorithmically correct this, the system applies a bitwise inversion to the display matrix:

$$D_{inverted}(x, y) = 255 - D(x, y)$$

---
Here is the formalized project structure based on your provided directory tree. You can replace the existing "Section 3: System Architecture and Implementation" overview in your report with this formatted breakdown.

---

### 3. Project Directory Structure and Organization

To ensure modularity and maintainability, the project is organized into distinct directories separating the core computational logic, testing frameworks, and output generation. The repository follows a standard hierarchical structure:

**Directory Tree:**

```text
📦 Project Root
 ┣ 📂 Scripts
 ┃ ┣ 📜 dicom_parser.py
 ┃ ┣ 📜 dicom_series.py
 ┃ ┣ 📜 image_export.py
 ┃ ┗ 📜 processing_engine.py
 ┣ 📂 Test Outputs
 ┃ ┣ 🖼️ test 1.png
 ┃ ┣ 🖼️ test 2.png
 ┃ ┣ 🖼️ test 3.png
 ┃ ┣ 🖼️ test 4.png
 ┃ ┣ 🖼️ test 5.png
 ┃ ┗ 🖼️ test 6.png
 ┣ 📂 Test
 ┃ ┗ 📜 local series test.py
 ┣ 📜 .gitignore
 ┗ 📜 README.md

```

**Module and Directory Descriptions:**

* **`Scripts/` (Computational Core & I/O Operations):**
This directory contains the primary backend modules responsible for data extraction and mathematical transformations.
* `dicom_parser.py`: Manages the ingestion of individual DICOM files, safely extracting metadata and handling specialized codec anomalies.
* `dicom_series.py`: Handles volumetric data aggregation, structurally sorting multiple 2D matrices into anatomically accurate 3D tensors based on spatial coordinates.
* `processing_engine.py`: Executes all vectorized mathematical operations, including Hounsfield Unit (HU) derivations, piecewise windowing normalization, and Region of Interest (ROI) statistical computations.
* `image_export.py`: Encodes the processed discrete matrices into web-standard formats (Base64/PNG) for downstream visual rendering.


* **`Test/` (Validation Framework):**
* `local series test.py`: Serves as the primary execution script and Command Line Interface (CLI) to validate the pipeline. It orchestrates the processing of single files, discrete series, or batch operations to verify algorithmic integrity.
---
## System Architecture and Implementation

The codebase was structured into highly cohesive, decoupled Python modules to separate input/output operations from complex mathematical processing.

###  Data Extraction Layer (`dicom_parser.py`)

This module manages file ingestion and metadata validation utilizing the `pydicom` library.

* **Defensive Parsing:** A strict `DicomMetadata` dataclass structures the required variables. Fallback mechanisms supply safe default parameters if critical elements (e.g., $c$ or $w$) are absent or malformed as vectors rather than scalar values.
* **Exception Management:** To address files compressed with algorithms requiring specialized C-level libraries (e.g., JPEG2000), the module intercepts obfuscated failures and provides actionable installation directives.

###  Volumetric Aggregation (`dicom_series.py`)

This module aggregates directory-level 2D matrices into a comprehensive 3D spatial tensor.

* **Spatial Sorting:** Slices are sorted algorithmically utilizing the Z-coordinate extracted from the `ImagePositionPatient` vector $[x, y, z]$, ensuring accurate anatomical reconstruction regardless of file nomenclature.
* **Integrity Validation:** The module verifies uniform dimensionality ($M \times N$) across all individual matrices, terminating execution if spatial dimensions conflict across the dataset.

###  Computational Core (`processing_engine.py`)

This module executes the mathematical models defined in Section 2. To meet performance requirements on matrices often exceeding $512 \times 512$ elements, operations are heavily vectorized utilizing the `numpy` library.

* **Vectorized Processing:** Linear transformations and piecewise clipping algorithms operate natively on C-optimized arrays, bypassing high-latency Python iterators. Data is explicitly upcast to 32-bit floating-point arrays to prevent integer overflow when processing negative HU values.
* **Region of Interest (ROI) Statistics:** The pipeline calculates foundational descriptive statistics over bounded regions. Let $R$ be an $m \times n$ sub-matrix representing the selected ROI, and $T = m \times n$ be the total pixel count. The system computes the arithmetic mean, $\mu_{ROI}$, and standard deviation, $\sigma_{ROI}$:

$$\mu_{ROI} = \frac{1}{T} \sum_{i=1}^{m} \sum_{j=1}^{n} R(i, j)$$

$$\sigma_{ROI} = \sqrt{\frac{1}{T} \sum_{i=1}^{m} \sum_{j=1}^{n} (R(i, j) - \mu_{ROI})^2}$$

###  Output Generation (`image_export.py`)

This module bridges the computational backend with rendering interfaces. Processed discrete matrices ($D(x, y)$) are encoded into optimal Base64 strings and Data URIs utilizing the Pillow framework, allowing direct downstream injection into standard HTTP responses.

###  Validation Suite (`test_dicom.py`)

A comprehensive Command Line Interface (CLI) was developed to validate algorithmic integrity across varied scenarios:

* **Single File Mode:** Isolates individual tensor processing for discrete mathematical verification.
* **Series Mode:** Validates the $M \times N \times Z$ volumetric sorting and dimensionality logic.
* **Batch Mode:** Recursively parses unstructured datasets, systematically logging computational faults to evaluate algorithmic resilience on malformed inputs.

---

## Technical Challenges and Methodological Solutions

1. **Metadata Instability:** DICOM attributes frequently deviate from standard constraints. This was mitigated by implementing standardization functions that isolate primary scalar parameters from unexpected arrays, preventing linear algebra operational faults.
2. **Data Overflow Anomalies:** Mapping raw pixels to HU inherently generates negative integers. Executing scalar multiplication on unsigned integer arrays resulted in binary wrap-around anomalies. This was corrected by strictly defining the tensor dtype as 32-bit float prior to $H(x,y)$ derivation.
3. **Missing Window Boundaries:** Certain datasets omitted $c$ and $w$ values. An algorithmic fallback was engineered to calculate optimal bounds by evaluating the absolute array limits:

$$w_{auto} = \max(H) - \min(H)$$

$$c_{auto} = \frac{\max(H) + \min(H)}{2}$$


