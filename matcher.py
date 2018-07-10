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
parser.add_argument('--ignore-substring', dest='ignore', action='store', required=True)
parser.add_argument('--directory', dest='directory', action='store', required=True)
parser.add_argument('--dry-run', dest='dry_run', default=False, action='store_true')

args = parser.parse_args()

tvdb = None
show = None

file_list = glob.glob("{}/*.mp4".format(args.directory))

if not file_list:
    # print "No episodes for {}".format(args.series)
    sys.exit(0)
else:
    print "Series {} has episodes".format(args.series)

for show_file in file_list:
    file_noext, ext = os.path.splitext(show_file)
    show_name = re.compile(args.ignore).sub("", os.path.basename(file_noext)).strip()

    companions = []
    for companion_type in ['srt']:
        companions += glob.glob("{}*.{}".format(file_noext, companion_type))

    if tvdb is None:
        tvdb = tvdb_api.Tvdb()
        show = tvdb[args.series]

    print "Looking up {} episode \"{}\"".format(args.series, show_name)

    def filename_filter(filename):
        return filename.replace("/", "-")

    def matching_episode(episode):
        nice_name = u"%s S%02dE%02d %s" % (
            episode.season.show['seriesName'],
            episode['airedSeason'],
            episode['airedEpisodeNumber'],
            filename_filter(episode['episodeName']),
            )
        nice_path = os.path.join(u"Season %02d" % episode['airedSeason'], nice_name)

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

            for companion in companions:
                new_companion = os.path.join(args.destination, u"{}{}".format(nice_path, os.path.splitext(companion)[1]))
                shutil.move(companion, new_companion)

    def normalise(tvdb_episode_name):
        return re.sub(r"[^0-9a-z ]", '', tvdb_episode_name.lower())

    
    fuzzyMatch = process.extractOne(
        query=show_name,
        choices={episode['id']: episode['episodeName'] for season in show.values() for episode in season.values()},
        score_cutoff=90
    )
    if (fuzzyMatch):
        matching_episode(show.search(fuzzyMatch[2], 'id')[0])
    else:
        print u"WARNING: No adequate match found for {}.".format(show_name)
