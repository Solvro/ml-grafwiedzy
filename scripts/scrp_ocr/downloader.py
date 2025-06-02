import os
import tempfile
import requests
import logging
from bs4 import BeautifulSoup
from config import PDF_PAGE_URL, OUTPUT_DIR, DEBUG_MODE, DEBUG_DIR

logger = logging.getLogger(__name__)

class PDFDownloader:
    """
    Responsible for downloading the latest PDF file from the WPPT schedule page.

    Attributes:
        page_url (str): URL of the schedule page.
        download_path (str): Local path where the PDF will be saved.
    """

    def __init__(self):
        """
        Initialize PDFDownloader by setting the download path based on DEBUG_MODE.

        If DEBUG_MODE is True, create DEBUG_DIR and save as 'original.pdf' there.
        Otherwise, create a temporary file for the downloaded PDF.
        """
        self.page_url = PDF_PAGE_URL
        if DEBUG_MODE:
            os.makedirs(DEBUG_DIR, exist_ok=True)
            self.download_path = os.path.join(DEBUG_DIR, "original.pdf")
        else:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            self.download_path = tmp.name
            tmp.close()

    def get_latest_pdf_url(self) -> str:
        """
        Retrieve the URL of the latest PDF from the schedule page.

        Sends an HTTP GET request to self.page_url, parses the HTML to find
        the first <a> tag whose text contains "Harmonogram sesji WPPT"
        and whose href ends with ".pdf".

        Returns:
            str: Full URL of the PDF file.

        Raises:
            RuntimeError: If no matching PDF link is found on the page.
        """
        logger.info("Fetching schedule page: %s", self.page_url)
        resp = requests.get(self.page_url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.find_all("a", href=True)

        pdfs = [
            a["href"] for a in links
            if "Harmonogram sesji WPPT" in a.text and a["href"].lower().endswith(".pdf")
        ]
        if not pdfs:
            logger.error("No PDF link for the schedule was found on the page.")
            raise RuntimeError("No PDF link for the schedule was found on the page.")

        link = pdfs[0]
        full_url = link if link.startswith("http") else f"https://wppt.pwr.edu.pl{link}"
        logger.debug("Found PDF URL: %s", full_url)
        return full_url

    def download(self, pdf_url: str) -> None:
        """
        Download the PDF from the given URL and save it to download_path.

        Parameters:
            pdf_url (str): URL of the PDF to download.

        Raises:
            HTTPError: If the HTTP request for pdf_url fails.
        """
        logger.info("Starting PDF download: %s", pdf_url)
        r = requests.get(pdf_url, timeout=15)
        r.raise_for_status()

        with open(self.download_path, "wb") as f:
            f.write(r.content)

        if DEBUG_MODE:
            logger.info("Downloaded PDF to: %s", self.download_path)
        else:
            logger.debug("Downloaded PDF to temporary file: %s", self.download_path)
