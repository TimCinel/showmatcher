# showmatcher

Takes TV episode files named by episode title and rename them to a standard format.
Also just does regex based renaming, since it was easy to add.

Might be useful in combination with [webdl](https://bitbucket.org/delx/webdl/) or 
[youtube-dl](https://github.com/rg3/youtube-dl/).

I tried to get FileBot to do this but ultimately couldn't. Now, as I write this README,
it occurs to me that I should've made a plugin for FileBot. Too bad - sunk cost fallacy,
I'm here now.

Features:

* Will rename any associated files (subtitles, for example) accordingly
* Supports "dry run" mode
* Supports CLI arguments being passed in a file

Episode name matching mode:

* Looks up episode title on TVDB to find Season / Episode and renames accordingly
* Uses fuzzy string matching

Pattern matching mode:

* Pulls episode Season / Episode number from file name according to pattern and renames accordingly

## Explained by examples

Assume we have these files...

    $ find "/home/me/iview-downloads/"
    /home/me/iview-downloads/four corners/Four Corners Series Outbreak.mp4
    /home/me/iview-downloads/four corners/Four Corners Series Outbreak.srt
    /home/me/iview-downloads/sarah duck/Sarah  Duck Boo Night.mp4
    /home/me/iview-downloads/mad as hell/Shaun Micallefs MAD AS HELL Series 10 Ep 1.mp4
    /home/me/iview-downloads/mad as hell/Shaun Micallefs MAD AS HELL Series 10 Ep 1.srt

... and we want to rename them into something resembling a standard format, like:

    /home/me/tv/sarah duck/Season 03/Sarah Duck S03E31 Boo Night.mp4
    /home/me/tv/four corners/Season 2018/Four Corners (1961) S2018E31 Outbreak.mp4
    /home/me/tv/four corners/Season 2018/Four Corners (1961) S2018E31 Outbreak.srt
    /home/me/tv/mad as hell/Season 10/Shaun Micallefs MAD AS HELL S10E01.mp4
    /home/me/tv/mad as hell/Season 10/Shaun Micallefs MAD AS HELL S10E01.srt

To do that, we could run showmatcher for each show:

    $ python matcher.py \
        --directory "/home/me/iview-downloads/sarah duck"
        --destination "/home/me/tv/sarah duck" \
        --series-name  "Sarah & Duck" \
        --ignore-substring "Sarah  Duck"

    Series Sarah & Duck has episodes
    Looking up Sarah & Duck episode "Boo Night"
    Renaming to Season 03/Sarah & Duck S03E31 Boo Night

    $ python matcher.py \
        --directory "/home/me/iview-downloads/four corners"
        --destination "/home/me/tv/four corners" \
        --series-name  "Four Corners (1961)" \
        --ignore-substring "Four Corners Series"

    Series Four Corners (1961) has episodes
    Looking up Four Corners (1961) episode "Outbreak"
    Renaming to Season 2018/Four Corners S2018E21 Outbreak

    $ python matcher.py \
        --directory "/home/me/iview-downloads/mad as hell"
        --destination "/home/me/tv/mad as hell" \
        --series-name  "Shaun Micallefs MAD AS HELL" \
        --naming-patttern "Shaun Micallefs MAD AS HELL Series (?P<season>[0-9]+) Ep (?P<episode>[0-9]+) ?(?P<name>.*)"

    Series Shaun Micallef's Mad as Hell has episodes
    Renaming to Season 10/Shaun Micallef's Mad as Hell S10E10

    $ python matcher.py \
        --directory "/home/me/iview-downloads/media watch"
        --destination "/home/me/tv/media watch" \
        --series-name  "Media Watch" \
        --naming-patttern "Media Watch (?P<day>[0-9]+)-(?P<month>[0-9]+)-(?P<year>[0-9]+)"

    Series Media Watch has episodes
    Renaming to Season 2020/Media Watch - 2020-02-17


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

    $ cat "/home/me/iview-downloads/mad as hell/.matcherrc"
    directory = /home/me/iview-downloads/mad as hell
    destination = /home/me/tv/mad as hell
    series-name  = Shaun Micallefs MAD AS HELL 
    naming-pattern = Shaun Micallefs MAD AS HELL Series (?P<season>[0-9]+) Ep (?P<episode>[0-9]+) ?(?P<name>.*)

    $ cat "/home/me/iview-downloads/media watch/.matcherrc"
    directory = /home/me/iview-downloads/media watch
    destination = /home/me/tv/media watch
    series-name  = Media Watch
    naming-pattern = Media Watch (?P<day>[0-9]+)-(?P<month>[0-9]+)-(?P<year>[0-9]+)

This way we don't have to remember the commands and can batch run
across multiple shows at once:

    $ find /home/me/iview-downloads -name .matcherrc -exec python matcher.py --config {} \;

    Series Sarah & Duck has episodes
    Looking up Sarah & Duck episode "Boo Night"
    Renaming to Season 03/Sarah & Duck S03E31 Boo Night
    Series Four Corners (1961) has episodes
    Looking up Four Corners (1961) episode "Outbreak"
    Renaming to Season 2018/Four Corners S2018E21 Outbreak
    Series Shaun Micallef's Mad as Hell has episodes
    Renaming to Season 10/Shaun Micallef's Mad as Hell S10E10
    Series Media Watch has episodes
    Renaming to Season 2020/Media Watch - 2020-02-17
