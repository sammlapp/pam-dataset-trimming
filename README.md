# trim

**trim.py** is a script used to remove (archive) audio recording files outside a specified period from a target folder. This is designed as part of a management and cleaning pipeline for data collected using Autonomous recording units (ARUs). While intended to monitor soundscapes and wildlife sounds, ARUs may record field teams performing installation, recovery, or maintenance. This script is designed to use field deployment logs to remove these recordings. 

To use this script, please make sure the target directory and deployment sheet in CSV format follow the standards below. 

By default, `python trim.py folder/` will create 3 destination folders in `folder/` and move files accordingly. 

- `in-period/`: files only containing recordings during the deployment period.
- `out-of-period/`:  files containing recordings outside the deployment period. Typically these are recordings from ARU that were not turned off after pick-up or that happened during ARU deployment/pick-up/swap.
- `not-processed/`: files that the script could not process. Usually, because the audio file contains no metadata and filenames 

This procedure does NOT delete any files. If necessary, the user can decide to delete the `out-of-period` folder after inspection. 

For more information, please visit [https://www.kitzeslab.org/](https://www.kitzeslab.org/)

## 1. Folder structure

The `trim` assumes audio files are organized in subdirectories. It also depends on a deployment sheet in CSV format in the parent folder. 

```
└── folder/
  ├── deployment-sheet.csv
  ├── subdir1/
     ├── 20220728_013000.mp3
     └── 20220728_010000.mp3
  └── subdir3/
     ├── 20220607_100000.WAV.mp3
     ├── 20220608_100000.WAV.mp3
     └── 20220609_100000.WAV.mp3
```

The original subdirectory structure is preserved in destination folders. 

The script will use audio file metadata to infer the beginning and end of recordings. If the file contains no metadata or it cannot be loaded, it will try to parse the filename assuming it follows the `yyyymmdd_hhmmss.audio_extension` standard, for example `20220728_013000.WAV`.


## 2. Deployment sheet

For `trim` to work please provide a CSV sheet containing the following columns: 

- `dropoff_date`: Date time of ARU deployment. The default format is `%m/%d/%y %H:%M.`
- `pickup_date`: Date and time for ARU recovery. The default format is `%m/%d/%y %H:%M.`
- `card_code`: Subdirectories names, typically micro-SD card IDs.

## 3. Usage

Usage:
```
python -i trim.py /path/to/target/folder/ --verbose --make-copies
```
Custom deployment sheet:
```
python -i trim.py /path/to/target/folder/ --rec-sheet my_deployment_sheet.csv  --pick-col my_pick_up_col_name --depl-col my_deployment_col_name --depl-col my_subirs_col_name --time-str '%m/%d/%y %H:%M' --verbose
```

