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

thumbnail_path = 'resources/thumbnails/thumbnail1.png'

# Opening parameter JSON file
parameters = open('config/youtube_parameters.json', )

# returns JSON object as
# a dictionary
parameter = json.load(parameters)

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

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

uploaded_video_ids = []


def create_description(title, link):
    description_chunks = parameter["description"].split("[")
    before_title = description_chunks[0]
    before_link = description_chunks[1]
    rest = description_chunks[2]
    return before_title + title + before_link + link + rest


def parse_arguments(title, description):
    title_arg = "--title=" + f'{title}'
    file_arg = "--file=" + 'resources/videos/pending_uploads/' + title + '.mp4'
    desc_arg = "--description=" + f'{description}'
    return argparser.parse_args([file_arg, title_arg, desc_arg])


def initialize_thumbnail_upload(youtube, video_id, tb_path):
    thumbnail_request = youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(tb_path, chunksize=-1, resumable=True)
    )

    resumable_thumbnail_upload(thumbnail_request)


# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_thumbnail_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print("Uploading thumbnail ...")
            status, response = insert_request.next_chunk()
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


def upload_thumbnail(video_id):
    youtube = get_authenticated_service()
    try:
        initialize_thumbnail_upload(youtube, video_id, thumbnail_path)
    except HttpError as e:
        print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
