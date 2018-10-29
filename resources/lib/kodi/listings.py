# -*- coding: utf-8 -*-
"""Helper functions to build plugin listings for Kodi"""
from __future__ import unicode_literals

from functools import wraps

import xbmc
import xbmcgui
import xbmcplugin

import resources.lib.common as common
import resources.lib.api.shakti as api
import resources.lib.kodi.library as library

from .infolabels import add_info, add_art

VIEW_FOLDER = 'folder'
VIEW_MOVIE = 'movie'
VIEW_SHOW = 'show'
VIEW_SEASON = 'season'
VIEW_EPISODE = 'episode'
VIEW_EXPORTED = 'exported'

VIEWTYPES = [VIEW_FOLDER, VIEW_MOVIE, VIEW_SHOW, VIEW_SEASON,
             VIEW_EPISODE, VIEW_EXPORTED]

CONTENT_FOLDER = 'files'
CONTENT_MOVIE = 'movies'
CONTENT_SHOW = 'tvshows'
CONTENT_SEASON = 'seasons'
CONTENT_EPISODE = 'episodes'

RUN_PLUGIN = 'XBMC.RunPlugin({})'

ADDITIONAL_MAIN_MENU_ITEMS = [
    {'path': ['genres', '83'],
     'label': common.get_local_string(30095),
     'icon': 'DefaultTVShows.png',
     'description': None},
    {'path': ['genres', '34399'],
     'label': common.get_local_string(30096),
     'icon': 'DefaultMovies.png',
     'description': None},
    {'path': ['search'],
     'label': common.get_local_string(30011),
     'icon': None,
     'description': common.get_local_string(30092)},
    {'path': ['exported'],
     'label': common.get_local_string(30048),
     'icon': 'DefaultHardDisk.png',
     'description': common.get_local_string(30091)},
]

def ctx_item_url(paths, mode=common.MODE_ACTION):
    """Return a function that builds an URL from a videoid
    for the predefined path"""
    def url_builder(videoid):
        """Build defined URL from videoid"""
        return common.build_url(paths, videoid, mode=mode)
    return url_builder

CONTEXT_MENU_ACTIONS = {
    'export': {
        'label': common.get_local_string(30018),
        'url': ctx_item_url(['export'], common.MODE_LIBRARY)},
    'remove': {
        'label': common.get_local_string(30030),
        'url': ctx_item_url(['remove'], common.MODE_LIBRARY)},
    'update': {
        'label': common.get_local_string(30030),
        'url': ctx_item_url(['update'], common.MODE_LIBRARY)},
    'rate': {
        'label': common.get_local_string(30019),
        'url': ctx_item_url(['rate'])},
    'add_to_list': {
        'label': common.get_local_string(30021),
        'url': ctx_item_url(['my_list', 'add'])},
    'remove_from_list': {
        'label': common.get_local_string(30020),
        'url': ctx_item_url(['my_list', 'remove'])},
}


def custom_viewmode(viewtype):
    """Decorator that sets a custom viewmode if currently in
    a listing of the plugin"""
    # pylint: disable=missing-docstring
    def decorate_viewmode(func):
        @wraps(func)
        def set_custom_viewmode(*args, **kwargs):
            # pylint: disable=no-member
            viewtype_override = func(*args, **kwargs)
            view = (viewtype_override
                    if viewtype_override in VIEWTYPES
                    else viewtype)
            _activate_view(view)
        return set_custom_viewmode
    return decorate_viewmode


def _activate_view(view):
    """Activate the given view if the plugin is run in the foreground
    and custom views are enabled"""
    if (('plugin://{}'.format(common.ADDON_ID) in
         xbmc.getInfoLabel('Container.FolderPath')) and
            common.ADDON.getSettingBool('customview')):
        view_id = common.ADDON.getSettingInt('viewmode' + view)
        if view_id != -1:
            xbmc.executebuiltin(
                'Container.SetViewMode({})'.format(view_id))


@custom_viewmode(VIEW_FOLDER)
def build_profiles_listing(profiles):
    """Builds the profiles list Kodi screen"""
    try:
        from HTMLParser import HTMLParser
    except ImportError:
        from html.parser import HTMLParser
    html_parser = HTMLParser()
    finalize_directory([_create_profile_item(guid, profile, html_parser)
                        for guid, profile
                        in profiles.iteritems()])


def _create_profile_item(profile_guid, profile, html_parser):
    """Create a tuple that can be added to a Kodi directory that represents
    a profile as listed in the profiles listing"""
    profile_name = profile.get('profileName', '')
    unescaped_profile_name = html_parser.unescape(profile_name)
    enc_profile_name = profile_name.encode('utf-8')
    list_item = list_item_skeleton(
        label=unescaped_profile_name, icon=profile.get('avatar'))
    autologin_url = common.build_url(
        pathitems=['save_autologin', profile_guid],
        params={'autologin_user': enc_profile_name},
        mode=common.MODE_ACTION)
    list_item.addContextMenuItems(
        [(common.get_local_string(30053),
          'RunPlugin({})'.format(autologin_url))])
    url = common.build_url(pathitems=['home'],
                           params={'profile_id': profile_guid},
                           mode=common.MODE_DIRECTORY)
    return (url, list_item, True)


@custom_viewmode(VIEW_FOLDER)
def build_main_menu_listing(lolomo):
    """
    Builds the video lists (my list, continue watching, etc.) Kodi screen
    """
    directory_items = [_create_videolist_item(list_id, user_list)
                       for list_id, user_list
                       in lolomo.lists_by_context(common.KNOWN_LIST_TYPES)]
    for context_type, data in common.MISC_CONTEXTS.iteritems():
        directory_items.append(
            (common.build_url([context_type], mode=common.MODE_DIRECTORY),
             list_item_skeleton(common.get_local_string(data['label_id']),
                                icon=data['icon'],
                                description=common.get_local_string(
                                    data['description_id'])),
             True))
    for menu_item in ADDITIONAL_MAIN_MENU_ITEMS:
        directory_items.append(
            (common.build_url(menu_item['path'], mode=common.MODE_DIRECTORY),
             list_item_skeleton(menu_item['label'],
                                icon=menu_item['icon'],
                                description=menu_item['description']),
             True))
    finalize_directory(directory_items, CONTENT_FOLDER,
                       title=common.get_local_string(30097))


@custom_viewmode(VIEW_FOLDER)
def build_lolomo_listing(lolomo, contexts=None):
    """Build a listing of vieo lists (LoLoMo). Only show those
    lists with a context specified context if contexts is set."""
    lists = (lolomo.lists_by_context(contexts)
             if contexts
             else lolomo.lists.iteritems())
    directory_items = [_create_videolist_item(video_list_id, video_list)
                       for video_list_id, video_list
                       in lists
                       if video_list['context'] != 'billboard']
    finalize_directory(directory_items, CONTENT_FOLDER,
                       title=lolomo.get('name'))


def _create_videolist_item(video_list_id, video_list):
    """Create a tuple that can be added to a Kodi directory that represents
    a videolist as listed in a LoLoMo"""
    if video_list['context'] in common.KNOWN_LIST_TYPES:
        video_list_id = video_list['context']
    list_item = list_item_skeleton(video_list['displayName'])
    add_info(video_list.id, list_item, video_list, video_list.data)
    add_art(video_list.id, list_item, video_list.artitem)
    url = common.build_url(['video_list', video_list_id],
                           mode=common.MODE_DIRECTORY)
    return (url, list_item, True)


@custom_viewmode(VIEW_SHOW)
def build_video_listing(video_list):
    """Build a video listing"""
    directory_items = [_create_video_item(videoid_value, video, video_list)
                       for videoid_value, video
                       in video_list.videos.iteritems()]
    if video_list.get('genreId'):
        directory_items.append(
            (common.build_url(pathitems=['genres', video_list['genreId']],
                              mode=common.MODE_DIRECTORY),
             list_item_skeleton(common.get_local_string(30088),
                                icon='DefaultAddSource.png',
                                description=common.get_local_string(30090)),
             True))
        # TODO: Implement browsing of subgenres
        # directory_items.append(
        #     (common.build_url(pathitems=['genres', genre_id, 'subgenres'],
        #                       mode=common.MODE_DIRECTORY),
        #      list_item_skeleton('Browse subgenres...'),
        #      True))
    finalize_directory(directory_items, CONTENT_SHOW,
                       title=video_list['displayName'])


def _create_video_item(videoid_value, video, video_list):
    """Create a tuple that can be added to a Kodi directory that represents
    a video as listed in a videolist"""
    is_movie = video['summary']['type'] == 'movie'
    videoid = common.VideoId(
        **{('movieid' if is_movie else 'tvshowid'): videoid_value})
    list_item = list_item_skeleton(video['title'])
    add_info(videoid, list_item, video, video_list.data)
    add_art(videoid, list_item, video)
    url = common.build_url(videoid=videoid,
                           mode=(common.MODE_PLAY
                                 if is_movie
                                 else common.MODE_DIRECTORY))
    list_item.addContextMenuItems(
        _generate_context_menu_items(videoid))
    return (url, list_item, not is_movie)


@custom_viewmode(VIEW_SEASON)
def build_season_listing(tvshowid, season_list):
    """Build a season listing"""
    directory_items = [_create_season_item(tvshowid, seasonid_value, season,
                                           season_list)
                       for seasonid_value, season
                       in season_list.seasons.iteritems()]
    finalize_directory(directory_items, CONTENT_SEASON,
                       title=' - '.join((season_list.tvshow['title'],
                                         common.get_local_string(20366)[2:])))


def _create_season_item(tvshowid, seasonid_value, season, season_list):
    """Create a tuple that can be added to a Kodi directory that represents
    a season as listed in a season listing"""
    seasonid = tvshowid.derive_season(seasonid_value)
    list_item = list_item_skeleton(season['summary']['name'])
    add_info(seasonid, list_item, season, season_list.data)
    add_art(tvshowid, list_item, season_list.tvshow)
    list_item.addContextMenuItems(
        _generate_context_menu_items(seasonid))
    url = common.build_url(videoid=seasonid, mode=common.MODE_DIRECTORY)
    return (url, list_item, True)


@custom_viewmode(VIEW_EPISODE)
def build_episode_listing(seasonid, episode_list):
    """Build a season listing"""
    directory_items = [_create_episode_item(seasonid, episodeid_value, episode,
                                            episode_list)
                       for episodeid_value, episode
                       in episode_list.episodes.iteritems()]
    finalize_directory(directory_items, CONTENT_EPISODE,
                       title=' - '.join(
                           (episode_list.tvshow['title'],
                            episode_list.season['summary']['name'])))


def _create_episode_item(seasonid, episodeid_value, episode, episode_list):
    """Create a tuple that can be added to a Kodi directory that represents
    an episode as listed in an episode listing"""
    episodeid = seasonid.derive_episode(episodeid_value)
    list_item = list_item_skeleton(episode['title'])
    add_info(episodeid, list_item, episode, episode_list.data)
    add_art(episodeid, list_item, episode)
    list_item.addContextMenuItems(
        _generate_context_menu_items(episodeid))
    url = common.build_url(videoid=episodeid, mode=common.MODE_PLAY)
    return (url, list_item, False)


def list_item_skeleton(label, icon=None, fanart=None, description=None):
    """Create a rudimentary list item skeleton with icon and fanart"""
    # pylint: disable=unexpected-keyword-arg
    list_item = xbmcgui.ListItem(label=label, iconImage=icon, offscreen=True)
    list_item.setContentLookup(False)
    if fanart:
        list_item.setProperty('fanart_image', fanart)
    info = {'title': label}
    if description:
        info['plot'] = description
    list_item.setInfo('video', info)
    return list_item


def finalize_directory(items, content_type=CONTENT_FOLDER, refresh=False,
                       title=None):
    """Finalize a directory listing.
    Add items, set available sort methods and content type"""
    if title:
        xbmcplugin.setPluginCategory(common.PLUGIN_HANDLE, title)
    xbmcplugin.addDirectoryItems(common.PLUGIN_HANDLE, items)
    xbmcplugin.setContent(common.PLUGIN_HANDLE, content_type)
    xbmcplugin.endOfDirectory(common.PLUGIN_HANDLE, updateListing=refresh)


def _generate_context_menu_items(videoid):
    library_actions = (['remove', 'update']
                       if library.is_in_library(videoid)
                       else ['export'])
    items = [_ctx_item(action, videoid) for action in library_actions]

    if videoid.mediatype != common.VideoId.SEASON:
        items.append(_ctx_item('rate', videoid))

    if videoid.mediatype in [common.VideoId.MOVIE, common.VideoId.SHOW]:
        list_action = ('remove_from_list'
                       if videoid.value in api.mylist_items()
                       else 'add_to_list')
        items.append(_ctx_item(list_action, videoid))

    return items


def _ctx_item(template, videoid):
    """Create a context menu item based on the given template and videoid"""
    return (CONTEXT_MENU_ACTIONS[template]['label'],
            RUN_PLUGIN.format(
                CONTEXT_MENU_ACTIONS[template]['url'](videoid)))
