import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4

ApplicationWindow {
    id: window
    width: 1100
    height: 700
    visible: true
    title: "Recorder"
    color: "#1a1a2e"

    property bool isRecording: false
    property bool isReplaying: false
    property int currentTab: 0
    property string selectedWorkflowPath: ""

    // Header
    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 60
        color: "#16213e"

        RowLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 16

            Text {
                text: "Recorder"
                font.pixelSize: 22
                font.bold: true
                color: "#e0e0e0"
            }

            // Tab buttons
            Row {
                spacing: 4
                Layout.leftMargin: 20

                TabButton {
                    text: "Record"
                    active: window.currentTab === 0
                    onClicked: window.currentTab = 0
                }
                TabButton {
                    text: "Replay"
                    active: window.currentTab === 1
                    onClicked: {
                        window.currentTab = 1
                        controller.refresh_workflow_list()
                    }
                }
            }

            Item { Layout.fillWidth: true }

            Text {
                id: statusLabel
                text: ""
                font.pixelSize: 13
                color: "#888"
            }
        }
    }

    // Tab button component
    component TabButton: Rectangle {
        property string text: ""
        property bool active: false
        signal clicked()

        width: 90
        height: 36
        radius: 6
        color: active ? "#e94560" : (mouseArea.containsMouse ? "#2a4a70" : "transparent")

        Text {
            anchors.centerIn: parent
            text: parent.text
            font.pixelSize: 14
            font.bold: active
            color: active ? "#fff" : "#aaa"
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
        }
    }

    // Record Tab
    Item {
        id: recordTab
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: window.currentTab === 0

        // URL input bar
        Rectangle {
            id: urlBar
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 16
            height: 56
            radius: 8
            color: "#16213e"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 6
                    color: "#0f3460"
                    border.color: urlInput.activeFocus ? "#e94560" : "#2a4a70"
                    border.width: 2

                    TextInput {
                        id: urlInput
                        anchors.fill: parent
                        anchors.margins: 12
                        font.pixelSize: 15
                        color: "#e0e0e0"
                        selectByMouse: true
                        verticalAlignment: TextInput.AlignVCenter
                        clip: true

                        Keys.onReturnPressed: {
                            if (text.trim()) {
                                controller.start_recording(text)
                                window.isRecording = true
                            }
                        }

                        Text {
                            anchors.fill: parent
                            verticalAlignment: Text.AlignVCenter
                            text: "Enter website URL (e.g., google.com)"
                            color: "#666"
                            font.pixelSize: 15
                            visible: !urlInput.text && !urlInput.activeFocus
                        }
                    }
                }

                Button {
                    id: recordBtn
                    text: window.isRecording ? "Stop" : "Record"
                    font.pixelSize: 14
                    font.bold: true
                    implicitWidth: 100
                    Layout.fillHeight: true

                    background: Rectangle {
                        radius: 6
                        color: window.isRecording ? "#c73e1d" : "#e94560"
                        opacity: recordBtn.hovered ? 0.9 : 1.0
                    }

                    contentItem: Text {
                        text: recordBtn.text
                        font: recordBtn.font
                        color: "#fff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    onClicked: {
                        if (window.isRecording) {
                            controller.stop_recording()
                            window.isRecording = false
                        } else if (urlInput.text.trim()) {
                            controller.start_recording(urlInput.text)
                            window.isRecording = true
                        }
                    }
                }
            }
        }

        // Main content
        RowLayout {
            anchors.top: urlBar.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 16
            anchors.topMargin: 8
            spacing: 16

            // Steps panel
            Rectangle {
                Layout.preferredWidth: 360
                Layout.fillHeight: true
                radius: 12
                color: "#16213e"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Recorded Steps"
                            font.pixelSize: 16
                            font.bold: true
                            color: "#e0e0e0"
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: timelineModel.rowCount() + " steps"
                            font.pixelSize: 12
                            color: "#888"
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 8
                        color: "#0f3460"

                        ListView {
                            id: timelineView
                            anchors.fill: parent
                            anchors.margins: 8
                            model: timelineModel
                            clip: true
                            spacing: 6

                            delegate: Rectangle {
                                width: timelineView.width - 16
                                height: 56
                                radius: 6
                                color: mouseArea.containsMouse ? "#1a4a80" : "#16213e"

                                MouseArea {
                                    id: mouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 10

                                    Rectangle {
                                        width: 32
                                        height: 32
                                        radius: 6
                                        color: {
                                            if (type === "click") return "#e94560"
                                            if (type === "input" || type === "change") return "#4ecca3"
                                            if (type === "keydown") return "#ffc93c"
                                            return "#7b68ee"
                                        }

                                        Text {
                                            anchors.centerIn: parent
                                            text: {
                                                if (type === "click") return "\u25CF"
                                                if (type === "input" || type === "change") return "\u270E"
                                                if (type === "keydown") return "\u2328"
                                                return "\u25A0"
                                            }
                                            font.pixelSize: 14
                                            color: "#fff"
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        Text {
                                            text: type.charAt(0).toUpperCase() + type.slice(1)
                                            font.pixelSize: 13
                                            font.bold: true
                                            color: "#e0e0e0"
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: target || "No target"
                                            font.pixelSize: 11
                                            color: "#888"
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }

                            Text {
                                anchors.centerIn: parent
                                visible: timelineModel.rowCount() === 0
                                text: "No steps recorded yet"
                                font.pixelSize: 14
                                color: "#666"
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Button {
                            Layout.fillWidth: true
                            text: "Save"
                            implicitHeight: 36

                            background: Rectangle {
                                radius: 6
                                color: parent.hovered ? "#2a4a70" : "#0f3460"
                            }

                            contentItem: Text {
                                text: parent.text
                                font.pixelSize: 13
                                color: "#e0e0e0"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }

                            onClicked: controller.save_workflow()
                        }

                        Button {
                            Layout.fillWidth: true
                            text: "Clear"
                            implicitHeight: 36

                            background: Rectangle {
                                radius: 6
                                color: parent.hovered ? "#3a2a40" : "#2a1a30"
                            }

                            contentItem: Text {
                                text: parent.text
                                font.pixelSize: 13
                                color: "#e0e0e0"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }

                            onClicked: controller.clear_timeline()
                        }
                    }
                }
            }

            // Instructions panel
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 12
                color: "#16213e"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 20

                    Text {
                        text: "How to Record"
                        font.pixelSize: 18
                        font.bold: true
                        color: "#e0e0e0"
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 14

                        InstructionStep { number: "1"; text: "Enter a website URL above" }
                        InstructionStep { number: "2"; text: "Click 'Record' to open browser" }
                        InstructionStep { number: "3"; text: "Interact with the website" }
                        InstructionStep { number: "4"; text: "Steps appear in left panel" }
                        InstructionStep { number: "5"; text: "Click 'Save' when done" }
                    }

                    Item { Layout.fillHeight: true }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 70
                        radius: 8
                        color: "#0f3460"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 12

                            Rectangle {
                                width: 42
                                height: 42
                                radius: 21
                                color: window.isRecording ? "#4ecca3" : "#666"

                                Text {
                                    anchors.centerIn: parent
                                    text: window.isRecording ? "\u25CF" : "\u25CB"
                                    font.pixelSize: 20
                                    color: "#fff"
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    text: window.isRecording ? "Recording Active" : "Ready"
                                    font.pixelSize: 14
                                    font.bold: true
                                    color: "#e0e0e0"
                                }
                                Text {
                                    text: window.isRecording ? "Interact with the browser" : "Enter URL and click Record"
                                    font.pixelSize: 12
                                    color: "#888"
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Replay Tab
    Item {
        id: replayTab
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 16
        visible: window.currentTab === 1

        RowLayout {
            anchors.fill: parent
            spacing: 16

            // Workflow list
            Rectangle {
                Layout.preferredWidth: 400
                Layout.fillHeight: true
                radius: 12
                color: "#16213e"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Saved Workflows"
                            font.pixelSize: 16
                            font.bold: true
                            color: "#e0e0e0"
                        }
                        Item { Layout.fillWidth: true }
                        Button {
                            text: "\u21BB"
                            implicitWidth: 36
                            implicitHeight: 28
                            background: Rectangle {
                                radius: 4
                                color: parent.hovered ? "#2a4a70" : "transparent"
                            }
                            contentItem: Text {
                                text: parent.text
                                font.pixelSize: 16
                                color: "#888"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            onClicked: controller.refresh_workflow_list()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 8
                        color: "#0f3460"

                        ListView {
                            id: workflowListView
                            anchors.fill: parent
                            anchors.margins: 8
                            model: workflowListModel
                            clip: true
                            spacing: 6

                            delegate: Rectangle {
                                width: workflowListView.width - 16
                                height: 70
                                radius: 8
                                color: window.selectedWorkflowPath === path ? "#e94560" : (wfMouseArea.containsMouse ? "#1a4a80" : "#16213e")
                                border.color: window.selectedWorkflowPath === path ? "#e94560" : "#2a4a70"
                                border.width: 1

                                MouseArea {
                                    id: wfMouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: window.selectedWorkflowPath = path
                                    onDoubleClicked: {
                                        window.selectedWorkflowPath = path
                                        controller.start_replay(path)
                                        window.isReplaying = true
                                    }
                                }

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 4

                                    Text {
                                        text: filename
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                    }
                                    Text {
                                        text: stepCount + " steps"
                                        font.pixelSize: 12
                                        color: window.selectedWorkflowPath === path ? "#fff" : "#888"
                                    }
                                    Text {
                                        text: baseUrl || "No base URL"
                                        font.pixelSize: 11
                                        color: window.selectedWorkflowPath === path ? "#ddd" : "#666"
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                }
                            }

                            Text {
                                anchors.centerIn: parent
                                visible: workflowListModel.rowCount() === 0
                                text: "No saved workflows\nRecord a session first"
                                font.pixelSize: 14
                                color: "#666"
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }
            }

            // Replay controls
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 12
                color: "#16213e"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 20

                    Text {
                        text: "Replay Controls"
                        font.pixelSize: 18
                        font.bold: true
                        color: "#e0e0e0"
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 100
                        radius: 8
                        color: "#0f3460"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8

                            Text {
                                text: window.selectedWorkflowPath ? "Selected:" : "No workflow selected"
                                font.pixelSize: 13
                                color: "#888"
                            }
                            Text {
                                text: window.selectedWorkflowPath ? window.selectedWorkflowPath.split("/").pop() : "Select a workflow from the list"
                                font.pixelSize: 14
                                font.bold: true
                                color: "#e0e0e0"
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: window.isReplaying ? "Stop Replay" : "Start Replay"
                        implicitHeight: 50
                        enabled: window.selectedWorkflowPath || window.isReplaying

                        background: Rectangle {
                            radius: 8
                            color: {
                                if (!parent.enabled) return "#333"
                                if (window.isReplaying) return "#c73e1d"
                                return parent.hovered ? "#d63e5c" : "#e94560"
                            }
                        }

                        contentItem: Text {
                            text: parent.text
                            font.pixelSize: 16
                            font.bold: true
                            color: parent.enabled ? "#fff" : "#666"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }

                        onClicked: {
                            if (window.isReplaying) {
                                controller.stop_replay()
                                window.isReplaying = false
                            } else if (window.selectedWorkflowPath) {
                                controller.start_replay(window.selectedWorkflowPath)
                                window.isReplaying = true
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 70
                        radius: 8
                        color: "#0f3460"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 12

                            Rectangle {
                                width: 42
                                height: 42
                                radius: 21
                                color: window.isReplaying ? "#4ecca3" : "#666"

                                Text {
                                    anchors.centerIn: parent
                                    text: window.isReplaying ? "\u25B6" : "\u25A0"
                                    font.pixelSize: 18
                                    color: "#fff"
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    text: window.isReplaying ? "Replaying..." : "Idle"
                                    font.pixelSize: 14
                                    font.bold: true
                                    color: "#e0e0e0"
                                }
                                Text {
                                    text: window.isReplaying ? "Browser automation in progress" : "Select a workflow and click Start"
                                    font.pixelSize: 12
                                    color: "#888"
                                }
                            }
                        }
                    }

                    Text {
                        text: "Tip: Double-click a workflow to replay it instantly"
                        font.pixelSize: 12
                        color: "#666"
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
        }
    }

    // Instruction step component
    component InstructionStep: RowLayout {
        property string number: "1"
        property string text: ""
        spacing: 12

        Rectangle {
            width: 26
            height: 26
            radius: 13
            color: "#e94560"

            Text {
                anchors.centerIn: parent
                text: parent.parent.number
                font.pixelSize: 13
                font.bold: true
                color: "#fff"
            }
        }

        Text {
            Layout.fillWidth: true
            text: parent.text
            font.pixelSize: 14
            color: "#ccc"
        }
    }

    Connections {
        target: controller
        function onStatusMessage(msg) { statusLabel.text = msg }
        function onReplayStateChanged(running) { window.isReplaying = running }
    }
}
