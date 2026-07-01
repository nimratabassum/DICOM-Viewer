# Development of a Medical Image Processing Pipeline for DICOM Data

##  Introduction

Medical imaging data significantly differs from standard consumer image formats. DICOM files function as comprehensive datasets, encapsulating high-depth pixel arrays (typically 12-bit or 16-bit), spatial coordinate mapping, and extensive hardware-specific metadata.

The objective of this semester project was to develop a resilient backend infrastructure to automate the extraction and rendering of these files. The system was designed with defensive programming principles to gracefully handle common real-world anomalies—such as missing metadata tags, proprietary data compression, and variable photometric interpretations—ensuring mathematically rigorous outputs.

---

##  Theoretical Framework and Mathematical Models

The pipeline relies on fundamental principles of medical imaging physics and linear algebra to accurately render diagnostic data. The core transformations applied to the 2D discrete matrices are defined as follows:

### Hounsfield Units (HU) Derivation

Computed Tomography (CT) scanners record radiodensity based on the linear attenuation coefficient, $\mu$, of the scanned tissue. To standardize these density measurements across different proprietary hardware, raw values are mapped to the Hounsfield scale. The theoretical definition of a Hounsfield Unit is:

$$HU = 1000 \times \frac{\mu - \mu_{water}}{\mu_{water} - \mu_{air}}$$

In practice, the DICOM standard pre-calculates the necessary slope and intercept for this conversion. Let $P_{raw}$ be the matrix of raw 16-bit pixel values from the scanner. The mathematical conversion to the standardized HU matrix, $H$, is a linear transformation:

$$H(x, y) = m \cdot P_{raw}(x, y) + b$$

Where $m$ represents the `RescaleSlope` and $b$ represents the `RescaleIntercept` embedded in the file's metadata.

### Windowing and Leveling (Grayscale Mapping)

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

##  Project Directory Structure and Organization

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

### Module and Directory Descriptions:

* **`Scripts/` (Computational Core & I/O Operations):** Contains the primary backend modules responsible for data extraction and mathematical transformations.
* **`Test/` (Validation Framework):** Houses the `local series test.py` file, which serves as the primary execution script and Command Line Interface (CLI) to orchestrate and validate the pipeline.
* **`Test Outputs/` (Verification Artifacts):** The destination for the successfully rendered 8-bit visual matrices generated during pipeline execution.

---

## System Architecture and Implementation

The codebase was structured into highly cohesive, decoupled Python modules to separate input/output operations from complex mathematical processing.

### Data Extraction Layer (`dicom_parser.py`)

This module manages file ingestion and metadata validation utilizing the `pydicom` library.

* **Defensive Parsing:** A strict `DicomMetadata` dataclass structures the required variables. Fallback mechanisms supply safe default parameters if critical elements (e.g., $c$ or $w$) are absent or malformed as vectors rather than scalar values.
* **Exception Management:** To address files compressed with algorithms requiring specialized C-level libraries (e.g., JPEG2000), the module intercepts obfuscated failures and provides actionable installation directives.

### Volumetric Aggregation (`dicom_series.py`)

This module aggregates directory-level 2D matrices into a comprehensive 3D spatial tensor.

* **Spatial Sorting:** Slices are sorted algorithmically utilizing the Z-coordinate extracted from the `ImagePositionPatient` vector $[x, y, z]$, ensuring accurate anatomical reconstruction regardless of file nomenclature.
* **Integrity Validation:** The module verifies uniform dimensionality ($M \times N$) across all individual matrices, terminating execution if spatial dimensions conflict across the dataset.

### Computational Core (`processing_engine.py`)

This module executes the mathematical models defined in Section 2. To meet performance requirements on matrices often exceeding $512 \times 512$ elements, operations are heavily vectorized utilizing the `numpy` library.

* **Vectorized Processing:** Linear transformations and piecewise clipping algorithms operate natively on C-optimized arrays, bypassing high-latency Python iterators. Data is explicitly upcast to 32-bit floating-point arrays to prevent integer overflow when processing negative HU values.
* **Region of Interest (ROI) Statistics:** The pipeline calculates foundational descriptive statistics over bounded regions. Let $R$ be an $m \times n$ sub-matrix representing the selected ROI, and $T = m \times n$ be the total pixel count. The system computes the arithmetic mean, $\mu_{ROI}$, and standard deviation, $\sigma_{ROI}$:

$$\mu_{ROI} = \frac{1}{T} \sum_{i=1}^{m} \sum_{j=1}^{n} R(i, j)$$

$$\sigma_{ROI} = \sqrt{\frac{1}{T} \sum_{i=1}^{m} \sum_{j=1}^{n} (R(i, j) - \mu_{ROI})^2}$$

### Output Generation (`image_export.py`)

This module bridges the computational backend with rendering interfaces. Processed discrete matrices ($D(x, y)$) are encoded into optimal Base64 strings and Data URIs utilizing the Pillow framework, allowing direct downstream injection into standard HTTP responses.

### Validation Suite (`local series test.py`)

A comprehensive Command Line Interface (CLI) was developed to validate algorithmic integrity across varied scenarios:

* **Single File Mode:** Isolates individual tensor processing for discrete mathematical verification.
* **Series Mode:** Validates the $M \times N \times Z$ volumetric sorting and dimensionality logic.
* **Batch Mode:** Recursively parses unstructured datasets, systematically logging computational faults to evaluate algorithmic resilience on malformed inputs.

---

##  Technical Challenges and Methodological Solutions

1. **Metadata Instability:** DICOM attributes frequently deviate from standard constraints. This was mitigated by implementing standardization functions that isolate primary scalar parameters from unexpected arrays, preventing linear algebra operational faults.
2. **Data Overflow Anomalies:** Mapping raw pixels to HU inherently generates negative integers. Executing scalar multiplication on unsigned integer arrays resulted in binary wrap-around anomalies. This was corrected by strictly defining the tensor dtype as 32-bit float prior to $H(x,y)$ derivation.
3. **Missing Window Boundaries:** Certain datasets omitted $c$ and $w$ values. An algorithmic fallback was engineered to calculate optimal bounds by evaluating the absolute array limits:

$$w_{auto} = \max(H) - \min(H)$$

$$c_{auto} = \frac{\max(H) + \min(H)}{2}$$

---
## Requirements and Installation

### Prerequisites

* **Python:** Version 3.8 or higher is required.

### 1. Install Core Dependencies

The pipeline relies on a few fundamental libraries for parsing, array manipulation, and image encoding. Install them using pip:

```bash
pip install pydicom numpy Pillow

```

### 2. Install Compression Codecs (Crucial)

Many real-world DICOM datasets (such as those downloaded from hospital archives or public datasets like TCIA) utilize proprietary compression algorithms (e.g., JPEG2000, JPEG Lossless, RLE). If the correct C-level codecs are not installed, `pydicom` will fail to decode the pixel arrays.

To ensure maximum compatibility across all file types, install the following packages:

```bash
pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg python-gdcm

```
---
## Results
<img width="512" height="512" alt="test 1" src="https://github.com/user-attachments/assets/2f7191c6-6cbb-461a-aafc-14149a9fd696" />
<img width="512" height="512" alt="test 2" src="https://github.com/user-attachments/assets/5b91179d-d7d8-45b2-820d-e9c22cec9ce8" />
<img width="512" height="512" alt="test 3" src="https://github.com/user-attachments/assets/b09aff3e-77e6-47b5-9f1b-4e82be736886" />

---
## References
Here is a list of formal academic references formatted in APA style. These cover the DICOM standard, the underlying physics (Hounsfield Units, Windowing), and the Python libraries used in your pipeline. You can add this as the final section of your report.

---

## 7. References

1. **National Electrical Manufacturers Association (NEMA).** (2024). *Digital Imaging and Communications in Medicine (DICOM) Standard*. Rosslyn, VA: NEMA. Retrieved from [https://www.dicomstandard.org/](https://www.dicomstandard.org/)
2. **Bushberg, J. T., Seibert, J. A., Leidholdt, E. M., & Boone, J. M.** (2011). *The Essential Physics of Medical Imaging* (3rd ed.). Lippincott Williams & Wilkins. (Reference for Hounsfield Units and Computed Tomography physics).
3. **Seeram, E.** (2015). *Computed Tomography: Physical Principles, Clinical Applications, and Quality Control* (4th ed.). Saunders. (Reference for Windowing, Leveling, and grayscale transformations in clinical viewers).
4. **Mason, D., et al.** (2023). *pydicom: An open source Python library for parsing DICOM files*. (Version 2.4.4) [Software]. Available at [https://github.com/pydicom/pydicom](https://github.com/pydicom/pydicom)
5. **Harris, C. R., Millman, K. J., van der Walt, S. J., et al.** (2020). Array programming with NumPy. *Nature*, 585(7825), 357–362. [https://doi.org/10.1038/s41586-020-2649-2](https://doi.org/10.1038/s41586-020-2649-2)
6. **Clark, K., Vendt, B., Smith, K., et al.** (2013). The Cancer Imaging Archive (TCIA): Maintaining and Operating a Public Information Repository. *Journal of Digital Imaging*, 26(6), 1045–1057. (Include this if your batch-testing datasets were sourced from TCIA).

