EVE Exploration Logger
======================

Installation
------------

This is a primtive tool to aid my obsessive book-keeping during exploration
trips in EVE Online: A Bad Game. `eve.xhtml` and `eve.cgi` are intended to be
deployed on a webserver that will run `eve.cgi` as a ruby `cgi` script, and to
be accessed from the EVE Online ingame webbrowser. The `cgi` script requires a
writable file with the name `eve-data` in its working directory. Adding to the
log requires the password hardcoded into `eve.cgi`, the default value is
"`secretpassword`".

Motivation
----------

Exploration in EVE Online means using a Probe Launcher and several Scanner
Probes to find locations in various EVE Online solar systems that cannot
otherwise be navigated to. These sites usually provide PvE activities like
hunting NPC pirates for bounties and loot or performing special
profession-based tasks. Other sites are wormholes that lead to other systems
in space.

During the scanning procedure, sites will be displayed under an ID consisting
of three letters and three digits, such as `ABC-123`, usually well before the
site is actually reachable or can even be classified. This ID will remain
constant for the duration of the site's existence (or until the next downtime,
whichever is sooner), so upon later searches in the same solar system, it may
be useful to compare the known IDs of known-useless sites against the ones
currently visible.

This tool will simply allow you to keep a log of identified sites and search
through the log by ID. The sole advantage over a text file or spreadsheet is
that the ingame browser will submit the solar system you are in with the
request to the `cgi` script, so that and the current time will be noted down
automatically.

Usage
-----

Use the EVE Online ingame browser to navigate to `eve.xhtml`. While scanning,
enter an ID into the first form and submit it to see if the ID has already
been identified and can be skipped. You will see the time and location along
with the information you entered for the site when first discovering it. Log
entries matching the current solar system will be displayed in bold. If the
ID is new (or was seen elsewhere, or a long time ago), proceed as usual.

Once you know the type (*Unknown*, *Gravimetric*, etc.) of a site, you might
decide it is not worth investigating further and enter the information into
the second form. You can omit the fourth field, the precise name of the site,
since you will often not know it by the time you decide to skip the site. The
`cgi` script will automatically complete your amend your submission with the
current time and location.

Future direction
----------------

* The ingame browser should really not be required. Maybe a "solar system"
  input field should be added to the second form and then hidden if the ingame
  browser trusts the page.
* Maybe the two forms should be collapsed into one so that new IDs only have
  to be entered once. But on the other hand, when confronted with multiple IDs
  at the same time, it might not actually make anything easier.
* The password should really be read from a separate credentials file outside
  of the webserver's document root, I suppose.
* A standalone webserver might be useful so that the whole thing can be run
  locally, trading the convenience of a central log that can be used by
  multiple users scanning the same systems for ease of setup.
* The (clientside) JavaScript is fairly ugly since I was pretty much learning
  as I went along, so it is lacking in use of frameworks and organization.
