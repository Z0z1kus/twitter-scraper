from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import pandas as pd
import time
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
USERNAME = os.getenv("TWITTER_USERNAME")
PASSWORD = os.getenv("TWITTER_PASSWORD")

def setup_logger():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def twitter_login(driver):
    logging.info("Logging into Twitter...")
    driver.get("https://twitter.com/login")
    
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "text"))
        )
        username_input = driver.find_element(By.NAME, "text")
        username_input.send_keys(USERNAME)
        username_input.send_keys(Keys.RETURN)
        time.sleep(3)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys(PASSWORD)
        password_input.send_keys(Keys.RETURN)
        time.sleep(5)
        
        # Check for two-factor authentication
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            code = input("Enter the Twitter confirmation code: ")
            code_input = driver.find_element(By.NAME, "text")
            code_input.send_keys(code)
            code_input.send_keys(Keys.RETURN)
            time.sleep(5)
        except Exception:
            logging.info("No confirmation code required.")
        
        logging.info("Login successful!")
    except Exception as e:
        logging.error("Failed to log in: " + str(e))
        driver.quit()
        exit()

def scrape_interactions(driver, tweet):
    interactions = {"likes": [], "retweets": [], "replies": []}
    
    try:
        # Open Likes panel
        likes_button = tweet.find_element(By.XPATH, ".//div[@data-testid='like']")
        likes_button.click()
        time.sleep(3)
        interactions["likes"] = [user.text for user in driver.find_elements(By.XPATH, "//div[@data-testid='User-Name']")]
        driver.back()
    except Exception:
        logging.info("No likes found.")
    
    try:
        # Open Retweets panel
        retweets_button = tweet.find_element(By.XPATH, ".//div[@data-testid='retweet']")
        retweets_button.click()
        time.sleep(3)
        interactions["retweets"] = [user.text for user in driver.find_elements(By.XPATH, "//div[@data-testid='User-Name']")]
        driver.back()
    except Exception:
        logging.info("No retweets found.")
    
    try:
        # Scrape Replies
        interactions["replies"] = [reply.text for reply in tweet.find_elements(By.XPATH, "//div[@data-testid='reply']")] 
    except Exception:
        logging.info("No replies found.")
    
    return interactions

def save_tweets(tweets):
    df = pd.DataFrame(tweets, columns=["Timestamp", "Username", "Tweet ID", "Tweet", "Likes", "Retweets", "Replies"])
    df.to_csv("tweets.csv", index=False)
    
    with open("tweets.txt", "w", encoding="utf-8") as f:
        for tweet in tweets:
            f.write(f"----------------------------------------\n")
            f.write(f"Timestamp: {tweet[0]}\n")
            f.write(f"Username: {tweet[1]}\n")
            f.write(f"Tweet ID: {tweet[2]}\n")
            f.write(f"Tweet:\n{tweet[3]}\n\n")
            f.write(f"Likes: {len(tweet[4])} | Retweets: {len(tweet[5])} | Replies: {len(tweet[6])}\n")
            f.write(f"----------------------------------------\n\n")
    
    logging.info(f"Saved {len(tweets)} tweets to tweets.csv and tweets.txt")

def scrape_twitter(url, limit=None):
    logging.info(f"Starting Twitter scraper for URL: {url}")
    
    if "x.com" in url:
        url = url.replace("x.com", "twitter.com")
    
    options = webdriver.FirefoxOptions()
    service = Service("/usr/local/bin/geckodriver")
    driver = webdriver.Firefox(service=service, options=options)
    
    twitter_login(driver)
    
    logging.info("Opening Twitter profile page...")
    driver.get(url)
    
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//article[@data-testid='tweet']"))
        )
    except Exception as e:
        logging.error("Tweets did not load: " + str(e))
        driver.quit()
        return
    
    tweets = []
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    while limit is None or len(tweets) < limit:
        logging.info(f"Extracting tweets... {len(tweets)}/{limit if limit else '∞'}")
        tweet_elements = driver.find_elements(By.XPATH, "//article[@data-testid='tweet']")
        
        for tweet in tweet_elements:
            if limit and len(tweets) >= limit:
                break
            
            try:
                timestamp = tweet.find_element(By.TAG_NAME, "time").get_attribute("datetime")
                username = tweet.find_element(By.XPATH, ".//span[contains(text(), '@')]").text
                tweet_id = tweet.get_attribute("data-tweet-id")
                text = tweet.find_element(By.XPATH, ".//div[@data-testid='tweetText']").text
                interactions = scrape_interactions(driver, tweet)
                tweets.append((timestamp, username, tweet_id, text, interactions["likes"], interactions["retweets"], interactions["replies"]))
                logging.info(f"Extracted tweet: {text[:50]}...")
            except Exception:
                continue
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            logging.info("No more tweets to load, stopping scrolling.")
            break
        last_height = new_height
    
    driver.quit()
    save_tweets(tweets)

def scrape_all_tweets(url):
    logging.info("Scraping all available tweets...")
    scrape_twitter(url, limit=None)

if __name__ == "__main__":
    setup_logger()
    url = input("Enter Twitter profile URL: ")
    mode = input("Scrape all tweets? (y/n): ")
    if mode.lower() == 'y':
        scrape_all_tweets(url)
    else:
        limit = int(input("Enter number of tweets to scrape: "))
        scrape_twitter(url, limit)

