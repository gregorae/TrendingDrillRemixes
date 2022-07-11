#!/usr/bin/python

import httplib2
import os
import random
import sys
import time
import json

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

# file paths
from utils.utils import get_authenticated_service

track_info_path = 'resources/videos/info/track_info.json'
tracks_pending = 'resources/tracks/pending_uploads/'
videos_pending = 'resources/videos/pending_uploads/'
tracks_archive = 'resources/tracks/archive/'
videos_archive = 'resources/videos/archive/'
id_path = 'upload/video_ids.json'

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError)
# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# Opening parameter JSON file
parameters = open('config/youtube_parameters.json', )
parameter = json.load(parameters)


def create_description(title, link):
    description_chunks = parameter["description"].split("[")
    before_title = description_chunks[0]
    before_link = description_chunks[1]
    rest = description_chunks[2]
    return before_title + title + before_link + link + rest


def parse_arguments(title: str, description: str, release_date: str):
    title_arg = "--title=" + f'{title}'
    file_arg = "--file=" + 'resources/videos/pending_uploads/' + title + '.mp4'
    desc_arg = "--description=" + f'{description}'
    date_arg = "--releaseDate=" + release_date
    return argparser.parse_args([file_arg, title_arg, desc_arg, date_arg])


def initialize_video_upload(youtube, options):
    tags = None
    if options.keywords:
        tags = options.keywords.split(",")

    release_date = options.releaseDate.split("T")[0].split("-")[:3]
    release_date.reverse()
    release_date = ".".join(release_date)
    release_time = ":".join(options.releaseDate.split("T")[1].split(".")[0].split(":")[:2])
    print(f'Video is scheduled to be released on {release_date} at {release_time} o\'clock')

    video_request_body = {
        "snippet": {
            "title": options.title,
            "description": options.description,
            "tags": tags,
            "categoryId": options.category,
        },
        "status": {
            "privacyStatus": options.privacyStatus,
            "publishAt": options.releaseDate,
        }
    }

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(video_request_body.keys()),
        body=video_request_body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting "chunksize" equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (If the upload fails,
        # it will still be retried where it left off.) This is usually a best
        # practice, but if you're using Python older than 2.6 or if you're
        # running on App Engine, you should set the chunksize to something like
        # 1024 * 1024 (1 megabyte).
        media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
    )

    return resumable_video_upload(insert_request)


# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_video_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    print("Video id '%s' was successfully uploaded." % response['id'])
                    return response['id']
                else:
                    exit("The upload failed with an unexpected response: %s" % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                     e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)


def upload_video(title, link, release_date):
    # Parsing the arguments
    description = create_description(title, link)
    args = parse_arguments(title, description, release_date)
    youtube = get_authenticated_service(args)
    try:
        return initialize_video_upload(youtube, args)
    except HttpError as e:
        print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
