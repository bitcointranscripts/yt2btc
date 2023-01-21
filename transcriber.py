import subprocess
import os
import click
from app import application
from app import __version__, __app_name__
from datetime import datetime
import time


@click.group()
def cli():
    pass


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"{__app_name__} v{__version__}")
    ctx.exit()


@click.command()
@click.argument('source', nargs=1)
@click.argument('loc', nargs=1)
@click.option('-m', '--model', type=click.Choice(['tiny', 'base', 'small', 'medium']), default='tiny',
              help='Options for transcription model'
              )
@click.option('-t', '--title', type=str, help="Supply transcribed file title in 'quotes'")
@click.option('-d', '--date', type=str, help="Supply the event date in format 'yyyy-mm-dd'")
@click.option('-T', '--tags', type=str, help="Supply the tags for the transcript in 'quotes' and separated by commas")
@click.option('-s', '--speakers', type=str, help="Supply the speakers for the transcript in 'quotes' and separated by "
                                                 "commas")
@click.option('-c', '--category', type=str, help="Supply the category for the transcript in 'quotes' and separated by "
                                                 "commas")
@click.option('-v', '--version', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True, help="Show the application's version and exit.")
def add(
        source: str,
        loc: str,
        model: str,
        title: str,
        date: str,
        tags: str,
        speakers: str,
        category: str,
) -> None:
    """Supply a YouTube video id and directory for transcription"""

    print("What is your github username?")
    username = input()
    curr_time = str(round(time.time() * 1000))
    if source.endswith('.mp3') or source.endswith('.wav'):
        print("audio file detected")
        if title is None:
            print("Please supply a title for the audio file")
            title = str(input())
        # process audio file
        filename = application.get_audio_file(source, title)
        print("processing audio file", filename)
        if filename is None:
            print("File not found")
            return
        if filename.endswith('wav'):
            filename = application.convert_wav_to_mp3(filename)
        result = application.process_mp3(filename, model)
        application.create_pr(result, source, title, date, tags, category, speakers, loc, username, curr_time,
                              filename[:-4])
    else:
        # process video or a playlist
        url = "https://www.youtube.com/watch?v=" + source
        videos = [url]
        if application.check_if_playlist(source):
            print("Playlist detected")
            url = "https://www.youtube.com/playlist?list=" + source
            videos = application.get_playlist_videos(url)
            if videos is None:
                print("Playlist is empty")
                return

        selected_model = model + '.en'

        event_date = str()
        if date:
            try:
                event_date = datetime.strptime(date, '%Y-%m-%d').date()
            except:
                print("Supplied date is invalid")
                return
        for video in videos:
            print("Transcribing video: " + video)
            filename = application.download_video(video)
            if filename is None:
                print("File not found")
                return
            application.convert(filename)
            result = application.process_mp3(filename, selected_model)
            application.create_pr(result, video, title, event_date, tags, category, speakers, loc, username, curr_time,
                                  filename[:-4])
    """ INITIALIZE GIT AND OPEN A PR"""
    branch_name = loc.replace("/", "-")
    subprocess.call(['bash', 'github.sh', branch_name, username, curr_time])
