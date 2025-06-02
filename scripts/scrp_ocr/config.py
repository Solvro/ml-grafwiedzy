import numpy as np

DEBUG_MODE = True  # Set to True if you want to enable debugging

LOG_FILE_NAME = "pipeline_debug.log"

# ------------------------------------------------------------------------
# Tesseract OCR configuration
# ------------------------------------------------------------------------
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# URL to fetch the latest PDF schedule
PDF_PAGE_URL = "https://wppt.pwr.edu.pl/studenci/harmonogram-sesji"

# Directories for output and debug files
OUTPUT_DIR = "data"
DEBUG_DIR = "scripts/scrp_ocr/debug"

# DPI setting for PDF-to-image conversion
PDF_DPI = 400

# Padding around detected contours
PADDING = 10

# ------------------------------------------------------------------------
# Preprocessing and contour detection parameters
# ------------------------------------------------------------------------
# Number of iterations for strong dilation (used in contour detection)
DILATE_STRONG_ITERATIONS = 30
# Number of iterations for weak dilation (optional/unused second pass)
DILATE_WEAK_ITERATIONS = 2

# Ratio to scale the width when applying perspective transform
TRANSFORM_WIDTH_RATIO = 0.9

# ------------------------------------------------------------------------
# Table line removal parameters
# ------------------------------------------------------------------------
# Number of iterations to erode vertical lines
VERT_ITERATIONS = 10
# Kernel to erode vertical lines
VERT_KERNEL_SIZE = [[1, 1, 1, 1, 1, 1]]

# Number of iterations to erode horizontal lines
HORIZ_ITERATIONS = 10
# Kernel to erode horizontal lines
HORIZ_KERNEL_SIZE = [[1], [1], [1], [1], [1], [1], [1]]

# ------------------------------------------------------------------------
# Cell detection and OCR parameters
# ------------------------------------------------------------------------
# Number of iterations to dilate combined vertical/horizontal lines
DILATE_LINES_ITER = 5

# Kernel to merge words horizontally
KER_WORDS = np.ones((1, 19), np.uint8)

# Kernel to merge lines vertically (simple)
KER_SIMPLE = np.ones((20, 1), np.uint8)

# Minimum cell area and dimension thresholds
MIN_AREA = 100
MIN_WIDTH = 50
MIN_HEIGHT = 20

# Padding around each detected cell before OCR
CELL_PADDING = 2

# OCR languages and configuration flags
OCR_LANG = "pol+eng"
OCR_CONFIG = "--oem 3 --psm 6"

# ------------------------------------------------------------------------
# Table merging/splitting parameters
# ------------------------------------------------------------------------
# Expected number of columns in the final table
EXPECTED_COLUMNS = 14

# Keywords used to split combined form/education type fields
COMB_KEYWORDS = ["stacjonarna", "niestacjonarna", "zdalna"]
# Index of the column assumed to contain combined fields
COMB_IDX_FORM = 4
