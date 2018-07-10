# showmatcher

Take TV episode files named by episode title and rename them to a standard format

Might be useful in combination with [webdl](https://bitbucket.org/delx/webdl/) or 
[youtube-dl](https://github.com/rg3/youtube-dl/).

I tried to get FileBot to do this but ultimately couldn't. Now, as I write this README,
it occurs to me that I should've made a plugin for FileBot. Too bad - sunk cost fallacy,
I'm here now.

Features:

* Looks up episode title on TVDB to find Season / Episode and renames accordingly
* Uses fuzzy string matching
* Will rename any associated files (subtitles, for example) accordingly
* Supports "dry run" mode
* Supports CLI arguments being passed in a file

## Explained by examples

Assume we have these files...

    $ find "/home/me/iview-downloads/"
    /home/me/iview-downloads/four corners/Four Corners Series Outbreak.mp4
    /home/me/iview-downloads/four corners/Four Corners Series Outbreak.srt
    /home/me/iview-downloads/sarah duck/Sarah  Duck Boo Night.mp4

... and we want to rename them into something resembling a standard format, like:

    /home/me/tv/sarah duck/Season 03/Sarah Duck S03E31 Boo Night.mp4
    /home/me/tv/four corners/Season 2018/Four Corners (1961) S2018E31 Outbreak.mp4
    /home/me/tv/four corners/Season 2018/Four Corners (1961) S2018E31 Outbreak.srt

To do that, we could run showmatcher for each show:

    $ python matcher.py \
        --directory "/home/me/iview-downloads/sarah duck"
        --destination "/home/me/tv/sarah duck" \
        --series-name  "Sarah & Duck" \
        --ignore-substring "Sarah  Duck" \

    Series Sarah & Duck has episodes
    Looking up Sarah & Duck episode "Boo Night"
    Renaming to Season 03/Sarah & Duck S03E31 Boo Night

    $ python matcher.py \
        --directory "/home/me/iview-downloads/four corners"
        --destination "/home/me/tv/four corners" \
        --series-name  "Four Corners (1961)" \
        --ignore-substring "Four Corners Series" \

    Series Four Corners (1961) has episodes
    Looking up Four Corners (1961) episode "Outbreak"
    Renaming to Season 2018/Four Corners S2018E21 Outbreak


Alternatively, we could create showmatcher config files:

    $ cat "/home/me/iview-downloads/four corners/.matcherrc"
    directory = /home/me/iview-downloads/four corners
    destination = /home/me/tv/four corners
    series-name  = Four Corners (1961)
    ignore-substring = Four Corners Series ....

    $ cat "/home/me/iview-downloads/sarah duck/.matcherrc"
    directory = /home/me/iview-downloads/sarah duck
    destination = /home/me/tv/sarah duck
    series-name  = Sarah & Duck
    ignore-substring = Sarah  Duck

This way we don't have to remember the commands and can batch run
across multiple shows at once:

    $ find /home/me/iview-downloads -name .matcherrc -exec python matcher.py --config {} \;

    Series Hey Duggee has episodes
    Looking up Hey Duggee episode "The Organising Badge"
    Renaming to Season 02/Hey Duggee S02E42 The Organising Badge
    Series Sarah & Duck has episodes
    Looking up Sarah & Duck episode "Boo Night"
    Renaming to Season 03/Sarah & Duck S03E31 Boo Night
    Series Four Corners (1961) has episodes
    Looking up Four Corners (1961) episode "Outbreak"
    Renaming to Season 2018/Four Corners S2018E21 Outbreak
