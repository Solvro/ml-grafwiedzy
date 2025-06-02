import os
import logging
import cv2
import numpy as np
import pytesseract
from config import (
    KER_WORDS,
    KER_SIMPLE,
    MIN_AREA,
    MIN_WIDTH,
    MIN_HEIGHT,
    CELL_PADDING,
    OCR_LANG,
    OCR_CONFIG,
    DEBUG_DIR
)

logger = logging.getLogger(__name__)

class CellDetector:
    def __init__(self):
        """
        Initialize CellDetector by loading configuration parameters and ensuring
        the debug directory exists.
        """
        self.ker_words    = KER_WORDS
        self.ker_simple   = KER_SIMPLE
        self.min_area     = MIN_AREA
        self.min_w        = MIN_WIDTH
        self.min_h        = MIN_HEIGHT
        self.cell_padding = CELL_PADDING
        self.ocr_lang     = OCR_LANG
        self.ocr_config   = OCR_CONFIG
        self.debug_dir    = DEBUG_DIR

        os.makedirs(self.debug_dir, exist_ok=True)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Created (or already existed) debug directory: %s", self.debug_dir)

    def dilate_for_cells(self, gray_img: np.ndarray, page_index: int) -> np.ndarray:
        """
        Apply horizontal and vertical dilation to a grayscale image to prepare for cell detection.

        Parameters:
        gray_img (np.ndarray): Grayscale image of the page.
        page_index (int): Index of the current page (for debug folder naming).

        Returns:
        np.ndarray: Dilated binary image highlighting potential cell regions.
        """
        page_dir = os.path.join(self.debug_dir, f"page_{page_index:02d}")
        os.makedirs(page_dir, exist_ok=True)
        logger.debug("Creating debug subfolder: %s", page_dir)

        _, thresh = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if logger.isEnabledFor(logging.DEBUG):
            path_thresh = os.path.join(page_dir, "debug_thresh.png")
            cv2.imwrite(path_thresh, thresh)
            logger.debug("Page %d: saved Otsu threshold image → %s", page_index, path_thresh)

        dilated = cv2.dilate(thresh, self.ker_words, iterations=1)
        if logger.isEnabledFor(logging.DEBUG):
            path_horiz = os.path.join(page_dir, "debug_dilated_horiz.png")
            cv2.imwrite(path_horiz, dilated)
            logger.debug("Page %d: saved horizontally dilated image → %s", page_index, path_horiz)

        dilated = cv2.dilate(dilated, self.ker_simple, iterations=1)
        if logger.isEnabledFor(logging.DEBUG):
            path_final = os.path.join(page_dir, "debug_dilated_final.png")
            cv2.imwrite(path_final, dilated)
            logger.debug("Page %d: saved final dilated image → %s", page_index, path_final)

        return dilated

    def find_cell_contours(self, dilated: np.ndarray):
        """
        Find contours in a dilated image representing cell boundaries.

        Parameters:
        dilated (np.ndarray): Dilated binary image from dilate_for_cells.

        Returns:
        list: List of contours detected by cv2.findContours.
        """
        contours, _ = cv2.findContours(dilated.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        logger.debug("Detected %d cell contours", len(contours))
        return contours

    def convert_contours_to_boxes(self, contours):
        """
        Convert contours to bounding boxes and filter by size thresholds.

        Parameters:
        contours (list): List of contours detected by find_cell_contours.

        Returns:
        list: List of tuples (x, y, w, h) for bounding boxes that meet size criteria.
        """
        boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w * h >= self.min_area and w >= self.min_w and h >= self.min_h:
                boxes.append((x, y, w, h))
        logger.debug("Filtered down to %d bounding boxes after applying size thresholds", len(boxes))
        return boxes

    def sort_boxes_into_rows(self, boxes):
        """
        Sort bounding boxes into rows based on their vertical midpoints.

        Parameters:
        boxes (list): List of bounding boxes (x, y, w, h).

        Returns:
        list: Nested list of rows, where each row is a list of boxes sorted by x coordinate.
        """
        if not boxes:
            logger.debug("No bounding boxes to sort into rows")
            return []

        boxes_with_mid = [(x, y, w, h, y + h/2) for (x, y, w, h) in boxes]
        boxes_with_mid.sort(key=lambda b: b[4])
        heights = [h for (_, _, _, h, _) in boxes_with_mid]
        mean_h = np.mean(heights)
        thresh = mean_h / 2

        rows = []
        current_row = [boxes_with_mid[0]]
        for box in boxes_with_mid[1:]:
            _, y, _, h, y_mid = box
            _, prev_y, _, prev_h, prev_y_mid = current_row[-1]
            if abs(y_mid - prev_y_mid) <= thresh:
                current_row.append(box)
            else:
                rows.append(current_row)
                current_row = [box]
        rows.append(current_row)

        cleaned_rows = []
        for row in rows:
            row_boxes = [(x, y, w, h) for (x, y, w, h, _) in row]
            row_boxes.sort(key=lambda b: b[0])
            cleaned_rows.append(row_boxes)

        logger.debug("Split into %d rows of cells", len(cleaned_rows))
        return cleaned_rows

    def ocr_cells_from_rows(self, rows, gray_img, page_index: int):
        """
        Perform OCR on each cell region defined by the rows of bounding boxes.

        Parameters:
        rows (list): Nested list of bounding boxes rows.
        gray_img (np.ndarray): Grayscale image to crop cell regions from.
        page_index (int): Index of the current page (unused here, but kept for consistency).

        Returns:
        list: 2D list of recognized text for each cell in each row.
        """
        table = []
        for row_idx, row in enumerate(rows, start=1):
            current_row_texts = []
            for col_idx, (x, y, w, h) in enumerate(row, start=1):
                pad = self.cell_padding
                x1 = max(0, x - pad)
                y1 = max(0, y - pad)
                x2 = x + w + pad
                y2 = y + h + pad
                crop = gray_img[y1:y2, x1:x2]
                raw_text = pytesseract.image_to_string(
                    crop,
                    lang=self.ocr_lang,
                    config=self.ocr_config
                ).strip()
                text = " ".join(raw_text.splitlines())
                current_row_texts.append(text)
            table.append(current_row_texts)
        return table

    def extract_table(self, gray_img, page_index: int):
        """
        Detect cell contours in a grayscale image, draw bounding boxes for debug,
        and return OCR results for each cell.

        Parameters:
        gray_img (np.ndarray): Input grayscale image of the page.
        page_index (int): Index of the current page (for debug folder naming).

        Returns:
        list: 2D list of recognized text data for each cell.
        """
        dil = self.dilate_for_cells(gray_img, page_index)
        contours = self.find_cell_contours(dil)
        boxes = self.convert_contours_to_boxes(contours)
        rows = self.sort_boxes_into_rows(boxes)

        img_debug = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)
        for (x, y, w, h) in [b for row in rows for b in row]:
            cv2.rectangle(img_debug, (x, y), (x + w, y + h), (0, 255, 0), 1)
        if logger.isEnabledFor(logging.DEBUG):
            page_dir = os.path.join(self.debug_dir, f"page_{page_index:02d}")
            bbox_path = os.path.join(page_dir, "cells_bbox.png")
            cv2.imwrite(bbox_path, img_debug)
            logger.debug("Page %d: saved image with cell bounding boxes → %s", page_index, bbox_path)

        return self.ocr_cells_from_rows(rows, gray_img, page_index)
