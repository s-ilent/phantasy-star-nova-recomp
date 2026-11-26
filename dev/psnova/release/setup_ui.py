"""Player-facing Windows setup window.

Support reports, the update panel and Roll back were added alongside the original controls: Export support report and Check for
updates sit beside the setup buttons, a failed setup offers the export, and the Updates panel shows what a newer release changes
before anything is downloaded or installed.
"""

from argparse import Namespace
import json
import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback
import webbrowser

REBUILD_TEXT = {
    "none": "no rebuild",
    "full": "a full rebuild of the game (about 30 minutes)",
    "english-text": "a rebuild of the English text only (a few minutes)",
    "english-movies": "a rebuild of the English movie subtitles only (about ten minutes)",
    "english-text+english-movies": "a rebuild of the English text and movie subtitles (about fifteen minutes)",
}


def megabytes(count):
    return f"{count / 1e6:.1f} MB" if count < 1e9 else f"{count / 1e9:.2f} GB"


def report_dialog(path, error=None):
    """The message box the game launcher's 'Create a support report' button ends in (no console, no setup window)."""
    window = tk.Tk()
    window.withdraw()
    if path:
        messagebox.showinfo("Support report saved", f"Your support report was saved here:\n\n{path}\n\nIt holds no saves, game files, "
                            "licenses or file paths. Nothing was sent: share the file yourself if you want help.", parent=window)
    else:
        messagebox.showerror("Support report", f"The report could not be created.\n\n{error}", parent=window)
    window.destroy()


def update_summary(status):
    """(headline, details) for the Updates panel from setup.update_status()."""
    state = status["state"]
    if not status["enabled"]:
        return "Update checks are off in this release.", ""
    plan = state.get("available")
    if plan:
        what = REBUILD_TEXT.get(plan["rebuild"], plan["rebuild"])
        head = (f"Update available: {plan['version']} (release {plan['release']}). Download {megabytes(plan['download_bytes'])}, "
                f"needs {what}.")
        return head, plan.get("notes", "")
    if state.get("last_error"):
        return state["last_error"], ""
    if state.get("last_result"):
        return f"You have the newest release ({status['highest']}). Last check: {state['last_result']}.", ""
    return "Updates have not been checked yet.", ""


def show(backend):
    root, data, game_exe = backend.root, backend.data, backend.game_exe
    window = tk.Tk()
    window.title("Phantasy Star Nova Recomp Setup")
    window.minsize(700, 700)
    panel = ttk.Frame(window, padding=18)
    panel.grid(sticky="nsew")
    window.columnconfigure(0, weight=1)
    window.rowconfigure(0, weight=1)
    panel.columnconfigure(1, weight=1)
    panel.rowconfigure(9, weight=1)

    ttk.Label(panel, text="Phantasy Star Nova Recomp", font=("Segoe UI", 17, "bold")).grid(
        row=0, columnspan=3, sticky="w")
    ttk.Label(panel, justify="left", text="Japanese PS Vita game (PCSG00351), base 1.00 and update 1.05. Choose the "
              "base-game PKG and the update PKG,\nor one ZIP that contains both. English installs automatically.").grid(
        row=1, columnspan=3, sticky="w", pady=(4, 14))

    try:
        previous = json.loads((data / "setup-inputs.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    fields = {}
    controls = []

    def path_row(row, key, label, filetypes=None):
        remembered = previous.get(key, "")
        value = tk.StringVar(value=remembered if remembered and Path(remembered).exists() else "")
        fields[key] = value
        ttk.Label(panel, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 12))
        entry = ttk.Entry(panel, textvariable=value)
        entry.grid(row=row, column=1, sticky="ew")

        def browse():
            if filetypes:
                choice = filedialog.askopenfilename(parent=window, title=label, filetypes=filetypes)
            else:
                choice = filedialog.askdirectory(parent=window, title=label, mustexist=True)
            if choice:
                value.set(choice)

        button = ttk.Button(panel, text="Browse…", command=browse)
        button.grid(row=row, column=2, padx=(8, 0))
        controls.extend((entry, button))

    path_row(2, "game", "Game PKG or ZIP", [("Game package or ZIP", "*.pkg *.zip"), ("All files", "*.*")])
    path_row(3, "update", "Update PKG (optional)", [("Update package", "*.pkg"), ("All files", "*.*")])
    path_row(4, "license", "Game license (if required)", [("Game license", "*.rif work.bin"), ("All files", "*.*")])
    path_row(5, "firmware", "Vita firmware 3.74", [("Vita update", "*.pup"), ("All files", "*.*")])
    path_row(6, "font", "Font file (.ttf or .otf)", [("Fonts", "*.ttf *.otf"), ("All files", "*.*")])

    buttons = ttk.Frame(panel)
    buttons.grid(row=7, columnspan=3, sticky="ew", pady=(10, 6))
    ttk.Button(buttons, text="Get firmware from Sony", command=lambda: webbrowser.open(backend.sony_firmware)).pack(side="left")
    ttk.Button(buttons, text="Open setup logs", command=lambda: os.startfile(os.environ.get("NOVA_SETUP_LOGS", str(root)))).pack(
        side="left", padx=8)
    export_button = ttk.Button(buttons, text="Export support report")
    export_button.pack(side="left")

    updates = ttk.LabelFrame(panel, text="Updates", padding=8)
    updates.grid(row=8, columnspan=3, sticky="ew", pady=(4, 8))
    updates.columnconfigure(0, weight=1)
    headline = tk.StringVar(value="Checking for updates…")
    # (two lines are always reserved, so the buttons below do not move when a long message wraps)
    tk.Label(updates, textvariable=headline, wraplength=640, justify="left", anchor="nw", height=2).grid(row=0, column=0, columnspan=4, sticky="w")
    notes = tk.Text(updates, height=3, width=70, wrap="word", state="disabled", font=("Segoe UI", 9))
    notes.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(4, 6))
    check_button = ttk.Button(updates, text="Check for updates")
    check_button.grid(row=2, column=1, padx=(0, 6))
    install_button = ttk.Button(updates, text="Install update", state="disabled")
    install_button.grid(row=2, column=2, padx=(0, 6))
    rollback_button = ttk.Button(updates, text="Roll back", state="disabled")
    rollback_button.grid(row=2, column=3)

    activity = ttk.Frame(panel)
    activity.grid(row=9, columnspan=3, sticky="nsew")
    activity.columnconfigure(0, weight=1)
    activity.rowconfigure(0, weight=1)
    log = tk.Text(activity, height=9, width=72, wrap="word", state="disabled", font=("Segoe UI", 10))
    log.grid(row=0, column=0, sticky="nsew")
    scroll = ttk.Scrollbar(activity, command=log.yview)
    scroll.grid(row=0, column=1, sticky="ns")
    log.configure(yscrollcommand=scroll.set)

    status = ttk.Frame(panel)
    status.grid(row=10, columnspan=3, sticky="ew", pady=(12, 0))
    progress = ttk.Progressbar(status, mode="indeterminate")
    progress.pack(side="left", fill="x", expand=True)

    def start_game():
        try:
            subprocess.Popen([str(game_exe)], cwd=root, creationflags=subprocess.CREATE_BREAKAWAY_FROM_JOB)
        except OSError as error:
            messagebox.showerror("Could not start the game", str(error), parent=window)

    play = ttk.Button(status, text="Play", command=start_game)
    play.pack(side="right", padx=(8, 0))

    def append(text):
        log.configure(state="normal")
        log.insert("end", text + "\n")
        log.see("end")
        log.configure(state="disabled")

    messages = Queue()
    worker = None
    busy_controls = [*controls, export_button, check_button, install_button, rollback_button]

    def set_notes(text):
        notes.configure(state="normal")
        notes.delete("1.0", "end")
        notes.insert("1.0", text)
        notes.configure(state="disabled")

    def refresh_updates():
        """Show the stored update state (no network). Buttons follow what is possible right now."""
        try:
            info = backend.update_status()
        except Exception as error:   # (a damaged state file must not stop the window)
            headline.set(f"Update state could not be read: {error}")
            return
        text, detail = update_summary(info)
        headline.set(text)
        set_notes(detail)
        idle = worker is None
        check_button.configure(state="normal" if idle and info["enabled"] else "disabled")
        install_button.configure(state="normal" if idle and info["enabled"] and info["state"].get("available") else "disabled")
        rollback_button.configure(state="normal" if idle and info["can_roll_back"] else "disabled")

    def run(label, function, then=None, check=False):
        """Run `function` on a worker thread with the controls locked. Errors go to the log and offer the support report."""
        nonlocal worker
        if worker is not None:
            return
        os.environ.pop("NOVA_SETUP_LOGS", None)
        for control in (*busy_controls, build, play):
            control.configure(state="disabled")
        progress.start(20)
        append(label)

        def work():
            try:
                messages.put(("result", function()))
            except (backend.setup_error, OSError, RuntimeError) as error:
                messages.put(("error", str(error)))
            except Exception:
                messages.put(("error", traceback.format_exc()))
            finally:
                messages.put(("finished", then))

        worker = threading.Thread(target=work, daemon=True)
        worker.start()

    def paths():
        return {key: Path(value.get().strip().strip('"')) if value.get().strip() else None for key, value in fields.items()}

    def say(text):
        messages.put(("status", text))

    def begin():
        options = Namespace(**paths())
        run("Starting setup…", lambda: backend.install(options, say))

    def install_update():
        options = Namespace(font=paths()["font"])
        run("Installing the update…", lambda: backend.install_update(options, say))

    def roll_back():
        if messagebox.askyesno("Roll back", "Go back to the earlier build of the game? Your saves and settings are not changed.",
                               parent=window):
            run("Rolling back…", lambda: backend.roll_back(say))

    def check_now():
        run("Checking for updates…", lambda: backend.check_updates(force=True))

    def export_report():
        try:
            path = backend.export_report()
        except (OSError, RuntimeError) as error:
            messagebox.showerror("Support report", f"The report could not be created.\n\n{error}", parent=window)
            return
        append(f"Support report saved: {path}")
        messagebox.showinfo("Support report saved", f"Your support report was saved here:\n\n{path}\n\nIt holds no saves, game "
                            "files, licenses or file paths. Nothing was sent: share the file yourself if you want help.", parent=window)

    build = ttk.Button(status, text="Build and install", command=begin)
    build.pack(side="right", padx=(12, 0))
    export_button.configure(command=export_report)
    check_button.configure(command=check_now)
    install_button.configure(command=install_update)
    rollback_button.configure(command=roll_back)
    if not game_exe.is_file():
        play.configure(state="disabled")
    append("Select your game package (or ZIP) and firmware, then choose Build and install.")

    def failed(text):
        append("Setup could not finish.\n" + text)
        summary = "\n".join(text.strip().splitlines()[:4])[:600]
        if messagebox.askyesno("Setup could not finish", f"{summary}\n\nCreate a support report you can share? It holds no saves, "
                               "game files, licenses or file paths.", parent=window):
            export_report()

    def poll():
        nonlocal worker
        try:
            while True:
                kind, message = messages.get_nowait()
                if kind == "finished":
                    progress.stop()
                    worker = None
                    for control in (*controls, export_button, build):
                        control.configure(state="normal")
                    if game_exe.is_file():
                        play.configure(state="normal")
                    refresh_updates()
                elif kind == "refresh":
                    refresh_updates()
                elif kind == "error":
                    failed(message)
                elif kind == "result":
                    if isinstance(message, dict) and "last_result" in message:
                        append("Updates: " + message["last_result"] + (f" - {message['last_error']}" if message.get("last_error") else ""))
                else:
                    append(message)
        except Empty:
            pass
        window.after(100, poll)

    def close():
        if worker is None or messagebox.askyesno("Stop setup?", "Completed stages are saved. Stop the current stage?", parent=window):
            window.destroy()

    def background_check():
        """Once a day at most (the check itself is throttled): never blocks the window and never raises."""
        def work():
            try:
                backend.check_updates(force=False)
            except Exception:
                pass
            messages.put(("refresh", None))
        threading.Thread(target=work, daemon=True).start()

    window.protocol("WM_DELETE_WINDOW", close)
    window.after(100, poll)
    refresh_updates()
    background_check()
    window.mainloop()
