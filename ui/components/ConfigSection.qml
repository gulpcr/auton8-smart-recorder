import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4
import QtQuick.Effects

/**
 * ConfigSection - Collapsible section for grouping step configuration options
 *
 * Usage:
 *   ConfigSection {
 *       title: "Execution Settings"
 *       icon: "\u23F1"
 *       summary: "Timeout: 30s, Retries: 0"
 *       importance: "optional"  // "required", "recommended", "optional"
 *       expanded: false
 *       showHelpButton: true
 *       onHelpClicked: helpPopup.open()
 *
 *       ConfigRow { ... }
 *   }
 */
Rectangle {
    id: root

    property string title: "Section"
    property string icon: ""
    property string summary: ""  // Shows when collapsed
    property string importance: "optional"  // required, recommended, optional
    property color accentColor: "#3b82f6"
    property bool expanded: false
    property bool showHelpButton: false
    property alias contentItem: contentColumn
    default property alias content: contentColumn.data

    signal helpClicked()

    width: parent ? parent.width : 300
    height: headerRow.height + (expanded ? contentColumn.height + 16 : 0)
    color: "transparent"
    clip: true

    Behavior on height {
        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
    }

    // Importance colors
    function getImportanceColor() {
        switch (importance) {
            case "required": return "#ef4444"  // Red
            case "recommended": return "#f59e0b"  // Amber
            default: return "transparent"
        }
    }

    function getImportanceLabel() {
        switch (importance) {
            case "required": return "Required"
            case "recommended": return "Recommended"
            default: return ""
        }
    }

    // Header
    Rectangle {
        id: headerRow
        width: parent.width
        height: 44
        radius: 8
        color: headerMouse.containsMouse ? "#1e293b" : "#0f172a"
        border.color: root.expanded ? root.accentColor + "60" : (headerMouse.containsMouse ? "#334155" : "#1e293b")
        border.width: root.expanded ? 2 : 1

        Behavior on color { ColorAnimation { duration: 150 } }
        Behavior on border.color { ColorAnimation { duration: 150 } }

        // Left accent bar when expanded
        Rectangle {
            visible: root.expanded
            width: 3
            height: parent.height - 12
            anchors.left: parent.left
            anchors.leftMargin: 4
            anchors.verticalCenter: parent.verticalCenter
            radius: 2
            color: root.accentColor
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 10
            spacing: 8

            // Expand icon
            Text {
                text: "\u25B6"
                font.pixelSize: 10
                color: root.expanded ? root.accentColor : "#64748b"
                rotation: root.expanded ? 90 : 0
                Layout.alignment: Qt.AlignVCenter

                Behavior on rotation { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                Behavior on color { ColorAnimation { duration: 200 } }
            }

            // Section icon
            Rectangle {
                visible: root.icon !== ""
                Layout.preferredWidth: 24
                Layout.preferredHeight: 24
                Layout.alignment: Qt.AlignVCenter
                radius: 6
                color: root.accentColor + "20"

                Text {
                    anchors.centerIn: parent
                    text: root.icon
                    font.pixelSize: 12
                    color: root.accentColor
                }
            }

            // Title
            Text {
                text: root.title
                font.pixelSize: 13
                font.weight: Font.DemiBold
                color: root.expanded ? "#f1f5f9" : "#e2e8f0"
                Layout.alignment: Qt.AlignVCenter
            }

            // Help button - INLINE with title
            Rectangle {
                visible: root.showHelpButton
                Layout.preferredWidth: 20
                Layout.preferredHeight: 20
                Layout.alignment: Qt.AlignVCenter
                radius: 10
                color: helpBtnMouse.containsMouse ? root.accentColor : root.accentColor + "30"
                border.color: root.accentColor
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "?"
                    font.pixelSize: 12
                    font.bold: true
                    color: helpBtnMouse.containsMouse ? "#ffffff" : root.accentColor
                }

                MouseArea {
                    id: helpBtnMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.helpClicked()
                }
            }

            // Importance badge
            Rectangle {
                visible: root.importance !== "optional"
                Layout.preferredWidth: importanceText.width + 10
                Layout.preferredHeight: 16
                Layout.alignment: Qt.AlignVCenter
                radius: 8
                color: getImportanceColor() + "20"
                border.color: getImportanceColor()
                border.width: 1

                Text {
                    id: importanceText
                    anchors.centerIn: parent
                    text: getImportanceLabel()
                    font.pixelSize: 9
                    font.weight: Font.Medium
                    color: getImportanceColor()
                }
            }

            // Spacer
            Item { Layout.fillWidth: true }

            // Summary text when collapsed
            Text {
                visible: !root.expanded && root.summary !== ""
                text: root.summary
                font.pixelSize: 11
                color: "#64748b"
                elide: Text.ElideRight
                Layout.alignment: Qt.AlignVCenter
                Layout.maximumWidth: 200
            }

            // Settings count badge when expanded
            Rectangle {
                visible: root.expanded && contentColumn.children.length > 0
                Layout.preferredWidth: countText.width + 12
                Layout.preferredHeight: 20
                Layout.alignment: Qt.AlignVCenter
                radius: 10
                color: "#1e293b"
                border.color: "#334155"
                border.width: 1

                Text {
                    id: countText
                    anchors.centerIn: parent
                    text: contentColumn.children.length + " settings"
                    font.pixelSize: 10
                    color: "#64748b"
                }
            }
        }

        MouseArea {
            id: headerMouse
            anchors.fill: parent
            anchors.rightMargin: root.showHelpButton ? 40 : 0
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.expanded = !root.expanded
        }
    }

    // Content area
    Rectangle {
        id: contentWrapper
        anchors.top: headerRow.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.leftMargin: 12
        anchors.right: parent.right
        anchors.rightMargin: 4
        height: contentColumn.height + 8
        color: "transparent"
        visible: expanded
        opacity: expanded ? 1.0 : 0.0

        Behavior on opacity {
            NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
        }

        // Left connector line
        Rectangle {
            width: 1
            height: contentColumn.height
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.topMargin: 4
            color: root.accentColor + "40"
        }

        Column {
            id: contentColumn
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.right: parent.right
            anchors.rightMargin: 4
            spacing: 4
        }
    }
}
