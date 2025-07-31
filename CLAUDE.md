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

## Recent Development Session (July 31, 2025)

### Major Changes Completed

#### 1. Python 3 Migration & TVDB API Upgrade
- **Problem**: Code was written for Python 2, using outdated TVDB API
- **Solution**: 
  - Migrated from Python 2 to Python 3 (removed `u""` strings, updated print statements)
  - Upgraded from legacy TVDB API to `tvdb_v4_official` library
  - Fixed dependency conflicts between `tvdb-api` and `requests-cache`
  - Added environment variable support for TVDB API key

#### 2. Pattern Matching Improvements
- **Problem**: Optional regex groups in patterns were causing crashes
- **Issue**: When `episode` or `season` groups were None, `int(None)` would fail
- **Solution**: Added proper validation for required groups in pattern matching mode
- **Better Error Messages**: Clear guidance when season/episode groups are missing, suggesting `--ignore-substring` for files without episode numbers

#### 3. Directory Creation Fix
- **Problem**: Matcher failed when destination directories didn't exist
- **Solution**: Added automatic directory creation with `os.makedirs(exist_ok=True)`

#### 4. Security Improvements
- **Problem**: Hardcoded API keys in source code
- **Solution**: Moved to environment variable (`TVDB_API_KEY`) with `.env` file support

#### 5. Comprehensive Test Suite Creation
Created a complete YAML-driven integration test framework:

**File Structure:**
- `tests/test_integration.py` - Main integration test suite (450+ lines)
- `tests/test_cases.yaml` - Test configuration with real episode data
- `tests/test_yaml_matcher.py` - Unit tests (legacy, replaced by integration tests)

**Test Features:**
- **Environment Isolation**: Tests never modify global `os.environ`
- **Real TVDB Integration**: Uses actual API calls with fuzzy matching
- **Multiple Test Scenarios**:
  - Pattern matching mode (regex-based, no TVDB needed)
  - Ignore-substring mode (TVDB lookup with fuzzy matching)
  - Multi-file handling (sidecar files like .srt, .jpg)
  - Dry-run mode verification
  - Error handling for invalid patterns
  - Character filtering in filenames
  - Both successful matches and no-match scenarios

**Test Data Structure:**
```yaml
test_suites:
  - name: "Peter Rabbit Pattern Matching"
    config:
      series-name: "Peter Rabbit (2013)"
      ignore-substring: "Peter Rabbit Series [0-9]+ "
    tests:
      - in: "Peter Rabbit Series 1 The Tale Of Benjamin-s New Map.mp4"
        out: "Season 01/Peter Rabbit (2013) S01E01 The Tale Of Benjamin-s New Map.mp4"
      - in: "Peter Rabbit Series 3 Made Up Episode.mp4"
        # No 'out' field = no match expected, file stays in input directory
```

#### 6. Two-Mode Architecture Clarification
- **Pattern Matching Mode** (`--naming-pattern`): Requires both season and episode groups in regex
- **Ignore-Substring Mode** (`--ignore-substring`): Uses TVDB fuzzy matching for episode names
- **Clear Error Messages**: When pattern matching fails, suggests using ignore-substring mode

### Current State

#### Files & Structure
- `matcher.py` - Main Python script (~260 lines, fully Python 3)
- `requirements.txt` - Updated dependencies for Python 3 and TVDB v4
- `tests/` - Complete integration test suite
- `.env` - Environment variables (API keys)
- `venv/` - Virtual environment

#### Dependencies (Updated)
```
ConfigArgParse>=1.0
fuzzywuzzy>=0.18.0
python-Levenshtein>=0.12.2
PyYAML>=6.0
tvdb_v4_official
```

#### Architecture Improvements
- **Automatic directory creation** for missing destination paths
- **Environment variable support** for sensitive configuration
- **Better error handling** with clear user guidance
- **Fuzzy matching** with 90% similarity threshold
- **Character filtering** removes problematic filename characters (`:<>/|?*\`)

#### Integration Test Results
✅ All 6 integration tests passing:
- Pattern matching with real files
- Multi-file (sidecar) handling  
- Dry-run mode verification
- Error handling with invalid configurations
- Filename character filtering
- Ignore-substring mode with TVDB lookup

### Usage Examples (Updated)

```bash
# Set up API key
export TVDB_API_KEY=your_api_key_here

# Episode name matching with TVDB lookup
python matcher.py --directory "/path/to/episodes" \
                 --destination "/path/to/output" \
                 --series-name "Peter Rabbit (2013)" \
                 --ignore-substring "Peter Rabbit Series [0-9]+ "

# Pattern matching (no TVDB needed)
python matcher.py --directory "/path/to/episodes" \
                 --destination "/path/to/output" \
                 --series-name "Test Show" \
                 --naming-pattern "Test Show S(?P<season>[0-9]+)E(?P<episode>[0-9]+) (?P<name>.*)"

# Run integration tests
cd tests && TVDB_API_KEY=your_key python3 test_integration.py
```

### Key Learnings
1. **Environment Variable Hygiene**: Test suites should never modify global environment
2. **Integration Testing**: Real API integration tests are valuable but need proper isolation
3. **Fuzzy Matching**: TVDB v4 fuzzy matching works well - "Cottontail-s" matches "Cotton-tail's"
4. **Clear Mode Separation**: Pattern matching vs. TVDB lookup serve different use cases
5. **Error Messages**: Good error messages guide users to correct solutions

### Next Steps / Future Improvements
- Consider fuzzy matching improvements (normalize punctuation, remove stop words)
- Add support for more video formats beyond .mp4
- Consider season/episode extraction from TVDB metadata
- Performance optimizations for large episode lists