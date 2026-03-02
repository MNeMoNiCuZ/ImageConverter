import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import TkinterDnD, DND_FILES
import subprocess
import sys
import os
import re

# Prevent console windows from flashing on Windows when running from a compiled exe.
# Third-party libraries (e.g. moviepy/ffmpeg) spawn subprocesses internally, and on
# Windows each one opens a visible console window by default. This monkey-patch injects
# CREATE_NO_WINDOW flags into every subprocess.Popen call.
if sys.platform == "win32":
    _original_popen_init = subprocess.Popen.__init__

    def _patched_popen_init(self, *args, **kwargs):
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        if "startupinfo" not in kwargs:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            kwargs["startupinfo"] = si
        _original_popen_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = _patched_popen_init

from moviepy.video.io.VideoFileClip import VideoFileClip

def clean_filepath(filepath):
    print(f"Original dropped filepath: {filepath}")
    filepath = filepath.strip().strip("{}")
    filepath = os.path.normpath(filepath)
    print(f"Cleaned and normalized filepath: {filepath}")
    return filepath

def convert_to_mp4(filepaths, overwrite):
    print(f"Starting conversion to MP4, overwrite: {overwrite.get()}")
    for filepath in filepaths:
        try:
            print(f"Processing file: {filepath}")
            filepath = clean_filepath(filepath)

            if not os.path.exists(filepath):
                print(f"File does not exist: {filepath}")
                continue

            file_name, file_ext = os.path.splitext(filepath)
            file_ext = file_ext.lower()[1:]

            if file_ext not in ["gif", "webp"]:
                print(f"Skipping unsupported file format: {file_ext}")
                continue

            output_file = f"{file_name}.mp4"

            if not overwrite.get() and os.path.exists(output_file):
                print(f"Skipping {output_file} (file exists and overwrite is disabled)")
                continue

            print(f"Converting {filepath} to MP4...")
            clip = VideoFileClip(filepath)
            clip.write_videofile(output_file, codec="libx264", audio=False)
            print(f"Successfully converted {filepath} to {output_file}")
        except Exception as e:
            print(f"Failed to convert {filepath}: {e}")

def on_drop(event):
    print(f"Raw drop event data: {event.data}")
    # Split paths while preserving files wrapped in braces
    files = event.data.split(" ") if "{" not in event.data else re.findall(r"{.*?}", event.data)
    files = [clean_filepath(f) for f in files if f]  # Clean all file paths

    print(f"Files after cleaning: {files}")

    if not files:
        print("No valid files detected in the drop.")
        return

    convert_to_mp4(files, overwrite_var)

root = TkinterDnD.Tk()
root.title("GIF/WEBP to MP4 Converter")
root.geometry("400x250")

label = tk.Label(root, text="Drag and drop GIF/WEBP files here\n\nFiles will be converted to MP4 and saved in the original folder", font=("Helvetica", 14))
label.pack(pady=20)

overwrite_var = tk.BooleanVar(value=True)
overwrite_checkbox = tk.Checkbutton(root, text="Overwrite existing files", variable=overwrite_var)
overwrite_checkbox.pack(pady=10)

root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', on_drop)

root.mainloop()
