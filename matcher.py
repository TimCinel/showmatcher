import argparse
import glob
import os
import re
import sys
import shutil

import tvdb_api
import configargparse

from fuzzywuzzy import process

parser = configargparse.ArgParser(description='Match some shows', default_config_files=['.matcherrc'])

parser.add('-c', '--config', required=False, is_config_file=True)
parser.add_argument('--destination', dest='destination', action='store', required=True)

parser.add_argument('--series-name', dest='series', action='store', required=True)
parser.add_argument('--series-id', dest='series_id', action='store', type=int)

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
    print "Series {} has episodes".format(args.series)

for show_file in file_list:
    file_noext, ext = os.path.splitext(show_file)
    basename_noext = os.path.basename(file_noext)

    sidcars = []
    for sidecar_type in ['srt','jpg']:
        sidcars += glob.glob("{}*.{}".format(file_noext, sidecar_type))

    def filename_filter(filename):
        return filename.replace("/", "-")

    def matching_episode(episode):
        episode_name = episode['episodeName']

        if episode_name != '':
            episode_name = u' {}'.format(episode_name)

        if 'airedEpisodeNumber' in episode:
            full_name = u"%s S%02dE%02d %s" % (
                episode['seriesName'],
                episode['airedSeason'],
                episode['airedEpisodeNumber'],
                filename_filter(episode_name),
                )
            nice_path = os.path.join(u"Season %02d" % episode['airedSeason'], full_name)
        else:
            full_name = u"%s -%s" % (
                episode['seriesName'],
                filename_filter(episode_name),
                )
            nice_path = os.path.join(u"Season %d" % episode['airedSeason'], full_name)

        print u"Renaming to {}".format(nice_path)
        new_file = os.path.join(args.destination, u"{}{}".format(nice_path, ext))
        if args.dry_run:
            print u"Dry run!"
        elif os.path.exists(new_file):
            print u"WARNING: Couldn't move {}, destination file already exists.".format(show_file)
        elif not os.path.exists(os.path.dirname(new_file)):
            print u"WARNING: Couldn't move {}, destination directory does not exist.".format(show_file)
        else:
            shutil.move(os.path.join(args.directory, show_file), new_file)

            for sidecar in sidcars:
                new_companion = os.path.join(args.destination, u"{}{}".format(nice_path, os.path.splitext(sidecar)[1]))
                shutil.move(sidecar, new_companion)

    def normalise(tvdb_episode_name):
        return re.sub(r"[^0-9a-z ]", '', tvdb_episode_name.lower())

    def episode_find_by_name():
        global tvdb

        if tvdb is None:
            tvdb = tvdb_api.Tvdb()

        show = tvdb[args.series if args.series_id is None else args.series_id]

        episode_name = re.compile(args.ignore).sub("", basename_noext).strip()
        print "Looking up {} episode \"{}\"".format(args.series, episode_name)

        fuzzyMatch = process.extractOne(
            query=episode_name,
            choices={episode['id']: episode['episodeName'] for season in show.values() for episode in season.values()},
            score_cutoff=90
        )
        if (fuzzyMatch):
            episode = show.search(fuzzyMatch[2], 'id')[0]
            episode['seriesName'] = episode.season.show['seriesName']

            matching_episode(episode)
        else:
            print u"WARNING: No adequate TVDB match found for {}.".format(episode_name)

    def episode_known_pattern():
        episode_details = re.compile(args.naming_pattern).search(basename_noext)

        try:
            if 'year' in args.naming_pattern:
                year = int(episode_details.group('year'))
                month = int(episode_details.group('month'))
                day = int(episode_details.group('day'))

                label = u"%d-%02d-%02d" % (year, month, day)

                matching_episode({
                    'episodeName': label,
                    'airedSeason': year,
                    'seriesName': args.series,
                })
            else:
                season = int(episode_details.group('season'))
                episode = int(episode_details.group('episode'))
                name = episode_details.group('name')

                matching_episode({
                    'episodeName': name,
                    'seriesName': args.series,
                    'airedSeason': season,
                    'airedEpisodeNumber': episode,
                })
        except:
            print u"WARNING: No pattern match for {}.".format(basename_noext)

    if args.ignore:
        episode_find_by_name()
    else:
        episode_known_pattern()
