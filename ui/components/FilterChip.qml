import QtQuick 6.4
import QtQuick.Controls 6.4

/**
 * FilterChip - Clickable filter chip with badge count
 */
Rectangle {
    id: root

    property string text: ""
    property bool active: false
    property int count: 0
    property color chipColor: "#e94560"

    signal clicked()

    implicitWidth: chipContent.width + 16
    implicitHeight: 28
    radius: 6
    color: active ? Qt.darker(root.chipColor, 2.5) : (mouseArea.containsMouse ? "#1a2a45" : "#0f3460")
    border.color: active ? root.chipColor : "transparent"
    border.width: active ? 1 : 0

    Behavior on color {
        ColorAnimation { duration: 150 }
    }

    Row {
        id: chipContent
        anchors.centerIn: parent
        spacing: 6

        Text {
            text: root.text
            font.pixelSize: 11
            font.bold: active
            color: active ? root.chipColor : "#999"
            anchors.verticalCenter: parent.verticalCenter
        }

        Rectangle {
            width: 18
            height: 18
            radius: 9
            color: active ? root.chipColor : "#1a2a45"
            visible: count > 0
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: count
                font.pixelSize: 9
                font.bold: true
                color: active ? "#fff" : "#888"
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
