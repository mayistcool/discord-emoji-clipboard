import sys
import json
import requests
from pathlib import Path
from typing import Optional
from PIL import Image
import os

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QAction, QMovie
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QDialog,
    QLineEdit,
    QCheckBox,
    QDialogButtonBox,
)
import ctypes
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('company.app.1')


class TextWithCheckbox(QDialog):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enter an ID")

        layout = QVBoxLayout(self)

        self.label = QLabel(
            "Enter the ID of the discord emoji you want to add:"
        )
        layout.addWidget(self.label)

        self.text_input = QLineEdit(self)
        layout.addWidget(self.text_input)

        self.check_box = QCheckBox("GIF", self)
        layout.addWidget(self.check_box)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)


    def get_data(self):
        return self.text_input.text(), self.check_box.isChecked()


class EmojiClipboardApp(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emojis")
        self.resize(229, 600)

        self.setWindowIcon(QIcon("./assets/discordcliboardicon.ico"))

        # --- Storage paths ---
        self.base_dir = Path.cwd() / "emoji_gallery"
        self.images_dir = self.base_dir / "images"
        self.meta_file = self.base_dir / "metadata.json"

        self._init_storage()
        self.meta = self._load_meta()

        # --- UI ---
        central = QWidget(self)
        self.setCentralWidget(central)
        self.setStyleSheet(
            """
            background-color: #282b30;
            """
        )
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self.toolbar = QToolBar("Main")
        self.toolbar.setMovable(False)
        self.toolbar.setStyleSheet(
            """
            QToolBar {
                background-color: #282b30;
                border: 0px;
            }
            QToolButton:hover { 
                background-color: #424549;
            }
            """
        )
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        add_act = QAction("Add", self)
        add_act.triggered.connect(self.add_images)
        self.toolbar.addAction(add_act)

        remove_act = QAction("Remove Selection", self)
        remove_act.triggered.connect(self.remove_selected)
        self.toolbar.addAction(remove_act)

        clear_act = QAction("Clear All", self)
        clear_act.triggered.connect(self.clear_all)
        self.toolbar.addAction(clear_act)

        self.list = QListWidget(self)
        self.list.setViewMode(QListView.ViewMode.IconMode)
        self.list.setIconSize(QSize(60, 60))
        self.list.setResizeMode(QListView.ResizeMode.Adjust)
        self.list.setMovement(QListView.Movement.Static)
        self.list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list.setSpacing(6)
        self.list.itemClicked.connect(self.copy_item_text)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.show_context_menu)
        self.list.setStyleSheet(
            """
            QListWidget {
                background-color: #424549;
                border-radius: 10px;
            }
            QScrollBar:vertical {
                border: 0px;
                background: #424549;
                width: 0px;
            }
            """
        )
        layout.addWidget(self.list, 1)

        self.setStatusBar(QStatusBar(self))

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
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.meta_file)
        
    def _persist_add(self, text: str, link: str) -> Optional[Path]:
        try:
            dest_name = f"{text}"
            dest = self.images_dir / dest_name
            if "animated" in link:
                self.meta[f'{text}.gif'] = {"text": link, "filename": f'{text}.gif'}
                self._save_meta(self.meta)
            else:
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
        dialog = TextWithCheckbox()
        if dialog.exec():
            text, checked= dialog.get_data()
        else:
            return

        link = self.create_link(text, checked)

        stored = self._persist_add(text, link)
        if stored:
            if "animated" in link:
                self._add_emoji_item(f'{stored}.gif', f'{text}.gif')
            else:
                self._add_emoji_item(f'{stored}.webp', f'{text}.webp')
            

    def create_link(self, id: int, checked: bool):
            link = f'https://cdn.discordapp.com/emojis/{id}.webp?size=48'
            
            if checked:
                link += '&animated=true'

            img_data = requests.get(link).content
            with open(f'./emoji_gallery/images/{id}.webp', 'wb') as handler:
                handler.write(img_data)
            
            if checked:
                img = Image.open(f'./emoji_gallery/images/{id}.webp')
                img.info.pop('background', None)
                img.save(f'./emoji_gallery/images/{id}.gif', 'gif', save_all=True)
                os.remove(f'./emoji_gallery/images/{id}.webp')
                

            return link

    def _add_emoji_item(self, image_path: Path, text: str):
        if ".gif" in text:
            movie = QMovie(str(image_path))
            label = QLabel()
            label.setStyleSheet("background: transparent;")
            try:
                movie.setBackgroundColor(Qt.transparent)  # available in Qt
            except AttributeError:
                pass

            label.setMovie(movie)
            movie.start()

            # Create a QListWidgetItem (just a container)
            item = QListWidgetItem()
            self.list.addItem(item)

            # Match item size to gif size
            item.setSizeHint(QSize(60, 60))
            item.setData(Qt.ItemDataRole.UserRole, text)
            item.setData(Qt.ItemDataRole.UserRole + 1, str(image_path))

            # Put the label (with the movie) into the item
            self.list.setItemWidget(item, label)
            
        else:
            pix = QPixmap(str(image_path))
            if pix.isNull():
                QMessageBox.warning(self, "Invalid image", f"Could not load: {image_path}")
                return
            icon = QIcon(pix)
            item = QListWidgetItem(icon, "")
        # Store the clipboard text and stored path in roles
            item.setData(Qt.ItemDataRole.UserRole, text)
            item.setData(Qt.ItemDataRole.UserRole + 1, str(image_path))
            item.setSizeHint(QSize(60, 60))
            self.list.addItem(item)

    def copy_item_text(self, item: QListWidgetItem):
        for filename, payload in list(self.meta.items()):
            if f'{item.data(Qt.ItemDataRole.UserRole)}.webp' == filename or item.data(Qt.ItemDataRole.UserRole) == filename:
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

    # ---- Context Menu ----
    def show_context_menu(self, pos):
        item = self.list.itemAt(pos)
        menu = QMenu(self)

        add_action = QAction("Add Images…", self)
        add_action.triggered.connect(self.add_images)
        menu.addAction(add_action)

        if item:
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
