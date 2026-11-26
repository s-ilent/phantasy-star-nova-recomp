"""Build the English text and UI archive from your own copy of the game's CPK archives."""

import argparse
import hashlib
import json
import os
import re
import sys
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

RECIPES = Path(__file__).resolve().with_name('text')
sys.path.insert(0, str(RECIPES))

import apply_spec
import cpk_build
import rmdwrite
from center_dialogue_names import patch as center_dialogue_names
from cpk import Cpk, read_entry
from encode_text import Encoder
from rmdlib import Rmd


class Archive:
    def __init__(self, archive):
        self.archive = archive
        self.entries = {entry['path'].casefold(): entry for entry in archive.entries}

    def read(self, name):
        try:
            entry = self.entries[name.casefold()]
        except KeyError as exc:
            raise ValueError(f'{name} is missing from {self.archive.f.name}') from exc
        return read_entry(self.archive, entry)

    def has(self, name):
        return name.casefold() in self.entries


def recipe(name):
    return json.loads((RECIPES / f'{name}.json').read_text(encoding='utf-8'))


def original_font_data(archives):
    for size, (archive, name) in recipe('atlases').items():
        raw = archives[archive].read(name)
        rmd = Rmd(raw)
        dimensions = tuple(map(int, size.split('x')))
        if dimensions != (rmd.W, rmd.H):
            raise ValueError(f'Unexpected atlas dimensions in {name}')
        rmdwrite._templates[dimensions] = raw[rmd.hs:rmd.hs + 0x1e0]

    pictures = {}
    for character, (archive, name, index) in recipe('glyphs').items():
        rmd = Rmd(archives[archive].read(name))
        width, glyph_class = rmd.recs[index][:2]
        pictures[character] = (rmd.glyph(index), width, glyph_class)

    base, patch = (archives[key] for key in ('base', 'patch'))
    charset = (patch if patch.has('BasicCharSet.rmd') else base).read('BasicCharSet.rmd')
    return recipe('codes'), pictures, charset


def build_messages(archives, font, fallback_font):
    codes, pictures, charset = original_font_data(archives)
    encoder = Encoder(str(font), str(fallback_font), recipe('font-metrics'), codes, pictures, charset)
    messages = recipe('messages')
    replacements = {}
    base, patch = (archives[key] for key in ('base', 'patch'))
    for message_id, (text, context) in messages.items():
        name = f'msg_{message_id}.rmd'
        template = patch.read(name) if patch.has(name) else base.read(name) if base.has(name) else None
        try:
            replacements[name] = encoder.encode(int(message_id), text, template=template, context=context)
        except ValueError as exc:
            raise ValueError(f'English text encoding failed for {name}: {exc}') from exc
        if len(replacements) % 2000 == 0:
            print(f'Encoded {len(replacements):,} of {len(messages):,} English messages', flush=True)
    print(f'Encoded {len(replacements):,} English messages', flush=True)
    return replacements


def build_name_tables(patch):
    names = recipe('names')
    replacements = {}
    for filename, prefix, column in (('uireferenceparameter.csv', 'StringFix_Name', 4),
                                     ('NpcBaseParameter.csv', 'key50', 26)):
        text = patch.read(filename).decode('cp932')
        newline = '\r\n' if '\r\n' in text else '\n'
        rows = []
        for line in text.split(newline):
            fields = line.split(',')
            if len(fields) > column and fields[0].startswith(prefix):
                fields[column] = names.get(fields[column], fields[column])
            rows.append(','.join(fields))
        replacements[filename] = newline.join(rows).encode('cp932')
    return replacements


def build_textures(archives, font, allow_missing=False):
    specs = recipe('textures')
    replacements = {}
    for name, spec in specs.items():
        if allow_missing and not archives[spec['archive']].has(name):
            print(f'{name} is missing from this copy (a fan translation dropped it): its English lettering is skipped',
                  flush=True)
            continue
        raw = archives[spec['archive']].read(name)
        if hashlib.sha256(raw).hexdigest() != spec['sha256']:
            raise ValueError(f'{name} differs from the original {spec["archive"]} archive used by this English patch')
        replacements[name] = apply_spec.apply(spec, raw, str(font))
    print(f'Redrew {len(replacements)} English UI textures', flush=True)
    return replacements


def build(base, patch, output, font, allow_missing=False):
    if not font.is_file():
        raise ValueError(f'English font file is missing: {font}')
    fallback_font = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts' / 'segoeuib.ttf'
    if not fallback_font.is_file():
        raise ValueError(f'Windows Segoe UI Bold fallback font is missing: {fallback_font}')
    if output in (base, patch) or (output.exists() and
                                   any(output.samefile(source) for source in (base, patch))):
        raise ValueError('The English overlay destination would replace an original game archive')

    with ExitStack() as stack:
        archives = {}
        for region, path in (('base', base), ('patch', patch)):
            archive = Cpk(path)
            stack.callback(archive.close)
            archives[region] = Archive(archive)
        replacements = build_messages(archives, font, fallback_font)
        replacements.update(build_name_tables(archives['patch']))
        replacements.update(build_textures(archives, font, allow_missing))
        replacements['ui_field.crbpj'] = center_dialogue_names(archives['patch'].read('ui_field.crbpj'))

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='text-build-', dir=output.parent) as stage:
        pending = Path(stage) / output.name
        cpk_build.build(patch, pending, replacements)
        os.replace(pending, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path, help='original NOVA_FileList_Vita.cpk from the base game')
    parser.add_argument('update', type=Path, help='original NOVA_FileList_Vita_patch.cpk from the 1.05 update')
    parser.add_argument('output', type=Path, help='destination for the English patch CPK')
    parser.add_argument('--font', type=Path, required=True, help='the font file to draw the text with')
    parser.add_argument('--allow-missing-textures', action='store_true',
                        help='an update archive restored from a fan translation: skip UI textures it no longer has')
    args = parser.parse_args()
    try:
        build(*(path.resolve() for path in (args.base, args.update, args.output, args.font)), args.allow_missing_textures)
    except (OSError, ValueError, KeyError, cpk_build.C.CpkError) as exc:
        parser.exit(1, f'English localization setup failed: {exc}\n')


if __name__ == '__main__':
    main()
