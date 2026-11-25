"""Shared imports and application constants."""
import sys, os, re, json, shutil, zipfile, platform, subprocess, threading, uuid, copy, random, math, base64, shlex, hashlib
from pathlib import Path
from PyQt6.QtCore import (Qt, QTimer, QPointF, QRectF, QRect, QSize, QSettings, QMimeData, pyqtSignal,
                          QBuffer, QByteArray, QIODevice)
from PyQt6.QtGui import (QAction, QColor, QFont, QFontMetricsF, QImage, QImageReader, QKeySequence,
                         QMovie, QPainter, QPainterPath, QPen)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsPathItem, QGraphicsEllipseItem, QMenu, QToolBar, QSplitter, QVBoxLayout,
    QHBoxLayout, QFormLayout, QComboBox, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QColorDialog, QFileDialog, QInputDialog, QMessageBox, QLabel, QFrame, QScrollArea,
    QTabWidget, QListWidget, QListWidgetItem, QButtonGroup)

APP = "Fetch Studio"
VERSION = "2.0.0"
GH_REPO = "bobbycomet/Fetch-Studio"
RELEASES_URL = "https://github.com/%s/releases" % GH_REPO
UPDATER_URL = "https://github.com/bobbycomet/GriffinUpdater"
DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "fetchstudio"
PROJ, ACTIVE = DATA / "projects", DATA / "active"
MARK_B, MARK_E = "# >>> fetchstudio >>>", "# <<< fetchstudio <<<"
PAL = ["#2e3436", "#cc0000", "#4e9a06", "#c4a000", "#3465a4", "#75507b", "#06989a", "#d3d7cf",
       "#555753", "#ef2929", "#8ae234", "#fce94f", "#729fcf", "#ad7fa8", "#34e2e2", "#eeeeec"]
IMG = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
# name -> (window title shown in preview, font size, executable used for detection)
TERMS = {
    "GNOME Terminal": ("Terminal", 11, "gnome-terminal"), "Console (kgx)": ("Console", 11, "kgx"),
    "Konsole": ("Konsole", 10, "konsole"), "Xfce Terminal": ("Terminal", 10, "xfce4-terminal"),
    "MATE Terminal": ("Terminal", 10, "mate-terminal"), "QTerminal": ("QTerminal", 10, "qterminal"),
    "LXTerminal": ("LXTerminal", 10, "lxterminal"), "Tilix": ("Tilix", 11, "tilix"),
    "Deepin Terminal": ("Deepin Terminal", 11, "deepin-terminal"),
    "COSMIC Terminal": ("COSMIC Terminal", 11, "cosmic-term"),
    "Pantheon Terminal": ("Terminal", 10, "io.elementary.terminal")}
