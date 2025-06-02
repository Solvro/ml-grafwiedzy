import os
import tempfile
import logging
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
from config import OUTPUT_DIR, PDF_DPI, DEBUG_MODE, DEBUG_DIR

logger = logging.getLogger(__name__)

class PDFConverter:
    """
    Responsible for converting between PDF files and images.
    
    Attributes:
        input_path (str): Path to the input PDF file.
        dpi (int): Dots per inch setting for PDF-to-image conversion.
        output_path (str): Path to save the processed PDF when in DEBUG_MODE.
    """

    def __init__(self, input_path: str):
        """
        Initialize the PDFConverter.

        Creates a permanent output path in DEBUG_DIR if DEBUG_MODE is True;
        otherwise, creates a temporary file.

        Args:
            input_path (str): Path to the PDF file to be converted.
        """
        self.input_path = input_path
        self.dpi = PDF_DPI
        if DEBUG_MODE:
            os.makedirs(DEBUG_DIR, exist_ok=True)
            self.output_path = os.path.join(DEBUG_DIR, "processed.pdf")
        else:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            self.output_path = tmp.name
            tmp.close()

    def pdf_to_images(self):
        """
        Convert the input PDF into a list of PIL.Image objects.

        Uses convert_from_path with the configured DPI. Raises an error
        if the input PDF does not exist.

        Returns:
            list[PIL.Image]: List of page images extracted from the PDF.

        Raises:
            FileNotFoundError: If input_path does not exist.
        """
        if not os.path.exists(self.input_path):
            logger.error("PDF file not found for conversion: %s", self.input_path)
            raise FileNotFoundError(f"PDF file not found for conversion: {self.input_path}")

        logger.info("Starting PDF-to-image conversion (DPI=%d): %s", self.dpi, self.input_path)
        pages = convert_from_path(self.input_path, dpi=self.dpi)
        logger.info("Generated %d images from PDF", len(pages))
        return pages

    def images_to_pdf(self, image_list):
        """
        Save a list of grayscale images to a multi-page PDF.

        Each image can be either a NumPy ndarray or a PIL.Image. Converts
        ndarrays to PIL grayscale images before saving.

        Args:
            image_list (list[Union[np.ndarray, PIL.Image]]): Images to save.

        Raises:
            ValueError: If image_list is empty.
        """
        if not image_list:
            logger.error("No images available to save to PDF")
            raise ValueError("No images available to save to PDF.")

        pil_images = []
        for idx, img in enumerate(image_list, start=1):
            if isinstance(img, np.ndarray):
                pil_img = Image.fromarray(img).convert("L")
            else:
                pil_img = img.convert("L")
            pil_images.append(pil_img)
            logger.debug("Converted page %d to PIL grayscale image", idx)

        if DEBUG_MODE:
            logger.info("Saving %d pages to PDF file: %s", len(pil_images), self.output_path)
            pil_images[0].save(
                self.output_path,
                format="PDF",
                resolution=float(self.dpi),
                save_all=True,
                append_images=pil_images[1:]
            )
            logger.info("Saved processed PDF: %s", self.output_path)
        else:
            logger.debug("DEBUG_MODE=False, skipping saving processed.pdf")
