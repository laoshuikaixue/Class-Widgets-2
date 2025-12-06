import importlib
import importlib.util
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import List, Dict

from PySide6.QtCore import Slot, QObject, Signal, Property, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog
from loguru import logger

from src.core.directories import PLUGINS_PATH, BUILTIN_PLUGINS_PATH
from src.core.plugin import CW2Plugin
from src.core.utils import check_api_version


REQUIRED_FIELDS = ["id", "name", "version", "api_version", "entry", "author"]


def validate_meta(meta: dict, plugin_dir: Path) -> bool:
    """
    校验插件 meta 字段完整性
    """
    # 检查必填字段
    for field in REQUIRED_FIELDS:
        if field not in meta or not meta[field]:
            logger.warning(f"Plugin meta missing required field '{field}' in {plugin_dir}")
            return False

    return True



class PluginManager(QObject):
    initialized = Signal()
    pluginListChanged = Signal()

    def __init__(self, plugin_api, app_central):
        super().__init__()
        self.api = plugin_api
        self.app_central = app_central
        self._plugins: Dict[str, CW2Plugin] = {}
        self.metas: List[dict] = []  # 所有找到的插件
        self.enabled_plugins = set(self.app_central.configs.plugins.enabled)

        self.external_path = PLUGINS_PATH
        self.builtin_path = BUILTIN_PLUGINS_PATH

        self.scan()
        logger.info(f"Found {len(self.metas)} plugins.")
        logger.info(f"Plugin Manager initialized.")
        self.initialized.emit()

    def discover_plugins_in_dir(self, base_dir: Path) -> List[Path]:
        found = []
        if base_dir.exists() and base_dir.is_dir():
            for plugin_dir in base_dir.iterdir():
                if plugin_dir.is_dir() and (plugin_dir / "cwplugin.json").exists():
                    found.append(plugin_dir)
        return found

    def scan(self):
        """扫描内置和外部插件目录，收集所有插件的元数据"""
        self.metas.clear()

        for plugin_dir in self.discover_plugins_in_dir(self.builtin_path):
            self._load_meta(plugin_dir, "builtin")

        for plugin_dir in self.discover_plugins_in_dir(self.external_path):
            self._load_meta(plugin_dir, "external")

        logger.info(f"Found {len(self.metas)} plugins.")

    def _load_meta(self, plugin_dir: Path, type="external"):
        try:
            meta_path = plugin_dir / "cwplugin.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["_path"] = plugin_dir
            meta["_type"] = type

            if not validate_meta(meta, plugin_dir):
                logger.warning(f"Plugin meta invalid, skipped: {plugin_dir}")
                return

            self.metas.append(meta)
        except Exception as e:
            logger.exception(f"Failed to read plugin meta from {plugin_dir}: {e}")

    # 加载启用插件
    def load_plugins(self):
        """加载插件实例"""
        for pid in self.enabled_plugins:
            meta = next((m for m in self.metas if m["id"] == pid), None)
            if meta:
                try:
                    self._initialized_plugin(meta)
                except Exception as e:
                    logger.exception(f"Failed to initialize plugin {meta['id']}: {e}")
            else:
                logger.warning(f"Enabled plugin {pid} not found in metas")

    def _initialized_plugin(self, meta: dict):
        plugin_dir = meta["_path"]
        try:
            if not check_api_version(meta["api_version"], self.app_central.configs.app.version):
                raise RuntimeError(
                    f"Plugin {meta['id']} (api_version {meta.get('api_version')}) "
                    f"is not compatible with app version {self.app_central.configs.app.version}"
                )

            entry_file = plugin_dir / meta["entry"]
            if not entry_file.exists():
                raise FileNotFoundError(f"Entry file not found: {entry_file}")

            sys.path.insert(0, str(plugin_dir))

            spec = importlib.util.spec_from_file_location(meta["id"], entry_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "Plugin"):
                raise AttributeError("Plugin entry file does not define a 'Plugin' class")

            plugin_instance = getattr(module, "Plugin")(self.api)

            if not isinstance(plugin_instance, CW2Plugin):
                raise TypeError("Plugin class must inherit from CW2Plugin")

            plugin_instance.on_load()
            self._plugins[meta["id"]] = plugin_instance

            logger.success(f"Loaded plugin {meta['name']} ({meta['id']}) v{meta['version']}")
        except Exception as e:
            logger.exception(f"Failed to load plugin {meta['id']}: {e}")

    def set_enabled_plugins(self, enabled_plugins: List[str]):
        if not enabled_plugins:
            return
        self.enabled_plugins = set(enabled_plugins)

    # 卸载全部
    def cleanup(self):
        for name, plugin in list(self._plugins.items()):
            try:
                plugin.on_unload()
            except Exception as e:
                logger.error(f"Failed to unload plugin {name}: {e}")
        self._plugins.clear()

    @Slot(result=bool)
    def importPlugin(self) -> bool:
        """从 ZIP 导入插件（带校验）"""
        zip_path, _ = QFileDialog.getOpenFileName(
            None, "Import Plugin", "", "Plugin ZIP (*.zip)"
        )
        if not zip_path:
            return False

        old_ids = {m["id"] for m in self.metas}  # 导入前已有的插件ID
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                members = zip_ref.namelist()
                top_dirs = {Path(m).parts[0] for m in members if not m.endswith('/')}

                if len(top_dirs) == 1:  # 检测目录层级
                    zip_ref.extractall(self.external_path)
                    target_dir = self.external_path / list(top_dirs)[0]
                else:
                    target_dir = self.external_path / Path(zip_path).stem
                    if target_dir.exists():
                        shutil.rmtree(target_dir)
                    zip_ref.extractall(target_dir)

            self.scan()  # 扫描新插件
            new_ids = {m["id"] for m in self.metas}
            diff = new_ids - old_ids

            if not diff:
                name_guess = Path(zip_path).stem
                candidate_dir = self.external_path / name_guess
                if candidate_dir.exists():
                    shutil.rmtree(candidate_dir)

                logger.warning(f"Plugin import failed: {zip_path} is not a valid plugin.")
                return False
            else:
                self.pluginListChanged.emit()
                logger.info(f"Imported plugin(s): {', '.join(diff)}")
                return True
        except Exception as e:
            logger.exception(f"Failed to import plugin: {e}")
            return False

    @Property('QVariant', notify=pluginListChanged)
    def plugins(self):
        """QML调用此函数获取插件列表"""
        return self.metas

    @Slot(str, result=bool)
    def isPluginEnabled(self, pid: str) -> bool:
        return pid in self.enabled_plugins

    @Slot(str, result=bool)
    def isPluginCompatible(self, pid: str) -> bool:
        meta = next((m for m in self.metas if m["id"] == pid), None)
        if not meta:
            return False
        return check_api_version(meta["api_version"], self.app_central.configs.app.version)

    @Slot(str, bool)
    def setPluginEnabled(self, pid: str, enabled: bool):
        if enabled:
            logger.info(f"Enabled plugin {pid}")
            self.enabled_plugins.add(pid)
        else:
            logger.info(f"Disabled plugin {pid}")
            self.enabled_plugins.discard(pid)
        self.app_central.configs.plugins.enabled = list(self.enabled_plugins)
        self.pluginListChanged.emit()

    @Slot(str, result=bool)
    def openPluginFolder(self, pid: str) -> bool:
        """
        打开指定插件的本地文件夹
        """
        meta = next((m for m in self.metas if m["id"] == pid), None)
        if not meta:
            logger.warning(f"Plugin {pid} not found, cannot open folder.")
            return False

        folder_path = meta.get("_path")
        if not folder_path or not Path(folder_path).exists():
            logger.warning(f"Plugin folder {folder_path} does not exist.")
            return False

        # 打开文件夹
        url = QUrl.fromLocalFile(str(folder_path))
        success = QDesktopServices.openUrl(url)
        if not success:
            logger.error(f"Failed to open plugin folder: {folder_path}")
        return success

    @Slot(str, result=bool)
    def uninstallPlugin(self, pid: str) -> bool:
        """
        卸载指定外部插件
        """
        meta = next((m for m in self.metas if m["id"] == pid), None)
        if not meta:
            logger.warning(f"Plugin {pid} not found, cannot uninstall.")
            return False

        # 内置插件卸载不了
        if meta.get("_type") == "builtin":
            logger.warning(f"Plugin {pid} is builtin and cannot be uninstalled.")
            return False

        try:
            # 终止插件运行
            if pid in self._plugins:
                try:
                    self._plugins[pid].on_unload()
                except Exception as e:
                    logger.error(f"Error while unloading plugin {pid}: {e}")
                self._plugins.pop(pid, None)

            # 删除插件目录
            plugin_dir = Path(meta["_path"])
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
                logger.info(f"Uninstalled plugin {pid}, removed {plugin_dir}")

            # 移除 enabled
            self.enabled_plugins.discard(pid)
            self.app_central.configs.plugins.enabled = list(self.enabled_plugins)

            # 重新扫描插件列表
            self.scan()
            self.pluginListChanged.emit()
            return True
        except Exception as e:
            logger.exception(f"Failed to uninstall plugin {pid}: {e}")
            return False


