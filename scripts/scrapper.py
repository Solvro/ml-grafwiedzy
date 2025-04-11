from selenium import webdriver
from selenium.webdriver.common.by import By
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import os
import threading

class Scrapper:
    def __init__(self):
        self.driver = webdriver.Firefox()
        self.links = []

    def gather_links(self, url: str, departament_id: str) -> None:
        self.driver.get(url)
        found = self.driver.find_elements(by=By.TAG_NAME, value="a")

        new_links = [link.get_attribute("href") for link in found
                        if link.get_attribute("href") and departament_id in
                        link.get_attribute("href")]

        self.links.extend(new_links)
        


    def crawler(self, start_url: str, departament_id: str,
                crawler_depth: int = 3) -> None:

        self.gather_links(start_url, departament_id)

        for _ in range(crawler_depth):
            for link in list(self.links):
                try:
                    self.gather_links(link, departament_id)
                except Exception as e:
                    print(f"Error during link executing {link}: {e}")

    def scrap_data(self, thread_num: int):
        print("Started scrapping...")
        links = [self.links[i::thread_num] for i in range(thread_num)]
        threads = []
        
        for link_group in links:
            thread = threading.Thread(target=self.scrap_links, args=(link_group,))
            thread.start() 
            threads.append(thread)
       
        for thread in threads:
            thread.join()

    def scrap_links(self, thread_links):

        PATH = "../data/scrapped_data/"

        os.makedirs(PATH, exist_ok=True)
        for link in thread_links:
            try:
                response = requests.get(link)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                                          'p',
                                          'ul', 'ol', 'li',
                                          'table', 'tr', 'th', 'td',
                                          'form', 'input', 'textarea', 'button'])

    
                text_to_save = (response.text if len(elements) == 0 
                           else "".join(element.getText() for element in elements))

                filename = "".join(c for c in link if c.isalnum()
                                   or c in ('-', '_', '.'))
                filename = filename[:100]


                with open(os.path.join(PATH, f"{filename}.txt"), "w",
                            encoding='utf-8') as file:
                        file.write(text_to_save)

            except requests.RequestException as e:
                print(f"Failed to process {link}: {str(e)}")
                continue


scrapper = Scrapper()

scrapper.crawler("https://wit.pwr.edu.pl/", "wit", 0)
scrapper.scrap_data(4)
