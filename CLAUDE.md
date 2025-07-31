# Showmatcher Project

## Overview
A Python utility that renames TV episode files to a standardized format by matching episode titles against TVDB or using regex patterns.

## Purpose
- Takes messy TV episode filenames and renames them to standard format (e.g., "Show S01E01 Episode Name.mp4")
- Handles associated files like subtitles (.srt) and thumbnails (.jpg)
- Supports both TVDB episode lookup and regex pattern matching
- Useful for organizing downloaded content from sources like webdl or youtube-dl

## Key Features
- **Two matching modes:**
  - Episode name matching: Uses TVDB API with fuzzy string matching
  - Pattern matching: Extracts season/episode from filename patterns
- **Dry run mode** for testing
- **Config file support** (.matcherrc files)
- **Associated file handling** (moves .srt, .jpg files alongside videos)
- **Batch processing** support

## Current State

### Files
- `matcher.py` - Main Python script (149 lines)
- `requirements.txt` - Dependencies
- `README.md` - Comprehensive documentation with examples
- `venv/` - Virtual environment directory
- `.python-version` - Untracked Python version file

### Dependencies
- ConfigArgParse 0.12.0
- fuzzywuzzy 0.16.0  
- python-Levenshtein 0.12.0
- tvdb-api 2.0
- requests-cache 0.5.2

### Code Structure
The main script follows a simple flow:
1. Parse arguments (CLI or config file)
2. Find .mp4 files in source directory
3. For each file:
   - Extract episode name/info
   - Match against TVDB or use pattern
   - Generate standardized filename
   - Move file and sidecars to destination

### Current Issues/Observations
- Uses older Python 2 string formatting (u"" strings, .format())
- No error handling around TVDB API calls
- Limited to .mp4 files only
- Hardcoded sidecar types (.srt, .jpg)
- No unit tests present

### Usage Examples
```bash
# Episode name matching
python matcher.py --directory "/path/to/episodes" --destination "/path/to/output" --series-name "Show Name" --ignore-substring "prefix to remove"

# Pattern matching  
python matcher.py --directory "/path/to/episodes" --destination "/path/to/output" --series-name "Show Name" --naming-pattern "Show S(?P<season>[0-9]+)E(?P<episode>[0-9]+)"

# Config file mode
python matcher.py --config .matcherrc

# Batch processing
find /downloads -name .matcherrc -exec python matcher.py --config {} \;
```

### Git Status
- Current branch: master
- Untracked: .python-version
- Recent commits focus on Python 2/3 compatibility fixes