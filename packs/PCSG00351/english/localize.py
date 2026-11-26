"""Build the English localization for Phantasy Star Nova from your own copy of the game.

vitarecomp localize PCSG00351 runs this after the build (and vitarecomp add runs it after an update's build). It reads the
original Japanese archives the add step decrypted into the library and writes a language overlay beside them:

    <library>/decrypted/PCSG00351/lang/en/NOVA_FileList_Vita_patch.cpk   menus, dialogue, names and UI art in English
    <library>/decrypted/PCSG00351/lang/en/NOVA_FileList_Vita_movie.cpk   the movies with the burned-in Japanese subtitles
                                                                         removed and English subtitles drawn in
    <library>/decrypted/PCSG00351/lang/en/language.txt                   the name the F10 Language row shows
    <library>/decrypted/PCSG00351/lang/default.txt                       "en": the language a new player starts in

A copy that already carries a fan translation (Arks-Layer's, often sold as a "v1.05 English" copy) has it removed first:
its update archive is rebuilt from the untouched base game (text/fan_restore.py), and its re-encoded story movies,
which show the fan's English under the Japanese line, have both lines erased before the English subtitles are drawn.
The warning notice the fan translation turns into its credits is drawn again too. What cannot come back from a fan copy
is said when it runs: an unmodified copy gives the full result.

The game's own files are only read. The runtime swaps in a file from lang/<code>/ when that language is chosen in F10, so
"Original" there still plays the Japanese game. Nothing of the game is in this folder: the recipes hold English text,
drawing instructions and the SHA-256 of each original file they apply to.

The text and subtitles are drawn with a font: the project ships a default (K2D Medium, SIL OFL), and a font you put in
fonts/ yourself is used in its place. --font or RECOMP_ENGLISH_FONT names another; its own metrics decide the spacing.

Usage: localize.py <library title folder> [--font F] [--ffmpeg F] [--force]
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
# A font ships with the project as the default (K2D Medium, SIL OFL, fonts/OFL-K2D.txt), so the English builds with
# nothing of your own. A font you put in fonts/ yourself is used in its place, and --font or RECOMP_ENGLISH_FONT names
# another still. Any font the builders can open works: its own metrics decide the spacing, and text/english_layout.py
# judges the result.
FONT_DIR = HERE / 'fonts'
FONT_DEFAULT = 'K2D-Medium.ttf'
FONT_SUFFIXES = ('.ttf', '.otf')


def font_files():
    """Every font in fonts/, in a stable order (two runs pick the same one)."""
    return sorted(p for p in FONT_DIR.iterdir() if p.suffix.lower() in FONT_SUFFIXES) if FONT_DIR.is_dir() else []


def default_font():
    """RECOMP_ENGLISH_FONT, else a font of your own in fonts/ (any font there that is not the shipped default), else the
    shipped default. The path returned is named in full only by the message that asks for one."""
    named = os.environ.get('RECOMP_ENGLISH_FONT')
    if named:
        p = Path(named)
        return p if p.is_file() else FONT_DIR / named
    files = font_files()
    return ([p for p in files if p.name != FONT_DEFAULT] or files or [FONT_DIR / FONT_DEFAULT])[0]


DEFAULT_FONT = default_font()

BASE, MOVIE, PATCH = 'NOVA_FileList_Vita.cpk', 'NOVA_FileList_Vita_movie.cpk', 'NOVA_FileList_Vita_patch.cpk'
# the unmodified Japanese 1.00 game and 1.05 update archives the recipes were made from
ORIGINALS = {
    ('app0', BASE): 'ad85c330c3258b0f18f57dcf77736f9fbea89c40b66dfef3fbb5c4daeff77e7a',
    ('app0', MOVIE): 'b006fcbf06008c1271b47b3999798e042243c6c99de570a6e069188ec971a01e',
    ('patch0', PATCH): 'ddd82122dd8cb6436566266879251b85c0b41cd758791bfd4f1e16239d9f9ba9',
}
MARK = '.localize.json'   # in lang/en: what the overlay was built from; a lang/en without it was made some other way


class Stop(Exception):
    pass


def file_hash(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_originals(title):
    """{archive name: (path, is the original)}, each checked once per file version (size and time kept in
    lang/.originals.json)"""
    cache_path = title / 'lang' / '.originals.json'
    try:
        cache = json.loads(cache_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        cache = {}
    found = {}
    for (folder, name), want in ORIGINALS.items():
        path = title / folder / name
        if not path.is_file():
            raise Stop(f'{path} is missing. Add the base game and its 1.05 update first (vitarecomp add).')
        st = path.stat()
        stamp = f'{st.st_size} {st.st_mtime_ns}'
        key = f'{folder}/{name}'
        if cache.get(key, {}).get('stamp') != stamp:
            print(f'Checking {key} against the original Japanese archive...', flush=True)
            cache[key] = {'stamp': stamp, 'sha256': file_hash(path)}
        found[name] = (path, cache[key]['sha256'] == want)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=1), encoding='utf-8')
    return found


def check_font(font):
    """The file to draw the English with, or Stop. The project ships a default (SIL OFL) and any other font works too,
    used as it comes: its own metrics decide the spacing, and text/english_layout.py checks the built text."""
    if not font.is_file():
        raise Stop(f'The English text needs a font: {FONT_DIR} has none of its own, and the default ({FONT_DEFAULT})\n'
                   f'is missing from it too. Restore that file, put a font in {FONT_DIR}, or name one with --font or\n'
                   f'RECOMP_ENGLISH_FONT, then run: vitarecomp localize PCSG00351')
    from PIL import ImageFont
    try:
        family, style = ImageFont.truetype(str(font), 18).getname()
    except OSError as error:
        raise Stop(f'{font} cannot be opened as a font') from error
    digest = file_hash(font)
    print(f'Drawing the English with {font.name} ({family} {style}).', flush=True)
    return digest


def find_ffmpeg(given):
    candidates = [given] if given else [
        Path(os.environ['ATIV_WIN_TOOLCHAIN']) / 'ffmpeg-cli' / 'ffmpeg.exe' if os.environ.get('ATIV_WIN_TOOLCHAIN') else None,
        ROOT / 'toolchain' / 'ffmpeg-cli' / 'ffmpeg.exe',
        Path(shutil.which('ffmpeg')) if shutil.which('ffmpeg') else None,
    ]
    for path in candidates:
        if path and Path(path).is_file():
            return Path(path).resolve()
    raise Stop('No FFmpeg program for the English movies. Run the toolchain setup again (README step 2): it adds '
               'toolchain/ffmpeg-cli/ffmpeg.exe. Or pass --ffmpeg.')


def recipe_key(font_digest, ffmpeg, title):
    """what an overlay is built from: the recipes and scripts, the font, FFmpeg and the copy's own archives"""
    h = hashlib.sha256()
    for path in sorted(p for p in HERE.rglob('*') if p.is_file() and 'fonts' not in p.relative_to(HERE).parts
                       and '__pycache__' not in p.parts):
        h.update(f'{path.relative_to(HERE).as_posix()} {file_hash(path)}\n'.encode())
    h.update(f'font {font_digest}\nffmpeg {file_hash(ffmpeg)}\n'.encode())
    h.update((title / 'lang' / '.originals.json').read_bytes())
    return h.hexdigest()


def step(label, argv):
    print(f'{label}...', flush=True)
    # (-u: the builders' progress shows as it happens; -B: no .pyc beside the recipes)
    result = subprocess.run([sys.executable, '-u', '-B', *map(str, argv)])
    if result.returncode:
        raise Stop(f'{label} failed (exit {result.returncode}); its output is above.')


def localize(title, font, ffmpeg, force):
    english = title / 'lang' / 'en'
    mark = english / MARK
    if english.is_dir() and any(english.iterdir()) and not mark.is_file() and not force:
        raise Stop(f'{english} already holds an English overlay that this script did not build. It was left as it is. '
                   'Run vitarecomp localize PCSG00351 --force to replace it.')
    found = check_originals(title)
    paths = {name: path for name, (path, _) in found.items()}
    if not found[BASE][1]:
        raise Stop(f'{BASE} is not the original Japanese base game archive. The English localization is built from the '
                   'unmodified base game (a fan translation leaves it as it is): add an unmodified copy, then run '
                   'vitarecomp localize PCSG00351.')
    fan_text, fan_movies = not found[PATCH][1], not found[MOVIE][1]
    if fan_text or fan_movies:
        print('English localization: this copy carries a fan translation (its update or movie archive is not the '
              'original). The fan translation is removed and this English is built in its place, as far as the base '
              'game allows. A few parts cannot be restored from a fan copy: one UI texture the fan translation deleted '
              '(some screens can show noise), eight untranslated lines that show the base game\'s older Japanese '
              'wording, and the story movies, which start from the fan\'s lower-quality re-encode. For the full '
              'result, add an unmodified Japanese copy (the game and its 1.05 update) and run this again.',
              flush=True)
    font_digest = check_font(font)
    key = recipe_key(font_digest, ffmpeg, title)
    outputs = [english / PATCH, english / MOVIE]
    try:
        built = json.loads(mark.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        built = {}
    if built.get('key') == key and (english / 'language.txt').is_file() and \
            all(p.is_file() and built.get('size', {}).get(p.name) == p.stat().st_size for p in outputs):
        print(f'English localization is up to date: {english}', flush=True)
    else:
        english.mkdir(parents=True, exist_ok=True)
        mark.unlink(missing_ok=True)   # (a build stopped half-way is redone next time)
        work = title / 'lang' / '.work'
        work.mkdir(parents=True, exist_ok=True)
        if fan_text:
            restored = work / PATCH
            step('Removing the fan translation from the update archive',
                 [HERE / 'text' / 'fan_restore.py', paths[PATCH], paths[BASE], restored])
            step('Building English menus, dialogue and UI art',
                 [HERE / 'build_text.py', paths[BASE], restored, english / PATCH, '--font', font,
                  '--allow-missing-textures'])
            restored.unlink(missing_ok=True)
        else:
            step('Building English menus, dialogue and UI art',
                 [HERE / 'build_text.py', paths[BASE], paths[PATCH], english / PATCH, '--font', font])
        if fan_movies:
            step('Building the English movies (erasing the fan translation\'s dual subtitles, drawing English ones)',
                 [HERE / 'build_movies.py', paths[MOVIE], english / MOVIE, '--font', font, '--ffmpeg', ffmpeg,
                  '--work', work / 'movies', '--fan'])
        else:
            step('Building the English movies (removing the Japanese subtitles, drawing English ones)',
                 [HERE / 'build_movies.py', paths[MOVIE], english / MOVIE, '--font', font, '--ffmpeg', ffmpeg,
                  '--work', work / 'movies'])
        shutil.rmtree(work, ignore_errors=True)
        (english / 'language.txt').write_text('English\n', encoding='utf-8')
        mark.write_text(json.dumps({'key': key, 'size': {p.name: p.stat().st_size for p in outputs}}, indent=1),
                        encoding='utf-8')
    default = title / 'lang' / 'default.txt'
    if not default.is_file():
        default.write_text('en\n# The language a new player starts in (F10 > Language changes it): en, or original for the '
                           'Japanese game.\n', encoding='utf-8')
    print(f'English localization ready: {english}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('title', type=Path, help='the library folder of the game: <library>/decrypted/PCSG00351')
    parser.add_argument('--font', type=Path, help=f'the font to draw the English with (default: {DEFAULT_FONT})')
    parser.add_argument('--ffmpeg', type=Path, help='an FFmpeg program with libx264 (default: toolchain/ffmpeg-cli)')
    parser.add_argument('--force', action='store_true', help='replace an English overlay this script did not build')
    args = parser.parse_args()
    try:
        localize(args.title.resolve(), (args.font or DEFAULT_FONT).resolve(), find_ffmpeg(args.ffmpeg), args.force)
    except Stop as stop:
        print(f'English localization: {stop}', file=sys.stderr, flush=True)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
