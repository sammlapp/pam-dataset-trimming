from pathlib import Path
import os, yaml, shutil, time, json, argparse
import joblib

import pandas as pd
from glob import glob
from datetime import datetime, timezone, timedelta
import librosa
from tqdm.autonotebook import tqdm

from opensoundscape.audio import Audio
from opensoundscape.spectrogram import Spectrogram
import opensoundscape


# ---------------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=str, help="Path to .yaml config file")
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=False,
        help="Don't move files, just create sheet,.",
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        default=False,
        help="Do not print performed actions while running the script.",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------------
# Functions


def get_start_end_timestamps(file, duration_s):
    try:
        # function name depends on the version of opensoundscape
        if hasattr(opensoundscape.audio, "parse_metadata"):
            metadata = opensoundscape.audio.parse_metadata(file)
        else:
            metadata = opensoundscape.audio._metadata_from_file_handler(file)
        audio_start = metadata["recording_start_time"]
        audio_end = audio_start + timedelta(seconds=duration_s)
        return audio_start, audio_end
    except:
        return None, None


def parse_filename(filename, file_name_separator="_", aru="audio-moth"):

    if aru == "audio-moth":
        date_str = Path(filename).stem
    elif aru == "smm":
        date_str = "_".join(Path(filename).stem.split(file_name_separator)[-2:])

    dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
    dt = dt.replace(tzinfo=timezone.utc)
    return dt


def format_date(date_str, format):
    """_summary_

    Args:
        date_str (_type_): _description_
        format (_type_): _description_

    Returns:
        _type_: _description_
    """
    if isinstance(date_str, str):
        return datetime.strptime(date_str, format).replace(tzinfo=timezone.utc)
    else:
        return None


import filecmp


def move_file(src, dst):
    src = Path(src)
    dst = Path(dst)

    if dst.is_dir():
        # If dst is a directory, append the filename from src
        dst = dst / src.name

    if dst.exists():
        if filecmp.cmp(src, dst, shallow=True):  # Compare file size & edit time
            # delete the source file, as it already exists at dst and files are equivalent
            src.unlink()  # Delete the source file if identical
        else:
            # the destination exists but is not the same as source file. We need to investigate what happened.
            raise FileExistsError(
                f"Attempted to move {src} to {dst}, but destination file exists and is not equivalent to source file."
            )
    else:
        shutil.move(str(src), str(dst))  # Move the file


# ---------------------------------------------------------------------------------
def process_file(
    path,
    dir_name,
    drop_folder,
    deployment_time,
    pickup_time,
    aru,
    dry_run,
    verbose,
):
    path = Path(path)
    filename_j = path.name
    if verbose:
        print(f"Processing {filename_j}")
    action_i = ""
    try:

        duration_j = librosa.get_duration(path=path)

        # try to get start/end timestamps using audio file metadata
        audio_j_st, audio_j_end = get_start_end_timestamps(path, duration_j)
        # If it does not have metadata get if from filename
        if audio_j_st is None:
            if verbose:
                print(
                    f"{filename_j} has no metadata. Extracting recording time from filename."
                )
            audio_j_st = parse_filename(filename_j, aru=aru)
            audio_j_end = audio_j_st + timedelta(seconds=duration_j)

        drop_filepath_j = os.path.join(drop_folder, filename_j)

        # Trim actions ------------------------------------------------
        # Check if deployment happened after recording stated
        if deployment_time is not None and audio_j_st < deployment_time:
            # audio starts before deployment, so move it to out-of-period
            if verbose:
                print(
                    f'{"":<4}{dir_name} was deployed at {deployment_time.strftime("%Y-%m-%d %H:%M")}, but {filename_j} srtarts recording at {audio_j_st.strftime("%Y-%m-%d %H:%M")}'
                )
            if not dry_run:
                Path(drop_folder).mkdir(exist_ok=True)
                move_file(path, drop_filepath_j)

            action_i = "out of period start"

        # Check if pick-up happened before recording ended
        elif pickup_time is not None and audio_j_end > pickup_time:
            # audio ends after pick-up, so move it to out-of-period
            if verbose:
                print(
                    f'{"":<4}{dir_name} was picked-up at {pickup_time.strftime("%Y-%m-%d %H:%M")}, but this file contains audio until {audio_j_end.strftime("%Y-%m-%d %H:%M")}.'
                )
            if not dry_run:
                Path(drop_folder).mkdir(exist_ok=True)
                move_file(path, drop_filepath_j)
                action_i = "out of period end"
        else:
            # the file starts after deployment and ends before pick-up, so it is within the period
            if verbose:
                print(f'{"":<4}{filename_j} is within the correct period.')
            # do not move the file
            action_i = "within period"
    except:
        print(f"{filename_j} Could not be loaded")
        print(path)
        action_i = "could not be loaded, not processed."
        audio_j_st = None
        audio_j_end = None

    # File actions df ------------------------------------------------

    file_dict = {
        "sub_dir": [dir_name],
        "action": [action_i],
        "file": [path],
        "audio_start": [format_date_if_exists(audio_j_st)],
        "audio_end": [format_date_if_exists(audio_j_end)],
        "deployment_time": [format_date_if_exists(deployment_time)],
        "pickup_time": [format_date_if_exists(pickup_time)],
    }

    return file_dict


# Format dates
def format_date_if_exists(date):
    if date:
        date_str = date.strftime("%Y-%m-%d %H:%M:%S")
    else:
        date_str = "NA"
    return date_str


def trim(
    directory,
    recordings_sheet,
    aru,
    folder_var="card_code",
    deployment_time_col="dropoff_date",
    pickup_time_col="pickup_date",
    subdirectories_column="card_code",
    time_str_format="%m/%d/%y %H:%M",
    glob_patterns=["*.mp3", "*.wav", "*.WAV"],
    verbose=True,
    buffer_hours=None,
    dry_run=False,
    parallel_jobs=1,
):
    """Move files to out-of-period sub-folder if they are outside of deployment and pickup times specified in the recordings sheet.

    Loop through sub-directories (typically storing different cards/recorders) and files and
    move files outside of desired range to a separate location. The out-of-period folder can be deleted if desired.

    Files that are not in the list of file types to consider, and files within the deployment period, are left un-touched.

    Args:
        directory (str): Path to target directory containing subfolders with audio recordings.
        recordings_sheet (str): Path to recordings sheet containing recordings metadata.
        folder_var (str, optional): Column in [recordings_sheet] containing sub-directories names. Defaults to 'card_code'.
        deployment_time_var (str, optional): Column in [recordings_sheet] containing ARU deployment datetime. Defaults to 'dropoff_date'.
        pickup_time_var (str, optional): Column in [recordings_sheet] containing ARU pick-up datetime. Defaults to 'pickup_date'.
        time_str_format (str, optional): Column in [recordings_sheet] datetime format. Defaults to '%m/%d/%y %H:%M'.
        glob_patterns (list, optional): Globbing patterns for files to consider for in/out of period.
            Defaults to ['*.mp3', '*.wav', '*.WAV'].
            - these files are expected to have either metadata or names that can be parsed into datetime objects.
            You can include GPS Audiomoth gps-log files such as "2025*.TXT" or "2025*.PPS".
        verbose (bool, optional): Whether to print performed actions while running the script. Defaults to True.
        delay_h (int, optional): Buffer time in hours to add to deployment time and subtract from pickup time. Defaults to None.
            - This can be used to account for potential delays in deployment and pick-up.
            - Files within the buffer are considered out-of-period
        dry_run (bool, optional): [default: False] If True, will not move any files, but will still create the trimming actions sheet.
        parallel_jobs (int, optional): Number of parallel jobs to run. Defaults to 1 (ie. no parallelization).
    Returns:
            Saves trimmed versions of audio files in [destination_dir]
    """
    # Recordings sheet ---------------------------------------------------------
    recordings_sheet_path = os.path.join(directory, recordings_sheet)
    df = pd.read_csv(recordings_sheet_path)

    # Folder structure  ---------------------------------------------------------
    assert (
        pickup_time_col in df.columns
    ), f"{pickup_time_col} not present in {recordings_sheet}."
    assert (
        pickup_time_col in df.columns
    ), f"{pickup_time_col} not present in {recordings_sheet}."
    assert folder_var in df.columns, f"{folder_var} not present in {recordings_sheet}."

    subdir_names = list(df[folder_var].dropna().unique())
    subdirs = [os.path.join(directory, dir) for dir in subdir_names]

    out_dir = directory

    # Create destination directories
    drop_folder_path = os.path.join(out_dir, "out-of-period/")

    if not dry_run:
        Path(drop_folder_path).mkdir(exist_ok=True)

    # Loop through sub-directories ----------------------------------------------

    action_list = []
    for dir_i in tqdm(subdirs):
        dir_i = Path(dir_i)
        dir_i_name = dir_i.stem

        if dir_i.exists():
            print(dir_i)
            if verbose:
                print(f"Processing audio files in {dir_i_name}.")

            # List all files from that card/recorder
            audio_files_i = []

            for glob_pattern in glob_patterns:
                if aru == "audio-moth":
                    # we expect to find audio files in the root of each card/recorder folder
                    audio_files_i.extend(list(dir_i.glob(glob_pattern)))
                elif aru == "smm":
                    # we expect to find audio files in a subfolder called "Data" within each card/recorder folder
                    audio_files_i.extend(list(dir_i.glob(f"Data/{glob_pattern}")))
                else:
                    raise Exception(f"aru arg should be audio-moth or smm, got {aru}")
            audio_files_i.sort()

            # Get deployment/swap/recovery information from sheet
            folder_dpl_info = df[df[folder_var] == dir_i_name]
            assert (
                len(folder_dpl_info) == 1
            ), f"found {len(folder_dpl_info)} entries for {dir_i_name}! Must be 1 entry"
            folder_dpl_info = folder_dpl_info.iloc[0]

            # Will create None if missing for deployment_time and pickup_time
            try:
                deployment_time = format_date(
                    folder_dpl_info[deployment_time_col], time_str_format
                )
            except Exception as e:
                raise ValueError(
                    f"Failed to parse deployment_time value: {folder_dpl_info[deployment_time_col]} \n\tfor file in folder: {folder_dpl_info[subdirectories_column]}. \n\tExpected format based on config `datetime_format_str`: {time_str_format}"
                ) from e
            try:
                pickup_time = format_date(
                    folder_dpl_info[pickup_time_col], time_str_format
                )

            except Exception as e:
                raise ValueError(
                    f"Failed to parse pickup_time value: {folder_dpl_info[pickup_time_col]} \n\tfor file in folder: {folder_dpl_info[subdirectories_column]}. \n\tExpected format based on config `datetime_format_str`: {time_str_format}"
                ) from e

            if buffer_hours:
                if deployment_time:
                    deployment_time = deployment_time + timedelta(hours=buffer_hours)
                if pickup_time:
                    pickup_time = pickup_time - timedelta(hours=buffer_hours)

            # Loop through files individually to check if in period -------------------
            n_files_i = len(audio_files_i)
            if n_files_i > 0:

                # Create subfoldes in destination
                drop_folder_path_subir_j = os.path.join(drop_folder_path, dir_i_name)
                results = joblib.Parallel(n_jobs=parallel_jobs)(
                    joblib.delayed(process_file)(
                        f,
                        dir_i_name,
                        drop_folder_path_subir_j,
                        deployment_time,
                        pickup_time,
                        aru,
                        dry_run,
                        verbose,
                    )
                    for f in audio_files_i
                )
                action_list.append(results)

            else:
                if verbose:
                    print(f"Found zero audio files in {dir_i_name}! Skipping.")
                action_j = "directory with zero files"
                no_folder_dict = {"sub_dir": [dir_i_name], "action": [action_j]}
                action_list = action_list + [no_folder_dict]
        else:
            if verbose:
                print(f"{dir_i_name} not found in {directory}! Skipping.")
            action_j = "directory skipped"
            no_folder_dict = {"sub_dir": [dir_i_name], "action": [action_j]}
            action_list = action_list + [no_folder_dict]

    df = pd.concat([pd.DataFrame.from_dict(r) for r in action_list])
    print("Done!")

    return df


# ---------------------------------------------------------------------------------
if __name__ == "__main__":
    args = parse_args()

    with open(args.config, "r") as stream:
        try:
            cfg = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    assert cfg["aru_type"] in [
        "audio-moth",
        "smm",
    ], f'{args.aru} not defined correctly, please select "audio-moth" or "smm"'

    df = trim(
        directory=cfg["data_folder"],
        recordings_sheet=cfg["deployment_sheet"],
        aru=cfg["aru_type"],
        folder_var=cfg["subdirectories_column"],
        deployment_time_col=cfg["deployment_time_column"],
        pickup_time_col=cfg["pickup_time_column"],
        subdirectories_column=cfg["subdirectories_column"],
        verbose=(not args.silent),
        time_str_format=cfg["datetime_format_str"],
        glob_patterns=cfg["glob_patterns"],
        buffer_hours=cfg["buffer_hours"],
        dry_run=args.dry_run,
        parallel_jobs=cfg["parallel_jobs"],
    )

    today = time.strftime("%Y-%m-%d")
    df.to_csv(
        os.path.join(cfg["data_folder"], f"_trimming-actions-{today}.csv"), index=False
    )
