from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException, NoSuchElementException, \
    StaleElementReferenceException
import time


class Chrome(webdriver.Chrome):

    def click_element(self, element_locator: tuple):

        max_wait = 10
        try:
            element = WebDriverWait(self, max_wait).until(
                EC.element_to_be_clickable(element_locator)
            )
            try:
                self.execute_script("arguments[0].scrollIntoView();", element)
                element.click()
            except ElementClickInterceptedException:
                print("Element click intercepted. Scrolling to the element and retrying...")
                # Scroll to the top of the page
                self.execute_script("arguments[0].scrollIntoView();", element)
                time.sleep(1)  # Wait for 1 second before retrying
                # Retry clicking the element
        except TimeoutException:
            print("The element is not clickable after waiting for 10 seconds")
        # Alternative way to handle click interception
        for _ in range(3):  # Retry up to 3 times
            try:
                element = self.find_element(*element_locator)
                element.click()
                break  # If click is successful, exit the loop
            except ElementClickInterceptedException:
                print("Element click intercepted. Retrying...")
                self.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)  # Wait for 1 second before retrying
