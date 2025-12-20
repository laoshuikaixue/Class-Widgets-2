import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import RinUI
import ClassWidgets.Components


ApplicationWindow {
    id: whatsNewWindow
    icon: PathManager.assets("images/icons/cw2_settings.png")
    title: qsTr("What's New ╰(*°▽°*)╯")
    width: Screen.width * 0.4
    height: Screen.height * 0.5

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 32
        anchors.topMargin: 16
        anchors.bottomMargin: 48


        ColumnLayout {
            Layout.alignment: Qt.AlignHCenter | Qt.AlignCenter
            Icon {
                Layout.alignment: Qt.AlignHCenter
                source: PathManager.images("logo.png")
                size: 72
            }
            Text {
                Layout.fillWidth: true
                typography: Typography.Subtitle
                horizontalAlignment: Text.AlignHCenter
                text: qsTr("Let's see what's new in " + Configs.data.app.version)
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Icon {
                name: "ic_fluent_code_20_regular"
                size: 32
            }
            Text {
                text: qsTr("Under development")
                font.pixelSize: 24
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter | Qt.AlignBottom
            Button {
                highlighted: true
                text: qsTr("Get started")
                onClicked: {
                    whatsNewWindow.hide()
                }
            }
        }
    }

    // 测试水印
    Watermark {
        anchors.centerIn: parent
    }
}