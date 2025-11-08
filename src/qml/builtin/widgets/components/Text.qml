import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import RinUI


Text {
    id: text

    // font.family: [Configs.data.preferences.font, Utils.fontFamily]
    // font.weight: Configs.data.preferences.font_weight || 400

    font: {
        var f = AppCentral.getQFont(Configs.data.preferences.font, Utils.fontFamily)
        f.weight = Configs.data.preferences.font_weight || 600
        return f
    }
}