import re

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

class CrawlingUtil:

    def __init__(self, driver):
        self.driver = driver

    def extract_content_text(self, html_content:str):
        soup = BeautifulSoup(html_content, 'html.parser')

        content_div = soup.find('div', id='content')
        text = content_div.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text)
        text = text + self.driver.current_url
        return text

    def get_last_page(self):
        paging = self.driver.find_element(By.CSS_SELECTOR, "div.paginate")
        nums = [
            int(a.text)
            for a in paging.find_elements(By.CSS_SELECTOR, "a")
            if a.text.strip().isdigit()
        ]
        last_page = max(nums) if nums else 1
        return last_page