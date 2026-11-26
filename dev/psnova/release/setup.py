"""Windows release installer for Phantasy Star Nova Recomp.

Support reports, in-place updates, build generations and rollback were added in setup_reports.py, setup_updates.py and
setup_generations.py, and in the parts of this file that use them.
"""

import argparse
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import setup_generations as G  # noqa: E402
import setup_reports as R  # noqa: E402
import setup_sources  # noqa: E402
import setup_updates as U  # noqa: E402
from setup_sources import CONTENT, TITLE, SetupError  # noqa: E402,F401
ENGINE = ROOT / "engine"
DATA = ROOT / "NovaData"
PLAYER = DATA / "Player"
PYTHON = ENGINE / "python/python.exe"
LOCALIZATION = ROOT / "localization"
BRIDGE = ENGINE / "release/Play Nova.exe"
GAME_EXE = ROOT / "Phantasy Star Nova.exe"
FFMPEG = ENGINE / "release/ffmpeg.exe"
ENGINE_SOURCES = U.ENGINE_DIRS
FONT_SUFFIXES = (".ttf", ".otf")


def first_font():
    """The font to draw the English with when none is chosen: the first font file in localization/fonts. No font ships
    with this project and none is named, so this is whatever the player put there."""
    found = sorted(p for p in (LOCALIZATION / "fonts").glob("*") if p.suffix.lower() in FONT_SUFFIXES)
    return found[0] if found else LOCALIZATION / "fonts" / "font.ttf"


DEFAULT_FONT = first_font()
FALLBACK_FONT = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeuib.ttf"   # the text builder's fallback (build_text.py)
SONY_FIRMWARE = "https://www.playstation.com/en-us/support/hardware/psvita/system-software/"
PUP_SHA256 = "6ef6dc8da6db026f28647713e473486d770087a605c52a8d751bfca7478386cf"
BASE = "NOVA_FileList_Vita.cpk"
MOVIE = "NOVA_FileList_Vita_movie.cpk"
PATCH = "NOVA_FileList_Vita_patch.cpk"
FIRMWARE_MODULES = (
    "os0/us/libgxm_es4.suprx.elf", "os0/us/libgpu_es4.suprx.elf",
    "vs0/sys/external/libc.suprx.elf", "vs0/sys/external/libscemp4.suprx.elf",
    "vs0/sys/external/libsceavplayer.suprx.elf",
)
BASE_FILES = {
    "eboot.bin.elf": "f4b3a669b53cf5ac8a2ecb26b3686011011129d8db7930c88a578e1463592542",
    BASE: "ad85c330c3258b0f18f57dcf77736f9fbea89c40b66dfef3fbb5c4daeff77e7a",
    MOVIE: "b006fcbf06008c1271b47b3999798e042243c6c99de570a6e069188ec971a01e",
}
PATCH_FILES = {
    "eboot.bin.elf": "abb45e179726d3021de144a900f912534fa6879061e068228cc0cd55286edcf3",
    PATCH: "ddd82122dd8cb6436566266879251b85c0b41cd758791bfd4f1e16239d9f9ba9",
}
LAYERED_FILES = {
    "sce_module/libc.suprx.elf": "b782bcdfd4ad9b019d82b88c03be0d1595b8c54ef60a799bf784c21df83abd87",
    "disc1/f00000.bin": "2279ffb66f388f46b4e611f90d31e5d7ec94dcb849a97fddf7b6ff5c9880f42f",
    "disc1/f00001.bin": "f58ef308d7e7213ab80f5ef05e325e01dd01beb4578471ac5bcb90226cfbeff0",
    "disc1/f00002.bin": "f34627d1493555cb7bf8497ab99d75b9f2e31b751f7a0cc5788cb6e2f698ebcb",
}
STAGES = ("firmware", "base", "update", "import", "analyze", "recompile", "build", "english-text", "english-movies")
NATIVE_STAGES = STAGES[:7]
DATA_STAGES = STAGES[:3]
UPDATE_HEADROOM = 1_500_000_000


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


atomic_text = G.atomic_text
json_file = lambda path: G.read_json(path) or {}  # noqa: E731


def sha_text(*parts):
    return hashlib.sha256("\n".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def check_paths(paths):
    missing = [str(path) for path in paths if not path.is_file() or not path.stat().st_size]
    if missing:
        raise SetupError("Missing or empty required files:\n" + "\n".join(missing))


def original_files(packages, license_given):
    """Check the extracted-folder inputs (the PKG and ZIP forms are checked by their headers and by hash after import)
    and yield (name, path) for every file in them, to fingerprint."""
    folders = [package for package in packages if package.form == "folder"]
    required = []
    for package in folders:
        folder = package.path
        archives = (BASE, MOVIE) if package.role == "base" else (PATCH,)
        required.extend(folder / name for name in (*archives, "eboot.bin"))
        pfs = folder / "sce_pfs"
        if pfs.exists():
            required.extend(pfs / name for name in ("files.db", "unicv.db", "pflist"))
        if pfs.exists() and package.role == "base" and not license_given:
            required.append(folder / "sce_sys/package/work.bin")
    if len(folders) == 2:   # (a PKG carries these files inside it: the layered hashes check them after import)
        base, update = (package.path for package in sorted(folders, key=lambda package: package.role != "base"))
        for name in LAYERED_FILES:
            name = name.removesuffix(".elf")
            if not any((folder / name).is_file() for folder in (base, update)):
                required.append(update / name)
    check_paths(required)
    for package in folders:
        license_file = package.path / "sce_sys/package/work.bin"
        encrypted = (package.path / "sce_pfs").is_dir()
        if package.role == "base" and encrypted and not license_given and license_file.stat().st_size not in (512, 1024):
            raise SetupError(f"Invalid game license size. Supply your original work.bin at {license_file}.")
    for package in folders:
        for path in sorted(package.path.rglob("*")):
            if path.is_symlink() or path.is_junction():
                raise SetupError(f"Copy the linked file or folder into your game dump first: {path}")
            if path.is_file():
                yield f"{package.role}/{path.relative_to(package.path).as_posix()}", path


def check_hashes(folder, expected, package=None):
    check_paths(folder / name for name in expected)
    for name, sha256 in expected.items():
        if digest(folder / name) != sha256:
            if package is not None and package.form != "folder":
                raise SetupError(f"The {package.role} package {package.label} produced a {name} that differs from the "
                                 "supported unmodified Japanese game. The download or copy is damaged, or the package has "
                                 "been modified. Get the original base game 1.00 and update 1.05 packages again. "
                                 "Use packages from before any fan patch.")
            raise SetupError(f"{folder / name} differs from the supported unmodified Japanese game. "
                             "Replace it with the matching file from your 1.00 base game or 1.05 update. "
                             "Use the original archives before applying a fan patch.")


@contextmanager
def setup_lock():
    import msvcrt
    DATA.mkdir(exist_ok=True)
    with (DATA / "setup.lock").open("a+b") as handle:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise SetupError("Another setup process is using this folder. Close it before trying again.") from error
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def stage_environment(library, engine=ENGINE):
    prefixes = ("RECOMP_", "ATIV_", "PYTHON", "BUILD_EXTRA_ENV", "NATIV_")
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith(prefixes)}
    for key in ("ANALYZER", "FORCE", "TARGET", "JOBS", "CPU", "CC", "CXX", "EXTRA_ENV"):
        env.pop(key, None)
    env.update(ATIV_DUMP=str(library), ATIV_WIN_TOOLCHAIN=str(ENGINE / "toolchain"),
               PYTHONUTF8="1", PYTHONNOUSERSITE="1", PYTHONUNBUFFERED="1", PYTHONDONTWRITEBYTECODE="1",
               RECOMP_NO_REPATCH="1", RECOMP_NO_OVERLAY="1", TARGET="windows", RECOMP_CPU="generic")
    return env


def free_bytes(path):
    """Free bytes on the drive. Only a test configuration (update.json with "qa": true) can override the measurement."""
    override = os.environ.get("NOVA_QA_FREE_BYTES")
    if override and U.load_config(ROOT).qa:
        return int(override)
    return shutil.disk_usage(path).free


def remember_inputs(args):
    """Keep what the player selected, so the setup window can reopen it after a stop or a failure. Only a font the
    player chose is remembered: the font bundled in the release is found again by its own path."""
    chosen = {key: str(getattr(args, key).resolve()) if getattr(args, key, None) else ""
              for key in ("game", "update", "license", "firmware", "font")}
    DATA.mkdir(exist_ok=True)
    atomic_text(DATA / "setup-inputs.json", json.dumps(chosen, indent=2) + "\n")


def library_outputs(library):
    """The files that make a generation run, by group, relative to its library folder. A later build reuses a group only when
    every file in it still has the SHA-256 recorded when it was built."""
    title = library / "decrypted" / TITLE
    recomp = title / "recomp"
    rel = lambda path: path.relative_to(library).as_posix()  # noqa: E731
    images = [recomp / "game.img"] + [recomp / (Path(name).name.split(".")[0] + ".img") for name in FIRMWARE_MODULES]
    return {
        "firmware": [rel(library / "firmware/3.74" / name) for name in FIRMWARE_MODULES],
        "native": [rel(title / "version"), rel(title / "analysis/eboot.data.json"), *map(rel, images),
                   rel(recomp / ".recompile_inputs"), rel(recomp / "game_host.exe"), rel(recomp / "SDL3.dll"),
                   rel(recomp / ".built_version")],
        "text": [rel(recomp / "fs/lang/en" / PATCH)],
        "movies": [rel(recomp / "fs/lang/en" / MOVIE)],
    }


def cri_hash(engine_root):
    """The CPK reader and writer the movie builder imports from the engine's pipeline/cri folder: part of what makes the movie archive."""
    cri = Path(engine_root) / "pipeline" / "cri"
    return U.tree_sha256({p.name: p for p in sorted(cri.glob("*.py"))}) if cri.is_dir() else ""


def make_ids(sourceset, font_sha, fallback_sha, inputs_sha):
    """The fingerprints of the three things a build is made of, and the generation id they make together. Each id includes the
    inputs (the player's packages, folders and license) so a different input is a different build, as before."""
    version = (ENGINE / "version.txt").read_bytes().decode("utf-8", "replace")
    ffmpeg_sha = digest(FFMPEG)
    ids = {"inputs": inputs_sha,
           "native": sha_text("native-v1", version, PUP_SHA256, sourceset.hashes["engine"], inputs_sha),
           "text": sha_text("text-v1", inputs_sha, sourceset.hashes["text"], font_sha, fallback_sha),
           "movies": sha_text("movies-v2", inputs_sha, sourceset.hashes["movies"], font_sha, ffmpeg_sha, cri_hash(sourceset.roots["engine"]))}
    ids["full"] = sha_text("generation-v2", ids["native"], ids["text"], ids["movies"])
    return ids, ffmpeg_sha


@dataclass
class Build:
    mode: str                          # "setup" (the player's own inputs) or "update" (inputs taken from the build being updated)
    sourceset: object
    ids: dict
    font: Path
    font_sha: str
    fallback_sha: str
    ffmpeg_sha: str
    report: object
    attempt: object
    sources: object = None             # setup_sources.Sources, for mode "setup"
    firmware: Path = None
    donor: str = None                  # a build whose files this one may reuse, if they verify
    holds_game_lock: bool = False
    seeded: dict = field(default_factory=dict)

    @property
    def generation(self):
        return self.ids["full"][:24]


# ---- reuse of an earlier build

def verified_donor(candidates, ids, mode, report):
    """The first earlier build whose recorded files still verify and whose fingerprints match. Returns (id, what it can supply)
    or (None, None). Anything that does not verify (no record, a changed file) just means this build is made the long way."""
    for name in candidates:
        record = G.read_provenance(DATA, name)
        if not record:
            continue
        reuse = {"native": record["ids"].get("native") == ids["native"], "text": record["ids"].get("text") == ids["text"],
                 "movies": record["ids"].get("movies") == ids["movies"]}
        if not reuse["native"] and not (mode == "update" and record["ids"].get("inputs") == ids["inputs"]):
            continue
        library = DATA / "installs" / name / "library"
        outputs = record["outputs"]
        problems = G.verify_outputs(library, outputs.get("firmware", {}))
        if reuse["native"]:
            problems += G.verify_outputs(library, outputs.get("native", {}))
        title = library / "decrypted" / TITLE
        try:
            check_hashes(title / "app0", BASE_FILES)
            check_hashes(title / "patch0", PATCH_FILES)
            if reuse["native"]:
                check_hashes(title / "recomp/fs/app0", LAYERED_FILES)
        except SetupError as error:
            problems.append(str(error).splitlines()[0])
        for group in ("text", "movies"):
            reuse[group] = reuse[group] and not G.verify_outputs(library, outputs.get(group, {}))
        if problems:
            report(f"Build {name[:8]} cannot be reused ({problems[0]}); making this build the long way.")
            continue
        return name, reuse
    return None, None


def skip_for_seed(level, reuse):
    """Which files of the earlier build's library are NOT copied into a new one. level "data" copies only the prepared game
    (firmware, the decrypted base and update) and the English archives that can be kept; level "native" copies what runs."""
    title = "decrypted/PCSG00351/"
    lang = title + "recomp/fs/lang/en/"
    data_prefixes = ("firmware/", "licenses/", title + "app0/", title + "patch0/")

    def skip(relative):
        if level == "data":
            if relative.endswith("/"):
                return not any(p.startswith(relative) or relative.startswith(p)
                               for p in (*data_prefixes, title + "license.rif", lang))
            if relative.startswith(lang):
                name = relative[len(lang):]
                return not (name == "language.txt" or (name == PATCH and reuse["text"]) or (name == MOVIE and reuse["movies"]))
            return not (relative.startswith(data_prefixes) or relative == title + "license.rif")
        recomp = title + "recomp/"
        if not relative.startswith(recomp):
            return False
        sub = relative[len(recomp):]
        if sub.startswith(("obj_win/", "obj/", "captures/", "nvidia-cache/", "shader_cache/")):
            return True
        if "/" not in sub.rstrip("/") and sub.endswith((".c", ".h", ".o", ".a", ".log")):
            return True
        if sub == f"fs/lang/en/{PATCH}":
            return not reuse["text"]
        if sub == f"fs/lang/en/{MOVIE}":
            return not reuse["movies"]
        return False
    return skip


def seed_generation(b, library, install, report):
    level = "native" if b.seeded["reuse"]["native"] else "data"
    source = DATA / "installs" / b.donor / "library"
    need = G.tree_bytes(source)
    if free_bytes(DATA) < need + UPDATE_HEADROOM // 2:
        raise SetupError(f"Not enough free space to prepare the new build: it needs about {need / 1e9:.1f} GB and "
                         f"{free_bytes(DATA) / 1e9:.1f} GB is free. The installed game is untouched. Free up space and try again.")
    report(f"Copying the prepared game from build {b.donor[:8]} ({need / 1e9:.1f} GB) instead of rebuilding it")
    started = time.time()
    G.copy_tree_independent(source, library, skip=skip_for_seed(level, b.seeded["reuse"]))
    stages = list(NATIVE_STAGES if level == "native" else DATA_STAGES)
    for group, stage_name in (("text", "english-text"), ("movies", "english-movies")):
        if b.seeded["reuse"][group]:
            stages.append(stage_name)
    report(f"Copied in {time.time() - started:.0f} s; reusing {', '.join(stages)}")
    atomic_text(install / "progress.json", json.dumps({"inputs": b.ids["full"], "stages": stages, "seeded": {
        "from": b.donor, "level": level, "reuse": b.seeded["reuse"]}}, indent=2) + "\n")


def run_build(b):
    """The stages that turn the player's game into a generation (or reuse an earlier one's), then the activation. Returns the
    generation id."""
    report, attempt = b.report, b.attempt
    generation = b.generation
    install = DATA / "installs" / generation
    library = install / "library"
    title = library / "decrypted" / TITLE
    recomp = title / "recomp"
    logs = install / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    os.environ["NOVA_SETUP_LOGS"] = str(logs)
    attempt.set(generation=generation, target_release=b.sourceset.release)
    engine_root = b.sourceset.roots["engine"]
    env = stage_environment(library, engine_root)

    def command(name, argv, cwd=None, extra_env=None):
        log = logs / f"{name}.log"
        with log.open("w", encoding="utf-8") as output:
            result = subprocess.run([str(x) for x in argv], cwd=cwd or engine_root, env={**env, **(extra_env or {})},
                                    stdout=output, stderr=subprocess.STDOUT,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            tail = "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-16:])
            raise SetupError(f"{name} failed (exit {result.returncode}).\nLog: {log}\n\n{tail}")

    pipeline_script = engine_root / "pipeline/vitarecomp.py"

    def pipeline(name, *argv):
        command(name, [PYTHON, "-s", "-B", pipeline_script, *argv])

    state = install / "progress.json"
    journal = json_file(state)
    if journal and journal.get("inputs") != b.ids["full"]:
        raise SetupError(f"The install record is inconsistent. Use a fresh release folder.\n{install}")
    if not journal and b.donor:
        G.remove_tree(library)
        seed_generation(b, library, install, report)
        journal = json_file(state)
    completed = journal.setdefault("stages", [])
    journal["inputs"] = b.ids["full"]
    seeded = bool(journal.get("seeded"))

    def stage(name, label, work, outputs):
        attempt.stage(name)
        if name in completed and all(path.is_file() and path.stat().st_size for path in outputs):
            report(f"{label} - already complete")
            return
        report(label)
        if name in completed:
            del completed[completed.index(name):]
            atomic_text(state, json.dumps(journal, indent=2) + "\n")
        work()
        check_paths(outputs)
        completed.append(name)
        atomic_text(state, json.dumps(journal, indent=2) + "\n")

    if "firmware" not in completed and free_bytes(ROOT) < 14 * 1024**3:
        raise SetupError("Setup needs 14 GB of available space on the release drive to build the game.")
    fw = library / "firmware/3.74"
    stage("firmware", "Preparing Vita firmware modules", lambda: pipeline("firmware", "firmware", b.firmware),
          [fw / name for name in FIRMWARE_MODULES])

    scratch = DATA / "scratch"   # unpacked ZIP members live here, on the release drive, only while one import runs
    sources = b.sources

    def clear_import_scratch(announce=False):
        """Remove what an interrupted or finished import leaves behind: an unpacked ZIP member, and the half-written
        decrypt folders (.add*) that a stopped `vitarecomp add` never cleans up."""
        leftovers = [scratch] if scratch.exists() else []
        decrypted = library / "decrypted"
        leftovers.extend(decrypted.glob(".add*") if decrypted.is_dir() else [])
        if leftovers and announce:
            report("Removing what an interrupted import left behind")
        for path in leftovers:
            if path.is_dir() and not path.is_symlink():
                G.remove_tree(path)
            else:
                path.unlink(missing_ok=True)

    def install_input(name, package, destination, expected):
        if package is None:
            raise SetupError(f"The {name} game files are needed again to make this build. Choose your Game PKG or ZIP, Update PKG, "
                             "game license, and firmware in Setup, then click Build and install. The installed game is untouched.")
        clear_import_scratch(announce=True)
        license_args = ["--license", sources.license] if sources.license else []
        try:
            source = package.path
            if package.form == "zip":
                source = setup_sources.stage_member(package, scratch / "imports" / f"{name}.pkg", report)
            try:
                pipeline(name, "add", source, "--no-build", *license_args)
            except SetupError as error:
                if package.form == "folder":
                    raise
                lines = (logs / f"{name}.log").read_text(encoding="utf-8", errors="replace").splitlines()
                cause = next((line for line in reversed(lines) if line.strip()), "")
                hint = ("The game license did not decrypt this package: it belongs to another copy of the game, or the "
                        "package is damaged." if "klicensee" in cause else
                        "The package may be damaged, or the game license may not match it.")
                raise SetupError(f"Importing the {name} package {package.label} failed.\n{hint}\n\nCause: {cause}\n\n"
                                 f"{error}") from error
            check_hashes(destination, expected, package)
        finally:
            clear_import_scratch()

    stage("base", "Importing and checking the base game",
          lambda: install_input("base", sources.base if sources else None, title / "app0", BASE_FILES),
          [title / "app0" / name for name in BASE_FILES])
    stage("update", "Importing and checking update 1.05",
          lambda: install_input("update", sources.update if sources else None, title / "patch0", PATCH_FILES),
          [title / "patch0" / name for name in PATCH_FILES])

    def import_game():
        pipeline("import", "import", TITLE)
        check_hashes(recomp / "fs/app0", LAYERED_FILES)

    stage("import", "Preparing the patched game", import_game,
          [title / "version", recomp / "fs/app0" / BASE] + [recomp / "fs/app0" / name for name in LAYERED_FILES])
    stage("analyze", "Analyzing the game and firmware modules", lambda: pipeline("analyze", "analyze", TITLE),
          [title / "analysis/eboot.data.json"])

    def recompile():
        pipeline("recompile", "recompile", TITLE)
        command("labels", [PYTHON, "-I", "-B", engine_root / "dev/psnova/check_labels.py", recomp, "game"])

    image_files = [recomp / "game.img"] + [recomp / (Path(name).name.split(".")[0] + ".img") for name in FIRMWARE_MODULES]
    recompile_outputs = image_files + [recomp / ".recompile_inputs"] + ([] if seeded else [recomp / "game_part99.c"])
    stage("recompile", "Recompiling Vita code and checking generated labels", recompile, recompile_outputs)
    stage("build", "Building the Windows game executable", lambda: pipeline("build", "build", TITLE),
          [recomp / "game_host.exe", recomp / "SDL3.dll", recomp / ".built_version"])
    game_data = recomp / "fs/app0"
    english = recomp / "fs/lang/en"
    english.mkdir(parents=True, exist_ok=True)
    text_root, movies_root = b.sourceset.roots["text"], b.sourceset.roots["movies"]
    stage("english-text", "Building English menus and dialogue",
          lambda: command("english-text", [PYTHON, "-I", "-B", "-u", text_root / "build_text.py", game_data / BASE,
                                           game_data / PATCH, english / PATCH, "--font", b.font], cwd=ENGINE), [english / PATCH])
    stage("english-movies", "Building the English movie subtitles",
          lambda: command("english-movies", [PYTHON, "-s", "-B", "-u", movies_root / "build_movies.py", game_data / MOVIE,
                                             english / MOVIE, "--font", b.font, "--ffmpeg", FFMPEG,
                                             "--work", install / "movie-work"], cwd=ENGINE,
                          extra_env={"PYTHONPATH": str(engine_root / "pipeline" / "cri")}), [english / MOVIE])
    shutil.rmtree(install / "movie-work", ignore_errors=True)   # scratch frames from the subtitle build
    attempt.stage("finishing")
    report("Installing the English language and game launcher")
    atomic_text(english / "language.txt", "English\n")
    atomic_text(english.parent / "default.txt", "en\n")
    data = json.loads((title / "analysis/eboot.data.json").read_text(encoding="utf-8"))
    atomic_text(recomp / "entry.txt", f"{data['functions']['module_start'] & ~1:x}\n")
    (PLAYER / "savedata0").mkdir(parents=True, exist_ok=True)
    (PLAYER / "captures").mkdir(exist_ok=True)
    settings = PLAYER / "settings.ini"
    if not settings.exists():
        try:
            with settings.open("x", encoding="utf-8", newline="\n") as file:
                file.write("# Phantasy Star Nova Recomp\ninput_mode = auto\nrender_scale = 4\n"
                           "frame_rate = 60\nsharpen = 0.507067\nfullscreen = 0\n")
        except FileExistsError:
            pass
    write_provenance(b, library)
    activate_generation(b, generation, report)
    return generation


def write_provenance(b, library):
    groups = library_outputs(library)
    record = {"schema": G.PROVENANCE_SCHEMA, "generation": b.generation, "release": b.sourceset.release,
              "version": R.release_info(ROOT)["version"], "built": R.now_iso(), "ids": b.ids,
              "sources": {kind: {"content": b.sourceset.hashes[kind], "origin": b.sourceset.origins[kind],
                                 "release": b.sourceset.releases[kind]} for kind in U.KINDS},
              "fonts": {"font": b.font_sha, "fallback": b.fallback_sha}, "tools": {"ffmpeg": b.ffmpeg_sha},
              "outputs": {group: G.hash_outputs(library, names) for group, names in groups.items()},
              "library_bytes": G.tree_bytes(library)}
    atomic_text(library.parent / G.PROVENANCE, json.dumps(record, indent=2, sort_keys=True) + "\n")


def activate_generation(b, generation, report):
    """Replace GAME_EXE if needed, then make the generation the one the game launches. Needs the game closed: the new build is
    complete either way, and a later run only repeats this step."""
    if not GAME_EXE.is_file() or digest(GAME_EXE) != digest(BRIDGE):
        tmp = GAME_EXE.with_suffix(".exe.tmp")
        shutil.copyfile(BRIDGE, tmp)
        try:
            tmp.replace(GAME_EXE)
        except PermissionError as error:
            tmp.unlink(missing_ok=True)
            raise SetupError(f"Close {GAME_EXE.name} and run setup again to finish the update.") from error
    try:
        with (nullcontext() if b.holds_game_lock else G.game_lock(PLAYER)):
            old = G.activate(DATA, generation, report)
    except G.GameRunning as error:
        raise SetupError(f"The new build is ready, but {error} Run setup again to switch to it.") from error
    except RuntimeError as error:
        raise SetupError(str(error)) from error
    U.accept_release(DATA, b.sourceset.release)
    keep = set()
    for name in filter(None, (G.read_generation(DATA / "current.txt"), G.read_generation(DATA / "previous.txt"))):
        record = G.read_provenance(DATA, name)
        for kind, item in ((record or {}).get("sources") or {}).items():
            if str(item.get("origin", "")).startswith("update:"):
                keep.add((kind, str(item["content"])[:16]))
    U.collect_components(DATA, keep)
    report(f"Setup complete. Start {GAME_EXE.name} from the release folder.")
    return old


# ---- normal setup: the player's own inputs

def active_context():
    """(the active build's id, its provenance or None, the sources it was made from)."""
    current = G.read_generation(DATA / "current.txt")
    record = G.read_provenance(DATA, current) if current else None
    return current, record, U.sources_from_provenance(ROOT, DATA, record)


def check_font(font):
    """The font to draw the English with. Yours: the builders take any font file, its own metrics deciding the spacing."""
    if not font.is_file():
        raise SetupError(f"The English text font was not found:\n{font}\n\nChoose a font file in the Font field of "
                         f"Setup, or copy one to:\n{DEFAULT_FONT}\nThe installed game is untouched.")
    from PIL import ImageFont
    try:
        family, style = ImageFont.truetype(str(font), 18).getname()
    except OSError as error:
        raise SetupError(f"The selected font cannot be opened: {font}") from error
    return family, style


def resolved_text(path) -> str:
    try:
        return str(Path(path).resolve())
    except OSError:
        return str(path)


def prepare_install(args, report, attempt):
    if not args.game:
        raise SetupError("Select the Japanese Phantasy Star Nova game: its base-game PKG, or one ZIP that holds the "
                         "base game and the update.")
    remember_inputs(args)
    sources = setup_sources.resolve(args.game, args.update, getattr(args, "license", None))
    attempt.private(*[p.path.name for p in (sources.base, sources.update)], *[p.member for p in (sources.base, sources.update)],
                    paths=[str(p.path) for p in (sources.base, sources.update)])
    for note in sources.notes:
        report(note)
    for package in (sources.base, sources.update):
        report(f"{package.role.capitalize()}: {package.label} ({'ZIP member' if package.form == 'zip' else package.form}, "
               f"version {package.version})")
    if not args.firmware:
        raise SetupError("Select Sony's Vita system software 3.74 file (PSVUPDAT.PUP).")
    firmware = args.firmware.resolve()
    font = args.font.resolve() if args.font else DEFAULT_FONT
    if not font.is_file():
        which = f"The selected font file was not found:\n{font}" if args.font else (
            "This release does not include a font, and none is named.")
        raise SetupError(f"{which}\n\nSetup draws the English text, UI art and movie subtitles with a font you supply: "
                         f"choose any .ttf or .otf in the Font field, or copy one to:\n{DEFAULT_FONT}")
    required = [PYTHON, ENGINE / "pipeline/vitarecomp.py", ENGINE / "version.txt", firmware, font, FALLBACK_FONT]
    required.extend((BRIDGE, FFMPEG, LOCALIZATION / "build_text.py", LOCALIZATION / "build_movies.py"))
    check_paths(required)
    report("Checking the game, update, firmware, and font...")
    if digest(firmware) != PUP_SHA256:
        raise SetupError(f"{firmware} is not the supported Sony Vita 3.74 update file. Download PSVUPDAT.PUP from Sony.\n"
                         + SONY_FIRMWARE)
    family, style = check_font(font)
    font_sha = digest(font)
    report(f"Drawing the English with {font.name} ({family} {style}).")

    attempt.stage("fingerprinting the inputs")
    inputs = hashlib.sha256()
    packages = (sources.base, sources.update)
    for name, path in original_files(packages, sources.license is not None):
        inputs.update(f"{name}\0{digest(path)}\n".encode())
    for package in packages:   # a PKG, or a PKG inside a ZIP: the hash of the package's own bytes
        if package.form != "folder":
            inputs.update(f"{package.role}-package\0{setup_sources.fingerprint(package, report)}\n".encode())
    if sources.license_sha256:
        inputs.update(f"license\0{sources.license_sha256}\n".encode())
    # (a newer full release folder beats a staged update; otherwise the active build's own sources are used again)
    _current, _record, sourceset = active_context()
    ids, ffmpeg_sha = make_ids(sourceset, font_sha, digest(FALLBACK_FONT), inputs.hexdigest())
    current = G.read_generation(DATA / "current.txt")
    candidates = ([current] if current else []) + [g for g in G.generations(DATA) if g != current]
    donor, reuse = (None, None)
    if not (DATA / "installs" / ids["full"][:24] / "progress.json").is_file():
        donor, reuse = verified_donor([g for g in candidates if g != ids["full"][:24]], ids, "setup", report)
    build = Build("setup", sourceset, ids, font, font_sha, digest(FALLBACK_FONT), ffmpeg_sha, report, attempt, sources=sources,
                  firmware=firmware, donor=donor, seeded={"reuse": reuse} if donor else {})
    return run_build(build)


def install(args, report):
    with setup_lock():
        selected = [getattr(args, key) for key in ("game", "update", "license", "firmware", "font") if getattr(args, key, None)]
        attempt = R.Attempt(DATA, "setup", private_names=[p.name for p in selected], private_paths=[*map(str, selected), *map(resolved_text, selected)])

        def say(message):
            attempt.line(message)
            report(message)

        try:
            prepare_install(args, say, attempt)
        except BaseException as error:
            attempt.finish("failed", 1, str(error) or type(error).__name__)
            raise
        attempt.finish("success", 0)


# ---- updates

def update_status():
    """What Setup shows about updates and builds, without any network use."""
    config = U.load_config(ROOT)
    current, record, sourceset = active_context()
    state = U.read_state(DATA)
    previous = G.read_generation(DATA / "previous.txt")
    return {"enabled": config.enabled, "problem": config.problem, "state": state, "current": current, "previous": previous,
            "can_roll_back": bool(previous and previous != current and previous in G.generations(DATA)),
            "release": sourceset.release, "highest": U.highest_release(ROOT, DATA), "has_record": bool(record),
            "game_running": G.game_is_running(PLAYER) if PLAYER.exists() else False}


def check_updates(force=False):
    _current, _record, sourceset = active_context()
    return U.check_for_updates(ROOT, dict(sourceset.hashes), force=force)


def read_pending(config):
    pending = DATA / "Updates" / "pending"
    try:
        manifest_bytes = (pending / "manifest.json").read_bytes()
        signature = bytes.fromhex((pending / "manifest.sig").read_text(encoding="ascii").strip())
        return U.verify_manifest(manifest_bytes, signature, config)
    except (OSError, ValueError, U.UpdateError):
        return None


def prepare_update(args, report, attempt):
    config = U.load_config(ROOT)
    if not config.enabled:
        raise SetupError(f"Updates are not available: {config.problem}.")
    current, record, active = active_context()
    if not current or not G.launchable(DATA, current)[0]:
        raise SetupError("There is no installed game to update. Run Build and install first.")
    attempt.stage("checking the update")
    manifest = read_pending(config)
    try:
        if manifest is None:
            _bytes, _sig, manifest = U.fetch_manifest(config)
    except U.UpdateError as error:
        raise SetupError(str(error)) from error
    highest = U.highest_release(ROOT, DATA)
    if manifest["release"] <= highest:
        raise SetupError(f"There is no newer update: this install already has release {highest} (the feed offers {manifest['release']}).")
    if manifest["min_updater"] > U.UPDATER_VERSION:
        raise SetupError("This update needs a newer Setup than this release has. Download the new release.")
    plan = U.plan_update(manifest, dict(active.hashes))
    attempt.set(target_release=manifest["release"])
    report(f"Update to {manifest['version']} (release {manifest['release']}): {plan['rebuild']} rebuild, "
           f"{plan['download_bytes'] / 1e6:.1f} MB to download")
    if not plan["components"]:
        U.accept_release(DATA, manifest["release"])
        report("This release has the same files as the installed build, so nothing was rebuilt.")
        return None
    if not record:
        raise SetupError("The installed build was made before build records were kept, so an update cannot reuse it. Run Build and "
                         "install once with your game files (Game PKG or ZIP, Update PKG, license and firmware); after that, "
                         "updates are quick. The installed game still works.")
    # what the new build would be made of, known from the signed manifest before anything is downloaded
    provisional = U.SourceSet(roots=dict(active.roots), hashes={**active.hashes, **{k: manifest["components"][k]["content_sha256"] for k in plan["components"]}})
    font = (args.font.resolve() if getattr(args, "font", None) else None) or Path(
        json_file(DATA / "setup-inputs.json").get("font") or DEFAULT_FONT)
    font_sha = digest(font) if font.is_file() else record["fonts"]["font"]
    fallback_sha = digest(FALLBACK_FONT) if FALLBACK_FONT.is_file() else record["fonts"]["fallback"]
    wanted, _ffmpeg = make_ids(provisional, font_sha, fallback_sha, record["ids"]["inputs"])
    if wanted["text"] != record["ids"]["text"] or wanted["movies"] != record["ids"]["movies"]:
        check_font(font)               # names the font to choose again; the installed game is untouched
        check_paths([FALLBACK_FONT, FFMPEG])
    need = plan["download_bytes"] + record.get("library_bytes", 7_000_000_000) + UPDATE_HEADROOM
    if free_bytes(DATA) < need:
        raise SetupError(f"Not enough free space for this update: it needs about {need / 1e9:.1f} GB on the release drive and "
                         f"{free_bytes(DATA) / 1e9:.1f} GB is free. Nothing was downloaded and the installed game is untouched.")

    try:
        lock = G.game_lock(PLAYER)
        lock.__enter__()
    except G.GameRunning as error:
        raise SetupError(str(error)) from error
    try:
        staged = {}
        for kind in plan["components"]:
            item = manifest["components"][kind]
            attempt.stage(f"downloading {kind}")
            payload = DATA / "Updates" / "downloads" / str(manifest["release"]) / item["payload"]
            folder = U.component_dir(DATA, kind, item["content_sha256"])
            meta = G.read_json(folder / "component.json") or {}
            if meta.get("content_sha256") != item["content_sha256"] or not folder.is_dir():
                try:
                    if not payload.is_file() or payload.stat().st_size != item["size"]:
                        report(f"Downloading the {kind} update ({item['size'] / 1e6:.1f} MB)")
                        U.http_download(config.feed_url + config.channel + "/payloads/" + item["payload"], payload, item["size"],
                                        item["sha256"])
                    U.verify_payload(payload, item["size"], item["sha256"])
                    report(f"Checked the {kind} update against the signed manifest; unpacking it")
                    U.extract_component(payload, kind, folder, item["content_sha256"], manifest["release"], ENGINE)
                except U.UpdateError as error:
                    payload.unlink(missing_ok=True)
                    raise SetupError(str(error)) from error
            staged[kind] = (folder, item["content_sha256"])
        sourceset = U.overlay_sources(active, staged, manifest["release"])
        ids, ffmpeg_sha = make_ids(sourceset, font_sha, fallback_sha, record["ids"]["inputs"])
        generation = ids["full"][:24]
        attempt.stage("preparing the new build")
        donor, reuse = (None, None)
        if not (DATA / "installs" / generation / "progress.json").is_file():
            donor, reuse = verified_donor([current], ids, "update", report)
            if not donor:
                raise SetupError("The installed build could not be reused: its files no longer verify. Run Build and install with "
                                 "your game files (Game PKG or ZIP, Update PKG, license and firmware) to rebuild it. The installed "
                                 "game is untouched.")
        build = Build("update", sourceset, ids, font, font_sha, fallback_sha, ffmpeg_sha, report, attempt, donor=donor,
                      seeded={"reuse": reuse} if donor else {}, holds_game_lock=True)
        return run_build(build)
    finally:
        lock.__exit__(None, None, None)


def install_update(args, report):
    with setup_lock():
        attempt = R.Attempt(DATA, "update")

        def say(message):
            attempt.line(message)
            report(message)

        try:
            prepare_update(args, say, attempt)
        except BaseException as error:
            attempt.finish("failed", 1, str(error) or type(error).__name__)
            raise
        attempt.finish("success", 0)


def roll_back(report):
    with setup_lock():
        attempt = R.Attempt(DATA, "rollback")
        try:
            attempt.stage("rolling back")
            with G.game_lock(PLAYER):
                now, _was = G.roll_back(DATA, lambda m: (attempt.line(m), report(m)))
            attempt.set(generation=now)
        except G.GameRunning as error:
            attempt.finish("failed", 1, str(error))
            raise SetupError(str(error)) from error
        except RuntimeError as error:
            attempt.finish("failed", 1, str(error))
            raise SetupError(str(error)) from error
        except BaseException as error:
            attempt.finish("failed", 1, str(error) or type(error).__name__)
            raise
        attempt.finish("success", 0)


def export_report():
    return R.export_report(ROOT)


class Backend:
    """What the setup window calls."""
    root, data, game_exe = ROOT, DATA, GAME_EXE
    sony_firmware = SONY_FIRMWARE
    setup_error = SetupError
    install = staticmethod(install)
    install_update = staticmethod(install_update)
    roll_back = staticmethod(roll_back)
    check_updates = staticmethod(check_updates)
    update_status = staticmethod(update_status)
    export_report = staticmethod(export_report)


def main():
    parser = argparse.ArgumentParser(description="Phantasy Star Nova Recomp setup")
    parser.add_argument("--game", type=Path, help="the base-game PKG, a ZIP that holds the base game and the update, "
                        "or an extracted game folder")
    parser.add_argument("--update", type=Path, help="the update PKG, or an extracted update folder. Not needed when --game "
                        "is a ZIP with both packages or a folder that has patch\\PCSG00351")
    parser.add_argument("--license", type=Path, help="the game's work.bin or .rif, when the PKG has no license inside it")
    parser.add_argument("--firmware", type=Path, help="Sony's Vita system software 3.74 file (PSVUPDAT.PUP)")
    parser.add_argument("--font", type=Path, help="a .ttf or .otf to draw the English with, when none is in localization\\fonts")
    parser.add_argument("--export-report", action="store_true", help="write a support report ZIP under NovaData\\Reports")
    parser.add_argument("--check-updates", action="store_true", help="ask the update feed (at most once a day unless --force)")
    parser.add_argument("--force", action="store_true", help="with --check-updates: ask now")
    parser.add_argument("--install-update", action="store_true", help="install the update --check-updates found")
    parser.add_argument("--rollback", action="store_true", help="go back to the earlier build")
    parser.add_argument("--update-status", action="store_true", help="print the update and build status")
    parser.add_argument("--quiet", action="store_true", help="print nothing (for the launcher's background check)")
    args = parser.parse_args()
    if len(sys.argv) == 1:
        from setup_ui import show
        show(Backend)
        return 0
    if sys.stdout is None:    # started without a console (the game launcher's "Create a support report" button)
        sys.stdout = sys.stderr = open(os.devnull, "w")
        if args.export_report:
            from setup_ui import report_dialog
            try:
                report_dialog(export_report())
            except (OSError, RuntimeError) as error:
                report_dialog(None, str(error))
            return 0
    say = (lambda message: None) if args.quiet else (lambda message: print(message, flush=True))
    try:
        if args.export_report:
            say(f"Support report written: {export_report()}")
            say("It holds no saves, game files, licenses or file paths. Share it yourself if you want help.")
        elif args.check_updates:
            state = check_updates(force=args.force)
            plan = state.get("available")
            say(f"Updates: {state.get('last_result', 'unknown')}" + (f" - {state['last_error']}" if state.get("last_error") else ""))
            if plan:
                say(f"  {plan['version']} (release {plan['release']}), {plan['download_bytes'] / 1e6:.1f} MB, rebuild: {plan['rebuild']}")
        elif args.update_status:
            say(json.dumps(update_status(), indent=2, default=str))
        elif args.install_update:
            install_update(args, say)
        elif args.rollback:
            roll_back(say)
        else:
            install(args, say)
    except (SetupError, OSError, RuntimeError) as error:
        print(f"Setup could not finish.\n{error}", file=sys.stderr)
        if not args.export_report:
            print("\nTo create a support report you can share, run: Setup Phantasy Star Nova.exe --export-report", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
