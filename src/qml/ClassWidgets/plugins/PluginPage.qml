import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import RinUI
import Widgets

FluentPage {
    id: settingsLayout

    // 属性
    property string pluginId
    property var backend: PluginBackendBridge.get_backend(pluginId)


    spacing: 4
}
