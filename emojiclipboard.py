import sys
import json
import uuid
import shutil
import requests
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


class EmojiClipboardApp(QMainWindow):
    """
    Emoji gallery that persists items between runs.
    - Stores copies of images in ./emoji_gallery/images
    - Stores metadata (image filename -> text) in ./emoji_gallery/metadata.json
    - Loads and displays everything on startup.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emoji Clipboard Gallery")
        self.resize(860, 560)

        # --- Storage paths ---
        self.base_dir = Path.cwd() / "emoji_gallery"
        self.images_dir = self.base_dir / "images"
        self.meta_file = self.base_dir / "metadata.json"

        self._init_storage()
        self.meta = self._load_meta()

        # --- UI ---
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.toolbar = QToolBar("Main")
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        add_act = QAction("Add Images", self)
        add_act.triggered.connect(self.add_images)
        self.toolbar.addAction(add_act)

        remove_act = QAction("Remove Selected", self)
        remove_act.triggered.connect(self.remove_selected)
        self.toolbar.addAction(remove_act)

        clear_act = QAction("Clear All", self)
        clear_act.triggered.connect(self.clear_all)
        self.toolbar.addAction(clear_act)

        self.list = QListWidget(self)
        self.list.setViewMode(QListView.ViewMode.IconMode)
        self.list.setIconSize(QSize(96, 96))
        self.list.setResizeMode(QListView.ResizeMode.Adjust)
        self.list.setMovement(QListView.Movement.Static)
        self.list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list.setSpacing(12)
        self.list.itemClicked.connect(self.copy_item_text)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.list, 1)

        self.setStatusBar(QStatusBar(self))

        hint = QLabel(
            "➕ Click ‘Add Images’ to choose emoji images. Your selections are saved and reloaded automatically."
        )
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        # Load persisted items
        self._load_all()

    # ---- Storage helpers ----
    def _init_storage(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        if not self.meta_file.exists():
            self._save_meta({})

    def _load_meta(self) -> dict:
        try:
            with self.meta_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                return data
        except Exception:
            return {}

    def _save_meta(self, data: dict):
        tmp = self.meta_file.with_suffix(".tmp")
        print(data)
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.meta_file)

    """ def _persist_add(self, source_path: Path, text: str, filename: str) -> Optional[Path]:
        try:
            ext = source_path.suffix.lower() or ".png"
            dest_name = f"{filename}"
            dest = self.images_dir / dest_name
            shutil.copy2(source_path, dest)
            self.meta[dest_name] = {"text": text, "filename": filename}
            self._save_meta(self.meta)
            return dest
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to store image: {e}")
            return None """
        
    def _persist_add(self, text: str, link: str) -> Optional[Path]:
        try:
            dest_name = f"{text}"
            dest = self.images_dir / dest_name
            self.meta[f'{text}.webp'] = {"text": link, "filename": f'{text}.webp'}
            self._save_meta(self.meta)
            return dest
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to store image: {e}")
            return None

    def _persist_remove(self, dest_path: Path):
        try:
            if dest_path.exists():
                dest_path.unlink()
        except Exception:
            pass
        self.meta.pop(dest_path.name, None)
        self._save_meta(self.meta)

    # ---- Loading UI from storage ----
    def _load_all(self):
        self.list.clear()
        removed = 0
        for filename, payload in list(self.meta.items()):
            p = self.images_dir / filename
            text = (payload or {}).get("filename") or Path(filename).stem
            if not p.exists():
                removed += 1
                self.meta.pop(filename, None)
                continue
            self._add_emoji_item(p, text)
        if removed:
            self._save_meta(self.meta)
        if self.list.count():
            self.statusBar().showMessage(f"Loaded {self.list.count()} saved item(s).", 3000)

    # ---- Core Behaviors ----
    def add_images(self):
        """ files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select image files",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"
        )
        if not files:
            return """

        """ added = 0
        for path_str in files:
            src = Path(path_str)
            if not src.exists():
                continue
            # Ask text per image, default to stem
            text, ok = QInputDialog.getText(
                self,
                "Associated Text",
                f"Enter the text to copy when this image is clicked:\n{src.name}",
                text=src.stem,
            )
            if not ok:
                continue
            stored = self._persist_add(src, text, src.stem)
            if stored:
                self._add_emoji_item(stored, src.stem)
                added += 1 """
        
        text = QInputDialog.getText(
                self,
                "Associated Text",
                f"Enter the ID of the emoji to copy",
                text="",
            )

        img_data = requests.get(f'https://cdn.discordapp.com/emojis/{text[0]}.webp?size=56').content
        with open(f'./emoji_gallery/images/{text[0]}.webp', 'wb') as handler:
            handler.write(img_data)

        stored = self._persist_add(text[0], f'https://cdn.discordapp.com/emojis/{text[0]}.webp?size=56')
        if stored:
            self._add_emoji_item(stored, text[0])

        """ if added:
            self.statusBar().showMessage(f"Added {added} item(s). Click an image to copy its text.", 3000) """

    def _add_emoji_item(self, image_path: Path, text: str):
        pix = QPixmap(str(image_path))
        if pix.isNull():
            QMessageBox.warning(self, "Invalid image", f"Could not load: {image_path}")
            return
        icon = QIcon(pix)
        item = QListWidgetItem(icon, text)
        # Store the clipboard text and stored path in roles
        item.setData(Qt.ItemDataRole.UserRole, text)
        item.setData(Qt.ItemDataRole.UserRole + 1, str(image_path))
        item.setSizeHint(QSize(80, 80))
        self.list.addItem(item)

    def copy_item_text(self, item: QListWidgetItem):
        for filename, payload in list(self.meta.items()):
            if f'{item.text()}.webp' == filename or item.text() == filename:
                text = (payload or {}).get("text") or Path(filename).stem
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage(f"Copied to clipboard: {text}", 2000)

    def remove_selected(self):
        to_remove = self.list.selectedItems()
        if not to_remove:
            self.statusBar().showMessage("No selection to remove.", 2000)
            return
        count = 0
        for it in to_remove:
            self._remove_item(it)
            count += 1
        self.statusBar().showMessage(f"Removed {count} item(s).", 2000)

    def clear_all(self):
        if self.list.count() == 0:
            return
        if QMessageBox.question(self, "Clear All", "Remove all items from gallery?") == QMessageBox.StandardButton.Yes:
            # remove files
            for i in range(self.list.count()):
                it = self.list.item(i)
                p = Path(it.data(Qt.ItemDataRole.UserRole + 1))
                self._persist_remove(p)
            self.list.clear()
            self.statusBar().showMessage("Cleared all items.", 2000)

    """ def edit_text(self, item: QListWidgetItem):
            # Ask text per image, default to stem
        text, ok = QInputDialog.getText(
            self,
            "Associated Text",
            f"Enter the text to copy when this image is clicked:\n{item.text()}",
            text=item.text(),
        )
   
        self.meta[item.text()] = {"text": text, "filename": item.text()}
        self._save_meta(self.meta) """
        

        

    # ---- Context Menu ----
    def show_context_menu(self, pos):
        item = self.list.itemAt(pos)
        menu = QMenu(self)

        add_action = QAction("Add Images…", self)
        add_action.triggered.connect(self.add_images)
        menu.addAction(add_action)

        if item:
            #edit_action = QAction("Edit Text", self)
            #edit_action.triggered.connect(self.edit_text(item))
            #menu.addAction(edit_action)

            copy_action = QAction("Copy Text", self)
            copy_action.triggered.connect(lambda: self.copy_item_text(item))
            menu.addAction(copy_action)

            remove_action = QAction("Remove", self)
            remove_action.triggered.connect(lambda: self._remove_item(item))
            menu.addAction(remove_action)

        menu.exec(self.list.mapToGlobal(pos))

    def _remove_item(self, item: Optional[QListWidgetItem]):
        if item is None:
            return
        p = Path(item.data(Qt.ItemDataRole.UserRole + 1))
        self._persist_remove(p)
        self.list.takeItem(self.list.row(item))


def main():
    app = QApplication(sys.argv)
    win = EmojiClipboardApp()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
