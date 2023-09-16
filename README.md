# trim

Remove (archive) audio recording files from directory if outside a specified period. This is designed as part of a management and cleaning pipeline for data collected using Autonomous recording units (ARUs). For more information, please visit [https://www.kitzeslab.org/](https://www.kitzeslab.org/)
 
## 1. Folder structure

The Target folder should contain:
 - A deployment sheet
 - Sub-directoroies containig audio files.

## 2. Deployment sheet

The deployment sheet should contain the following columns:
- `dropoff_date`
- `pickup_date`
- `card_code` containing the names of subdirectories [CHANGE FOR A CLI ARGUMENT]

## 3. Usage

Usage:
```
python -i trim.py /path/to/target/folder/ --rec-sheet appl2022a_deployment_sheet.csv  --verbose --make-copies

```
