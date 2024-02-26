# trim

**trim.py** is a script used to remove (archive in a different folder) audio recording files outside a specified period. This is designed as part of a management and cleaning pipeline for data collected using Autonomous recording units (ARUs). While intended to monitor soundscapes and wildlife sounds, ARUs may record field teams performing installation, recovery, or maintenance. This script is designed to use deployment log data containing the date and time of these activities to remove these recordings. 

By default, `python trim.py folder/` will create 3 destination folders in `folder/` and move files accordingly. 

- `in-period/`: files only containing recordings during the deployment period.
- `out-of-period/`:  files containing recordings outside the deployment period. Typically these are recordings from ARU that were not turned off after pick-up or that happened during ARU deployment/pick-up/swap.
- `not-processed/`: files that the script could not process. Usually, because the audio file contains no metadata and filenames 

This procedure does NOT delete any files. If necessary, the user can decide to delete the `out-of-period` folder after inspection. 

For more information, please visit [https://www.kitzeslab.org/](https://www.kitzeslab.org/)

## 1. Folder structure

The `trim` assumes audio files are organized in subdirectories and a file named `deployment-sheet.csv` in the parent folder containing columns for deployment and/or pick-up dates and times.

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

It is recommended to use the `--verbose` flag to print actions performed on each file:
```
python trim.py /path/to/target/folder/ --verbose
```

Additional command line arguments:

`--rec-sheet`: Custom filename for recordings sheet in parent folder containing recordings metadata.

`--pick-col`: Custom pick-up time column name in [`rec-sheet`]

`--depl-col`: Custom deployment time column name in [`rec-sheet`]

`--dirs-col`: Custom sub-directories name column name in [`rec-sheet`]

`--time-str` Dates formatting string. Defaults to `'%m/%d/%y %H:%M'`

`--make-copies`: Create trimmed copies of original files in the parent folder. The default behavior is to move files. This is useful for testing prior to moving the original files.

`--verbose`: Print performed actions while running the script.

`--delay`: Add a delay in hours to deployment time and subtract from pickup time.


