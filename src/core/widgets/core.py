from pathlib import Path
from PySide6.QtCore import QObject, Slot, Property, Signal, QRect, Qt, QTimer
import RinUI
from PySide6.QtGui import QRegion, QCursor
from PySide6.QtWidgets import QApplication
from loguru import logger

from src.core import QML_PATH


class WidgetsWindow(RinUI.RinUIWindow, QObject):
    def __init__(self, app_central):
        super().__init__()
        self.app_central = app_central
        self.accepts_input = True

        self._setup_qml_context()
        self.qml_main_path = Path(QML_PATH / "MainInterface.qml")
        self.interactive_rect = QRegion()

        self.engine.objectCreated.connect(self.on_qml_ready, type=Qt.ConnectionType.QueuedConnection)

    def _setup_qml_context(self):
        """设置QML上下文属性"""
        self.app_central.setup_qml_context(self)

    def _start_listening(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_mouse_state)
        self.timer.start(33)  # 大约每秒30帧检测一次

    def run(self):
        """启动widgets窗口"""
        self.app_central.widgets_model.load_config()
        self._load_with_theme()
        self.app_central.theme_manager.themeChanged.connect(self.on_theme_changed)
        self.app_central.retranslate.connect(self.engine.retranslate)

    def _load_with_theme(self):
        """加载QML并应用主题"""
        current_theme = self.app_central.theme_manager.currentTheme
        if current_theme:
            self.engine.addImportPath(str(current_theme))
        self.load(self.qml_main_path)

        self._start_listening()

    def on_theme_changed(self):
        """主题变更时重新加载界面"""
        self.engine.clearComponentCache()
        self._load_with_theme()

    def on_qml_ready(self, obj, objUrl):
        if obj is None:
            logger.error("Main QML Load Failed")
            return

        widgets_loader = self.root_window.findChild(QObject, "widgetsLoader")
        if widgets_loader:
            widgets_loader.geometryChanged.connect(self.update_mask)
            return
        logger.error("'widgetsLoader' object has not found'")

    # 裁剪窗口
    def update_mask(self):
        mask = QRegion()
        widgets_loader = self.root_window.findChild(QObject, "widgetsLoader")
        if not widgets_loader:
            return

        menu_show = widgets_loader.property("menuVisible") or False
        edit_mode = widgets_loader.property("editMode") or False

        if menu_show or edit_mode:
            self.root_window.setMask(QRegion())
            return

        for w in widgets_loader.childItems():
            if w.objectName() == "addWidgetsContainer":
                continue
            rect = QRect(
                int(w.x() + widgets_loader.x()),
                int(w.y() + widgets_loader.y()),
                int(w.width()),
                int(w.height())
            )
            mask = mask.united(QRegion(rect))

        self.interactive_rect = mask
        self.root_window.setMask(mask)

    def update_mouse_state(self):
        if not self.interactive_rect:
            return  # 没有 mask 就不处理
        if not self.app_central.configs.interactions.hover_fade:
            return  # 配置文件

        global_pos = QCursor.pos()
        # local_pos = self.widgets_loader.mapFromGlobal(global_pos)
        local_pos = global_pos

        in_mask = self.interactive_rect.contains(local_pos)

        if in_mask and not self.accepts_input:
            self.root_window.setProperty(
                "mouseHovered",
                True
            )
            self.root_window.show()
            self.accepts_input = True

            # 鼠标不在有效区域
        elif not in_mask and self.accepts_input:
            self.root_window.setProperty(
                "mouseHovered",
                False
            )
            self.root_window.show()
            self.accepts_input = False