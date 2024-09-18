from opensoundscape.audio import Audio
from opensoundscape.spectrogram import Spectrogram

import os, yaml, shutil, time, json, argparse

import pandas as pd
from glob import glob
from datetime import datetime, timezone, timedelta

#---------------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=str, help = 'Path to .yaml config file')
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=False, help = "Don't move files, just create sheet,.")
    parser.add_argument("--silent", action="store_true", default=False, help = "Do not print performed actions while running the script.")

    return parser.parse_args()

#---------------------------------------------------------------------------------
# Functions

def get_metadata(audio, duration_s):
    try: 
        audio_start = audio.metadata['recording_start_time']
        audio_end = (audio_start + timedelta(seconds = duration_s))
        return audio_start, audio_end
    except:
        return None, None

def parse_filename(filename, file_name_separator = '_', aru = 'audio-moth'):
    
    if aru == 'audio-moth':
        date_str, time_str = filename.split('.')[0].split(file_name_separator)
    elif aru == 'smm':
        date_str, time_str =  filename.split('.')[0].split(file_name_separator)[-2:]
    
    year = int(date_str[0:4])
    month = int(date_str[4:6])
    day = int(date_str[6:9])
    hour = int(time_str[0:2])
    minutes = int(time_str[2:4])
    seconds = int(time_str[4:6])
    
    return datetime(year, month, day, hour, minutes, seconds, tzinfo=timezone.utc)

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
    
#---------------------------------------------------------------------------------

def trim(directory, 
         recordings_sheet,
         aru,
         folder_var = 'card_code',
         deployment_time_var = 'dropoff_date',
         pickup_time_var = 'pickup_date',
         time_str_format = '%m/%d/%y %H:%M',
         audio_formats = ['mp3', 'wav','WAV'],
         gps_formats = ['PPS', 'pps', 'CSV', 'csv'],
         verbose = True,
         delay_h = None,
         dry_run = False):
    """Loop through sub-directories (typically storing different cards/recorders) and files and remove files outside of desired range.
    
    Args:
        directory (str): Path to target directory containing subfolders with audio recordings.
        recordings_sheet (str): Path to recordings sheet containing recordings metadata.
        folder_var (str, optional): Column in [recordings_sheet] containing sub-directories names. Defaults to 'card_code'.
        deployment_time_var (str, optional): Column in [recordings_sheet] containing ARU deployment datetime. Defaults to 'dropoff_date'.
        pickup_time_var (str, optional): Column in [recordings_sheet] containing ARU pick-up datetime. Defaults to 'pickup_date'.
        time_str_format (str, optional): Column in [recordings_sheet] datetime format. Defaults to '%m/%d/%y %H:%M'.
        audio_formats (list, optional): Possible audio formats. Defaults to ['mp3', 'wav','WAV'].
        gps_formats (list, optional): Possible GPS file formats for localization arrays. Defaults to ['PPS', 'pps', 'CSV', 'csv'].
        copy_files (bool, optional): If true creates copies of files in destination folder, if false move files. Defaults to False.
        verbose (bool, optional): Print actions for each file. Defaults to True.
    
    Returns:
            Saves trimmed versions of audio files in [destination_dir]
    """
    # Recordings sheet ---------------------------------------------------------
    recordings_sheet_path = os.path.join(directory, recordings_sheet)
    df = pd.read_csv(recordings_sheet_path)
    
    # Folder structure  ---------------------------------------------------------
    assert (pickup_time_var in df.columns), f'{pickup_time_var} not present in {recordings_sheet}.'
    assert (pickup_time_var in df.columns), f'{pickup_time_var} not present in {recordings_sheet}.'
    assert (folder_var in df.columns), f'{folder_var} not present in {recordings_sheet}.'
    
    subdir_names = list(df[folder_var].dropna().unique())
    subdirs = [os.path.join(directory, dir) for dir in subdir_names]
    
    
    # Create directory if copying and not moving files
    # if copy_files:
    #     out_dir = os.path.join(directory, '_trimmed/')
    #     if (not os.path.exists(out_dir)) & (not dry_run): 
    #         os.mkdir(out_dir)
    # else:
    out_dir = directory
    
    # Create destination directories
    keep_folder_path = os.path.join(out_dir, 'in-period/')
    drop_folder_path = os.path.join(out_dir, 'out-of-period/')
    not_processed_folder_path = os.path.join(out_dir, 'not-processed/') # only created if it happens
    
    if (not os.path.exists(keep_folder_path))& (not dry_run): 
        os.mkdir(keep_folder_path)
    if (not os.path.exists(drop_folder_path))& (not dry_run): 
        os.mkdir(drop_folder_path)
    
    # Loop through sub-directories ----------------------------------------------
    
    action_list = [] 
    for dir_i in subdirs:
        dir_i_name = dir_i.split('/')[-1] # grabbing second last because it is defined with a '/' in the name
        
        if os.path.exists(dir_i):
            if verbose: 
                print(f'Processing audio files in {dir_i_name}.')
            
            # List all files from that card/recorder
            audio_files_i = []
            
            formats = audio_formats + gps_formats
            for audio_extension in formats:
                if aru == 'audio-moth':
                    audio_files_i = audio_files_i + glob(os.path.join(dir_i, f'*.{audio_extension}')) 
                elif aru == 'smm':
                    audio_files_i = audio_files_i + glob(os.path.join(dir_i, f'Data/*.{audio_extension}')) 
                else:
                    raise Exception("ARU not defined correctly")
            audio_files_i.sort()
            
            # Get deployment/swap/recovery information from sheet
            row_i = df[df[folder_var] == dir_i_name]
            
            # Will crate None if missing
            deployment_time = format_date(row_i[deployment_time_var].item(), time_str_format)
            pickup_time = format_date(row_i[pickup_time_var].item(), time_str_format)

            if delay_h:
                if deployment_time: deployment_time = deployment_time + timedelta(hours = delay_h)
                if pickup_time: pickup_time = pickup_time - timedelta(hours = delay_h)
            
            # Loop through files individually to check if in period -------------------
            n_files_i = len(audio_files_i)
            if n_files_i > 0: 
                
                # Create subfoldes in destination
                keep_folder_path_subir_j = os.path.join(keep_folder_path, dir_i_name)
                drop_folder_path_subir_j = os.path.join(drop_folder_path, dir_i_name)
                
                for file_j in audio_files_i:
                    # filename_j =   '/'.join(file_j.split('/')[-2:])
                    filename_j =   file_j.split('/')[-1]
                    if verbose: print(f'Processing {filename_j}')
                    
                    try:
                        audio_j = Audio.from_file(file_j)
                        duration_j = audio_j.duration
                        
                        # If it does not have metadata get if from filename
                        audio_j_st, audio_j_end  = get_metadata(audio_j, duration_j)
                        if audio_j_st is None:
                            if verbose: print(f'{filename_j} has no metadata. Extracting recording time from filename.')
                            audio_j_st = parse_filename(filename_j, aru = aru)
                            audio_j_end = audio_j_st + timedelta(seconds = duration_j)
                        
                        drop_filepath_j = os.path.join(drop_folder_path_subir_j, filename_j)
                        keep_filepath_j = os.path.join(keep_folder_path_subir_j, filename_j)
                    
                        # Trim actions ------------------------------------------------
                        # Check if deployment happened after recording stated
                        if deployment_time is not None and audio_j_st < deployment_time:
                            if verbose: print(f'{"":<4}{dir_i_name} was deployed at {deployment_time.strftime("%Y-%m-%d %H:%M")}, but {filename_j} srtarts recording at {audio_j_st.strftime("%Y-%m-%d %H:%M")}')
                            if not dry_run:
                                if not os.path.exists(drop_folder_path_subir_j): os.mkdir(drop_folder_path_subir_j)
                                shutil.move(file_j, drop_filepath_j)
                            action_i = 'out of period start'
                            
                        # Check if pick-up happened before recording ended
                        elif pickup_time is not None and audio_j_end > pickup_time:
                            if verbose: print(f'{"":<4}{dir_i_name} was picked-up at {pickup_time.strftime("%Y-%m-%d %H:%M")}, but this file contains audio until {audio_j_end.strftime("%Y-%m-%d %H:%M")}.')
                            if not dry_run:
                                if not os.path.exists(drop_folder_path_subir_j): os.mkdir(drop_folder_path_subir_j)
                                shutil.move(file_j, drop_filepath_j)
                                action_i = 'out of period end'
                        else:
                            if verbose: print(f'{"":<4}{filename_j} is within the correct period.')
                            if not dry_run:
                                if not os.path.exists(keep_folder_path_subir_j): os.mkdir(keep_folder_path_subir_j)
                                shutil.move(file_j, keep_filepath_j)
                            action_i = 'within period'
                    except:
                        print(f'{filename_j} Could not be loaded')
                        action_i = 'could not be loaded, not processed.'
                    
                    
                    # File actions df ------------------------------------------------
                    
                    # Format dates
                    def format_date_if_exists(date):
                        if date:
                            date_str = date.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            date_str = "NA"
                        return date_str
                    
                    
                    
                    file_dict = {
                        'sub_dir' : [dir_i_name],
                        'action' : [action_i],
                        'file' : [file_j],
                        'audio_start' : [format_date_if_exists(audio_j_st)],
                        'audio_end' : [format_date_if_exists(audio_j_end)],
                        'deployment_time' : [format_date_if_exists(deployment_time)],
                        'pickup_time': [format_date_if_exists(pickup_time)],
                        }
                    action_list = action_list + [file_dict]
                
                # Remove original directory after it is done
                # if not copy_files:
                
                # If directory is empty remove it
                if ((not os.listdir(dir_i)) & (not dry_run)):
                    os.rmdir(dir_i)
                
                # If it is not empty, we could not process all files for some reason
                else:
                    if verbose: print(f'{"":<4} Could not process all files in {dir_i_name}.')
                    if (not os.path.exists(not_processed_folder_path)) & (not dry_run): 
                        os.mkdir(not_processed_folder_path)
                    
                    # Create card specific subdirs
                    np_dir_i = os.path.join(not_processed_folder_path, dir_i_name)
                    if not dry_run: os.mkdir(np_dir_i)
                    
                    # Move not processed filese
                    for file_j in os.listdir(dir_i):
                        if not dry_run: shutil.move(os.path.join(dir_i, file_j), np_dir_i)
                    
                    if not dry_run:
                        os.rmdir(dir_i)
                
            else:
                if verbose: print(f'Found zero audio files in {dir_i_name}! Skiping.')
                action_j = 'directory with zero files'
                no_folder_dict ={'sub_dir' : [dir_i_name], 'action' : [action_j]}
                action_list = action_list + [no_folder_dict]
        else: 
            if verbose: 
                print(f'{dir_i_name} not found in {directory}! Skipping.')
            action_j = 'directory skipped'
            no_folder_dict ={'sub_dir' : [dir_i_name], 'action' : [action_j]}
            action_list = action_list + [no_folder_dict]
    
    df = pd.concat([pd.DataFrame.from_dict(r) for r in action_list])
    print('Done!')
    
    return df

#---------------------------------------------------------------------------------
if __name__ == "__main__":
    args = parse_args()
    
    with open(args.config, "r") as stream:
        try:
            cfg = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    
    assert cfg['aru_type'] in ['audio-moth', 'smm'], f'{args.aru} not defined correctly, please select "audio-moth" or "smm"'
    
    df = trim(
        directory = cfg['data_folder'], 
        recordings_sheet = cfg['deployment_sheet'],
        aru = cfg['aru_type'],
        folder_var = cfg['subdirectories_column'],
        deployment_time_var = cfg['deployment_time_column'],
        pickup_time_var = cfg['pickup_time_column'],
        verbose = (not args.silent), 
        time_str_format = cfg['datetime_format_str'],
        audio_formats = cfg['audio_formats'],
        gps_formats = cfg['gps_formats'],
        delay_h = cfg['delay_hours'],
        dry_run= args.dry_run)
    
    today = time.strftime("%Y-%m-%d")
    df.to_csv(os.path.join(cfg['data_folder'], f'_trimming-actions-{today}.csv'), index = False    )

