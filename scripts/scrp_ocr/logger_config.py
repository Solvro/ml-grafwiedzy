import logging
from config import DEBUG_MODE, DEBUG_DIR, LOG_FILE_NAME

def setup_logger():
    """
    Configure the global logger based on DEBUG_MODE.

    If DEBUG_MODE is True:
        - Set level to DEBUG.
        - Log to both console and a file in DEBUG_DIR.
    If DEBUG_MODE is False:
        - Set level to INFO.
        - Log to console only.

    Also suppresses verbose logging from pytesseract.
    """
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    if DEBUG_MODE:
        import os
        os.makedirs(DEBUG_DIR, exist_ok=True)

        logging.basicConfig(
            level=logging.DEBUG,
            format=fmt,
            datefmt=datefmt,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f"{DEBUG_DIR}/{LOG_FILE_NAME}", encoding="utf-8")
            ]
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format=fmt,
            datefmt=datefmt,
            handlers=[logging.StreamHandler()]
        )
    
    logging.getLogger("pytesseract").setLevel(logging.WARNING)
