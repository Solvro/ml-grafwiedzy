import os
import logging
import cv2
import numpy as np
from config import (
    PADDING,
    DILATE_STRONG_ITERATIONS,
    DILATE_WEAK_ITERATIONS,
    TRANSFORM_WIDTH_RATIO,
    VERT_ITERATIONS,
    VERT_KERNEL_SIZE,
    HORIZ_ITERATIONS,
    HORIZ_KERNEL_SIZE,
    DILATE_LINES_ITER,
    DEBUG_DIR
)

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    """
    Class responsible for processing a single page image:
    - perspective alignment
    - table line removal
    - preparing the image for cell detection
    All parameters are imported directly from config.py.
    """

    def __init__(self):
        """
        Initialize the ImagePreprocessor by loading configuration parameters
        and ensuring the debug directory exists.
        """
        self.padding            = PADDING
        self.dilate_strong_iter = DILATE_STRONG_ITERATIONS
        self.dilate_weak_iter   = DILATE_WEAK_ITERATIONS
        self.transform_ratio    = TRANSFORM_WIDTH_RATIO

        self.vert_iter    = VERT_ITERATIONS
        self.vert_kernel  = np.array(VERT_KERNEL_SIZE, dtype=np.uint8)
        self.horiz_iter   = HORIZ_ITERATIONS
        self.horiz_kernel = np.array(HORIZ_KERNEL_SIZE, dtype=np.uint8)

        self.dilate_lines_iter = DILATE_LINES_ITER
        self.debug_dir         = DEBUG_DIR

        os.makedirs(self.debug_dir, exist_ok=True)
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Created (or existing) debug directory: %s", self.debug_dir)

    def preprocess_image(self, pil_img, page_index: int):
        """
        Preprocess a single page image by:
          1. Converting PIL → BGR → grayscale → Otsu threshold → invert.
          2. Applying strong dilation to detect the page contour.
          3. Finding the largest contour, computing bounding box → order_points.
          4. Calculating new dimensions and applying the perspective transform.
          5. Removing table lines via remove_lines.
        
        Args:
            pil_img: PIL.Image object of the page.
            page_index: Index of the current page (integer).

        Returns:
            result: Cleaned image, either a BGR numpy array or a grayscale numpy array.
        """
        logger.info("Starting preprocessing for page %d", page_index)

        page_dir = os.path.join(self.debug_dir, f"page_{page_index:02d}")
        os.makedirs(page_dir, exist_ok=True)
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Created debug subfolder: %s", page_dir)

        # Convert PIL to BGR
        img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        if logger.isEnabledFor(logging.DEBUG):
            save_path = os.path.join(page_dir, "step_01_bgr.png")
            cv2.imwrite(save_path, img_bgr)
            logger.debug("Page %d: saved BGR image → %s", page_index, save_path)

        # 1. Grayscale → Otsu threshold → invert
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        if logger.isEnabledFor(logging.DEBUG):
            gray_path = os.path.join(page_dir, "step_02_gray.png")
            cv2.imwrite(gray_path, img_gray)
            logger.debug("Page %d: saved grayscale image → %s", page_index, gray_path)

        # 2. Denoise with Gaussian blur
        denoised = cv2.GaussianBlur(img_gray, (5, 5), 0)
        if logger.isEnabledFor(logging.DEBUG):
            denoise_path = os.path.join(page_dir, "step_03_denoised.png")
            cv2.imwrite(denoise_path, denoised)
            logger.debug("Page %d: saved denoised image → %s", page_index, denoise_path)

        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if logger.isEnabledFor(logging.DEBUG):
            thresh_path = os.path.join(page_dir, "step_04_threshold.png")
            cv2.imwrite(thresh_path, thresh)
            logger.debug("Page %d: saved Otsu threshold image → %s", page_index, thresh_path)

        inverted = cv2.bitwise_not(thresh)
        if logger.isEnabledFor(logging.DEBUG):
            inv_path = os.path.join(page_dir, "step_05_inverted.png")
            cv2.imwrite(inv_path, inverted)
            logger.debug("Page %d: saved inverted image → %s", page_index, inv_path)

        # 2. Strong dilation for contour detection
        dilated_strong = cv2.dilate(inverted, None, iterations=self.dilate_strong_iter)
        if logger.isEnabledFor(logging.DEBUG):
            dil_strong_path = os.path.join(page_dir, "step_06_dilated_strong.png")
            cv2.imwrite(dil_strong_path, dilated_strong)
            logger.debug("Page %d: saved strongly dilated image → %s", page_index, dil_strong_path)

        # 3. Find all contours
        contours, _ = self.find_contours(dilated_strong)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Page %d: detected %d contours", page_index, len(contours))

        largest = self.find_largest_contour(contours)

        H, W = img_bgr.shape[:2]
        if largest is not None:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Page %d: found largest contour with area = %.2f", page_index, cv2.contourArea(largest))
            pts = self.get_bounding_rect_points(largest, img_shape=(H, W))
            ordered = self.order_points(pts)
            new_w, new_h = self.calculate_new_dimensions(ordered, W)
            warped = self.apply_perspective_transform(img_bgr, ordered, new_w, new_h)
            if logger.isEnabledFor(logging.DEBUG):
                warp_path = os.path.join(page_dir, "step_07_warped.png")
                cv2.imwrite(warp_path, warped)
                logger.debug("Page %d: saved warped image → %s", page_index, warp_path)
            result = self.remove_lines(warped, page_dir, page_index)
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.warning("Page %d: no contour found, removing lines on original image", page_index)
            result = self.remove_lines(img_bgr, page_dir, page_index)

        logger.info("Finished preprocessing for page %d", page_index)
        return result

    def find_contours(self, binary_img):
        """
        Wrapper around cv2.findContours to detect contours in a binary image.

        Args:
            binary_img (np.ndarray): Binary (thresholded) image.

        Returns:
            contours: List of detected contours.
            hierarchy: Hierarchy array of contours.
        """
        contours, hierarchy = cv2.findContours(
            binary_img.copy(),
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_SIMPLE
        )
        return contours, hierarchy

    def find_largest_contour(self, contours):
        """
        Identify and return the contour with the largest area.

        Args:
            contours (list): List of contours to evaluate.

        Returns:
            contour_with_max (np.ndarray or None): Contour with maximum area, or None if list is empty.
        """
        max_area = 0
        contour_with_max = None
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > max_area:
                max_area = area
                contour_with_max = cnt
        return contour_with_max

    def order_points(self, pts):
        """
        Order four unordered points into the sequence:
        [top-left, top-right, bottom-right, bottom-left].

        Args:
            pts (np.ndarray): Array of four corner points in arbitrary order (shape (4,2)).

        Returns:
            rect (np.ndarray): Array of ordered points with shape (4,2).
        """
        pts = pts.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")

        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        return rect

    def calculate_new_dimensions(self, ordered_pts, existing_width):
        """
        Calculate new dimensions for perspective transform based on ordered corner points.

        Args:
            ordered_pts (np.ndarray): Four ordered corner points.
            existing_width (int): Width of the original image.

        Returns:
            (new_w, new_h) (tuple[int, int]): New width and height for the warped image.
        """
        reduced_w = int(existing_width * self.transform_ratio)
        top_left, top_right, bottom_right, bottom_left = ordered_pts

        width  = np.linalg.norm(bottom_right - bottom_left)
        height = np.linalg.norm(top_right - bottom_right)
        aspect = height / width if width != 0 else 1

        new_w = reduced_w
        new_h = int(new_w * aspect)
        logger.debug("Calculated new dimensions: width %d, height %d", new_w, new_h)
        return new_w, new_h

    def get_bounding_rect_points(self, contour, img_shape):
        """
        Compute a padded bounding rectangle around a contour and return its corner points.

        Args:
            contour (np.ndarray): Contour for which to compute the bounding rectangle.
            img_shape (tuple[int, int]): Shape (height, width) of the image to enforce bounds.

        Returns:
            pts (np.ndarray): Array of four corner points with padding (shape (4,2)).
        """
        x, y, w, h = cv2.boundingRect(contour)
        x_p = max(0, x - self.padding)
        y_p = max(0, y - self.padding)
        w_p = min(img_shape[1] - x_p, w + 2 * self.padding)
        h_p = min(img_shape[0] - y_p, h + 2 * self.padding)

        pts = np.array([
            [x_p,       y_p],
            [x_p + w_p, y_p],
            [x_p + w_p, y_p + h_p],
            [x_p,       y_p + h_p]
        ], dtype="float32")
        logger.debug(
            "Bounding rect: (%d,%d,%d,%d) with padding %d → points: %s",
            x, y, w, h, self.padding, pts.tolist()
        )
        return pts

    def apply_perspective_transform(self, img_bgr, ordered_pts, new_w, new_h):
        """
        Apply a perspective transform to warp the image to a new rectangular shape.

        Args:
            img_bgr (np.ndarray): Input BGR image.
            ordered_pts (np.ndarray): Four ordered corner points of the source region.
            new_w (int): Desired width of the warped image.
            new_h (int): Desired height of the warped image.

        Returns:
            warped (np.ndarray): Warped BGR image of size (new_h, new_w).
        """
        pts1 = np.float32(ordered_pts)
        pts2 = np.float32([
            [0,       0],
            [new_w,   0],
            [new_w, new_h],
            [0,     new_h]
        ])
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        warped = cv2.warpPerspective(img_bgr, matrix, (new_w, new_h))
        logger.debug("Applied warpPerspective, matrix:\n%s", matrix)
        return warped

    def remove_lines(self, img_bgr, page_dir: str, page_index: int):
        """
        Remove vertical and horizontal table lines from a BGR image.

        Steps:
          1. Convert to grayscale, apply simple threshold, then invert.
          2. Erode and dilate to isolate vertical lines.
          3. Erode and dilate to isolate horizontal lines.
          4. Combine both line masks and dilate.
          5. Subtract combined lines from inverted mask and remove noise.

        Args:
            img_bgr (np.ndarray): Input BGR image.
            page_dir (str): Path to the current page's debug directory.
            page_index (int): Index of the current page.

        Returns:
            cleaned (np.ndarray): Grayscale image with table lines removed.
        """
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        if logger.isEnabledFor(logging.DEBUG):
            gray_path = os.path.join(page_dir, "step_08_remove_gray.png")
            cv2.imwrite(gray_path, gray)
            logger.debug("Page %d: saved remove_lines grayscale → %s", page_index, gray_path)

        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        if logger.isEnabledFor(logging.DEBUG):
            thresh_path = os.path.join(page_dir, "step_09_remove_thresh.png")
            cv2.imwrite(thresh_path, thresh)
            logger.debug("Page %d: saved remove_lines threshold → %s", page_index, thresh_path)

        inv = cv2.bitwise_not(thresh)
        if logger.isEnabledFor(logging.DEBUG):
            inv_path = os.path.join(page_dir, "step_10_remove_inverted.png")
            cv2.imwrite(inv_path, inv)
            logger.debug("Page %d: saved remove_lines inverted → %s", page_index, inv_path)

        vert_eroded = self.erode_vertical_lines(inv)
        horiz_eroded = self.erode_horizontal_lines(inv)

        if logger.isEnabledFor(logging.DEBUG):
            vert_path = os.path.join(page_dir, "step_11_vert_eroded.png")
            cv2.imwrite(vert_path, vert_eroded)
            logger.debug("Page %d: saved erode_vertical → %s", page_index, vert_path)

        if logger.isEnabledFor(logging.DEBUG):
            horiz_path = os.path.join(page_dir, "step_12_horiz_eroded.png")
            cv2.imwrite(horiz_path, horiz_eroded)
            logger.debug("Page %d: saved erode_horizontal → %s", page_index, horiz_path)

        combined = cv2.add(vert_eroded, horiz_eroded)
        if logger.isEnabledFor(logging.DEBUG):
            combined_path = os.path.join(page_dir, "step_13_combined.png")
            cv2.imwrite(combined_path, combined)
            logger.debug("Page %d: saved remove_lines combined → %s", page_index, combined_path)

        combined_dilated = self.dilate_combined(combined)
        if logger.isEnabledFor(logging.DEBUG):
            dilated_path = os.path.join(page_dir, "step_14_combined_dilated.png")
            cv2.imwrite(dilated_path, combined_dilated)
            logger.debug("Page %d: saved remove_lines dilated → %s", page_index, dilated_path)

        without_lines = cv2.subtract(inv, combined_dilated)
        if logger.isEnabledFor(logging.DEBUG):
            without_lines_path = os.path.join(page_dir, "step_15_without_lines.png")
            cv2.imwrite(without_lines_path, without_lines)
            logger.debug("Page %d: saved remove_lines without_lines → %s", page_index, without_lines_path)

        cleaned = self.remove_noise(without_lines)
        if logger.isEnabledFor(logging.DEBUG):
            cleaned_path = os.path.join(page_dir, "step_16_cleaned.png")
            cv2.imwrite(cleaned_path, cleaned)
            logger.debug("Page %d: saved remove_lines cleaned → %s", page_index, cleaned_path)

        return cleaned

    def erode_vertical_lines(self, inv):
        """
        Isolate vertical table lines by eroding and then dilating horizontally.

        Args:
            inv (np.ndarray): Inverted binary image from remove_lines.

        Returns:
            np.ndarray: Binary mask of vertical lines.
        """
        eroded = cv2.erode(inv, self.vert_kernel, iterations=self.vert_iter)
        logger.debug("After vertical line erosion")
        return cv2.dilate(eroded, self.vert_kernel, iterations=self.vert_iter)

    def erode_horizontal_lines(self, inv):
        """
        Isolate horizontal table lines by eroding and then dilating vertically.

        Args:
            inv (np.ndarray): Inverted binary image from remove_lines.

        Returns:
            np.ndarray: Binary mask of horizontal lines.
        """
        eroded = cv2.erode(inv, self.horiz_kernel, iterations=self.horiz_iter)
        logger.debug("After horizontal line erosion")
        return cv2.dilate(eroded, self.horiz_kernel, iterations=self.horiz_iter)

    def dilate_combined(self, combined):
        """
        Thicken combined vertical and horizontal line masks before subtraction.

        Args:
            combined (np.ndarray): Combined binary mask of vertical+horiz lines.

        Returns:
            np.ndarray: Dilated mask of all table lines.
        """
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        logger.debug("Dilating combined lines, iterations = %d", self.dilate_lines_iter)
        return cv2.dilate(combined, kernel, iterations=self.dilate_lines_iter)

    def remove_noise(self, img):
        """
        Remove small artifacts by applying an erosion followed by dilation with a 2×2 kernel.

        Args:
            img (np.ndarray): Binary image after line subtraction.

        Returns:
            np.ndarray: Cleaned binary image with reduced noise.
        """
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        eroded = cv2.erode(img, kernel, iterations=1)
        logger.debug("After noise erosion")
        return cv2.dilate(eroded, kernel, iterations=1)
