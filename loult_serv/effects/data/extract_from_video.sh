#!/usr/bin/env bash
# extracts sound from a video and converts it to the the format accepted by pysndx
ffmpeg -i "$1" -vn -acodec pcm_f32le -ar 16000 -ac 1 "$2"
