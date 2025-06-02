import os
import logging
import cv2

from logger_config import setup_logger
from config import OUTPUT_DIR, DEBUG_DIR
from downloader import PDFDownloader
from pdf_utils import PDFConverter
from preprocessing import ImagePreprocessor
from cell_detection import CellDetector
from postprocessing import TableProcessor

def main():
    """
    Execute the full OCR pipeline:
    1. Configure logging and create output/debug directories.
    2. Download the latest PDF from the WPPT schedule page.
    3. Convert the PDF into images.
    4. For each page:
       a. Preprocess image (perspective alignment + line removal).
       b. Detect and OCR table cells.
    5. Save processed images back into a PDF (if DEBUG_MODE).
    6. Postprocess extracted tables into a final CSV.
    """
    # 0. Logger setup
    setup_logger()
    logger = logging.getLogger(__name__)

    # 1. Create output and debug directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DEBUG_DIR, exist_ok=True)
    logger.debug("Created directories: OUTPUT_DIR=%s, DEBUG_DIR=%s", OUTPUT_DIR, DEBUG_DIR)

    # 2. Download the latest PDF
    downloader = PDFDownloader()
    pdf_url = downloader.get_latest_pdf_url()
    downloader.download(pdf_url)

    # 3. Convert PDF to images
    converter = PDFConverter(input_path=downloader.download_path)
    pages = converter.pdf_to_images()

    # 4. Initialize preprocessor and cell detector
    preprocessor = ImagePreprocessor()
    cell_detector = CellDetector()

    all_raw_tables = []
    processed_images = []

    # 5. Process each page: preprocessing + table extraction
    total_pages = len(pages)
    for idx, pil_page in enumerate(pages, start=1):
        logger.info("Processing page %d/%d", idx, total_pages)
        cleaned_bgr = preprocessor.preprocess_image(pil_page, page_index=idx)
        processed_images.append(cleaned_bgr)

        gray = (
            cv2.cvtColor(cleaned_bgr, cv2.COLOR_BGR2GRAY)
            if cleaned_bgr.ndim == 3
            else cleaned_bgr
        )
        raw_table = cell_detector.extract_table(gray, page_index=idx)
        all_raw_tables.append(raw_table)

    # 6. Save processed images back to PDF
    converter.images_to_pdf(processed_images)

    # 7. Postprocess tables and save resulting CSV
    table_processor = TableProcessor()
    final_table = table_processor.finalize(all_raw_tables)
    csv_path = os.path.join(OUTPUT_DIR, "all_exams_with_meta.csv")
    table_processor.generate_csv(final_table, output_path=csv_path)

    logger.info("Done - result CSV saved: %s", csv_path)

if __name__ == "__main__":
    main()
