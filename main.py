from track_download.sound_cloud_downloader import download
from upload.upload import upload
from video_creation.create_video_from_track import video_from_track
from utils.utils import clean_up


def main():
    clean_up()  # Cleaning up directories and files before starting
    download()  # Downloading the tracks from soundcloud
    video_from_track()  # Transforming the track to a video
    upload()  # Uploading all videos
    clean_up()  # Cleaning up after being done


if __name__ == '__main__':
    main()
