#!/usr/bin/env python

###################### SETTINGS ######################
xbmc_hostname = '127.0.0.1'
xbmc_port = '80'
xbmc_username = 'xbmc'
xbmc_password = 'xbmc'

trakt_username = 'username'
trakt_password = 'password'
trakt_apikey = '123456789'
#################### END SETTINGS ####################


try:
    import json
except ImportError:
    import simplejson as json
import urllib2, base64, hashlib, copy


xbmc_movies = []
xbmc_movies_seen = []
xbmc_movies_unseen = []
trakt_movies = []

xbmc_shows = []
trakt_shows = []


class XBMCJSON:
    '''Connects to XBMC JSON API'''
    def __init__(self, server):
        """Initialize the XBMC server"""
        self.server = server

    def __call__(self, **kwargs):
        """Gets method and params from call"""
        method = '.'.join(map(str, self.n))
        self.n = []
        return XBMCJSON.__dict__['Request'](self, method, kwargs)
 
    def __getattr__(self, name):
        """Convert method to list"""
        if not self.__dict__.has_key('n'):
            self.n=[]
        self.n.append(name)
        return self

    def Request(self, method, kwargs):
        """Process the XBMC request"""

        if not self.server:
            quit('No XBMC server defined')

        # JSON data to be sent to XBMC
        data = [
            {
                'method': method,
                'params': kwargs,
                'jsonrpc': '2.0',
                'id': 0
            }
        ]

        data = json.JSONEncoder().encode(data)

        # Set content
        content = {
            'Content-Type': 'application/json',
            'Content-Length': len(data),
        }

        request = urllib2.Request(self.server, data, content)

        # If XBMC server requires username and password add auth header
        if xbmc_username and xbmc_password:
            base64string = base64.encodestring('%s:%s' % (xbmc_username, xbmc_password)).replace('\n', '')
            request.add_header("Authorization", "Basic %s" % base64string)

        # Send the request
        try:
            response = urllib2.urlopen(request).read()
        except urllib2.URLError, e:
            quit(e.reason)

        response = json.JSONDecoder().decode(response)

        try:
            # Return the response result
            return response[0]['result']
        except:
            # If there is a error, print the error message
            quit(response[0]['error']['message'])


def trakt_api(url, params={}):
    '''Connects to trakt.tv api'''
    username = trakt_username
    password = hashlib.sha1(trakt_password).hexdigest()

    params = json.JSONEncoder().encode(params)
    request = urllib2.Request(url, params)
    base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)

    response = urllib2.urlopen(request).read()
    response = json.JSONDecoder().decode(response)

    return response


xbmc_address = 'http://%s:%s/jsonrpc' % (xbmc_hostname, xbmc_port)
xbmc = XBMCJSON(xbmc_address)


def get_xbmc_movies():
    print '\nGetting movies from XBMC'

    movies = xbmc.VideoLibrary.GetMovies(properties=['title', 'imdbnumber', 'year', 'playcount'])['movies']

    for movie in movies:
        xbmc_movies.append(movie)

        if movie['playcount']:
            xbmc_movies_seen.append(movie)
        else:
            xbmc_movies_unseen.append(movie)


def get_trakt_movies():
    print '\nGetting movies from trakt.tv'

    # Collection
    url = 'http://api.trakt.tv/user/library/movies/collection.json/%s/%s' % (trakt_apikey, trakt_username)
    try:
        movies = trakt_api(url)
    except Exception as e:
        quit(e)

    for movie in movies:
        trakt_movie = {
            'title': movie['title'],
            'year': movie['year'],
        }

        if 'imdb_id' in movie:
            trakt_movie['imdb_id'] = movie['imdb_id']
        if 'tmdb_id' in movie:
            trakt_movie['tmdb_id'] = movie['tmdb_id']

        trakt_movies.append(trakt_movie)

    # Seen
    url = 'http://api.trakt.tv/user/library/movies/watched.json/%s/%s' % (trakt_apikey, trakt_username)
    try:
        seen_movies = trakt_api(url)
    except Exception as e:
        quit(e)

    # Add playcounts to trakt collection
    for seen in seen_movies:
        if 'imdb_id' in seen:
            for movie in trakt_movies:
                if 'imdb_id' in movie:
                    if seen['imdb_id'] == movie['imdb_id']:
                        movie['plays'] = seen['plays']
        elif 'tmdb_id' in seen:
            for movie in trakt_movies:
                if 'tmdb_id' in movie:
                    if seen['tmdb_id'] == movie['tmdb_id']:
                        movie['plays'] = seen['plays']

        elif 'title' in seen:
            for movie in trakt_movies:
                if 'title' in movie:
                    if seen['title'] == movie['title']:
                        movie['plays'] = seen['plays']

    for movie in trakt_movies:
        if not 'plays' in movie:
            movie['plays'] = 0


def convert_xbmc_movie_to_trakt(movie):
    '''
    Converts XBMC movie into a format usable with trakt.tv api
    '''
    trakt_movie = {}

    if 'imdbnumber' in movie:
        if movie['imdbnumber'].startswith('tt'):
            trakt_movie['imdb_id'] = movie['imdbnumber']
        else:
            trakt_movie['tmdb_id'] = movie['imdbnumber']

    if 'title' in movie:
        trakt_movie['title'] = movie['title']

    if 'year' in movie:
        trakt_movie['year'] = movie['year']

    if 'playcount' in movie:
        trakt_movie['plays'] = movie['playcount']

    return trakt_movie


def xbmc_movies_to_trakt():
    '''
    Adds movies to trakt collection from XBMC library if the movie 
    does not already exist in trakt.tv collection.
    '''

    print '\nChecking for XBMC movies that are not in trakt.tv collection'
    xbmc_movies_to_trakt = []

    if trakt_movies and xbmc_movies:
        imdb_ids = [x['imdb_id'] for x in trakt_movies if 'imdb_id' in x]
        tmdb_ids = [x['tmdb_id'] for x in trakt_movies if 'tmdb_id' in x]
        titles = [x['title'] for x in trakt_movies if 'title' in x]

        if xbmc_movies:
            for movie in xbmc_movies:
                if 'imdbnumber' in movie:
                    if movie['imdbnumber'].startswith('tt'):
                        if not movie['imdbnumber'] in imdb_ids:
                            xbmc_movies_to_trakt.append(movie)

                            trakt_movie = convert_xbmc_movie_to_trakt(movie)
                            trakt_movie['plays'] = 0
                            trakt_movies.append(trakt_movie)

                    else:
                        if not movie['imdbnumber'] in tmdb_ids:
                            xbmc_movies_to_trakt.append(movie)

                            trakt_movie = convert_xbmc_movie_to_trakt(movie)
                            trakt_movie['plays'] = 0
                            trakt_movies.append(trakt_movie)

                elif not movie['title'] in titles and not movie in xbmc_movies_to_trakt:
                    xbmc_movies_to_trakt.append(movie)

                    trakt_movie = convert_xbmc_movie_to_trakt(movie)
                    trakt_movie['plays'] = 0
                    trakt_movies.append(trakt_movie)

    if xbmc_movies_to_trakt:
        print '  %s movies will be added to trakt.tv collection' % len(xbmc_movies_to_trakt)

        for i in range(len(xbmc_movies_to_trakt)):
            #convert xbmc movie into something trakt will understand
            xbmc_movies_to_trakt[i] = convert_xbmc_movie_to_trakt(xbmc_movies_to_trakt[i])

        # Send request to add movies to trakt.tv
        url = 'http://api.trakt.tv/movie/library/' + trakt_apikey
        params = {'movies': xbmc_movies_to_trakt}

        try:
            print '    Adding movies to trakt.tv collection...'
            trakt_api(url, params)
            for movie in xbmc_movies_to_trakt:
                print '    --> ' + movie['title'].encode('utf-8')
        except Exception, e:
            print 'Failed to add movies to trakt.tv collection'
            print e
            
    else:
        print '  trakt.tv movie collection is up to date'


def xbmc_movies_watched_to_trakt():
    '''
    If XBMC movie has higher play count then its trakt.tv
    counterpart. Update movie on trakt.tv.
    '''

    print '\nComparing XBMC watched movies against trakt.tv'
    xbmc_movies_to_trakt = []

    if trakt_movies and xbmc_movies:

        for i in range(len(trakt_movies)):
            for movie in xbmc_movies:

                if 'imdb_id' in trakt_movies[i]:
                    if movie['imdbnumber'] == trakt_movies[i]['imdb_id']:
                        if trakt_movies[i]['plays'] < movie['playcount']:
                            xbmc_movies_to_trakt.append(convert_xbmc_movie_to_trakt(movie))

                elif 'tmdb_id' in trakt_movies[i]:
                    if movie['imdbnumber'] == trakt_movies[i]['tmdb_id']:
                        if trakt_movies[i]['plays'] < movie['playcount']:
                            xbmc_movies_to_trakt.append(convert_xbmc_movie_to_trakt(movie))

                elif movie['title'] == trakt_movies[i]['title']:
                    if trakt_movies[i]['plays'] < movie['playcount']:
                        xbmc_movies_to_trakt.append(convert_xbmc_movie_to_trakt(movie))

    if xbmc_movies_to_trakt:
        print '  %s movies playcount will be updated on trakt.tv' % len(xbmc_movies_to_trakt)

        # Send request to update playcounts on trakt.tv
        url = 'http://api.trakt.tv/movie/seen/' + trakt_apikey
        params = {'movies': xbmc_movies_to_trakt}

        try:
            print '    Updating playcount for movies on trakt.tv...'
            trakt_api(url, params)
            for movie in xbmc_movies_to_trakt:
                print '    --> ' + movie['title'].encode('utf-8')

        except Exception, e:
            print 'Failed to update playcount for movies on trakt.tv'
            print e
    else:
        print '  trakt.tv movie playcount is up to date'


def trakt_movies_watched_to_xbmc():
    '''
    If trakt.tv movie has higher play count then its XBMC
    counterpart. Update movie on XBMC.
    '''

    print '\nComparing trakt.tv watched movies against XBMC'

    trakt_movies_seen = []

    if trakt_movies and xbmc_movies:
        for i in range(len(trakt_movies)):
            for movie in xbmc_movies:

                if 'imdb_id' in trakt_movies[i]:
                    if movie['imdbnumber'] == trakt_movies[i]['imdb_id']:
                        if trakt_movies[i]['plays'] > movie['playcount']:
                            trakt_movies[i]['movieid'] = movie['movieid']

                elif 'tmdb_id' in trakt_movies[i]:
                    if movie['imdbnumber'] == trakt_movies[i]['tmdb_id']:
                        if trakt_movies[i]['plays'] > movie['playcount']:
                            trakt_movies[i]['movieid'] = movie['movieid']

                elif movie['title'] == trakt_movies[i]['title']:
                    if trakt_movies[i]['plays'] > movie['playcount']:
                        trakt_movies[i]['movieid'] = movie['movieid']

    # Remove movies without a movieid
    if trakt_movies:

        for movie in trakt_movies:
            if 'movieid' in movie:
                trakt_movies_seen.append(movie)

    if trakt_movies_seen:
        print '  %s movies playcount will be updated on XBMC' % len(trakt_movies_seen)

        for movie in trakt_movies_seen:
            print '    --> ' + movie['title'].encode('utf-8')

            xbmc.VideoLibrary.SetMovieDetails(
                movieid=movie['movieid'],
                playcount=movie['plays']
            )
    else:
        print '  Watched movies on XBMC are up to date'


def get_xbmc_shows():
    print '\nGetting TV shows from XBMC'

    shows = xbmc.VideoLibrary.GetTVShows(properties=['title', 'imdbnumber'])

    if 'tvshows' in shows:
        shows = shows['tvshows']

    for show in shows:
        show['episodes'] = []

        episodes = xbmc.VideoLibrary.GetEpisodes(tvshowid=show['tvshowid'], properties=['season', 'episode', 'playcount'])

        if 'episodes' in episodes:
            episodes = episodes['episodes']

        for episode in episodes:
            if type(episode) == type(dict()):
                show['episodes'].append(episode)

        if show['episodes']:
            xbmc_shows.append(show)


def get_trakt_shows():
    print '\nGetting TV shows from trakt'

    # Collection
    url = 'http://api.trakt.tv/user/library/shows/collection.json/%s/%s' % (trakt_apikey, trakt_username)
    try:
        collection_shows = trakt_api(url)
    except Exception as e:
        quit(e)

    for show in collection_shows:
        trakt_show = {
            'title': show['title'],
            'episodes': []
        }

        if 'imdb_id' in show:
            trakt_show['imdb_id'] = show['imdb_id']
        if 'tvdb_id' in show:
            trakt_show['tvdb_id'] = show['tvdb_id']

        for season in show['seasons']:
            for episode in season['episodes']:
                ep = {'season': season['season'], 'episode': episode, 'plays': 0}
                trakt_show['episodes'].append(ep)


        trakt_shows.append(trakt_show)

    # Seen
    url = 'http://api.trakt.tv/user/library/shows/watched.json/%s/%s' % (trakt_apikey, trakt_username)
    try:
        seen_shows = trakt_api(url)
    except Exception as e:
        quit(e)

    for show in seen_shows:
        for season in show['seasons']:
            for episode in season['episodes']:
                for trakt_show in trakt_shows:
                    if 'imdb_id' in show and 'imdb_id' in trakt_show and show['imdb_id'] == trakt_show['imdb_id']:
                        for trakt_episode in trakt_show['episodes']:
                            if trakt_episode['season'] == season['season'] and trakt_episode['episode'] == episode:
                                trakt_episode['plays'] = 1

                    elif 'tvdb_id' in show and 'tvdb_id' in trakt_show and show['tvdb_id'] == trakt_show['tvdb_id']:
                        for trakt_episode in trakt_show['episodes']:
                            if trakt_episode['season'] == season['season'] and trakt_episode['episode'] == episode:
                                trakt_episode['plays'] = 1

                    elif show['title'] == trakt_show['title']:
                        for trakt_episode in trakt_show['episodes']:
                            if trakt_episode['season'] == season['season'] and trakt_episode['episode'] == episode:
                                trakt_episode['plays'] = 1


def convert_xbmc_show_to_trakt(show):
    '''
    Converts XBMC show into a format usable with trakt.tv api
    '''
    trakt_show = {'episodes': []}

    if 'imdbnumber' in show:
        if show['imdbnumber'].startswith('tt'):
            trakt_show['imdb_id'] = show['imdbnumber']
        else:
            trakt_show['tvdb_id'] = show['imdbnumber']

    if 'title' in show:
        trakt_show['title'] = show['title']

    if 'episodes' in show and show['episodes']:
        for episode in show['episodes']:
            ep = {'episode': episode['episode'], 'season': episode['season']}

            if 'playcount' in episode:
                 ep['plays'] = episode['playcount']

            trakt_show['episodes'].append(ep)

    return trakt_show


def xbmc_shows_to_trakt():
    '''
    Adds shows and episodes to trakt collection from XBMC library if thet are 
    missing from the trakt.tv collection.
    '''

    print '\nChecking for XBMC episodes that are not in trakt.tv collection'
    xbmc_shows_to_trakt = []

    def clean_episodes(shows):
        if shows:
            for show in shows:
                episodes = []
                for episode in show['episodes']:
                    episodes.append({'season': episode['season'], 'episode': episode['episode']})
                show['episodes'] = episodes

        return shows

    if trakt_shows and xbmc_shows:
        x_shows = copy.deepcopy(xbmc_shows)
        x_shows = clean_episodes(x_shows)

        t_shows = copy.deepcopy(trakt_shows)
        t_shows = clean_episodes(t_shows)

        tvdb_ids = {}
        imdb_ids = {}

        for i in range(len(t_shows)):
            if 'tvdb_id' in t_shows[i]:
                tvdb_ids[t_shows[i]['tvdb_id']] = i

            if 'imdb_id' in t_shows[i]:
                imdb_ids[t_shows[i]['imdb_id']] = i

        for show in x_shows:
            if 'imdbnumber' in show:
                if show['imdbnumber'].startswith('tt'):
                    if not show['imdbnumber'] in imdb_ids.keys():
                        xbmc_shows_to_trakt.append(show)

                        trakt_show = convert_xbmc_show_to_trakt(show)
                        trakt_show['plays'] = 0
                        trakt_shows.append(trakt_show)
                        imdb_ids['imdbnumber'] = len(imdb_ids) + 1

                    else:
                        t_index = imdb_ids[show['imdbnumber']]

                        xbmc_show = {
                            'title': show['title'],
                            'imdbnumber': show['imdbnumber'],
                            'episodes': []
                        }

                        for episode in show['episodes']:
                            if episode not in t_shows[t_index]['episodes']:
                                xbmc_show['episodes'].append(episode)

                                trakt_shows[t_index]['episodes'].append(episode)
                                trakt_shows[t_index]['episodes'][-1]['plays'] = 0

                        if xbmc_show['episodes']:
                            xbmc_shows_to_trakt.append(xbmc_show)

                else:
                    if not show['imdbnumber'] in tvdb_ids.keys():
                        xbmc_shows_to_trakt.append(show)

                        trakt_show = convert_xbmc_show_to_trakt(show)
                        trakt_show['plays'] = 0
                        trakt_shows.append(trakt_show)
                        tvdb_ids['imdbnumber'] = len(tvdb_ids) + 1

                    else:
                        t_index = tvdb_ids[show['imdbnumber']]

                        xbmc_show = {
                            'title': show['title'],
                            'imdbnumber': show['imdbnumber'],
                            'episodes': []
                        }

                        for episode in show['episodes']:
                            if episode not in t_shows[t_index]['episodes']:
                                xbmc_show['episodes'].append(episode)

                                trakt_shows[t_index]['episodes'].append(episode)
                                trakt_shows[t_index]['episodes'][-1]['plays'] = 0

                        if xbmc_show['episodes']:
                            xbmc_shows_to_trakt.append(xbmc_show)

        if xbmc_shows_to_trakt:
            print '  %s TV shows have episodes missing from trakt.tv collection' % len(xbmc_shows_to_trakt)

            for i in range(len(xbmc_shows_to_trakt)):
                #convert xbmc show into something trakt will understand
                xbmc_shows_to_trakt[i] = convert_xbmc_show_to_trakt(xbmc_shows_to_trakt[i])

            # Send request to add TV shows to trakt.tv
            url = 'http://api.trakt.tv/show/episode/library/' + trakt_apikey

            for show in xbmc_shows_to_trakt:
                try:
                    print '\n    --> ' + show['title'].encode('utf-8')
                    trakt = trakt_api(url, show)
                    print '      ' + trakt['message']
                except Exception, e:
                    print 'Failed to add %s\'s new episodes to trakt.tv collection' % show['title'].encode('utf-8')
                    print e

        else:
            print '  trakt.tv TV show collection is up to date'


def xbmc_shows_watched_to_trakt():
    '''
    If XBMC episode has been watched and the episode 
    has not been marked as watched on trakt.tv. 
    Update episode on trakt.tv.
    '''

    print '\nComparing XBMC watched TV shows against trakt.tv'
    xbmc_shows_to_trakt = []

    if xbmc_shows and trakt_shows:

        tvdb_ids = {}
        imdb_ids = {}

        for i in range(len(trakt_shows)):
            if 'tvdb_id' in trakt_shows[i]:
                tvdb_ids[trakt_shows[i]['tvdb_id']] = i

            if 'imdb_id' in trakt_shows[i]:
                imdb_ids[trakt_shows[i]['imdb_id']] = i

        for show in xbmc_shows:
            if 'imdbnumber' in show:
                if show['imdbnumber'].startswith('tt'):
                    if show['imdbnumber'] in imdb_ids.keys():
                        trakt_show = trakt_shows[imdb_ids[show['imdbnumber']]]

                        trakt_show_watched = {
                            'title': show['title'],
                            'imdb_id': show['imdbnumber'],
                            'episodes': []
                        }

                        for xbmc_ep in show['episodes']:
                            for trakt_ep in trakt_show['episodes']:
                                if trakt_ep['season'] == xbmc_ep['season']:
                                    if trakt_ep['episode'] == xbmc_ep['episode']:
                                        if trakt_ep['plays'] == 0 and xbmc_ep['playcount'] >= 1:

                                            trakt_show_watched['episodes'].append(
                                                {
                                                    'season': xbmc_ep['season'],
                                                    'episode': xbmc_ep['episode']
                                                }
                                            )

                        if trakt_show_watched['episodes']:
                            xbmc_shows_to_trakt.append(trakt_show_watched)

                else:
                    if show['imdbnumber'] in tvdb_ids.keys():
                        trakt_show = trakt_shows[tvdb_ids[show['imdbnumber']]]

                        trakt_show_watched = {
                            'title': show['title'],
                            'tvdb_id': show['imdbnumber'],
                            'episodes': []
                        }

                        for xbmc_ep in show['episodes']:
                            for trakt_ep in trakt_show['episodes']:
                                if trakt_ep['season'] == xbmc_ep['season']:
                                    if trakt_ep['episode'] == xbmc_ep['episode']:
                                        if trakt_ep['plays'] == 0 and xbmc_ep['playcount'] >= 1:

                                            trakt_show_watched['episodes'].append(
                                                {
                                                    'season': xbmc_ep['season'],
                                                    'episode': xbmc_ep['episode']
                                                }
                                            )

                        if trakt_show_watched['episodes']:
                            xbmc_shows_to_trakt.append(trakt_show_watched)

        if xbmc_shows_to_trakt:
            print '  %s TV shows have episodes that will be marked as watched in trakt.tv collection' % len(xbmc_shows_to_trakt)

            for i in range(len(xbmc_shows_to_trakt)):
                #convert xbmc show into something trakt will understand
                xbmc_shows_to_trakt[i] = convert_xbmc_show_to_trakt(xbmc_shows_to_trakt[i])

            # Send request to add TV shows to trakt.tv
            url = 'http://api.trakt.tv/show/episode/seen/' + trakt_apikey

            for show in xbmc_shows_to_trakt:
                try:
                    print '\n    --> ' + show['title'].encode('utf-8')
                    trakt = trakt_api(url, show)
                    print '      ' + trakt['message']
                except Exception, e:
                    print 'Failed to mark %s\'s episodes as watched in trakt.tv collection' % show['title'].encode('utf-8')
                    print e

        else:
            print '  trakt.tv TV show watched status is up to date'


def trakt_shows_watched_to_xbmc():
    '''
    If trakt.tv episode has been watched and the episode 
    has not been marked as watched on XBMC. 
    Update episode on XBMC.
    '''

    print '\nComparing trakt.tv watched TV shows against XBMC'
    trakt_shows_seen = []

    if xbmc_shows and trakt_shows:

        tvdb_ids = {}
        imdb_ids = {}

        for i in range(len(trakt_shows)):
            if 'tvdb_id' in trakt_shows[i]:
                tvdb_ids[trakt_shows[i]['tvdb_id']] = i

            if 'imdb_id' in trakt_shows[i]:
                imdb_ids[trakt_shows[i]['imdb_id']] = i

        for show in xbmc_shows:
            if 'imdbnumber' in show:
                if show['imdbnumber'].startswith('tt'):
                    if show['imdbnumber'] in imdb_ids.keys():
                        trakt_show = trakt_shows[imdb_ids[show['imdbnumber']]]

                        xbmc_show = {'title': show['title'], 'episodes': []}

                        for xbmc_ep in show['episodes']:
                            for trakt_ep in trakt_show['episodes']:
                                if trakt_ep['season'] == xbmc_ep['season']:
                                    if trakt_ep['episode'] == xbmc_ep['episode']:
                                        if trakt_ep['plays'] == 1 > xbmc_ep['playcount']:

                                            xbmc_show['episodes'].append(
                                                {
                                                    'label': xbmc_ep['label'],
                                                    'episodeid': xbmc_ep['episodeid']
                                                }
                                            )

                        if xbmc_show['episodes']:
                            trakt_shows_seen.append(xbmc_show)

                else:
                    if show['imdbnumber'] in tvdb_ids.keys():
                        trakt_show = trakt_shows[tvdb_ids[show['imdbnumber']]]

                        xbmc_show = {'title': show['title'], 'episodes': []}

                        for xbmc_ep in show['episodes']:
                            for trakt_ep in trakt_show['episodes']:
                                if trakt_ep['season'] == xbmc_ep['season']:
                                    if trakt_ep['episode'] == xbmc_ep['episode']:
                                        if trakt_ep['plays'] == 1 > xbmc_ep['playcount']:

                                            xbmc_show['episodes'].append(
                                                {
                                                    'label': xbmc_ep['label'],
                                                    'episodeid': xbmc_ep['episodeid']
                                                }
                                            )

                        if xbmc_show['episodes']:
                            trakt_shows_seen.append(xbmc_show)

        if trakt_shows_seen:
            print '  %s TV shows episodes playcount will be updated on XBMC' % len(trakt_shows_seen)

            for show in trakt_shows_seen:
                print '    --> ' + show['title'].encode('utf-8')

                for episode in show['episodes']:
                    print '      %s' % episode['label'].encode('utf-8')

                    xbmc.VideoLibrary.SetEpisodeDetails(
                        episodeid=episode['episodeid'],
                        playcount=1
                    )
        else:
            print '  Watched TV shows on XBMC are up to date'


if __name__ == '__main__':
    get_xbmc_movies()
    get_trakt_movies()
    xbmc_movies_to_trakt()
    xbmc_movies_watched_to_trakt()
    trakt_movies_watched_to_xbmc()
    get_xbmc_shows()
    get_trakt_shows()
    xbmc_shows_to_trakt()
    xbmc_shows_watched_to_trakt()
    trakt_shows_watched_to_xbmc()
    print '\n Sync complete.'

