from scripts.scrapper.scrapper import Scrapper
import sys
import time

def main():
    location = sys.argv[1]
    deepness_level = sys.argv[2]
    threads_number = sys.argv[3]
    site = sys.argv[4]
    
    
    print(f"{'='*50}\nSCRAPPER RECAP\n{'='*50}\nData location: {location}\nDeepness level: "+
          f"{deepness_level}\nThreads amount: {threads_number}\nEntry website: {site}\n{'='*50}")
    input("Press enter to proceed...")
    scrapper = Scrapper(site, location)
    scrapper.crawler(site, int(deepness_level))
    scrapper.scrap_data(int(threads_number))
    
    
