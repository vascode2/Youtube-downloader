"""PySide6 desktop GUI for the YouTube audio downloader.

Single-window app that maps 1:1 to the CLI flags. Reuses `download_audio()`
from `downloader.py` (per AGENTS.md: do NOT subprocess the CLI).

Run:
    python -m src.gui
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QObject, QThread, Signal, Slot
from PySide6.QtGui import QClipboard, QDragEnterEvent, QDropEvent, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .cli import parse_batch_file, parse_mixed_file, parse_song_file, resolve_songs
from .downloader import DEFAULT_OUT_DIR, DownloaderError, download_audio


# ---------------------------------------------------------------------------
# Worker — runs the long-running download work on a QThread.
# ---------------------------------------------------------------------------


class Worker(QObject):
    """Runs one job (single URL, batch file, or search [+download]).

    Lives on a worker QThread. Emits signals back to the GUI.
    """

    log = Signal(str)
    file_progress = Signal(int, int, str)  # current_index (1-based), total, label
    item_progress = Signal(int)             # 0..100 for the current file
    finished = Signal(int, int)             # (ok_count, fail_count)

    def __init__(
        self,
        urls: list[str],
        opts: dict,
        search_queries: list[str] | None = None,
        search_only: bool = False,
        search_input_path: Path | None = None,
    ):
        super().__init__()
        self._urls = urls
        self._opts = opts
        self._search_queries = search_queries
        self._search_only = search_only
        self._search_input_path = search_input_path
        self._cancel = False

    @Slot()
    def cancel(self) -> None:
        self._cancel = True

    def _hook(self, d: dict) -> None:
        """yt-dlp progress hook -> Qt signal (thread-safe via auto-connection)."""
        if self._cancel:
            raise DownloaderError("Cancelled by user")
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            pct = int(done * 100 / total) if total else 0
            self.item_progress.emit(min(pct, 100))
        elif status == "finished":
            self.item_progress.emit(100)

    @Slot()
    def run(self) -> None:
        urls = list(self._urls)

        # --search step (optional, runs first).
        if self._search_queries is not None:
            self.log.emit(f"Resolving {len(self._search_queries)} song name(s)...")
            try:
                results = resolve_songs(self._search_queries)
            except Exception as e:  # noqa: BLE001
                self.log.emit(f"  search failed: {e}")
                self.finished.emit(0, len(self._search_queries))
                return
            ids: list[str] = []
            body: list[str] = []
            failed = 0
            for query, vid, yt_title in results:
                if vid:
                    url = f"https://www.youtube.com/watch?v={vid}"
                    urls.append(url)
                    ids.append(vid)
                    body.append(f"{query} - {url}")
                    self.log.emit(f"  OK   {query[:40]:40s} -> {(yt_title or '')[:50]}")
                else:
                    body.append(f"# FAILED: {query}")
                    self.log.emit(f"  FAIL {query}")
                    failed += 1

            # Persist the .urls.txt next to the input (same logic as cli._run_search).
            if self._search_input_path is not None:
                in_path = self._search_input_path
                if in_path.suffix == ".txt":
                    out_file = in_path.with_name(in_path.stem + ".urls.txt")
                else:
                    out_file = in_path.with_name(in_path.name + ".urls.txt")
                header = [f"# Resolved from {in_path.name}"]
                if ids:
                    capped = ids[:50]
                    pl = "https://www.youtube.com/watch_videos?video_ids=" + ",".join(capped)
                    header.append(f"# Playlist URL: {pl}")
                    self.log.emit(f"\nYouTube playlist URL:\n  {pl}")
                try:
                    out_file.write_text("\n".join(header + body) + "\n", encoding="utf-8")
                    self.log.emit(f"\nWrote {len(ids)} URL(s) to {out_file}")
                except OSError as e:
                    self.log.emit(f"  could not write {out_file}: {e}")

            if self._search_only:
                self.finished.emit(len(ids), failed)
                return

        # Download step.
        if not urls:
            self.log.emit("Nothing to download.")
            self.finished.emit(0, 0)
            return

        ok = 0
        fail = 0
        total = len(urls)
        for i, url in enumerate(urls, 1):
            if self._cancel:
                self.log.emit("Cancelled.")
                break
            self.file_progress.emit(i, total, url)
            self.log.emit(f"\n[{i}/{total}] {url}")
            self.item_progress.emit(0)
            try:
                paths = download_audio(url=url, progress_hook=self._hook, **self._opts)
                for p in paths:
                    self.log.emit(f"  saved: {p.name}")
                ok += 1
            except DownloaderError as e:
                self.log.emit(f"  FAILED: {e}")
                fail += 1
            except Exception as e:  # noqa: BLE001
                self.log.emit(f"  FAILED: {type(e).__name__}: {e}")
                fail += 1

        self.finished.emit(ok, fail)


# ---------------------------------------------------------------------------
# Drop zone — lets the user drag a .txt file onto the window.
# ---------------------------------------------------------------------------


class DropZone(QFrame):
    """File drop target; emits `fileDropped(Path)` when the user drops a .txt."""

    fileDropped = Signal(Path)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(70)
        self._label = QLabel(
            "Drop a .txt file here  —  URLs => batch download,  song names => search + download"
        )
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.addWidget(self._label)
        self._set_idle_style()

    def _set_idle_style(self) -> None:
        self.setStyleSheet(
            "DropZone { border: 2px dashed #888; border-radius: 8px; background: #fafafa; }"
            "QLabel { color: #555; }"
        )

    def _set_hover_style(self) -> None:
        self.setStyleSheet(
            "DropZone { border: 2px dashed #2a7; border-radius: 8px; background: #eefbe6; }"
            "QLabel { color: #2a7; }"
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if urls and urls[0].toLocalFile().lower().endswith(".txt"):
            event.acceptProposedAction()
            self._set_hover_style()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._set_idle_style()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self._set_idle_style()
        urls = event.mimeData().urls()
        if not urls:
            return
        path = Path(urls[0].toLocalFile())
        if path.is_file():
            self.fileDropped.emit(path)


# ---------------------------------------------------------------------------
# Main window.
# ---------------------------------------------------------------------------


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("YouTube Downloader")
        self.resize(720, 560)

        self._thread: QThread | None = None
        self._worker: Worker | None = None

        self._build_ui()

    # -- UI construction ---------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # URL row.
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("URL:"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Paste a YouTube URL  (or leave empty + click Paste)")
        url_row.addWidget(self.url_edit, 1)
        paste_btn = QPushButton("Paste")
        paste_btn.clicked.connect(self._on_paste)
        url_row.addWidget(paste_btn)
        root.addLayout(url_row)

        # Options grid.
        grid = QGridLayout()
        grid.addWidget(QLabel("Quality:"), 0, 0)
        self.quality = QComboBox()
        self.quality.addItems(["64", "128", "192", "256", "320", "highest"])
        self.quality.setCurrentText("192")
        grid.addWidget(self.quality, 0, 1)

        grid.addWidget(QLabel("Format:"), 0, 2)
        self.fmt = QComboBox()
        self.fmt.addItems(["m4a", "mp3", "ogg"])
        grid.addWidget(self.fmt, 0, 3)

        grid.addWidget(QLabel("Out:"), 1, 0)
        self.out_edit = QLineEdit(DEFAULT_OUT_DIR)
        grid.addWidget(self.out_edit, 1, 1, 1, 2)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse)
        grid.addWidget(browse_btn, 1, 3)
        root.addLayout(grid)

        # Checkboxes.
        check_row = QHBoxLayout()
        self.cb_playlist = QCheckBox("Playlist (download all in &list=...)")
        self.cb_rename = QCheckBox("Auto-rename to 'Artist - Title'")
        self.cb_rename.setChecked(True)
        self.cb_tags = QCheckBox("Embed tags + cover art")
        self.cb_tags.setChecked(True)
        check_row.addWidget(self.cb_playlist)
        check_row.addWidget(self.cb_rename)
        check_row.addWidget(self.cb_tags)
        check_row.addStretch(1)
        root.addLayout(check_row)

        # Drop zone.
        self.drop = DropZone()
        self.drop.fileDropped.connect(self._on_file_dropped)
        root.addWidget(self.drop)

        # Action row.
        action_row = QHBoxLayout()
        self.go_btn = QPushButton("Download")
        self.go_btn.setMinimumWidth(120)
        self.go_btn.clicked.connect(self._on_go)
        action_row.addWidget(self.go_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        action_row.addWidget(self.cancel_btn)
        action_row.addStretch(1)
        self.batch_label = QLabel("")
        action_row.addWidget(self.batch_label)
        root.addLayout(action_row)

        # Progress bar + log.
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        root.addWidget(self.bar)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Output will appear here...")
        root.addWidget(self.log, 1)

        # Pending file path (set by drop / batch button).
        self._pending_file: Path | None = None
        self._pending_mode: str | None = None  # "batch" | "search"

    # -- Slots -------------------------------------------------------------

    @Slot()
    def _on_paste(self) -> None:
        cb: QClipboard = QGuiApplication.clipboard()
        text = cb.text().strip()
        if text:
            self.url_edit.setText(text)

    @Slot()
    def _on_browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Output folder", self.out_edit.text())
        if d:
            self.out_edit.setText(d)

    @Slot(Path)
    def _on_file_dropped(self, path: Path) -> None:
        # Classify: a file with ANY YouTube URL is treated as a batch file.
        # Lines without URLs in that file are auto-resolved via search at
        # download time. A file with only name lines (no URLs) is
        # search-and-download mode.
        try:
            urls, queries = parse_mixed_file(path)
        except DownloaderError as e:
            self._append_log(f"Cannot read {path}: {e}")
            return
        if urls:
            self._pending_file = path
            self._pending_mode = "batch"
            extra = f" + {len(queries)} name(s) to resolve" if queries else ""
            self._append_log(f"Loaded batch file: {path}  ({len(urls)} URL(s){extra})")
            self.go_btn.setText(f"Download batch ({len(urls) + len(queries)})")
        elif queries:
            self._pending_file = path
            self._pending_mode = "search"
            self._append_log(
                f"Loaded song-names file: {path}  ({len(queries)} name(s)) — will search + download"
            )
            self.go_btn.setText(f"Search + download ({len(queries)})")
        else:
            self._append_log(f"{path}: no URLs and no song names found.")

    @Slot()
    def _on_go(self) -> None:
        url = self.url_edit.text().strip()
        opts = {
            "quality": self.quality.currentText(),
            "fmt": self.fmt.currentText(),
            "out_dir": self.out_edit.text().strip() or DEFAULT_OUT_DIR,
            "playlist": self.cb_playlist.isChecked(),
            "rename": self.cb_rename.isChecked(),
            "tags": self.cb_tags.isChecked(),
        }

        urls: list[str] = []
        search_queries: list[str] | None = None
        search_input: Path | None = None

        if self._pending_file is not None:
            if self._pending_mode == "batch":
                try:
                    urls, extra_queries = parse_mixed_file(self._pending_file)
                except DownloaderError as e:
                    QMessageBox.warning(self, "Error", str(e))
                    return
                # Name-only lines in a batch file get resolved alongside the
                # explicit URLs, same as CLI batch mode. We do NOT pass
                # search_input here -- writing a sibling .urls.txt is only
                # the right behavior in pure search mode, not when resolution
                # is a side effect of a mostly-URL batch.
                if extra_queries:
                    search_queries = extra_queries
            else:  # "search"
                try:
                    search_queries = parse_song_file(self._pending_file)
                except DownloaderError as e:
                    QMessageBox.warning(self, "Error", str(e))
                    return
                search_input = self._pending_file
            if url:
                urls.insert(0, url)  # allow mixing
        else:
            if not url:
                QMessageBox.information(
                    self,
                    "Nothing to do",
                    "Enter a URL or drop a .txt file (URLs or song names).",
                )
                return
            urls = [url]

        self._start_worker(urls, opts, search_queries, search_input)

    @Slot()
    def _on_cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self._append_log("Cancel requested...")

    # -- Worker plumbing ---------------------------------------------------

    def _start_worker(
        self,
        urls: list[str],
        opts: dict,
        search_queries: list[str] | None,
        search_input: Path | None,
    ) -> None:
        self.log.clear()
        self.bar.setValue(0)
        self.batch_label.setText("")
        self.go_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        self._thread = QThread(self)
        self._worker = Worker(
            urls=urls,
            opts=opts,
            search_queries=search_queries,
            search_only=False,  # GUI always downloads after search (the natural flow)
            search_input_path=search_input,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)

        self._worker.log.connect(self._append_log)
        self._worker.file_progress.connect(self._on_file_progress)
        self._worker.item_progress.connect(self.bar.setValue)
        self._worker.finished.connect(self._on_finished)

        self._thread.start()

    @Slot(str)
    def _append_log(self, line: str) -> None:
        self.log.appendPlainText(line)

    @Slot(int, int, str)
    def _on_file_progress(self, idx: int, total: int, label: str) -> None:
        self.batch_label.setText(f"{idx}/{total}")

    @Slot(int, int)
    def _on_finished(self, ok: int, fail: int) -> None:
        self._append_log("\n" + "=" * 50)
        self._append_log(f"Done. {ok} ok, {fail} failed.")
        self.bar.setValue(100 if fail == 0 else self.bar.value())
        self.go_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        # Reset go-button label and pending file so the next click starts fresh.
        self._pending_file = None
        self._pending_mode = None
        self.go_btn.setText("Download")

        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread.deleteLater()
            self._thread = None
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
