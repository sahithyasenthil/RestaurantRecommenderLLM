import csv
import time

from datetime import datetime
from pathlib import Path
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def get_embedding(text, client, model="text-embedding-ada-002"):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding

if __name__ == "__main__":
    query = "vegetarian restaurant Pittsburgh"
    dir_path = f"/home/ec2-user/capstone/{query}_{int(datetime.now().timestamp())}"
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}/"
    options = Options()
    options.add_argument("--headless")
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    time.sleep(1)

    side_bar = driver.find_element(By.CSS_SELECTOR,f"div[aria-label='Results for {query}']")
    max_entities = 20
    max_reviews_per_entities = 50
    while True:
        side_bar.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.5)
        side_bar.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.5)
        html =driver.find_element(By.TAG_NAME, "html").get_attribute('outerHTML')
        if html.find("You've reached the end of the list.") != -1 or len(driver.find_elements(By.CLASS_NAME, "hfpxzc")) >= max_entities:
            break
    
    client = OpenAI(
        api_key="",
    )
    csv_header = ["customer_name", "rating", "review", "review_embedding"]
    for entity in driver.find_elements(By.CLASS_NAME, "hfpxzc"):
        reviews = []
        if len(entity.parent.find_elements(By.CLASS_NAME, "OcdnDb ")) > 0:
            # Sponsored
            continue
        entity_name = entity.get_attribute("aria-label")
        entity_url = entity.get_attribute("href")

        print(f"Processing {entity_name}, url={entity_url}")
        suboptions = Options()
        suboptions.add_argument("--headless")
        subservice = Service()
        subdriver = webdriver.Chrome(service=subservice, options=suboptions)
        subdriver.get(entity_url)
        subdriver.find_element(By.CSS_SELECTOR, f"button[aria-label^='Reviews for']").click()
        time.sleep(1)

        side_bar = subdriver.find_element(By.CLASS_NAME, "DxyBCb")
        last_cnt = 0
        while True:
            for _ in range(last_cnt + 2):
                side_bar.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.5)
            new_cnt = len(subdriver.find_elements(By.CLASS_NAME, "jJc9Ad"))
            if new_cnt == last_cnt or new_cnt >= max_reviews_per_entities:
                break
            last_cnt = new_cnt
        
        for review in subdriver.find_elements(By.CLASS_NAME, "jJc9Ad"):
            review_text = review.find_elements(By.CLASS_NAME, "wiI7pd")[0].text.replace("\n", " ") if len(review.find_elements(By.CLASS_NAME, "wiI7pd")) > 0 else ""
            if review.find_elements(By.CSS_SELECTOR, f"button[aria-label='See more']"):
                review.find_element(By.CSS_SELECTOR, f"button[aria-label='See more']").click()
                time.sleep(1)

                for block in review.find_elements(By.CLASS_NAME, "RfDO5c"):
                    review_text += " " + block.text.replace("\n", " ")

            reviews.append(
                (
                    review.find_element(By.CLASS_NAME, "d4r55").text,
                    len(review.find_elements(By.CLASS_NAME, "vzX5Ic")),
                    review_text,
                    " ".join(str(val) for val in get_embedding(review_text, client)),
                )
            )

        with open(f"{dir_path}/{entity_name}.csv", "w") as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(csv_header)
            writer.writerows(reviews)
        subdriver.quit()
    driver.quit()
