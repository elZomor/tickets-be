"""The staff roles: Django Groups, each with the model permissions it carries.

`sync_roles` is idempotent and runs after every migrate (and as
`manage.py seed_roles`), so a deploy always has the groups and their grants in
line with this table. A reader has no group. Site Admin is `is_superuser`, not a
group: it holds everything, including what is not listed here.

Article rights beyond add/change/delete/view: `review_article` moves a piece
through review (send back for changes, reject, mark ready for editing);
`publish_article` schedules, publishes and archives it. An author (anyone with
`add_article` but not `change_article`) edits only their own piece while it is a
draft, rejected or sent back for changes.
"""

from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.db.models import Q

APP_LABEL = 'third_side'


def reviewers():
    """Who an article can be assigned to: staff who review articles."""
    from third_side.models import ThirdSideUser

    return Q(pk__in=ThirdSideUser.objects.with_perm('review_article').values('pk'))


def _crud(model, *verbs):
    return [f'{verb}_{model}' for verb in verbs]


ALL = ('add', 'change', 'delete', 'view')

REVIEWER = [
    'add_article',
    'change_article',
    'view_article',
    'review_article',
    'add_media',
    'add_tag',
    'view_comment',
    'view_report',
]

ROLES = {
    # Staff author: writes pieces and edits their own until they are submitted.
    'Writer': ['add_article', 'add_media', 'add_tag'],
    'Reviewer': REVIEWER,
    'Publisher': REVIEWER + ['publish_article', 'delete_article'],
    # The site's structure and standing content.
    'Content Manager': [
        *_crud('category', *ALL),
        *_crud('navgroup', *ALL),
        *_crud('tag', *ALL),
        *_crud('critic', *ALL),
        *_crud('festival', *ALL),
        *_crud('festivalpost', *ALL),
        *_crud('aboutpage', *ALL),
        *_crud('termsversion', *ALL),
        'add_media',
    ],
    'Moderator': [
        'view_article',
        'view_comment',
        'change_comment',
        'delete_comment',
        'view_report',
        'change_report',
    ],
    'Marketing': [*_crud('ad', *ALL), 'add_outgoingemail', 'view_outgoingemail'],
}


def sync_roles(app_config=None):
    """Create or update the role groups. Returns {group name: missing codenames}."""
    from django.apps import apps

    # Permissions are created by auth's own post_migrate hook; make sure ours
    # exist whichever hook runs first.
    create_permissions(app_config or apps.get_app_config(APP_LABEL), verbosity=0)
    known = {
        p.codename: p
        for p in Permission.objects.filter(content_type__app_label=APP_LABEL)
    }
    missing = {}
    for name, codenames in ROLES.items():
        group, _ = Group.objects.get_or_create(name=name)
        group.permissions.set([known[c] for c in codenames if c in known])
        gone = [c for c in codenames if c not in known]
        if gone:
            missing[name] = gone
    return missing
