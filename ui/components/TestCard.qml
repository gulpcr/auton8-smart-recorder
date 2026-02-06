import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4

/**
 * TestCard - Card display for a single test case
 */
Rectangle {
    id: root
    
    // Properties
    property string testName: "Unnamed Test"
    property string testStatus: "draft"
    property var testTags: []
    property int testSteps: 0
    property string testUrl: ""
    property string testUpdated: ""
    property string testPath: ""
    property real testSuccessRate: 0.0
    property string testSuccessProjection: "unknown"
    
    // Signals
    signal clicked()
    signal edit()
    signal replay()
    signal duplicate()
    signal deleteTest()
    signal exportTest()
    signal upload()
    
    radius: 10
    color: cardMouseArea.containsMouse ? "#1a2a45" : "#16213e"
    border.color: cardMouseArea.containsMouse ? "#e94560" : "#1a2a45"
    border.width: 1

    Behavior on color {
        ColorAnimation { duration: 150 }
    }
    Behavior on border.color {
        ColorAnimation { duration: 150 }
    }

    // Status accent bar
    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 4
        radius: 2
        color: {
            switch(testStatus) {
                case "ready": return "#4ecca3"
                case "flaky": return "#ffc93c"
                case "broken": return "#c73e1d"
                default: return "#3a3a5a"
            }
        }
    }

    // Main content
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        anchors.leftMargin: 16
        spacing: 10

        // Header row
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            // Test name
            Text {
                text: testName
                font.pixelSize: 15
                font.bold: true
                color: "#e0e0e0"
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            // Status badge
            Rectangle {
                width: statusText.width + 12
                height: 20
                radius: 4
                color: {
                    switch(testStatus) {
                        case "ready": return "#1a3a2e"
                        case "flaky": return "#3a3a1a"
                        case "broken": return "#3a1a1a"
                        default: return "#2a2a3a"
                    }
                }
                border.width: 1
                border.color: {
                    switch(testStatus) {
                        case "ready": return "#4ecca3"
                        case "flaky": return "#ffc93c"
                        case "broken": return "#c73e1d"
                        default: return "#555"
                    }
                }

                Text {
                    id: statusText
                    anchors.centerIn: parent
                    text: testStatus.charAt(0).toUpperCase() + testStatus.slice(1)
                    font.pixelSize: 10
                    font.bold: true
                    color: {
                        switch(testStatus) {
                            case "ready": return "#4ecca3"
                            case "flaky": return "#ffc93c"
                            case "broken": return "#c73e1d"
                            default: return "#888"
                        }
                    }
                }
            }
            
            // More menu button
            Rectangle {
                width: 28
                height: 28
                radius: 14
                color: moreBtnMouseArea.containsMouse ? "#2a4a70" : "transparent"
                
                Text {
                    anchors.centerIn: parent
                    text: "\u22EE"  // ⋮
                    font.pixelSize: 18
                    color: "#e0e0e0"
                }
                
                MouseArea {
                    id: moreBtnMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        mouse.accepted = true
                        contextMenu.popup()
                    }
                }
                
                Menu {
                    id: contextMenu
                    
                    MenuItem {
                        text: "Duplicate"
                        onTriggered: root.duplicate()
                    }
                    MenuItem {
                        text: "Export Package"
                        onTriggered: root.exportTest()
                    }
                    MenuItem {
                        text: "Upload to Portal"
                        onTriggered: root.upload()
                    }
                    MenuSeparator {}
                    MenuItem {
                        text: "Delete"
                        onTriggered: root.deleteTest()
                    }
                }
            }
        }
        
        // Tags row
        Flow {
            Layout.fillWidth: true
            spacing: 4
            
            Repeater {
                model: testTags.slice(0, 3)  // Show max 3 tags
                
                Rectangle {
                    height: 20
                    width: tagText.width + 12
                    radius: 10
                    color: "#0f3460"
                    
                    Text {
                        id: tagText
                        anchors.centerIn: parent
                        text: "\uD83C\uDFF7\uFE0F " + modelData  // 🏷️
                        font.pixelSize: 11
                        color: "#aaa"
                    }
                }
            }
            
            Text {
                visible: testTags.length > 3
                text: "+" + (testTags.length - 3) + " more"
                font.pixelSize: 11
                color: "#666"
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        
        // URL
        Text {
            text: testUrl || "No base URL"
            font.pixelSize: 12
            color: "#666"
            elide: Text.ElideMiddle
            Layout.fillWidth: true
        }
        
        Item { Layout.fillHeight: true }
        
        // Footer row
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            // Step count badge
            Rectangle {
                width: stepsText.width + 10
                height: 22
                radius: 4
                color: "#0f3460"

                Text {
                    id: stepsText
                    anchors.centerIn: parent
                    text: testSteps + " steps"
                    font.pixelSize: 11
                    color: "#aaa"
                }
            }

            // Updated time
            Text {
                text: formatTimeAgo(testUpdated)
                font.pixelSize: 11
                color: "#666"
            }

            // Success rate (if available)
            Rectangle {
                visible: testSuccessRate > 0
                width: successText.width + 10
                height: 22
                radius: 4
                color: testSuccessRate >= 0.8 ? "#1a3a2e" : testSuccessRate >= 0.5 ? "#3a3a1a" : "#3a1a1a"

                Text {
                    id: successText
                    anchors.centerIn: parent
                    text: Math.round(testSuccessRate * 100) + "%"
                    font.pixelSize: 11
                    font.bold: true
                    color: testSuccessRate >= 0.8 ? "#4ecca3" : testSuccessRate >= 0.5 ? "#ffc93c" : "#c73e1d"
                }
            }

            Item { Layout.fillWidth: true }

            // Quick actions (visible on hover)
            Row {
                spacing: 4
                opacity: cardMouseArea.containsMouse ? 1 : 0.4

                Behavior on opacity {
                    NumberAnimation { duration: 150 }
                }

                IconButton {
                    icon: "\u25B6"  // ▶
                    tooltip: "Run Test"
                    onClicked: {
                        mouse.accepted = true
                        root.replay()
                    }
                }

                IconButton {
                    icon: "\u270E"  // ✎
                    tooltip: "Edit Test"
                    onClicked: {
                        mouse.accepted = true
                        root.edit()
                    }
                }
            }
        }
    }
    
    // Click area (excluding action buttons)
    MouseArea {
        id: cardMouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
        z: -1
    }
    
    // Helper to format time
    function formatTimeAgo(isoTime) {
        if (!isoTime) return "Never"
        var date = new Date(isoTime)
        var now = new Date()
        var diffMs = now - date
        var diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
        
        if (diffDays === 0) return "Today"
        if (diffDays === 1) return "Yesterday"
        if (diffDays < 7) return diffDays + "d ago"
        if (diffDays < 30) return Math.floor(diffDays / 7) + "w ago"
        if (diffDays < 365) return Math.floor(diffDays / 30) + "mo ago"
        return Math.floor(diffDays / 365) + "y ago"
    }
}
