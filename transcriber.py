import json
import logging
import tempfile
import traceback

import click

from app import (
    __app_name__,
    __version__,
    application,
    utils
)
from app.commands import queue
from app.transcript import Transcript
from app.transcription import Transcription
from app.logging import configure_logger, get_logger

logger = get_logger()


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"{__app_name__} v{__version__}")
    ctx.exit()


@click.option(
    "-v",
    "--version",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help="Show the application's version and exit.",
)
@click.group()
def cli():
    pass


def print_help(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    logging.info(ctx.get_help())
    ctx.exit()


whisper = click.option(
    "-m",
    "--model",
    type=click.Choice(
        [
            "tiny",
            "tiny.en",
            "base",
            "base.en",
            "small",
            "small.en",
            "medium",
            "medium.en",
            "large-v2",
        ]
    ),
    default="tiny.en",
    show_default=True,
    help="Select which whisper model to use for the transcription",
)
deepgram = click.option(
    "-D",
    "--deepgram",
    is_flag=True,
    default=False,
    help="Use deepgram for transcription",
)
diarize = click.option(
    "-M",
    "--diarize",
    is_flag=True,
    default=False,
    help="Supply this flag if you have multiple speakers AKA "
    "want to diarize the content",
)
summarize = click.option(
    "-S",
    "--summarize",
    is_flag=True,
    default=False,
    help="Summarize the transcript [only available with deepgram]",
)
github = click.option(
    "--github",
    is_flag=True,
    default=False,
    help="Push transcripts to a new branch on the origin bitcointranscripts repo",
)
upload_to_s3 = click.option(
    "-u",
    "--upload",
    is_flag=True,
    default=False,
    help="Upload processed model files to AWS S3",
)
save_to_markdown = click.option(
    "--markdown",
    is_flag=True,
    default=False,
    help="Save the resulting transcript to a markdown format supported by bitcointranscripts",
)
noqueue = click.option(
    "--noqueue",
    is_flag=True,
    default=False,
    help="Do not push the resulting transcript to the Queuer backend",
)
needs_review = click.option(
    "--needs-review",
    is_flag=True,
    default=False,
    help="Add 'needs review' flag to the resulting transcript",
)
model_output_dir = click.option(
    "-o",
    "--model_output_dir",
    type=str,
    default="local_models/",
    show_default=True,
    help="Set the directory for saving model outputs",
)
nocleanup = click.option(
    "--nocleanup",
    is_flag=True,
    default=False,
    help="Do not remove temp files on exit",
)
verbose_logging = click.option(
    "-V",
    "--verbose",
    is_flag=True,
    default=False,
    help="Supply this flag to enable verbose logging",
)

add_loc = click.option(
    "--loc",
    default="misc",
    help="Add the location in the bitcointranscripts hierarchy that you want to associate the transcript with",
)
add_title = click.option(
    "-t",
    "--title",
    type=str,
    help="Add the title for the resulting transcript (required for audio files)",
)
add_date = click.option(
    "-d",
    "--date",
    type=str,
    help="Add the event date to transcript's metadata in format 'yyyy-mm-dd'",
)
add_tags = click.option(
    "-T",
    "--tags",
    multiple=True,
    help="Add a tag to transcript's metadata (can be used multiple times)",
)
add_speakers = click.option(
    "-s",
    "--speakers",
    multiple=True,
    help="Add a speaker to the transcript's metadata (can be used multiple times)",
)
add_category = click.option(
    "-c",
    "--category",
    multiple=True,
    help="Add a category to the transcript's metadata (can be used multiple times)",
)


@cli.command()
@click.argument("source", nargs=1)
# Available transcription models and services
@whisper
@deepgram
# Available features for transcription services
@diarize
@summarize
# Options for adding metadata
@add_title
@add_date
@add_tags
@add_speakers
@add_category
@add_loc
# Options for configuring the transcription postprocess
@github
@upload_to_s3
@save_to_markdown
@noqueue
@needs_review
# Configuration options
@model_output_dir
@nocleanup
@verbose_logging
def transcribe(
    source: str,
    loc: str,
    model: str,
    title: str,
    date: str,
    tags: list,
    speakers: list,
    category: list,
    github: bool,
    deepgram: bool,
    summarize: bool,
    diarize: bool,
    upload: bool,
    verbose: bool,
    model_output_dir: str,
    nocleanup: bool,
    noqueue: bool,
    markdown: bool,
    needs_review: bool,
) -> None:
    """Transcribe the provided sources. Suported sources include: \n
    - YouTube videos and playlists\n
    - Local and remote audio files\n
    - JSON files containing individual sources\n

    Notes:\n
    - The https links need to be wrapped in quotes when running the command
    on zsh\n
    - The JSON can be generated by `preprocess-sources` or created manually
    """
    tmp_dir = tempfile.mkdtemp()
    configure_logger(logging.DEBUG if verbose else logging.INFO, tmp_dir)

    logger.info(
        "This tool will convert Youtube videos to mp3 files and then "
        "transcribe them to text using Whisper. "
    )
    try:
        transcription = Transcription(
            model=model,
            github=github,
            summarize=summarize,
            deepgram=deepgram,
            diarize=diarize,
            upload=upload,
            model_output_dir=model_output_dir,
            nocleanup=nocleanup,
            queue=not noqueue,
            markdown=markdown,
            needs_review=needs_review,
            working_dir=tmp_dir
        )
        if source.endswith(".json"):
            transcription.add_transcription_source_JSON(source)
        else:
            transcription.add_transcription_source(
                source_file=source, loc=loc, title=title, date=date, tags=list(tags), category=list(category), speakers=list(speakers),
            )
        transcription.start()
        if nocleanup:
            logger.info("Not cleaning up temp files...")
        else:
            transcription.clean_up()
    except Exception as e:
        logger.error(e)
        logger.info(f"Exited with error, not cleaning up temp files: {tmp_dir}")


@cli.command()
@click.argument("source", nargs=1)
@click.option(
    "--nocheck",
    is_flag=True,
    default=False,
    help="Do not check for existing sources using btctranscripts.com/status.json",
)
@click.option(
    "--no-batched-output",
    is_flag=True,
    default=False,
    help="Output preprocessing output in a different JSON file for each source",
)
# Options for adding metadata
@add_title
@add_date
@add_tags
@add_speakers
@add_category
@add_loc
def preprocess(
    source: str,
    loc: str,
    title: str,
    date: str,
    tags: list,
    speakers: list,
    category: list,
    nocheck: bool,
    no_batched_output: bool
):
    """Preprocess the provided sources. Suported sources include: \n
    - YouTube videos and playlists\n
    - JSON files containing individual sources\n

    Preprocessing will fetch all the given sources, and output them
    in a JSON alongside the available metadata.
    The JSON can then be edited and piped to `transcribe`
    """
    try:
        configure_logger(log_level=logging.INFO)
        logger.info(f"Preprocessing sources...")
        transcription = Transcription(
            batch_preprocessing_output=not no_batched_output)
        if source.endswith(".json"):
            transcription.add_transcription_source_JSON(source, nocheck=nocheck)
        else:
            transcription.add_transcription_source(
                source_file=source,
                loc=loc,
                title=title,
                date=date,
                tags=tags,
                category=category,
                speakers=speakers,
                preprocess=True,
                nocheck=nocheck
            )
        if not no_batched_output:
            # Batch write all preprocessed sources to JSON
            utils.write_to_json([preprocessed_source for preprocessed_source in transcription.preprocessing_output],
                                transcription.model_output_dir, "preprocessed_sources")
    except Exception as e:
        logger.info(f"Exited with error: {e}")


@cli.command()
@click.argument(
    "service",
    nargs=1,
    type=click.Choice(
        [
            "whisper",
            "deepgram"
        ]
    )
)
@click.argument("metadata_json_file", nargs=1)
# Options for configuring the transcription postprocess
@github
@upload_to_s3
@save_to_markdown
@noqueue
@needs_review
def postprocess(
    metadata_json_file,
    service,
    github: bool,
    upload: bool,
    markdown: bool,
    noqueue: bool,
    needs_review: bool,
):
    """Postprocess the output of a transcription service.
    Requires the metadata JSON file that is the output of the previous stage
    of the transcription process.
    """
    try:
        configure_logger(log_level=logging.INFO)
        utils.check_if_valid_file_path(metadata_json_file)
        transcription = Transcription(
            deepgram=service == "deepgram",
            github=github,
            upload=upload,
            markdown=markdown,
            queue=not noqueue,
            needs_review=needs_review,
        )
        logger.info(
            f"Postprocessing {service} transcript from {metadata_json_file}")
        with open(metadata_json_file, "r") as outfile:
            metadata_json = json.load(outfile)
        metadata = utils.configure_metadata_given_from_JSON(metadata_json)
        transcription.add_transcription_source(
            source_file=metadata["source_file"],
            loc=metadata["loc"],
            title=metadata["title"],
            category=metadata["category"],
            tags=metadata["tags"],
            speakers=metadata["speakers"],
            date=metadata["date"],
            youtube_metadata=metadata["youtube_metadata"],
            chapters=metadata["chapters"],
            link=metadata["media"],
            preprocess=False,
        )
        # Finalize transcription service output
        transcript_to_postprocess = transcription.transcripts[0]
        transcript_to_postprocess.transcription_service_output_file = metadata[
            f"{service}_output"]
        transcript_to_postprocess.result = transcription.service.finalize_transcript(
            transcript_to_postprocess)
        postprocessed_transcript = transcription.postprocess(transcript_to_postprocess)

        if transcription.bitcointranscripts_dir:
            transcription.push_to_github([postprocessed_transcript])
    except Exception as e:
        logger.error(e)
        traceback.print_exc()


cli.add_command(queue.commands)

if __name__ == '__main__':
    cli()
