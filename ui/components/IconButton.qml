import QtQuick 6.4
import QtQuick.Controls 6.4

/**
 * IconButton - Small icon button with tooltip
 */
Rectangle {
    id: root
    
    property string icon: "\u2713"  // ✓
    property string tooltip: ""
    property alias mouse: mouseArea
    
    signal clicked(var mouse)
    
    width: 32
    height: 32
    radius: 6
    color: mouseArea.containsMouse ? "#2a4a70" : "#0f3460"
    
    Behavior on color {
        ColorAnimation { duration: 150 }
    }
    
    Text {
        anchors.centerIn: parent
        text: icon
        font.pixelSize: 14
        color: "#e0e0e0"
    }
    
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: (mouse) => root.clicked(mouse)
    }
    
    ToolTip {
        visible: mouseArea.containsMouse && tooltip !== ""
        text: tooltip
        delay: 500
    }
}
