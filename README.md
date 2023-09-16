# trim

Remove (archive) audio recording files from directory if outside a specified period. This is designed as part of a management and cleaning pipeline for data collected using Autonomous recording units (ARUs). For more information, please visit [https://www.kitzeslab.org/](https://www.kitzeslab.org/)

By default `python trim.py folder/` will create 3 destination folders in `folder/` and move files accordingly. 

- `in-period/`: files only containing recordings during the deployment period.
- `out-of-period/`:  files containing recordings outside the deployment period. Typically these are recordings from ARU that were not turned off after pick-up or that happened during ARU deployment/pick-up/swap.
- `not-processed/`: files that the script could not process. Usually, because the audio file contains no metadata and filenames 

This procedure does NOT delete any files. If necessary, the user can decide to delete the `out-of-period` folder after inspection. 

## 1. Folder structure
The Target folder should contain:
 - A deployment sheet
 - Sub-directoroies containig audio files.

```
└── folder/
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

The deployment sheet should contain the following columns:
- `dropoff_date`
- `pickup_date`
- `card_code` containing the names of subdirectories

## 3. Usage

Usage:
```
python -i trim.py /path/to/target/folder/ --rec-sheet appl2022a_deployment_sheet.csv  --verbose --make-copies

```
