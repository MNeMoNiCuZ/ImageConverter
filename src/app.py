"""
Image Converter - Main Application
Queue-based GUI for converting images between formats.
Supports drag-and-drop, CLI arguments, and config persistence.
"""

import src.no_window  # noqa: F401 — must be imported before PIL

import tkinter as tk
from tkinter import ttk, font as tkfont
from tkinterdnd2 import TkinterDnD, DND_FILES
import datetime
import os
import sys
import threading

from PIL import Image
import pillow_avif  # noqa: F401

from src import config


class ToolTip:
    """Simple tooltip that shows on hover."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#ffffe0", relief="solid", borderwidth=1,
            padx=6, pady=4,
        )
        label.pack()
        self.tip_window = tw

    def _hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

# Supported input formats
_exts = Image.registered_extensions()
SUPPORTED_INPUT = sorted({ex[1:].upper() for ex, f in _exts.items() if f in Image.OPEN})

OUTPUT_FORMATS = ["PNG", "JPG", "WEBP", "GIF", "BMP", "TIFF", "AVIF"]


def clean_filepath(filepath):
    filepath = filepath.strip().strip("{}")
    return os.path.normpath(filepath)


def parse_drop_data(data):
    """Parse TkinterDnD drop data, handling brace-wrapped and space-separated paths."""
    results = []
    # TkinterDnD wraps paths containing spaces in {}, others are space-separated
    # e.g.: {C:/path with spaces/file.png} C:/simple.png {C:/another path/img.jpg}
    i = 0
    while i < len(data):
        if data[i] == '{':
            end = data.index('}', i)
            results.append(data[i+1:end])
            i = end + 1
        elif data[i] in (' ', '\t', '\n', '\r'):
            i += 1
        else:
            # Read until next space or end
            end = i
            while end < len(data) and data[end] not in (' ', '\t', '\n', '\r'):
                end += 1
            results.append(data[i:end])
            i = end
    return [clean_filepath(f) for f in results if f]


def convert_single(filepath, output_format, overwrite):
    """Convert one file. Returns (output_path, error_string_or_None)."""
    filepath = clean_filepath(filepath)
    if not os.path.exists(filepath):
        return filepath, "File not found"

    file_name, file_ext = os.path.splitext(filepath)
    file_ext = file_ext.lower()[1:]
    fmt = output_format.lower()

    if file_ext == "jpeg":
        file_ext = "jpg"
    if file_ext == fmt and not overwrite:
        return filepath, "Already in target format"

    output_file = os.path.join(
        os.path.dirname(filepath),
        f"{os.path.splitext(os.path.basename(filepath))[0]}.{fmt}",
    )

    if not overwrite and os.path.exists(output_file):
        return output_file, "File exists (overwrite disabled)"

    try:
        img = Image.open(filepath)
        if fmt == "jpg":
            img.convert("RGB").save(output_file, "JPEG", quality=95)
        elif fmt == "png":
            img.save(output_file, "PNG")
        elif fmt == "webp":
            img.save(output_file, "WEBP", quality=90)
        elif fmt == "gif":
            img = img.convert("RGBA")
            bg = Image.new("RGBA", img.size)
            bg.paste(img, (0, 0), img)
            bg.convert("P", palette=Image.ADAPTIVE).save(output_file, format="GIF", transparency=0)
        elif fmt == "avif":
            img.save(output_file, "AVIF", quality=90)
        else:
            img.save(output_file, fmt.upper())
        return output_file, None
    except PermissionError:
        return output_file, "Permission denied"
    except Exception as e:
        return output_file, str(e)


class ImageConverterApp:
    def __init__(self, initial_files=None):
        self.cfg = config.load()

        self.root = TkinterDnD.Tk()
        self.root.title("Image Converter")
        self.root.geometry("600x1040")

        # Try to set icon
        ico_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except tk.TclError:
                pass

        # Tk variables
        self.overwrite_var = tk.BooleanVar(value=self.cfg["overwrite"])
        self.auto_process_var = tk.BooleanVar(value=self.cfg["auto_process"])
        self.clear_on_drop_var = tk.BooleanVar(value=self.cfg["clear_on_drop"])
        self.save_log_var = tk.BooleanVar(value=self.cfg["save_log"])

        # Format checkbox vars — one BooleanVar per format
        saved_fmts = self.cfg.get("output_formats", ["JPG"])
        self.format_vars = {}
        for fmt in OUTPUT_FORMATS:
            self.format_vars[fmt] = tk.BooleanVar(value=(fmt in saved_fmts))

        self._build_ui()
        self._setup_traces()
        self._setup_dnd()

        # Add CLI files
        if initial_files:
            for f in initial_files:
                self._add_to_queue(f)

    def _build_ui(self):
        main = ttk.Frame(self.root, padding="10")
        main.pack(fill=tk.BOTH, expand=True)

        # --- File Queue (also the drop target) ---
        queue_frame = ttk.LabelFrame(main, text="File Queue — drag and drop files here", padding="5")
        queue_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        list_frame = ttk.Frame(queue_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.queue_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.queue_listbox.yview)
        self.queue_listbox.configure(yscrollcommand=scrollbar.set)
        self.queue_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(queue_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        remove_btn = ttk.Button(btn_frame, text="Remove Selected", command=self._remove_selected)
        remove_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(remove_btn, "Remove highlighted files from the queue")
        clear_btn = ttk.Button(btn_frame, text="Clear", command=self._clear_queue)
        clear_btn.pack(side=tk.LEFT)
        ToolTip(clear_btn, "Remove all files from the queue")

        # --- Output Formats (checkboxes) ---
        fmt_frame = ttk.LabelFrame(main, text="Output Formats", padding="5")
        fmt_frame.pack(fill=tk.X, pady=5)

        fmt_row = ttk.Frame(fmt_frame)
        fmt_row.pack(fill=tk.X)
        for fmt in OUTPUT_FORMATS:
            cb = ttk.Checkbutton(fmt_row, text=fmt, variable=self.format_vars[fmt])
            cb.pack(side=tk.LEFT, padx=(0, 10))
            ToolTip(cb, f"Include {fmt} in conversion output")

        # --- Options ---
        opts_frame = ttk.LabelFrame(main, text="Options", padding="5")
        opts_frame.pack(fill=tk.X, pady=5)

        overwrite_cb = ttk.Checkbutton(opts_frame, text="Overwrite existing files", variable=self.overwrite_var)
        overwrite_cb.pack(anchor=tk.W)
        ToolTip(overwrite_cb, "Replace output files that already exist.\nWhen off, existing files are skipped.")
        auto_cb = ttk.Checkbutton(opts_frame, text="Auto-process on drop", variable=self.auto_process_var)
        auto_cb.pack(anchor=tk.W)
        ToolTip(auto_cb, "Automatically start conversion when files are dropped")
        clear_cb = ttk.Checkbutton(opts_frame, text="Clear file queue on drop", variable=self.clear_on_drop_var)
        clear_cb.pack(anchor=tk.W)
        ToolTip(clear_cb, "Clear the existing queue before adding newly dropped files")
        log_cb = ttk.Checkbutton(opts_frame, text="Save log file", variable=self.save_log_var)
        log_cb.pack(anchor=tk.W)
        ToolTip(log_cb, "Write conversion results to imageconverter.log")

        # --- Convert Button (large bold text) ---
        bold_font = tkfont.Font(family="Helvetica", size=14, weight="bold")
        self.convert_btn = tk.Button(
            main, text="Convert All", command=self._on_convert,
            font=bold_font, relief="raised", bd=2,
        )
        self.convert_btn.pack(fill=tk.X, pady=(5, 5), ipady=4)
        ToolTip(self.convert_btn, "Convert all queued files to the selected output formats")

        # --- Status Bar ---
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main, textvariable=self.status_var, relief="sunken", padding=3).pack(fill=tk.X)

    def _setup_traces(self):
        self.overwrite_var.trace_add("write", lambda *_: self._save_config())
        self.auto_process_var.trace_add("write", lambda *_: self._save_config())
        self.clear_on_drop_var.trace_add("write", lambda *_: self._save_config())
        self.save_log_var.trace_add("write", lambda *_: self._save_config())
        for var in self.format_vars.values():
            var.trace_add("write", lambda *_: self._save_config())

    def _save_config(self):
        self.cfg["overwrite"] = self.overwrite_var.get()
        self.cfg["auto_process"] = self.auto_process_var.get()
        self.cfg["clear_on_drop"] = self.clear_on_drop_var.get()
        self.cfg["save_log"] = self.save_log_var.get()
        self.cfg["output_formats"] = [f for f in OUTPUT_FORMATS if self.format_vars[f].get()]
        config.save(self.cfg)

    def _setup_dnd(self):
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self._on_drop)

    def _add_to_queue(self, filepath):
        filepath = clean_filepath(filepath)
        if not os.path.isfile(filepath):
            return
        items = self.queue_listbox.get(0, tk.END)
        if filepath not in items:
            self.queue_listbox.insert(tk.END, filepath)

    def _on_drop(self, event):
        files = parse_drop_data(event.data)
        if self.clear_on_drop_var.get():
            self._clear_queue()
        for f in files:
            self._add_to_queue(f)
        if self.auto_process_var.get():
            self._on_convert()

    def _remove_selected(self):
        for idx in reversed(self.queue_listbox.curselection()):
            self.queue_listbox.delete(idx)

    def _clear_queue(self):
        self.queue_listbox.delete(0, tk.END)

    def _get_selected_formats(self):
        return [f for f in OUTPUT_FORMATS if self.format_vars[f].get()]

    def _on_convert(self):
        files = list(self.queue_listbox.get(0, tk.END))
        if not files:
            self.status_var.set("No files in queue")
            return

        formats = self._get_selected_formats()
        if not formats:
            self.status_var.set("No output formats selected")
            return

        overwrite = self.overwrite_var.get()
        total_ops = len(files) * len(formats)

        self.convert_btn.configure(state="disabled")
        self.status_var.set(f"Converting 0/{total_ops}...")

        def worker():
            results = []
            done = 0
            for filepath in files:
                for fmt in formats:
                    out, err = convert_single(filepath, fmt, overwrite)
                    results.append((filepath, fmt, out, err))
                    done += 1
                    if total_ops <= 20 or done % 10 == 0 or done == total_ops:
                        self.root.after(0, lambda n=done: self.status_var.set(f"Converting {n}/{total_ops}..."))
            self.root.after(0, lambda: self._conversion_done(results))

        threading.Thread(target=worker, daemon=True).start()

    def _conversion_done(self, results):
        self.convert_btn.configure(state="normal")
        ok = sum(1 for *_, e in results if e is None)
        skipped = [(src, fmt, err) for src, fmt, _, err in results if err is not None]
        parts = [f"Done: {ok} converted"]
        if skipped:
            parts.append(f"{len(skipped)} skipped/failed")
            # Show the reason from the first skipped file
            first_err = skipped[0][2]
            parts.append(f"reason: {first_err}")
        self.status_var.set(", ".join(parts))

        if self.save_log_var.get():
            self._write_log(results)

    def _write_log(self, results):
        """Append conversion results to a log file next to the exe/script."""
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))
        log_path = os.path.join(base, "imageconverter.log")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"--- {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ---\n")
                for src, fmt, out, err in results:
                    if err is None:
                        f.write(f"  OK: {src} -> {out}\n")
                    else:
                        f.write(f"  SKIP: {src} [{fmt}] ({err})\n")
                f.write("\n")
        except OSError:
            pass

    def run(self):
        self.root.mainloop()


def main():
    initial_files = sys.argv[1:] if len(sys.argv) > 1 else None
    app = ImageConverterApp(initial_files=initial_files)
    app.run()
