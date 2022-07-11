import os
import json

# file paths
import sys
import random
import time

import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

track_info_path = 'resources/videos/info/track_info.json'
tracks_pending = 'resources/tracks/pending_uploads/'
videos_pending = 'resources/videos/pending_uploads/'
tracks_archive = 'resources/tracks/archive/'
videos_archive = 'resources/videos/archive/'
thumbnails_dir_path = 'resources/thumbnails/'

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

# Opening parameter JSON file
parameters = open('config/youtube_parameters.json', )
parameter = json.load(parameters)

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google API Console at
# https://console.developers.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "config/logindata.json"

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

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


def remove_illegal_characters(word, characters):
    for char in characters:
        word = word.replace(char, "")
    return word


def add_parsing_arguments():
    argparser.add_argument("--file", required=True, help="Video file to upload")
    argparser.add_argument("--title", help="Video title", default=parameter["title"])
    argparser.add_argument("--description", help="Video description",
                           default=parameter['description'])
    argparser.add_argument("--releaseDate", help="Release date of the video")
    argparser.add_argument("--category", default=parameter['category'],
                           help="Numeric video category. " +
                                "See https://developers.google.com/youtube/v3/docs/videoCategories/list")
    argparser.add_argument("--keywords", help="Video keywords, comma separated",
                           default=parameter['keywords'])
    argparser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES,
                           default=parameter['privacyStatus'], help="Video privacy status.")


def rotate_through_thumbnails():
    thumbnails = os.listdir(thumbnails_dir_path)
    index = len(thumbnails) + 1

    # Reversing the list in order to prevent overwriting thumbnail 2 with thumbnail 1 when increasing the index
    thumbnails.reverse()

    # Increasing the counter on every thumbnail
    for thumbnail in thumbnails:
        os.rename(thumbnails_dir_path + thumbnail, thumbnails_dir_path + f"thumbnail{index}.png")
        index -= 1

    os.rename(thumbnails_dir_path + f"thumbnail{index + len(thumbnails)}.png", thumbnails_dir_path + "thumbnail1.png")


def clean_up():
    # moving tracks to archive
    for track in os.listdir(tracks_pending):
        if track == ".gitignore":
            continue
        source = tracks_pending + track
        destination = tracks_archive + track
        try:
            os.rename(source, destination)
        except FileExistsError:
            os.remove(source)

    # moving videos to archive
    for video in os.listdir(videos_pending):
        if video == ".gitignore":
            continue
        source = videos_pending + video
        destination = videos_archive + video
        # Removing the temp videos
        if video.split(".")[-2] == "temp":
            os.remove(source)
        else:
            try:
                os.rename(source, destination)
            except FileExistsError:
                os.remove(source)

    with open(track_info_path, "w") as track_info:
        track_info_dict = {
            "tracks": []
        }
        json.dump(track_info_dict, track_info, indent=4)


def get_authenticated_service(args=None):
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
                                   scope=YOUTUBE_UPLOAD_SCOPE,
                                   message=MISSING_CLIENT_SECRETS_MESSAGE)
    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                 http=credentials.authorize(httplib2.Http()))


# Not working properly // 403: Permissions Denied Error
def add_song_to_playlist(playlist_id, video_id):
    youtube = get_authenticated_service()
    try:

        request_body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "videoId": video_id,
                },
            }
        }

        playlist_request = youtube.playlistItems().insert(
            part="snippet",
            body=request_body,
        )

        response = None
        error = None
        retry = 0
        while response is None:
            try:
                print("Uploading thumbnail ...")
                status, response = playlist_request.execute()
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
    except HttpError as e:
        print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
