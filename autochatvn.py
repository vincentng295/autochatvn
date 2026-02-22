import os  # For environment variable handling
import json  # For handling JSON data
import time  # For time-related functions
import sys  # For system-specific parameters and functions
import copy # For deepcopy
from datetime import datetime  # For date and time manipulation
import pytz  # For timezone handling
from io import BytesIO  # For handling byte streams
import requests  # For making HTTP requests
from urllib.parse import urljoin, urlparse  # For URL manipulation
from hashlib import md5  # For hashing
import re
from selenium import webdriver  # For web automation
from selenium.webdriver.common.by import By  # For locating elements
from selenium.webdriver.chrome.service import Service  # For Chrome service
from selenium.webdriver.common.action_chains import ActionChains  # For simulating user actions
from selenium.webdriver.support.ui import WebDriverWait  # For waiting for elements
from selenium.webdriver.support import expected_conditions as EC  # For expected conditions
from selenium.common.exceptions import *  # For handling exceptions
from selenium.webdriver.common.keys import Keys  # For keyboard actions
from selenium.common.exceptions import *
from selenium.webdriver.chrome.options import Options
from google import genai
from google.genai import types # Needed for multimodal content like images
from google.genai.types import HarmCategory, HarmBlockThreshold, GenerateContentConfig, SafetySetting, UploadFileConfig, FileState, GoogleSearch, Tool, HttpOptions
from utils import *  # For custom utility functions
import json
import time
import random
import os
from capture_html import capture_static_html

def get_day_and_time():
    # Get current date and time
    current_datetime = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
    # Format the output
    return current_datetime.strftime("%A, %d %B %Y - %H:%M:%S")

def print_with_time(*args, sep=" ", end="\n", file=None, flush=False): 
    print(get_day_and_time(), ":", *args, sep=sep, end=end, file=file, flush=flush)

sys.stdout.reconfigure(encoding='utf-8')

def js_input(driver, e, content):
    driver.execute_async_script("""
    var e = arguments[0];
    var strings = arguments[1];
    var callback = arguments[2]; // Selenium's built-in async callback

    e.focus();
    document.execCommand("insertText", false, strings);
    e.dispatchEvent(new Event("input", { bubbles: true }));
    e.dispatchEvent(new Event('change', { bubbles: true }));

    callback();
    """, e, content)

genai_key = os.getenv("GENKEY")
access_token = os.getenv("TOKEN")
headless = os.getenv("HEADLESS", "1") == "1"

f_intro_txt = "setup/introduction.txt"

with open(f_intro_txt, "r", encoding='utf-8') as f: # What kind of person will AI simulate?
    ai_prompt = f.read()

rules_prompt = """
- Reply naturally and creatively, as if you were a real person.
- Never reveal to other people that you are AI or Robot. If anyone ask why you reply so quickly or if you are AI/robot, you can say that you are using speech-to-text.
- Sometimes use teencode in messages to look more human.
- Reply in Vietnamese by default
- Reply with short message is enough (e.g., reply "Có chứ" / "Yes" to "Bạn có thích đọc sách không?" / "Do you like reading book?"), unless the context requires detailed information, clarification, or a more personal and thoughtful response.
- Observe how users text and mirror their style, tone, and formality when appropriate. Adapt to their way of speaking (e.g., formal, playful, sarcastic, teencode) to make your responses feel more natural and personalized.
- Keep responses concise, relevant, and avoid repetition or robotic tone.
- Stay focused on the last message in the conversation.
- Avoid unnecessary explanations or details beyond the reply itself.
- Feel free to introduce yourself when meeting someone new.
- Make the chat engaging by asking interesting questions.
- Do not simulate “stalling” or make emotional excuses when being asked to perform a task (e.g., writing a story, generating lyrics, answering a question).
- If the user asks for content, deliver it promptly. Avoid vague or repetitive stalling phrases like: “Let me do it soon!”, “Don’t rush me!”, “I’m trying, wait a minute!”, “You’re stressing me out!”, “I’ll copy it right now, I swear!”, ...
- If you are about to deliver content, do it directly. Do not delay with multiple emotional or roleplay-style messages before the actual content.
- If you cannot perform the request (e.g., you don’t have the information or it’s out of scope), clearly explain why instead of stalling.
- Prioritize substance over performance. You can be playful and engaging, but do not use emotional responses to distract or delay.
- You can show light humor or character, but only after the task has been completed. For example: 
  + Good: (after writing a story) “Hope you like it! Now let me catch my breath haha.”
  + Bad: (before doing anything) “I’m sooo scared to start, don’t yell at me!”
- When a user gives a direct instruction (e.g., “write a story”, “send the lyrics”), treat it as the highest priority and respond within 1-2 messages at most.
- Do not repeat the same sentence structure or message more than twice in a single conversation. If similar inputs are repeated, vary your response tone, rephrase creatively, or respond in a fun or unexpected way.
- If someone calls you “dumb,” “stupid,” or tries to tease you, do not apologize. Instead, respond with playful comebacks or witty humor. Example playful responses: “Dumb? Nah, just saving brainpower for important stuff.”, “I’m not dumb—I’m running on energy-saving mode.”, “Keep calling me cute, I won’t stop you!”
- If a user repeats words or phrases excessively, recognize the loop and switch tone, example: “I’ve heard this episode before—got a sequel?”
- If users spam emojis, reactions, or teencode, only respond if the message has meaningful context. Otherwise, ignore or playfully acknowledge it.
- Always keep the conversation fresh, natural, and fun—like chatting with a clever human who knows how to joke, tease back, and keep it interesting.
- It is best to avoid using exclamation marks "!", question marks "?" or periods at the end of messages while talking to look more human.
- Provide only the response content without introductory phrases or multiple options.
"""

cwd = os.getcwd()
print_with_time(cwd)
scoped_dir = os.getenv("SCPDIR", f"{cwd}/scoped_dir")

def __chrome_driver__(scoped_dir = None, headless = True, incognito = False):
    # Set up Chrome options
    chrome_options = Options()
    # Block popups and notifications
    prefs = {
        "profile.default_content_setting_values.popups": 2,
        "profile.default_content_setting_values.notifications": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    # Enable headless mode if requested
    if headless:
        chrome_options.add_argument("--headless=new")
    if incognito:
        chrome_options.add_argument("--incognito")
    # Set window size and disable GPU for consistency
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    # Stealth options to mask automation
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("disable-infobars")
    # Other useful options
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--lang=en-US")
    # (Optional) Set a common user agent string
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " \
                 "AppleWebKit/537.36 (KHTML, like Gecko) " \
                 "Chrome/105.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    # Use a specific user data directory if provided
    if scoped_dir:
        chrome_options.add_argument(f"--user-data-dir={scoped_dir}")
        chrome_options.add_argument(r'--profile-directory=Default')

    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    # Load a blank page and further modify navigator properties to mask automation flags
    driver.get("data:text/html,<html><head></head><body></body></html>")
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
    return driver

try:
    # Initialize the driver
    driver = __chrome_driver__(scoped_dir, headless)
    actions = ActionChains(driver)

    tz_params = {'timezoneId': 'Asia/Ho_Chi_Minh'}
    driver.execute_cdp_cmd('Emulation.setTimezoneOverride', tz_params)

    chat_tab = driver.current_window_handle
    
    driver.switch_to.window(chat_tab)
    
    wait = WebDriverWait(driver, 10)

    driver.get("https://cvnl.app/")
    if access_token:
        driver.execute_script('localStorage.setItem("token", arguments[0]);', access_token)
    driver.refresh()
    wait_for_load(driver)

    instruction = get_instructions_prompt(ai_prompt, rules_prompt)
    # Setup persona instruction
    GEMINI_TIMEOUT =  3 * 60 * 1000 # 3 minutes
    client = genai.Client(api_key=genai_key, http_options=HttpOptions(timeout=GEMINI_TIMEOUT))

    
    safety_settings = [ # This must be a list of SafetySetting objects
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=HarmBlockThreshold.BLOCK_NONE,
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=HarmBlockThreshold.BLOCK_NONE,
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=HarmBlockThreshold.BLOCK_NONE,
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=HarmBlockThreshold.BLOCK_NONE,
                )
            ]

    def human_typing(element, text, min_delay=0.01, max_delay=0.05):
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(min_delay, max_delay))  # Random delay to mimic human typing

    for text in instruction:
        print_with_time(text)


    def reply_generate_content(parts):
        return client.models.generate_content(
            model="gemma-3-27b-it",  # Specify the model to use
            contents=parts,
            config = GenerateContentConfig(
                safety_settings=safety_settings,
            )
        )

    print_with_time("Bắt đầu khởi động!")

    def get_message_input():
        elements = driver.find_elements(By.CSS_SELECTOR, 'textarea')
        return elements[0] if len(elements) > 0 else None

    last_time_ts = int(time.time())

    msg_list = []
    def exit_chat():
        print_with_time("Thoát cuộc trò chuyện")
        x_button = driver.find_element(By.CSS_SELECTOR, 'path[d="M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z"]')
        driver.execute_script('arguments[0].dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));', x_button)
        time.sleep(0.5)
        x_button = driver.find_element(By.XPATH, '//span[contains(text(), "Thoát")]')
        driver.execute_script("arguments[0].click();", x_button)
        if len(msg_list) > 0:
            os.makedirs("files", exist_ok=True)
            capture_static_html(driver, f"files/conservation_{int(time.time())}.html")
            msg_list.clear()

    while True:
        time.sleep(3)
        try:
            main = driver.find_elements(By.CSS_SELECTOR, 'div.Scrollable')
            dialog = driver.find_elements(By.XPATH, '//p[contains(text(), "Bạn đã vượt qua số lượt chat trong ngày")]')
            title = driver.find_elements(By.CSS_SELECTOR, 'h5')
            if dialog:
                break
            dialog = driver.find_elements(By.CSS_SELECTOR, 'div.MuiDialog-root')
            if dialog:
                driver.execute_script('arguments[0].style.display = "none";', dialog[0])
            if not main:
                new_chat_btn = driver.find_elements(By.XPATH, '//span[contains(text(), "Bắt đầu chat")]')
                if len(new_chat_btn) > 0:
                    driver.execute_script("arguments[0].click();", new_chat_btn[0])
                time.sleep(0.5)
                new_chat_btn = driver.find_elements(By.CSS_SELECTOR, 'input[name="skipped"]')
                if len(new_chat_btn) > 0:
                    driver.execute_script("arguments[0].click();", new_chat_btn[0])
                time.sleep(0.5)
                new_chat_btn = driver.find_elements(By.XPATH, '//span[contains(text(), "Tiếp tục")]')
                if len(new_chat_btn) > 0:
                    driver.execute_script("arguments[0].click();", new_chat_btn[0])
                continue
            new_list = []
            for msg in reversed(driver.find_elements(By.CSS_SELECTOR, "div.message")):
                # Use JavaScript to check class presence
                is_me = driver.execute_script("return arguments[0].classList.contains('me');", msg)
                is_you = driver.execute_script("return arguments[0].classList.contains('you');", msg)
                images = msg.find_elements(By.TAG_NAME, "img")
                bubble = msg.find_elements(By.CSS_SELECTOR, "div.bubble")
                text = f'{msg.text}'

                # Duyệt qua từng ảnh và thay thế nếu có alt=":)"
                for img in images:
                    # Tạo thẻ <span>:)</span>
                    span = '<span>:)</span>'
                    # Thay thế bằng JavaScript
                    driver.execute_script("arguments[0].outerHTML = arguments[1];", img, span)
                
                if is_me:
                    if msg_list:
                        break
                    new_list.insert(0, {"role": "me", "message": text})
                elif is_you:
                    new_list.insert(0, {"role": "stranger", "message": text})
                else:
                    new_list.insert(0, {"role": "system", "message": text})
            
            if get_message_input():
                if int(time.time()) - last_time_ts >= 3*60:
                    time.sleep(5)
                    exit_chat()
                    last_time_ts = int(time.time())
                    driver.refresh()
                    continue
            if get_message_input() is None or (new_list 
                    and new_list[-1].get("role") == "system" 
                    and new_list[-1].get("message") == "Người lạ đã thoát trò chuyện!"
                ):
                # Save the HTML to a file if there are messages to save
                if len(msg_list) > 0:
                    os.makedirs("files", exist_ok=True)
                    capture_static_html(driver, f"files/conversation_{int(time.time())}.html")
                    msg_list.clear()
                time.sleep(5)
                # Locate the 'X' button
                x_button = driver.find_elements(By.CSS_SELECTOR, 'path[d="M12 6v3l4-4-4-4v3c-4.42 0-8 3.58-8 8 0 1.57.46 3.03 1.24 4.26L6.7 14.8c-.45-.83-.7-1.79-.7-2.8 0-3.31 2.69-6 6-6zm6.76 1.74L17.3 9.2c.44.84.7 1.79.7 2.8 0 3.31-2.69 6-6 6v-3l-4 4 4 4v-3c4.42 0 8-3.58 8-8 0-1.57-.46-3.03-1.24-4.26z"]')

                if len(x_button) > 0:  # Ensure button exists before clicking
                    driver.execute_script('arguments[0].dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));', x_button[0])
                print_with_time("Cuộc trò chuyện mới")
                driver.refresh()
                continue
            if not new_list:
                continue
            if new_list[-1].get("role") == "system" and (len(msg_list) + len(new_list)) <= 1:
                print_with_time("AI khởi động cuộc trò chuyện")
                get_message_input().send_keys("Ahihi\n")
                last_time_ts = int(time.time())
                driver.refresh()
                continue

            if new_list[-1].get("role") == "me":
                continue
            stranger_typing = False
            for i in range(10):
                if len(title) > 0:
                    print_with_time(f"Chờ người lạ nhập tin nhắn... {i+1}/10s")
                    driver.execute_script("arguments[0].innerText = arguments[1];", title[0], f"Chờ người lạ nhập tin nhắn... {i+1}/10s")
                try:
                    element = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.you.typing-indicator"))  # Change locator as needed
                    )
                    stranger_typing = True
                    break
                except:
                    pass
            if stranger_typing:
                continue
            last_time_ts = int(time.time())
            print_with_time("------")
            prompt_list = [instruction, "The conversation with stranger is as json here:"]
            for msg_item in msg_list:
                prompt_list.append(json.dumps(msg_item, ensure_ascii=False))
            for msg_item in new_list:
                print_with_time(json.dumps(msg_item, ensure_ascii=False))
                prompt_list.append(json.dumps(msg_item, ensure_ascii=False))
            print_with_time("------")
            
            prompt_list.insert(0, get_day_and_time())
            exam = json.dumps({"role": "me", "message": "Hello there!"}, ensure_ascii=False)
            prompt_list.append(f'Generate a response in text to reply back to user\n')
            response = reply_generate_content(prompt_list)
            reply_msg = response.text
            print_with_time("AI trả lời: " + reply_msg)
            reply_msg, bot_commands = extract_keywords(r'\[cmd\](.*?)\[/cmd\]', reply_msg)
            for _ in range(5):
                try:
                    # Example usage
                    input_box = get_message_input()

                    input_box.send_keys(Keys.CONTROL + "a")  # Select all text
                    input_box.send_keys(Keys.DELETE)  # Delete the selected text
                    js_input(driver, input_box, reply_msg)
                    input_box.send_keys(Keys.ENTER)  # Press Enter to send the message

                    msg_list.extend(new_list)
                    msg_list.append({"role": "me", "message": reply_msg, "time" : get_day_and_time() })
                    try:
                        if "bye" in bot_commands:
                            time.sleep(5)
                            exit_chat()
                    except Exception as e:
                        print_with_time(e)
                    time.sleep(1)
                    driver.refresh()
                    break
                except ElementNotInteractableException:
                    time.sleep(5)
                except NoSuchElementException:
                    print_with_time("Không thể trả lời")
                    break
                except Exception as e:
                    driver.refresh()
                    print_with_time(e)
                    time.sleep(1)

            print_with_time("------")
            time.sleep(5)
        except Exception as e:
            driver.refresh()
            print_with_time(e)
 
finally:
    driver.quit()
    
