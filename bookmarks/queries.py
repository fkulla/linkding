from typing import Optional

from django.contrib.auth.models import User
from django.db.models import Q, QuerySet

from bookmarks.models import Bookmark, Tag
from bookmarks.utils import unique


def query_bookmarks(user: User, query_string: str) -> QuerySet:
    return _base_bookmarks_query(user, query_string) \
        .filter(is_archived=False)


def query_archived_bookmarks(user: User, query_string: str) -> QuerySet:
    return _base_bookmarks_query(user, query_string) \
        .filter(is_archived=True)


def query_shared_bookmarks(user: Optional[User], query_string: str) -> QuerySet:
    return _base_bookmarks_query(user, query_string) \
        .filter(shared=True) \
        .filter(owner__profile__enable_sharing=True)


def _base_bookmarks_query(user: Optional[User], query_string: str) -> QuerySet:
    query_set = Bookmark.objects

    # Filter for user
    if user:
        query_set = query_set.filter(owner=user)

    # Split query into search terms and tags
    query = parse_query_string(query_string)

    # Filter for search terms and tags
    for term in query['search_terms']:
        query_set = query_set.filter(
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(website_title__icontains=term)
            | Q(website_description__icontains=term)
            | Q(url__icontains=term)
        )

    for tag_name in query['tag_names']:
        query_set = query_set.filter(
            tags__name__iexact=tag_name
        )

    # Untagged bookmarks
    if query['untagged']:
        query_set = query_set.filter(
            tags=None
        )
    # Unread bookmarks
    if query['unread']:
        query_set = query_set.filter(
            unread=True
        )

    # Sort by date added
    query_set = query_set.order_by('-date_added')

    return query_set


def query_bookmark_tags(user: User, query_string: str) -> QuerySet:
    bookmarks_query = query_bookmarks(user, query_string)

    query_set = Tag.objects.filter(bookmark__in=bookmarks_query)

    return query_set.distinct()


def query_archived_bookmark_tags(user: User, query_string: str) -> QuerySet:
    bookmarks_query = query_archived_bookmarks(user, query_string)

    query_set = Tag.objects.filter(bookmark__in=bookmarks_query)

    return query_set.distinct()


def query_shared_bookmark_tags(user: Optional[User], query_string: str) -> QuerySet:
    bookmarks_query = query_shared_bookmarks(user, query_string)

    query_set = Tag.objects.filter(bookmark__in=bookmarks_query)

    return query_set.distinct()


def query_shared_bookmark_users(query_string: str) -> QuerySet:
    bookmarks_query = query_shared_bookmarks(None, query_string)

    query_set = User.objects.filter(bookmark__in=bookmarks_query)

    return query_set.distinct()


def get_user_tags(user: User):
    return Tag.objects.filter(owner=user).all()


def parse_query_string(query_string):
    # Sanitize query params
    if not query_string:
        query_string = ''

    # Split query into search terms and tags
    keywords = query_string.strip().split(' ')
    keywords = [word for word in keywords if word]

    search_terms = [word for word in keywords if word[0] != '#' and word[0] != '!']
    tag_names = [word[1:] for word in keywords if word[0] == '#']
    tag_names = unique(tag_names, str.lower)

    # Special search commands
    untagged = '!untagged' in keywords
    unread = '!unread' in keywords

    return {
        'search_terms': search_terms,
        'tag_names': tag_names,
        'untagged': untagged,
        'unread': unread,
    }
