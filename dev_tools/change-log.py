#!/usr/bin/env python3
"""
Utility to dynamically create changelogs from fragment files
"""
import argparse
import glob
import os
import itertools
import operator
import functools
import sys
import contextlib
import datetime
from typing import NamedTuple, List, Iterable, Dict, Tuple

import yaml


TODAY = datetime.date.today().isoformat()
APP_NAME = os.path.basename(__file__)


def is_semver(argument: str) -> str:
    parts = argument.split('.')
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            'expected 3 version parts separate by %r, got %d' % ('.', len(parts))
        )
    try:
        list(map(int, parts))
    except ValueError:
        raise argparse.ArgumentTypeError('all version parts must be integers')
    return argument


def main():
    options = CLI.parse_args()
    action = options.action
    action(options)


def compile(options: argparse.Namespace):
    compile_changelog(
        fragment_dir=options.FRAGMENT_DIR,
        output=options.output,
        item_format=options.item_format,
        categories=options.categories
    )


def release(options: argparse.Namespace):
    release_changes(
        fragment_dir=options.FRAGMENT_DIR,
        new_ver=options.SEMVER,
    )


CLI = argparse.ArgumentParser(
    description="dynamically create changelogs from fragment files"
)
CLI.add_argument(
    'FRAGMENT_DIR',
    type=str,
    help='path to directory containing fragments'
)
SUB_CLI = CLI.add_subparsers(required=True, dest='SUBCMD')

# CLI for updating release metadata
RELEASE_CLI = SUB_CLI.add_parser(
    'release',
    help='prepare unreleased fragments'
)
RELEASE_CLI.set_defaults(action=release)
RELEASE_CLI.add_argument(
    'SEMVER',
    help='version of unreleased fragments',
    type=is_semver,
)

# CLI for writing changelogs
COMPILE_CLI = SUB_CLI.add_parser(
    'compile',
    help='compile a changelog',
)
COMPILE_CLI.set_defaults(action=compile)
COMPILE_CLI.add_argument(
    '-o',
    '--output',
    help='output path or "-" for stdout',
    default='-',
)
COMPILE_CLI.add_argument(
    '-f',
    '--item_format',
    default='* {short}',
    help='format of individual changes'
)
COMPILE_CLI.add_argument(
    '-c',
    '--categories',
    nargs='+',
    default=['Added', 'Changed', 'Fixed', 'Security']
)


# General components
def yaml_block_representer(dumper, data: str):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    elif data.count(' ') > 1:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
    else:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='')


yaml.SafeDumper.add_representer(str, yaml_block_representer)


@functools.total_ordering
class Release(NamedTuple):
    """
    Metadata on a single release

    Releases can be compared by their version number, e.g.
    ``Release('1.0.3', ...) > Release('0.9.5', ...)``.
    """
    semver: str
    date: str

    @property
    def numeric(self) -> Tuple[int, int, int]:
        """Numeric version number as ``major, minor, patch``"""
        if self.semver == UNRELEASED.semver:
            return int(1e16), 0, 0
        major, minor, patch = self.semver.split('.')
        return int(major), int(minor), int(patch)

    @classmethod
    def from_file(cls, path) -> 'List[Release]':
        """Load all releases from a file at ``path``"""
        try:
            with open(path) as in_stream:
                meta_data = yaml.safe_load(in_stream)
            if meta_data is None:
                raise FileNotFoundError
        except FileNotFoundError:
            return []
        return [
            cls(**version)
            for version in meta_data
        ]

    @staticmethod
    def to_file(path, instances: 'List[Release]'):
        """Store all release to a file at ``path``"""
        with open(path, 'w') as out_stream:
            yaml.safe_dump(
                [dict(instance._asdict()) for instance in instances],
                out_stream,
                sort_keys=False,
            )

    def __gt__(self, other):
        if not isinstance(other, Release):
            return NotImplemented
        return self.numeric > other.numeric

    def __eq__(self, other):
        if not isinstance(other, Release):
            return NotImplemented
        return self.numeric == other.numeric


UNRELEASED = Release('Unreleased', TODAY)


class Fragment(NamedTuple):
    """
    Metadata of a single change
    """
    path: str
    category: str
    short: str
    long: str
    version: str = UNRELEASED.semver
    pulls: List[str] = []
    issues: List[str] = []

    @classmethod
    def from_file(cls, path):
        """Load a single fragment from a file at ``path``"""
        with open(path) as in_stream:
            meta_data = yaml.safe_load(in_stream)
        if meta_data is None:
            raise RuntimeError(f'failed to load YAML data from {path}')
        meta_data['pulls'] = meta_data.pop('pull requests', [])
        return cls(path=path, **meta_data)

    def to_file(self):
        meta_data = {
            'category': self.category,
            'short': self.short,
            'long': self.long,
        }
        if self.issues:
            meta_data['issues'] = self.issues
        if self.pulls:
            meta_data['pull requests'] = self.pulls
        if self.version != UNRELEASED.semver:
            meta_data['version'] = self.version
        with open(self.path, 'w') as out_stream:
            yaml.safe_dump(meta_data, out_stream, sort_keys=False)


def categorise(fragments: Iterable[Fragment], field: str) -> Dict[str, List[Fragment]]:
    """Categorise fragments by a shared field"""
    key = operator.attrgetter(field)
    fragments = sorted(fragments, key=key)
    return {
        category: list(group)
        for category, group in itertools.groupby(
            fragments, key=key
        )
    }


def load_metadata(fragment_dir: str) -> Tuple[List[Release], Dict[str, List[Fragment]]]:
    """
    Load all metadata from ``fragment_dir``

    Returns a list of currently stored :py:class:`Release` \ s
    and a mapping from version number to :py:class:`Fragment` \ s.
    """
    releases = Release.from_file(os.path.join(fragment_dir, 'versions.yaml'))
    versioned_fragments = categorise(
        (
            Fragment.from_file(path)
            for path in glob.glob(os.path.join(fragment_dir, '*.yaml'))
            if os.path.basename(path) != 'versions.yaml'
        ),
        'version',
    )
    if UNRELEASED.semver in versioned_fragments:
        releases.append(UNRELEASED)
    releases.sort()
    return releases, versioned_fragments


def underline(line: str, symbol: str) -> List[str]:
    """Underline a single-line ``.rst`` string"""
    return [line, symbol * len(line), '']


# Release information update
def release_changes(fragment_dir, new_ver: str):
    releases, versioned_fragments = load_metadata(fragment_dir=fragment_dir)
    # no releases, no fragments
    if not releases:
        Release.to_file(
            os.path.join(fragment_dir, 'versions.yaml'),
            [Release(new_ver, TODAY)]
        )
    else:
        if releases[0] == UNRELEASED:
            releases[0] = Release(new_ver, TODAY)
            for fragment in versioned_fragments[UNRELEASED.semver]:
                fragment._replace(version=new_ver).to_file()
        else:
            releases.insert(0, Release(new_ver, TODAY))
        Release.to_file(
            os.path.join(fragment_dir, 'versions.yaml'),
            releases
        )


# Changelog compilation
def format_release(
        release: Release,
        fragments: List[Fragment],
        item_format: str,
        categories: List[str],
) -> List[str]:
    """Compile the changelog section for a single release"""
    lines = underline(f'[{release.semver}] - {release.date}', '=')
    categorised_fragments = {
        cat.casefold(): frags
        for cat, frags in categorise(fragments, 'category').items()
    }
    for category in categories:
        caseless = category.casefold()
        if caseless not in categorised_fragments:
            continue
        lines.extend(underline(category, '-'))
        for fragment in categorised_fragments[caseless]:
            lines.append(item_format.format(**fragment._asdict()))
        lines.append('')
    return lines


CHANGELOG_HEADER = f"""
.. Created by {APP_NAME} at {TODAY}, command
   '{" ".join(sys.argv)}'
   based on the format of 'https://keepachangelog.com/'

#########
CHANGELOG
#########

""".lstrip()


def compile_changelog(fragment_dir, output, item_format, categories: List[str]):
    """Compile a changelog and write it to ``output``"""
    releases, versioned_fragments = load_metadata(fragment_dir=fragment_dir)
    unknown_versions = set(versioned_fragments) - set(rl.semver for rl in releases)
    if unknown_versions:
        raise RuntimeError(
            'Fragments include unknown versions: "%s"' % '", "'.join(unknown_versions)
        )
    out_context = contextlib.nullcontext(sys.stdout) if output == '-'\
        else open(output, 'w')
    with out_context as out_stream:
        out_stream.write(CHANGELOG_HEADER)
        for release in releases:
            for line in format_release(
                release, versioned_fragments[release.semver], item_format, categories
            ):
                out_stream.write(line + '\n')


if __name__ == '__main__':
    main()
