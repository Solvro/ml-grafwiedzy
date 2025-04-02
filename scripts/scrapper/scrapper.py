import requests
from bs4 import BeautifulSoup
import os
import threading
import time
from sys import platform
import random
from urllib.parse import urljoin

# Supported file extensions for downloading
FILE_EXTENSIONS = [".pdf", ".doc", ".docx", ".txt",
                   ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".rar"]


class Scrapper:
    def __init__(self, key: str, path: str):
        """
        Initialize the Scrapper with a search key and output path.
        
        Args:
            key: The keyword to search for in URLs
            path: The directory path to save scraped data
        """
        self.links = set()        # Stores all discovered links
        self.visited = set()      # Tracks visited URLs
        self.session = requests.Session()  # Persistent HTTP session
        self.key = key            # Search keyword
        self.path = path          # Output directory path
        print(f"Initialized scraper with keyword: {self.key}")

    def check_CAPTCHA(self, response: str, url: str) -> None:
        """
        Check if the response contains CAPTCHA and handle it.
        
        Args:
            response: The HTTP response text
            url: The URL being processed
        """
        if "captcha" in response.lower() or "are you a robot" in response.lower():
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            print(f"CAPTCHA encountered at: {url}")
            # TODO: Implement CAPTCHA handling with Selenium
            input("Please solve the CAPTCHA manually and press Enter to continue...")

    def gather_links(self, url: str) -> None:
        """
        Collect all relevant links from a given URL.
        
        Args:
            url: The URL to scrape for links
        """
        # Skip if URL already visited, doesn't contain keyword, or is a file
        if (url in self.visited or 
            not self.key in url or 
            any(ext in url for ext in FILE_EXTENSIONS)):
            return

        try:
            # Random delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            self.check_CAPTCHA(response.text, url)

            if response.text:
                soup = BeautifulSoup(
                    response.text, 'html.parser', from_encoding='utf-8')

                # Find all links containing the keyword
                new_links = {
                    urljoin(url, a['href'])
                    for a in soup.find_all('a', href=True)
                    if self.key in a['href']
                }

                self.links.update(new_links)
                self.visited.add(url)

            # Clear console based on OS
            if platform == "linux" or platform == "linux2":
                os.system("clear")
            print(
                f"Processed link: {url} | Unique links found: {len(self.links)}")

        except requests.RequestException as e:
            print(f"Error processing {url}: {e}")

    def crawler(self, start_url: str, crawl_depth: int = 3) -> None:
        """
        Crawl websites starting from a URL up to specified depth.
        
        Args:
            start_url: The initial URL to start crawling from
            crawl_depth: How many layers deep to crawl (default: 3)
        """
        self.gather_links(start_url)

        for current_depth in range(1, crawl_depth + 1):
            print(f"Crawling at depth: {current_depth}")

            # Process only unvisited links
            links_to_process = self.links - self.visited
            for link in list(links_to_process):
                self.gather_links(link)

    def scrap_data(self, thread_num: int) -> None:
        """
        Start multi-threaded scraping of collected links.
        
        Args:
            thread_num: Number of threads to use for scraping
        """
        print("Started scraping...")
        # Distribute links evenly across threads
        links = [list(self.links)[i::thread_num] for i in range(thread_num)]
        threads = []

        for link_group in list(links):
            thread = threading.Thread(
                target=self.scrap_links, args=(link_group,))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        print(f"Scraping completed. Links processed: {len(self.links)}")

    def scrap_links(self, thread_urls: list[str]) -> None:
        """
        Scrape content from a list of URLs (designed for thread execution).
        
        Args:
            thread_urls: List of URLs to be processed by this thread
        """
        PATH = self.path
        FILES_PATH = os.path.join(PATH, "files")
        
        # Ensure directories exist
        os.makedirs(PATH, exist_ok=True)
        os.makedirs(FILES_PATH, exist_ok=True)

        for url in thread_urls:
            try:
                # Random delay to avoid detection
                time.sleep(random.uniform(1, 3))
                response = requests.get(url)
                response.raise_for_status()

                self.check_CAPTCHA(response.text, url)

                soup = BeautifulSoup(response.text, "html.parser")

                # Download all supported files
                for a_tag in soup.find_all('a', href=True):
                    file_url = a_tag['href']
                    if any(file_url.lower().endswith(ext) for ext in FILE_EXTENSIONS):
                        if not file_url.startswith(('http://', 'https://')):
                            file_url = requests.compat.urljoin(url, file_url)

                        try:
                            file_response = requests.get(file_url, stream=True)
                            file_response.raise_for_status()

                            filename = os.path.basename(file_url)
                            file_path = os.path.join(FILES_PATH, filename)

                            with open(file_path, 'wb') as f:
                                for chunk in file_response.iter_content(1024):
                                    f.write(chunk)
                            print(f"File downloaded: {filename}")
                        except Exception as e:
                            print(f"Error downloading file {file_url}: {e}")

                # Extract text content from various HTML elements
                elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                                          'p',
                                          'ul', 'ol', 'li',
                                          'table', 'tr', 'th', 'td',
                                          'form', 'input', 'textarea', 'button'])

                # Use full page text if no specific elements found
                text_to_save = (response.text if len(elements) == 0
                               else "".join(element.getText() for element in elements))

                # Include URL in saved content
                text_to_save += f"\n\nSource URL: {url}"

                # Create safe filename from URL
                filename = "".join(url.replace(self.key, "").replace(
                    "/", "_").replace("https", "").replace("http", ""))
                filename = filename[:100]  # Limit filename length

                # Save extracted text
                with open(os.path.join(PATH, f"{filename}.txt"), "w",
                         encoding='utf-8') as file:
                    file.write(text_to_save)
                print(f"Content saved to: {PATH}")

            except requests.RequestException as e:
                print(f"Failed to process {url}: {str(e)}")
                continue
            