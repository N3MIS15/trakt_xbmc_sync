trakt_xbmc_sync
===============

Sync trakt.tv and XBMC


**What it does:**

Gets a list of movies and TV shows from XBMC.
Gets a list of movies and TV shows from trakt.tv.
Checks for missing movies/shows in trakt.tv collection.
Compares watched progress for movies/shows.
Updates trakt.tv with playcounts from XBMC if the trakt.tv counterpart is not marked as watched.
Updates XBMC with playcounts from trakt.tv if the XBMC counterpart is not marked as watched.

The script will only ADD playcounts and new movies/shows, it will not remove shows/movies or watched status. I built this script to recover my watched shows/movies after I had lost my database and adding watched status back in was all i needed.
