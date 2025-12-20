from PySide6.QtCore import Property, Slot, QObject, Signal
from PySide6.QtGui import QGuiApplication
from loguru import logger

from src.core.directories import LOGS_PATH, ROOT_PATH
from src.core.utils.auto_startup import autostart_supported, enable_autostart, disable_autostart, is_autostart_enabled


class UtilsBackend(QObject):
    logsUpdated = Signal()
    extraSettingsChanged = Signal()
    licenseLoaded = Signal()

    MAX_LOG_LINES = 200

    def __init__(self, app):
        super().__init__()
        self.app = app
        self._extra_settings: list = []
        self._license_text: str = ""
        self._logs: list = []
        self.app.plugin_api.ui.settingsPageRegistered.connect(lambda: self.extraSettingsChanged.emit())

        # 执行初始化逻辑
        self._init_logger()
        self.load_license()  # 启动时立即加载

    def _init_logger(self):
        """配置 Loguru 钩子"""
        logger.add(self._capture_log, level="DEBUG", enqueue=True)

    def _capture_log(self, message):
        """Loguru 回调函数"""
        record = message.record
        log_entry = {
            "time": record["time"].strftime("%H:%M:%S"),
            "level": record["level"].name,
            "message": record["message"]
        }
        self._logs.append(log_entry)

        if len(self._logs) > self.MAX_LOG_LINES:
            self._logs.pop(0)

        self.logsUpdated.emit()

    @Property("QVariantList", notify=logsUpdated)
    def logs(self):
        return self._logs

    @Slot(result=list)
    def clearLogs(self):
        """清理物理日志文件"""
        try:
            size = 0
            if LOGS_PATH.exists():
                for file in LOGS_PATH.glob("**/*"):
                    if file.is_file():
                        try:
                            file_size = file.stat().st_size / 1024 # kb
                            file.unlink()
                            size += file_size
                        except PermissionError:
                            logger.debug(f"Permission denied: {file.name}")
            return True, round(size, 2)
        except Exception as e:
            logger.exception(f"Failed to clear logs: {e}")
            return [False, 0]

    # 设置与插件
    @Property(list, notify=extraSettingsChanged)
    def extraSettings(self):
        return self.app.plugin_api.ui.pages

    # 设置功能
    @Property(str, notify=licenseLoaded)
    def licenseText(self):
        return self._license_text

    def load_license(self):
        try:
            license_path = ROOT_PATH / "LICENSE"
            if license_path.exists():
                with open(license_path, "r", encoding="utf-8") as f:
                    self._license_text = f.read()
            else:
                self._license_text = "License file not found."
        except Exception as e:
            logger.error(f"Failed to load license: {e}")
            self._license_text = "Error loading license."
        finally:
            self.licenseLoaded.emit()

    @Slot(str, result=bool)
    def copyToClipboard(self, text):
        try:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(text)
            return True
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            return False

    # 自启动
    @Property(bool, constant=True)
    def autostartSupported(self):
        return autostart_supported()

    @Slot(bool, result=bool)
    def setAutostart(self, enabled):
        if enabled:
            enable_autostart()
        else:
            disable_autostart()
        return is_autostart_enabled()

    @Slot(result=bool)
    def autostartEnabled(self):
        return autostart_supported() and is_autostart_enabled()
