import argparse
import glob
import os
import re
import sys
import shutil

import tvdb_v4_official
import configargparse

from fuzzywuzzy import process

parser = configargparse.ArgParser(description='Match some shows', default_config_files=['.matcherrc'])

parser.add('-c', '--config', required=False, is_config_file=True)
parser.add_argument('--destination', dest='destination', action='store', required=True)

parser.add_argument('--series-name', dest='series', action='store', required=True)
parser.add_argument('--series-id', dest='series_id', action='store', type=int)
parser.add_argument('--tvdb-api-key', dest='tvdb_api_key', action='store', 
                    default=os.environ.get('TVDB_API_KEY'),
                    help='TVDB API key (default: from TVDB_API_KEY environment variable)')

parser.add_argument('--directory', dest='directory', action='store', required=True)
parser.add_argument('--dry-run', dest='dry_run', default=False, action='store_true')

ignore_or_series = parser.add_mutually_exclusive_group(required=True)
ignore_or_series.add_argument('--ignore-substring', dest='ignore', action='store')
ignore_or_series.add_argument('--naming-pattern', dest='naming_pattern', action='store')

args = parser.parse_args()

tvdb = None

file_list = glob.glob("{}/*.mp4".format(args.directory))

if not file_list:
    # print "No episodes for {}".format(args.series)
    sys.exit(0)
else:
    print("Series {} has episodes".format(args.series))

for show_file in file_list:
    file_noext, ext = os.path.splitext(show_file)
    basename_noext = os.path.basename(file_noext)

    sidcars = []
    for sidecar_type in ['srt','jpg']:
        sidcars += glob.glob("{}.{}".format(file_noext, sidecar_type))

    def filename_filter(filename):
        return re.sub('[:<>/|?*\\\\]', '-', filename)

    def matching_episode(episode):
        episode_name = episode['episodeName']

        if episode_name != '':
            episode_name = ' {}'.format(episode_name)

        if 'airedEpisodeNumber' in episode:
            full_name = "{} S{:0>2d}E{:0>2d}{}".format(
                filename_filter(episode['seriesName']),
                episode['airedSeason'],
                episode['airedEpisodeNumber'],
                filename_filter(episode_name),
                )
            nice_path = os.path.join("Season {:0>2d}".format(episode['airedSeason']), full_name)
        else:
            full_name = "{} -{}".format(
                episode['seriesName'],
                filename_filter(episode_name),
                )
            nice_path = os.path.join("Season {:d}".format(episode['airedSeason']), full_name)

        print("Renaming to {}".format(nice_path))
        new_file = os.path.join(args.destination, "{}{}".format(nice_path, ext))
        if args.dry_run:
            print("Dry run!")
            return
        elif os.path.exists(new_file):
            print("WARNING: Couldn't move {}, destination file already exists.".format(show_file))
        else:
            # Create destination directory if it doesn't exist
            if not os.path.exists(os.path.dirname(new_file)):
                os.makedirs(os.path.dirname(new_file), exist_ok=True)
                print("Created directory: {}".format(os.path.dirname(new_file)))
            
            shutil.move(os.path.join(args.directory, show_file), new_file)

            for sidecar in sidcars:
                new_sidecar = os.path.join(args.destination, "{}{}".format(nice_path, os.path.splitext(sidecar)[1]))
                shutil.move(sidecar, new_sidecar)

    def normalise(tvdb_episode_name):
        return re.sub(r"[^0-9a-z ]", '', tvdb_episode_name.lower())

    def episode_find_by_name():
        global tvdb

        if tvdb is None:
            if not args.tvdb_api_key:
                print("ERROR: TVDB API key is required for episode name matching.")
                print("Set the TVDB_API_KEY environment variable or use --tvdb-api-key")
                print("Get your API key from: https://thetvdb.com/api-information")
                sys.exit(1)
            
            tvdb = tvdb_v4_official.TVDB(args.tvdb_api_key)

        # Clean up the episode name from the filename
        episode_name = re.compile(args.ignore).sub("", basename_noext).strip()
        print("Looking up {} episode \"{}\"".format(args.series, episode_name))

        try:
            # First, find the series
            series_id = args.series_id
            if series_id is None:
                # Use the search API to find the series by name
                try:
                    search_results = tvdb.search(args.series)
                    series_found = None
                    
                    if search_results:
                        # Look for exact or close matches in the search results
                        for result in search_results:
                            result_name = result.get('name', '').lower()
                            search_name = args.series.lower()
                            
                            # Try exact match first, then partial match
                            if (result_name == search_name or 
                                search_name in result_name or 
                                result_name in search_name):
                                series_found = result
                                # Extract numeric ID from the series ID string
                                series_id_str = result.get('tvdb_id', result.get('id', ''))
                                if isinstance(series_id_str, str) and series_id_str.isdigit():
                                    series_id = int(series_id_str)
                                elif isinstance(series_id_str, int):
                                    series_id = series_id_str
                                else:
                                    # Try to extract from compound ID like "series-78804"
                                    if isinstance(series_id_str, str) and '-' in series_id_str:
                                        series_id = int(series_id_str.split('-')[-1])
                                
                                print("Found series: {} (ID: {})".format(result.get('name'), series_id))
                                break
                    
                    if not series_found:
                        print("WARNING: Series '{}' not found in TVDB search results.".format(args.series))
                        return
                        
                except Exception as e:
                    print("ERROR: TVDB search failed: {}".format(e))
                    return

            # Get all episodes for the series
            all_episodes = []
            page = 0
            while True:
                try:
                    episodes_data = tvdb.get_series_episodes(series_id, page=page)
                    if 'episodes' not in episodes_data or not episodes_data['episodes']:
                        break
                    all_episodes.extend(episodes_data['episodes'])
                    page += 1
                    # Limit to prevent infinite loops
                    if page > 20:
                        break
                except:
                    break

            if not all_episodes:
                print("WARNING: No episodes found for series '{}'.".format(args.series))
                return

            # Build choices for fuzzy matching
            choices = {}
            for episode in all_episodes:
                ep_name = episode.get('name', '')
                if ep_name:
                    choices[episode.get('id', 0)] = ep_name

            if not choices:
                print("WARNING: No episode names found for fuzzy matching.")
                return

            # Perform fuzzy matching
            fuzzyMatch = process.extractOne(
                query=episode_name,
                choices=choices,
                score_cutoff=90
            )

            if fuzzyMatch:
                # Find the matched episode
                matched_episode = None
                for episode in all_episodes:
                    if episode.get('id') == fuzzyMatch[2]:
                        matched_episode = episode
                        break

                if matched_episode:
                    # Convert v4 episode format to old format for compatibility
                    episode_data = {
                        'episodeName': matched_episode.get('name', ''),
                        'airedSeason': matched_episode.get('seasonNumber', 1),
                        'airedEpisodeNumber': matched_episode.get('number', 1),
                        'seriesName': args.series,
                        'id': matched_episode.get('id', 0)
                    }
                    matching_episode(episode_data)
                else:
                    print("WARNING: Matched episode not found in episode list.")
            else:
                print("WARNING: No adequate TVDB match found for {}.".format(episode_name))

        except Exception as e:
            print("ERROR: TVDB lookup failed: {}".format(e))

    def episode_known_pattern():
        episode_details = re.compile(args.naming_pattern).search(basename_noext)

        try:
            if 'year' in args.naming_pattern:
                year = int(episode_details.group('year'))
                month = int(episode_details.group('month'))
                day = int(episode_details.group('day'))

                label = "{:d}-{:0>2d}-{:0>2d}".format(year, month, day)

                matching_episode({
                    'episodeName': label,
                    'airedSeason': year,
                    'seriesName': args.series,
                })
            else:
                # Validate that required groups are present
                if not episode_details.group('season'):
                    print("ERROR: Pattern matched but 'season' group is missing for: {}".format(basename_noext))
                    print("       The naming-pattern must include (?P<season>...) group")
                    return
                if not episode_details.group('episode'):
                    print("ERROR: Pattern matched but 'episode' group is missing for: {}".format(basename_noext))
                    print("       The naming-pattern must include (?P<episode>...) group") 
                    print("       Use --ignore-substring for files without episode numbers")
                    return
                    
                season = int(episode_details.group('season'))
                episode = int(episode_details.group('episode'))
                name = episode_details.group('name')

                matching_episode({
                    'episodeName': name,
                    'seriesName': args.series,
                    'airedSeason': season,
                    'airedEpisodeNumber': episode,
                })
        except Exception as e:
            print("WARNING: No pattern match for {}.".format(basename_noext))

    if args.ignore:
        episode_find_by_name()
    else:
        episode_known_pattern()
