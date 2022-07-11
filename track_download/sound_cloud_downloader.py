import datetime
import json
import os
import sys
from datetime import date

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from scdl import scdl

from utils.utils import remove_illegal_characters

illegal_characters = ["|", "/", "\\", ":"]
track_info_path = "../../videos/info/track_info.json"


def result_list_length_reached(prev_list_length, max_list_length):
    return lambda web_driver: len(web_driver.find_element(By.CLASS_NAME, "lazyLoadingList__list")
                                  .find_elements(By.CLASS_NAME, "searchList__item")) > prev_list_length \
                              or len(web_driver.find_element(By.CLASS_NAME, "lazyLoadingList__list")
                                     .find_elements(By.CLASS_NAME, "searchList__item")) == max_list_length


def download():
    # Defining base URL
    base_url = "https://soundcloud.com"

    # Opening browser
    driver = webdriver.Chrome()
    driver.get(base_url + "/search/sounds?q=drill%20remix&filter.created_at=last_day&filter.duration=medium")

    number_of_tries = 3
    play_count_link_list = []
    no_tracks = 0
    list_length = 0
    first_try = True
    while number_of_tries > 0:
        try:
            if first_try:
                # Waiting for the button to render for accepting cookies
                # assert len(driver.find_elements(By.XPATH, '//button[text()="Ich stimme zu"]')) < 1
                wait = WebDriverWait(driver, 15)
                wait.until(ec.visibility_of_element_located((By.ID, "onetrust-accept-btn-handler")))
                # assert len(driver.find_elements(By.ID, "onetrust-accept-btn-handler")) >= 1

                # Clicking the accept cookies button
                cookie_button = driver.find_element(By.ID, "onetrust-accept-btn-handler")
                cookie_button.send_keys(Keys.RETURN)

            # Finding number of found tracks
            if no_tracks == 0:
                no_tracks = int(driver.find_element(By.CLASS_NAME, "lazyLoadingList__list")
                                .find_element(By.CLASS_NAME, "resultCounts").text.split(" ")[1])

            # finding a random object to send the page down keys
            button = driver.find_element(By.TAG_NAME, "button")

            # scrolling down the page as long as the length of the search results item list increases
            list_length = len(driver.find_element(By.CLASS_NAME, "lazyLoadingList__list")
                              .find_elements(By.CLASS_NAME, "searchList__item"))
            while list_length < no_tracks:
                for i in range(5):
                    button.send_keys(Keys.PAGE_DOWN)

                wait.until(result_list_length_reached(list_length, no_tracks))
                list_length = len(driver.find_element(By.CLASS_NAME, "lazyLoadingList__list")
                                  .find_elements(By.CLASS_NAME, "searchList__item"))

            # Iterating over all the list element to find the play count
            result_list = driver.find_element(By.CLASS_NAME, "lazyLoadingList__list")
            search_list_items = result_list.find_elements(By.CLASS_NAME, "searchList__item")
            for search_list_item in search_list_items:
                try:
                    sound_header = search_list_item.find_element(By.CLASS_NAME, "sound__header")
                    sound_footer = search_list_item.find_element(By.CLASS_NAME, "sound__footer")

                    play_count_string = sound_footer.find_element(By.CSS_SELECTOR, 'span[aria-hidden="true"]').text
                    play_count = int(play_count_string.replace(",", "").replace(".", "").replace("K", "000"))
                    anchor_to_song = sound_header.find_element(By.CLASS_NAME, "soundTitle__title")
                    link_to_song = anchor_to_song.get_attribute("href")
                    song_title = anchor_to_song.find_element(By.TAG_NAME, "span").text

                    song_title = remove_illegal_characters(song_title, illegal_characters)

                    # Adding play count and link combination to dictionary
                    play_count_link_list.append([play_count, [link_to_song, song_title]])
                except NoSuchElementException:
                    continue
            break  # breaking out of while loop on success
        except TimeoutException:
            number_of_tries -= 1
            if number_of_tries == 0:
                print("Timed out. Aborting ...")
                return
            else:
                print("Timed out, trying again ...")

                # Setting the number of tracks to the number of tracks in the list
                no_tracks = list_length
                first_try = False

    driver.close()

    play_count_link_list.sort(key=lambda pcll: pcll[0], reverse=True)

    # Getting the track urls
    track_urls = [x[1] for x in play_count_link_list]

    # Getting the most played ones
    most_played_track_urls = [track_urls[4]]

    # Changing working directory to the resources/tracks/pending_uploads folder
    os.chdir("resources/tracks/pending_uploads")

    # tracking the loop index
    index = 0
    for track_url, title in most_played_track_urls:
        # Resetting the arguments
        sys.argv = [sys.argv[0]]

        # Adding CLI arguments for downloader
        sys.argv.append("-l")
        sys.argv.append(track_url)
        scdl.main()

        # TODO: Check if song title on website match with download file name (especially double spaces)

        # determining the release date
        release_date = create_release_date(index, len(most_played_track_urls))

        # Writing info about link and title to config file
        write_track_info_to_config(title, track_url, release_date)

        index += 1

    os.chdir("../../..")


def create_release_date(video_index, number_of_tracks):
    today = str(date.today() + datetime.timedelta(1))
    hour = "10"
    if number_of_tracks != 1:
        hour = str(int(hour) + int(video_index * 8 / (number_of_tracks - 1)))
    if len(hour) < 2:
        hour = "0" + hour
    minute = "00"
    second = "00.0"
    return f"{today}T{hour}:{minute}:{second}+02:00"


def write_track_info_to_config(title, link, release_date):
    with open(track_info_path) as json_config:
        tracks = json.load(json_config)
        track_data = {
            "title": title,
            "link": link,
            "releaseDate": release_date,
        }

        if len(tracks["tracks"]) < 1:  # initialise array
            tracks["tracks"] = [track_data]
        else:
            tracks["tracks"].append(track_data)

    with open(track_info_path, "w") as json_config:
        json.dump(tracks, json_config, indent=4)
