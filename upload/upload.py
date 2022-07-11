import json

from upload.thumbnail_uploader import upload_thumbnail
from upload.video_uploader import upload_video
from utils.utils import rotate_through_thumbnails, add_parsing_arguments, remove_illegal_characters

tracks_path = 'resources/videos/info/track_info.json'
illegal_characters = ["|", "/", "\\", ":"]


def upload():
    # adding the arguments for parsing
    add_parsing_arguments()

    # Loading the tracks that are to be uploaded from the info dictionary
    tracks_info = json.load(open(tracks_path))["tracks"]
    for track_info in tracks_info:
        # Extracting title, link and release date
        title = remove_illegal_characters(track_info["title"], illegal_characters)
        link = track_info["link"]
        release_date = track_info["releaseDate"]

        # Uploading the video and saving the video ID of the uploaded video
        video_id = upload_video(title, link, release_date)

        # Uploading a thumbnail to the previously uploaded video
        upload_thumbnail(video_id)

        # Rotating through the thumbnails
        rotate_through_thumbnails()
