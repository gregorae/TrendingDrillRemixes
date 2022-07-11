import math
import os
import subprocess

import cv2
import moviepy.editor as mpe


def combine_audio(vidname, audname, outname, fps=30):
    my_clip = mpe.VideoFileClip(vidname)
    audio_background = mpe.AudioFileClip(audname)
    final_clip = my_clip.set_audio(audio_background)
    final_clip.write_videofile(outname, fps=fps)


def create_video():
    videos_path = "resources/videos/pending_uploads/"
    background_video_path = "resources/backgrounds/"
    img = cv2.imread(f"{background_video_path}background.png")
    height, width, layers = img.shape
    size = (width, height)

    tracks_path = "resources/tracks/pending_uploads/"
    for song in os.listdir(tracks_path):
        if song == ".gitignore":
            continue
        song_name = ".".join(song.split(".")[:-1])
        background_audio = mpe.AudioFileClip(tracks_path + song)
        duration = background_audio.duration

        out = cv2.VideoWriter(videos_path + song_name + ".temp" + ".mp4", cv2.VideoWriter_fourcc(*'mp4v'), 30, size)

        print(f"Creating video for: {song_name}")
        for i in range(math.ceil(duration) * 30):
            out.write(img)
        out.release()


def add_background_song():
    videos_path = "resources/videos/pending_uploads"
    tracks_path = "resources/tracks/pending_uploads/"
    for video in os.listdir(videos_path):
        if video == ".gitignore":
            continue
        video_name = video.replace(".temp.mp4", "")
        video = mpe.VideoFileClip(videos_path + "/" + video)
        for i in range(2):
            try:
                open(tracks_path + video_name + ".mp3")
                background_audio = mpe.AudioFileClip(tracks_path + video_name + ".mp3")
                video.audio = background_audio
                video.write_videofile(videos_path + "/" + video_name + ".mp4", fps=30)
                break
            except IOError:
                # Convert to mp3
                cmd = f'ffmpeg -i "{tracks_path + video_name}.wav" -vn -b:a 192k "{tracks_path + video_name}.mp3"'
                subprocess.call(cmd, shell=True)


def video_from_track():
    create_video()
    add_background_song()
