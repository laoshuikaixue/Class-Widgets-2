import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import RinUI


Text {
    id: text
    // font.pixelSize: 16
    // font.weight: 600
    opacity: 0.6

    font: {
        var f = AppCentral.getQFont(Configs.data.preferences.font, Utils.fontFamily)
        f.pixelSize = 16
        f.weight = Configs.data.preferences.font_weight || 600
        return f
    }
}