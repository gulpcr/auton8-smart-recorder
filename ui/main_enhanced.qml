import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4
import "components"

ApplicationWindow {
    id: window
    width: 1400
    height: 900
    visible: true
    title: "Auton8 Capture Pro"
    color: "#1a1a2e"

    property bool isRecording: false
    property bool isReplaying: false
    property int currentTab: 0
    property string selectedWorkflowPath: ""
    property bool isEditMode: false  // True when editing existing test from Library
    property string editingWorkflowPath: ""  // Path of test being edited
    property string pendingTestName: ""  // Name entered in New Test dialog

    // Header with tabs
    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 70
        color: "#16213e"

        RowLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 20

            // Logo/Title
            Text {
                text: "Auton8 Capture Pro"
                font.pixelSize: 22
                font.bold: true
                color: "#e0e0e0"
            }

            // Tab buttons
            Row {
                spacing: 8
                Layout.leftMargin: 40

                TabButton {
                    text: "📚 Library"
                    active: window.currentTab === 0
                    onClicked: {
                        window.currentTab = 0
                        controller.refresh_workflow_list()
                    }
                }
                TabButton {
                    text: "⚫ Record"
                    active: window.currentTab === 1
                    onClicked: {
                        // Only clear when coming from a different tab (not already on Record)
                        var wasOnDifferentTab = (window.currentTab !== 1)
                        window.currentTab = 1
                        if (wasOnDifferentTab) {
                            window.isEditMode = false
                            window.editingWorkflowPath = ""
                            // Defer clearing until after tab switch completes
                            Qt.callLater(function() {
                                urlInput.text = ""
                                timelineModel.clear()
                            })
                        }
                    }
                }
                TabButton {
                    text: "▶️ Replay"
                    active: window.currentTab === 2
                    onClicked: {
                        window.currentTab = 2
                        controller.refresh_workflow_list()
                    }
                }
                TabButton {
                    text: "📊 Runs"
                    active: window.currentTab === 3
                    onClicked: {
                        window.currentTab = 3
                        if (executionHistoryModel) {
                            executionHistoryModel.load_history()
                        }
                    }
                }
                TabButton {
                    text: "🧠 ML"
                    active: window.currentTab === 4
                    onClicked: {
                        window.currentTab = 4
                        controller.update_ml_stats()
                    }
                }
                TabButton {
                    text: "⚙ Settings"
                    active: window.currentTab === 5
                    onClicked: {
                        window.currentTab = 5
                    }
                }
            }

            Item { Layout.fillWidth: true }
            
            // ML Status indicator
            Rectangle {
                width: 120
                height: 36
                radius: 18
                color: "#0f3460"
                visible: true
                
                Row {
                    anchors.centerIn: parent
                    spacing: 8
                    
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: "#4ecca3"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    
                    Text {
                        text: "ML Active"
                        font.pixelSize: 12
                        color: "#aaa"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }

            // Status message
            Text {
                id: statusLabel
                text: ""
                font.pixelSize: 13
                color: "#888"
                Layout.preferredWidth: 300
                elide: Text.ElideRight
            }
        }
    }

    // Main content area
    StackLayout {
        id: contentStack
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        currentIndex: window.currentTab

        // Tab 0: Test Library
        Item {
            TestLibrary {
                anchors.fill: parent
                anchors.margins: 20
                
                onCreateNewTest: newTestWizard.open()
                
                onTestSelected: (path) => {
                    window.selectedWorkflowPath = path
                }
                
                onTestEdit: (path) => {
                    controller.load_workflow(path)
                    window.currentTab = 1
                }
                
                onTestReplay: (path) => {
                    window.selectedWorkflowPath = path
                    controller.start_replay(path)
                    window.isReplaying = true
                    window.currentTab = 2
                }
                
                onTestDuplicate: (path) => {
                    statusLabel.text = "Duplicate feature coming soon..."
                }
                
                onTestDelete: (path) => {
                    deleteConfirmDialog.workflowPath = path
                    deleteConfirmDialog.open()
                }
                
                onExportTest: (path) => {
                    statusLabel.text = "Export feature coming soon..."
                }
                
                onUploadTest: (path) => {
                    statusLabel.text = "Portal upload feature coming soon..."
                }
            }
        }

        // Tab 1: Record
        Item {
            id: recordTab

            // Recording status banner (visible when recording)
            Rectangle {
                id: recordingBanner
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: 20
                height: window.isRecording ? 44 : 0
                radius: 8
                color: "#c73e1d"
                visible: window.isRecording
                clip: true

                Behavior on height {
                    NumberAnimation { duration: 200; easing.type: Easing.OutQuad }
                }

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 12

                    // Pulsing recording dot
                    Rectangle {
                        width: 12
                        height: 12
                        radius: 6
                        color: "#fff"

                        SequentialAnimation on opacity {
                            running: window.isRecording
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.3; duration: 500 }
                            NumberAnimation { to: 1.0; duration: 500 }
                        }
                    }

                    Text {
                        text: "RECORDING IN PROGRESS"
                        font.pixelSize: 13
                        font.bold: true
                        font.letterSpacing: 1
                        color: "#fff"
                    }

                    Text {
                        text: "•"
                        font.pixelSize: 13
                        color: "#ffb3b3"
                    }

                    Text {
                        text: "Interact with the browser to capture steps"
                        font.pixelSize: 12
                        color: "#ffb3b3"
                    }
                }
            }

            // URL input bar
            Rectangle {
                id: configBar
                anchors.top: recordingBanner.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: 20
                anchors.topMargin: window.isRecording ? 8 : 20
                height: 60
                radius: 10
                color: "#16213e"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12

                    Text {
                        text: "Test URL"
                        font.pixelSize: 12
                        font.bold: true
                        color: "#888"
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 6
                        color: window.isRecording ? "#1a2a40" : "#0f3460"
                        border.color: urlInput.activeFocus ? "#e94560" : "#2a4a70"
                        border.width: 1

                        TextInput {
                            id: urlInput
                            anchors.fill: parent
                            anchors.margins: 12
                            font.pixelSize: 14
                            color: window.isRecording ? "#888" : "#e0e0e0"
                            selectByMouse: true
                            verticalAlignment: TextInput.AlignVCenter
                            clip: true
                            readOnly: window.isRecording

                            Keys.onReturnPressed: {
                                if (text.trim() && !window.isRecording) {
                                    controller.start_recording(text)
                                    window.isRecording = true
                                }
                            }

                            Text {
                                anchors.fill: parent
                                verticalAlignment: Text.AlignVCenter
                                text: "https://example.com"
                                color: "#555"
                                font.pixelSize: 14
                                visible: !urlInput.text && !urlInput.activeFocus
                            }
                        }

                        // Lock icon when recording
                        Text {
                            anchors.right: parent.right
                            anchors.rightMargin: 10
                            anchors.verticalCenter: parent.verticalCenter
                            text: "🔒"
                            font.pixelSize: 12
                            visible: window.isRecording
                        }
                    }

                    Button {
                        id: recordBtn
                        text: window.isRecording ? "◼ Stop" : "● Record"
                        font.pixelSize: 13
                        font.bold: true
                        implicitWidth: 100
                        implicitHeight: 36
                        enabled: window.isRecording || urlInput.text.trim().length > 0

                        ToolTip.visible: recordBtn.hovered
                        ToolTip.text: window.isRecording ? "Stop recording and review captured steps" : "Start browser and begin capturing actions"
                        ToolTip.delay: 500

                        background: Rectangle {
                            radius: 6
                            color: {
                                if (!recordBtn.enabled) return "#2a2a3a"
                                if (window.isRecording) return "#c73e1d"
                                return recordBtn.hovered ? "#d63e5c" : "#e94560"
                            }
                        }

                        contentItem: Text {
                            text: recordBtn.text
                            font: recordBtn.font
                            color: recordBtn.enabled ? "#fff" : "#555"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }

                        onClicked: {
                            if (window.isRecording) {
                                controller.stop_recording()
                                window.isRecording = false
                            } else if (urlInput.text.trim()) {
                                // Use pendingTestName if available, otherwise generate one
                                if (window.pendingTestName.trim().length > 0) {
                                    controller.create_new_test(window.pendingTestName, urlInput.text)
                                    window.pendingTestName = ""  // Clear after use
                                } else {
                                    controller.start_recording(urlInput.text)
                                }
                                window.isEditMode = false
                                window.editingWorkflowPath = ""
                                window.isRecording = true
                            }
                        }
                    }

                    // Replay button (only in edit mode)
                    Button {
                        id: replayBtn
                        text: "▶ Replay"
                        font.pixelSize: 13
                        font.bold: true
                        implicitWidth: 90
                        implicitHeight: 36
                        visible: window.isEditMode && !window.isRecording
                        enabled: timelineModel.count > 0

                        background: Rectangle {
                            radius: 6
                            color: replayBtn.enabled ? (replayBtn.hovered ? "#3a8a80" : "#4ecca3") : "#2a2a3a"
                        }

                        contentItem: Text {
                            text: replayBtn.text
                            font: replayBtn.font
                            color: replayBtn.enabled ? "#fff" : "#555"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }

                        onClicked: {
                            if (window.editingWorkflowPath) {
                                controller.start_replay(window.editingWorkflowPath)
                            }
                        }
                    }
                }
            }

            // Main content
            RowLayout {
                anchors.top: configBar.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 20
                anchors.topMargin: 12
                spacing: 16

                // Steps panel
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
                            spacing: 10

                            Text {
                                text: "Captured Steps"
                                font.pixelSize: 16
                                font.bold: true
                                color: "#e0e0e0"
                            }

                            Rectangle {
                                width: 28
                                height: 22
                                radius: 11
                                color: timelineModel.count > 0 ? "#4ecca3" : "#3a3a5a"
                                visible: true

                                Text {
                                    anchors.centerIn: parent
                                    text: timelineModel.count
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: "#fff"
                                }
                            }

                            Item { Layout.fillWidth: true }

                            // Live indicator when recording
                            Row {
                                spacing: 6
                                visible: window.isRecording

                                Rectangle {
                                    width: 8
                                    height: 8
                                    radius: 4
                                    color: "#e94560"
                                    anchors.verticalCenter: parent.verticalCenter

                                    SequentialAnimation on opacity {
                                        running: window.isRecording
                                        loops: Animation.Infinite
                                        NumberAnimation { to: 0.3; duration: 400 }
                                        NumberAnimation { to: 1.0; duration: 400 }
                                    }
                                }

                                Text {
                                    text: "LIVE"
                                    font.pixelSize: 10
                                    font.bold: true
                                    font.letterSpacing: 1
                                    color: "#e94560"
                                    anchors.verticalCenter: parent.verticalCenter
                                }
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

                                // Property to track drag state
                                property int draggedIndex: -1

                                delegate: Item {
                                    id: delegateRoot
                                    width: timelineView.width - 16
                                    height: 58

                                    // Drop area for reordering
                                    DropArea {
                                        anchors.fill: parent
                                        keys: ["timelineStep"]

                                        onEntered: function(drag) {
                                            if (timelineView.draggedIndex !== index && timelineView.draggedIndex >= 0) {
                                                timelineModel.moveStep(timelineView.draggedIndex, index)
                                                timelineView.draggedIndex = index
                                            }
                                        }
                                    }

                                    Rectangle {
                                        id: stepDelegate
                                        width: parent.width
                                        height: 58
                                        radius: 6
                                        color: dragArea.drag.active ? "#2a5a90" : (stepMouseArea.containsMouse ? "#1a4a80" : "#192a45")
                                        border.width: 1
                                        border.color: dragArea.drag.active ? "#4ecca3" : (stepMouseArea.containsMouse ? "#2a5a90" : "transparent")

                                        Drag.active: dragArea.drag.active
                                        Drag.keys: ["timelineStep"]
                                        Drag.hotSpot.x: width / 2
                                        Drag.hotSpot.y: height / 2

                                        // Drag handle
                                        Rectangle {
                                            id: dragHandle
                                            width: 20
                                            height: parent.height - 8
                                            anchors.left: parent.left
                                            anchors.leftMargin: 2
                                            anchors.verticalCenter: parent.verticalCenter
                                            radius: 3
                                            color: dragArea.containsMouse ? "#2a4a70" : "transparent"

                                            Column {
                                                anchors.centerIn: parent
                                                spacing: 3
                                                Repeater {
                                                    model: 3
                                                    Rectangle {
                                                        width: 12
                                                        height: 2
                                                        radius: 1
                                                        color: "#555"
                                                    }
                                                }
                                            }

                                            MouseArea {
                                                id: dragArea
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.SizeAllCursor
                                                drag.target: stepDelegate
                                                drag.axis: Drag.YAxis

                                                onPressed: {
                                                    timelineView.draggedIndex = index
                                                    stepDelegate.z = 100
                                                }

                                                onReleased: {
                                                    stepDelegate.x = 0
                                                    stepDelegate.y = 0
                                                    stepDelegate.z = 1
                                                    timelineView.draggedIndex = -1
                                                }
                                            }
                                        }

                                        // Left accent bar
                                        Rectangle {
                                            width: 3
                                            height: parent.height - 8
                                            anchors.left: dragHandle.right
                                            anchors.leftMargin: 2
                                            anchors.verticalCenter: parent.verticalCenter
                                            radius: 2
                                            color: {
                                                if (type === "click") return "#e94560"
                                                if (type === "input" || type === "change") return "#4ecca3"
                                                if (type === "keydown" || type === "keyup") return "#ffc93c"
                                                if (type === "submit") return "#7b68ee"
                                                return "#5a5a7a"
                                            }
                                        }

                                        // Animated entrance
                                        opacity: 0
                                        Component.onCompleted: {
                                            opacity = 1
                                        }
                                        Behavior on opacity {
                                            NumberAnimation { duration: 200 }
                                        }

                                        MouseArea {
                                            id: stepMouseArea
                                            anchors.fill: parent
                                            anchors.leftMargin: 24
                                            hoverEnabled: true
                                        }

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 30
                                            anchors.rightMargin: 10
                                            anchors.topMargin: 8
                                            anchors.bottomMargin: 8
                                        spacing: 10

                                        // Step number
                                        Text {
                                            text: (index + 1).toString().padStart(2, '0')
                                            font.pixelSize: 11
                                            font.family: "Consolas"
                                            color: "#666"
                                            Layout.preferredWidth: 20
                                        }

                                        // Type icon
                                        Rectangle {
                                            width: 32
                                            height: 32
                                            radius: 6
                                            color: {
                                                if (type === "click") return "#3d1a25"
                                                if (type === "input" || type === "change") return "#1a3d2e"
                                                if (type === "keydown" || type === "keyup") return "#3d3a1a"
                                                if (type === "submit") return "#2a1a3d"
                                                return "#2a2a3d"
                                            }

                                            Text {
                                                anchors.centerIn: parent
                                                text: {
                                                    if (type === "click") return "👆"
                                                    if (type === "input") return "⌨"
                                                    if (type === "change") return "✏"
                                                    if (type === "keydown" || type === "keyup") return "⎄"
                                                    if (type === "submit") return "📤"
                                                    return "▪"
                                                }
                                                font.pixelSize: 14
                                            }
                                        }

                                        // Step info
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 2

                                            RowLayout {
                                                spacing: 8

                                                Text {
                                                    text: {
                                                        var t = type.charAt(0).toUpperCase() + type.slice(1)
                                                        if (t === "Keydown") return "Key Press"
                                                        if (t === "Keyup") return "Key Release"
                                                        return t
                                                    }
                                                    font.pixelSize: 13
                                                    font.bold: true
                                                    color: "#e0e0e0"
                                                }

                                                // Type badge
                                                Rectangle {
                                                    width: typeBadgeText.width + 8
                                                    height: 16
                                                    radius: 3
                                                    color: {
                                                        if (type === "click") return "#e94560"
                                                        if (type === "input" || type === "change") return "#4ecca3"
                                                        if (type === "keydown" || type === "keyup") return "#ffc93c"
                                                        if (type === "submit") return "#7b68ee"
                                                        return "#5a5a7a"
                                                    }
                                                    opacity: 0.8

                                                    Text {
                                                        id: typeBadgeText
                                                        anchors.centerIn: parent
                                                        text: type.toUpperCase()
                                                        font.pixelSize: 9
                                                        font.bold: true
                                                        color: "#fff"
                                                    }
                                                }
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: target || "—"
                                                font.pixelSize: 11
                                                font.family: "Consolas"
                                                color: "#777"
                                                elide: Text.ElideMiddle
                                            }
                                        }

                                        // Action buttons (visible on hover)
                                        Row {
                                            spacing: 4
                                            opacity: stepMouseArea.containsMouse ? 1 : 0

                                            Behavior on opacity {
                                                NumberAnimation { duration: 150 }
                                            }

                                            // Edit step button
                                            Rectangle {
                                                width: 24
                                                height: 24
                                                radius: 4
                                                color: editBtnMouse.containsMouse ? "#ffc93c" : "#0f3460"

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "✎"
                                                    font.pixelSize: 12
                                                    color: "#fff"
                                                }

                                                MouseArea {
                                                    id: editBtnMouse
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        timelineEditDialog.stepIndex = index
                                                        timelineEditDialog.stepType = type
                                                        timelineEditDialog.stepTarget = target
                                                        timelineEditDialog.open()
                                                    }
                                                }
                                            }

                                            // Add step button (subtle secondary action)
                                            Rectangle {
                                                width: 20
                                                height: 20
                                                radius: 3
                                                color: addBtnMouse.containsMouse ? "#2a4a50" : "transparent"
                                                border.width: addBtnMouse.containsMouse ? 1 : 0
                                                border.color: "#4ecca3"
                                                opacity: stepMouseArea.containsMouse || addBtnMouse.containsMouse ? 1.0 : 0.4

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "+"
                                                    font.pixelSize: 12
                                                    color: addBtnMouse.containsMouse ? "#4ecca3" : "#666"
                                                }

                                                MouseArea {
                                                    id: addBtnMouse
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        timelineAddMenu.stepIndex = index
                                                        timelineAddMenu.open()
                                                    }
                                                }
                                            }

                                            // Delete step button (subtle secondary action)
                                            Rectangle {
                                                width: 20
                                                height: 20
                                                radius: 3
                                                color: delBtnMouse.containsMouse ? "#3a2a35" : "transparent"
                                                border.width: delBtnMouse.containsMouse ? 1 : 0
                                                border.color: "#e94560"
                                                opacity: stepMouseArea.containsMouse || delBtnMouse.containsMouse ? 1.0 : 0.4

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "×"
                                                    font.pixelSize: 14
                                                    color: delBtnMouse.containsMouse ? "#e94560" : "#666"
                                                }

                                                MouseArea {
                                                    id: delBtnMouse
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        timelineDeleteDialog.stepIndex = index
                                                        timelineDeleteDialog.stepType = type
                                                        timelineDeleteDialog.open()
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    }
                                }

                                // Empty state
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 10
                                    visible: timelineModel.count === 0
                                    width: parent.width - 40

                                    Text {
                                        text: window.isRecording ? "Waiting for Actions" : "No steps recorded yet"
                                        font.pixelSize: 14
                                        font.bold: true
                                        color: "#888"
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }

                                    Text {
                                        text: window.isRecording
                                            ? "Recording is active. Interact with the browser window to capture clicks, inputs, and navigation. Steps will appear here in real time."
                                            : "Steps will appear here in real time once recording starts.\n\nEnter a Test URL above, then click Record to begin."
                                        font.pixelSize: 12
                                        color: "#666"
                                        horizontalAlignment: Text.AlignHCenter
                                        wrapMode: Text.WordWrap
                                        width: parent.width
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Button {
                                id: saveBtn
                                Layout.fillWidth: true
                                implicitHeight: 38
                                enabled: timelineModel.count > 0

                                ToolTip.visible: saveBtn.hovered && !saveBtn.enabled
                                ToolTip.text: "Record at least one step to enable Save"
                                ToolTip.delay: 300

                                background: Rectangle {
                                    radius: 6
                                    color: parent.enabled ? (saveBtn.hovered ? "#3a8a80" : "#4ecca3") : "#2a2a3a"
                                }

                                contentItem: Row {
                                    anchors.centerIn: parent
                                    spacing: 6

                                    Text {
                                        text: "Save Test"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: saveBtn.enabled ? "#fff" : "#555"
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }

                                onClicked: {
                                    controller.save_workflow()
                                }
                            }

                            Button {
                                id: clearBtn
                                Layout.preferredWidth: 80
                                implicitHeight: 38
                                enabled: timelineModel.count > 0

                                background: Rectangle {
                                    radius: 6
                                    color: parent.enabled ? (clearBtn.hovered ? "#e94560" : "#3a2a35") : "#2a2a3a"
                                    border.width: parent.enabled ? 1 : 0
                                    border.color: "#e94560"
                                }

                                contentItem: Text {
                                    text: "Revert"
                                    font.pixelSize: 13
                                    color: clearBtn.enabled ? "#e94560" : "#555"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }

                                ToolTip.visible: clearBtn.hovered
                                ToolTip.text: "Revert to last saved version"
                                ToolTip.delay: 500

                                onClicked: {
                                    timelineModel.clearChanges()
                                }
                            }
                        }
                    }
                }

                // Instructions panel (right side)
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 12
                    color: "#16213e"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 30
                        spacing: 24

                        // Edit Mode indicator (only when editing existing test)
                        Rectangle {
                            Layout.fillWidth: true
                            height: 50
                            radius: 8
                            color: "#1a3a2e"
                            border.width: 1
                            border.color: "#4ecca3"
                            visible: window.isEditMode

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10

                                Rectangle {
                                    width: 8
                                    height: 8
                                    radius: 4
                                    color: "#4ecca3"
                                }

                                Text {
                                    text: "Editing existing test"
                                    font.pixelSize: 13
                                    font.bold: true
                                    color: "#4ecca3"
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    text: "Changes will update the original"
                                    font.pixelSize: 11
                                    color: "#6a9"
                                }
                            }
                        }

                        // New Test button (only show when editing or has steps - to start fresh)
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            visible: window.isEditMode || timelineModel.count > 0

                            Text {
                                text: "Start Fresh"
                                font.pixelSize: 16
                                font.bold: true
                                color: "#e0e0e0"
                            }

                            // New Test option
                            Rectangle {
                                Layout.fillWidth: true
                                height: 60
                                radius: 8
                                color: newTestMouseArea.containsMouse ? "#1a3a55" : "#1a2a45"
                                border.width: 1
                                border.color: "#e94560"

                                MouseArea {
                                    id: newTestMouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: newTestWizard.open()
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 12

                                    Rectangle {
                                        width: 36
                                        height: 36
                                        radius: 6
                                        color: "#e94560"

                                        Text {
                                            anchors.centerIn: parent
                                            text: "+"
                                            font.pixelSize: 20
                                            font.bold: true
                                            color: "#fff"
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        Text {
                                            text: "New Test"
                                            font.pixelSize: 13
                                            font.bold: true
                                            color: "#e0e0e0"
                                        }
                                        Text {
                                            text: "Discard current and start fresh"
                                            font.pixelSize: 10
                                            color: "#888"
                                        }
                                    }

                                    Text {
                                        text: ">"
                                        font.pixelSize: 16
                                        color: "#e94560"
                                    }
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }

                        // Status indicator
                        Rectangle {
                            Layout.fillWidth: true
                            height: 80
                            radius: 8
                            color: window.isRecording ? "#1a3a2e" : "#0f3460"
                            border.width: window.isRecording ? 1 : 0
                            border.color: "#4ecca3"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 12

                                Rectangle {
                                    width: 44
                                    height: 44
                                    radius: 22
                                    color: window.isRecording ? "#4ecca3" : "#3a3a5a"

                                    Text {
                                        anchors.centerIn: parent
                                        text: window.isRecording ? "●" : "○"
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
                                        color: window.isRecording ? "#4ecca3" : "#e0e0e0"
                                    }
                                    Text {
                                        text: window.isRecording ? "Interact with browser to capture steps" : "Click 'New Test' to start, then enter URL and click Record"
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

        // Tab 2: Replay
        Item {
            id: replayTab

            // Track replay summary
            property int totalDuration: 0
            property int passedCount: 0
            property int failedCount: 0

            RowLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 16

                // Workflow list
                Rectangle {
                    Layout.preferredWidth: 350
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
                                text: "🔄"
                                implicitWidth: 32
                                implicitHeight: 28
                                background: Rectangle {
                                    radius: 6
                                    color: parent.hovered ? "#2a4a70" : "transparent"
                                }
                                contentItem: Text {
                                    text: parent.text
                                    font.pixelSize: 14
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
                                    id: wfDelegate
                                    width: workflowListView.width - 16
                                    height: 64
                                    radius: 8
                                    color: window.selectedWorkflowPath === path ? "#1a2a45" : (wfMouseArea.containsMouse ? "#1a2a45" : "#192a40")
                                    border.color: window.selectedWorkflowPath === path ? "#e94560" : "transparent"
                                    border.width: window.selectedWorkflowPath === path ? 2 : 0

                                    // Selection indicator
                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.top: parent.top
                                        anchors.bottom: parent.bottom
                                        width: 3
                                        radius: 2
                                        color: window.selectedWorkflowPath === path ? "#e94560" : "transparent"
                                    }

                                    MouseArea {
                                        id: wfMouseArea
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            window.selectedWorkflowPath = path
                                            controller.load_workflow_steps(path)
                                        }
                                        onDoubleClicked: {
                                            window.selectedWorkflowPath = path
                                            controller.start_replay(path)
                                            window.isReplaying = true
                                        }
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 14
                                        anchors.rightMargin: 12
                                        anchors.topMargin: 10
                                        anchors.bottomMargin: 10
                                        spacing: 10

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 3

                                            Text {
                                                text: name || filename
                                                font.pixelSize: 13
                                                font.bold: true
                                                color: "#e0e0e0"
                                                elide: Text.ElideMiddle
                                                Layout.fillWidth: true
                                            }

                                            RowLayout {
                                                spacing: 8

                                                Rectangle {
                                                    width: stepsCountText.width + 8
                                                    height: 18
                                                    radius: 4
                                                    color: "#0f3460"

                                                    Text {
                                                        id: stepsCountText
                                                        anchors.centerIn: parent
                                                        text: stepCount + " steps"
                                                        font.pixelSize: 10
                                                        color: "#888"
                                                    }
                                                }

                                                Text {
                                                    text: baseUrl || ""
                                                    font.pixelSize: 10
                                                    color: "#555"
                                                    elide: Text.ElideRight
                                                    Layout.fillWidth: true
                                                    visible: baseUrl && baseUrl.length > 0
                                                }
                                            }
                                        }

                                        // Play icon on hover
                                        Rectangle {
                                            width: 28
                                            height: 28
                                            radius: 14
                                            color: wfMouseArea.containsMouse ? "#e94560" : "transparent"
                                            opacity: wfMouseArea.containsMouse ? 1 : 0

                                            Behavior on opacity {
                                                NumberAnimation { duration: 150 }
                                            }

                                            Text {
                                                anchors.centerIn: parent
                                                text: "▶"
                                                font.pixelSize: 12
                                                color: "#fff"
                                            }
                                        }
                                    }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    visible: workflowListModel.rowCount() === 0
                                    text: "No saved workflows\n\n📚 Go to Library"
                                    font.pixelSize: 13
                                    color: "#666"
                                    horizontalAlignment: Text.AlignHCenter
                                }
                            }
                        }

                        // Replay button
                        Button {
                            id: replayButton
                            Layout.fillWidth: true
                            implicitHeight: 44
                            enabled: window.selectedWorkflowPath || window.isReplaying

                            background: Rectangle {
                                radius: 8
                                color: {
                                    if (!parent.enabled) return "#333"
                                    if (window.isReplaying) return "#c73e1d"
                                    return parent.hovered ? "#d63e5c" : "#e94560"
                                }

                                // Animated progress bar at bottom when replaying
                                Rectangle {
                                    visible: window.isReplaying
                                    anchors.bottom: parent.bottom
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    height: 3
                                    radius: 1.5
                                    color: "#1a1a2e"

                                    Rectangle {
                                        id: progressBar
                                        height: parent.height
                                        radius: 1.5
                                        color: "#4ecca3"
                                        width: parent.width * 0.3

                                        SequentialAnimation on x {
                                            running: window.isReplaying
                                            loops: Animation.Infinite
                                            NumberAnimation {
                                                from: 0
                                                to: progressBar.parent.width - progressBar.width
                                                duration: 1000
                                                easing.type: Easing.InOutQuad
                                            }
                                            NumberAnimation {
                                                from: progressBar.parent.width - progressBar.width
                                                to: 0
                                                duration: 1000
                                                easing.type: Easing.InOutQuad
                                            }
                                        }
                                    }
                                }
                            }

                            contentItem: Row {
                                spacing: 10
                                anchors.centerIn: parent

                                // Spinning indicator when replaying
                                Rectangle {
                                    visible: window.isReplaying
                                    width: 18
                                    height: 18
                                    radius: 9
                                    color: "transparent"
                                    border.width: 2
                                    border.color: "#fff"
                                    anchors.verticalCenter: parent.verticalCenter

                                    Rectangle {
                                        width: 8
                                        height: 2
                                        radius: 1
                                        color: "#fff"
                                        anchors.centerIn: parent

                                        RotationAnimation on rotation {
                                            running: window.isReplaying
                                            from: 0
                                            to: 360
                                            duration: 800
                                            loops: Animation.Infinite
                                        }
                                    }
                                }

                                // Play icon when not replaying
                                Text {
                                    visible: !window.isReplaying
                                    text: "▶"
                                    font.pixelSize: 14
                                    color: replayButton.enabled ? "#fff" : "#666"
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: window.isReplaying ? "Stop Replay" : "Start Replay"
                                    font.pixelSize: 13
                                    font.bold: true
                                    color: replayButton.enabled ? "#fff" : "#555"
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            onClicked: {
                                if (window.isReplaying) {
                                    controller.stop_replay()
                                    window.isReplaying = false
                                } else if (window.selectedWorkflowPath) {
                                    replayTab.totalDuration = 0
                                    replayTab.passedCount = 0
                                    replayTab.failedCount = 0
                                    controller.start_replay(window.selectedWorkflowPath)
                                    window.isReplaying = true
                                }
                            }
                        }
                    }
                }

                // Right pane - Step Details or Replay Results
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 12
                    color: "#16213e"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        // Tab bar for switching views
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Rectangle {
                                width: detailsTabText.width + 24
                                height: 32
                                radius: 6
                                color: !window.isReplaying && replayResultsModel.rowCount() === 0 ? "#e94560" : (detailsTabMouse.containsMouse ? "#2a4a70" : "#0f3460")

                                Text {
                                    id: detailsTabText
                                    anchors.centerIn: parent
                                    text: "📋 Step Details"
                                    font.pixelSize: 12
                                    font.bold: !window.isReplaying && replayResultsModel.rowCount() === 0
                                    color: "#e0e0e0"
                                }

                                MouseArea {
                                    id: detailsTabMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: rightPaneStack.currentIndex = 0
                                }
                            }

                            Rectangle {
                                width: resultsTabText.width + 24
                                height: 32
                                radius: 6
                                color: window.isReplaying || replayResultsModel.rowCount() > 0 ? "#e94560" : (resultsTabMouse.containsMouse ? "#2a4a70" : "#0f3460")

                                Text {
                                    id: resultsTabText
                                    anchors.centerIn: parent
                                    text: "▶️ Replay Results"
                                    font.pixelSize: 12
                                    font.bold: window.isReplaying || replayResultsModel.rowCount() > 0
                                    color: "#e0e0e0"
                                }

                                MouseArea {
                                    id: resultsTabMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: rightPaneStack.currentIndex = 1
                                }
                            }

                            Item { Layout.fillWidth: true }

                            // Summary badges (visible during replay)
                            Row {
                                spacing: 8
                                visible: replayResultsModel.rowCount() > 0

                                Rectangle {
                                    width: passedLabel.width + 16
                                    height: 26
                                    radius: 13
                                    color: "#1a4a30"

                                    Text {
                                        id: passedLabel
                                        anchors.centerIn: parent
                                        text: "✓ " + replayTab.passedCount
                                        font.pixelSize: 12
                                        font.bold: true
                                        color: "#4ecca3"
                                    }
                                }

                                Rectangle {
                                    width: failedLabel.width + 16
                                    height: 26
                                    radius: 13
                                    color: replayTab.failedCount > 0 ? "#4a1a1a" : "#2a2a2a"

                                    Text {
                                        id: failedLabel
                                        anchors.centerIn: parent
                                        text: "✗ " + replayTab.failedCount
                                        font.pixelSize: 12
                                        font.bold: true
                                        color: replayTab.failedCount > 0 ? "#e94560" : "#666"
                                    }
                                }

                                Rectangle {
                                    width: durationLabel.width + 16
                                    height: 26
                                    radius: 13
                                    color: "#0f3460"

                                    Text {
                                        id: durationLabel
                                        anchors.centerIn: parent
                                        text: "⏱ " + (replayTab.totalDuration / 1000).toFixed(1) + "s"
                                        font.pixelSize: 12
                                        color: "#888"
                                    }
                                }
                            }
                        }

                        // Stack layout for switching between views
                        StackLayout {
                            id: rightPaneStack
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            currentIndex: window.isReplaying || replayResultsModel.rowCount() > 0 ? 1 : 0

                            // View 0: Step Details Panel
                            StepDetailPanel {
                                workflowPath: window.selectedWorkflowPath
                            }

                            // View 1: Replay Results
                            ColumnLayout {
                                spacing: 12

                                // Results list
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    radius: 8
                                    color: "#0f3460"

                                    ListView {
                                        id: replayResultsView
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        model: replayResultsModel
                                        clip: true
                                        spacing: 4

                                        delegate: Rectangle {
                                            id: resultDelegate
                                            width: replayResultsView.width - 16
                                            height: status === "failed" && error && error.length > 0 ? Math.max(90, 60 + Math.ceil(error.length / 50) * 14) : 52
                                            radius: 6
                                            color: {
                                                if (status === "passed") return "#152a22"
                                                if (status === "failed") return "#2a1515"
                                                if (status === "running") return "#15202a"
                                                if (status === "skipped") return "#1a1a20"
                                                return "#151a25"
                                            }
                                            border.color: {
                                                if (status === "passed") return "#4ecca3"
                                                if (status === "failed") return "#e94560"
                                                if (status === "running") return "#4a9eff"
                                                return "transparent"
                                            }
                                            border.width: status === "running" ? 2 : (status === "passed" || status === "failed" ? 1 : 0)

                                            // Running glow effect
                                            Rectangle {
                                                visible: status === "running"
                                                anchors.fill: parent
                                                radius: parent.radius
                                                color: "transparent"
                                                border.width: 4
                                                border.color: "#4a9eff"
                                                opacity: 0.3

                                                SequentialAnimation on opacity {
                                                    running: status === "running"
                                                    loops: Animation.Infinite
                                                    NumberAnimation { to: 0.6; duration: 500 }
                                                    NumberAnimation { to: 0.2; duration: 500 }
                                                }
                                            }

                                            ColumnLayout {
                                                anchors.fill: parent
                                                anchors.margins: 10
                                                spacing: 4

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 10

                                                    // Step number and status icon
                                                    Rectangle {
                                                        width: 26
                                                        height: 26
                                                        radius: 13
                                                        color: {
                                                            if (status === "passed") return "#4ecca3"
                                                            if (status === "failed") return "#e94560"
                                                            if (status === "running") return "#4a9eff"
                                                            if (status === "skipped") return "#555"
                                                            return "#3a3a4a"
                                                        }

                                                        Text {
                                                            anchors.centerIn: parent
                                                            text: {
                                                                if (status === "passed") return "✓"
                                                                if (status === "failed") return "✗"
                                                                if (status === "running") return ""
                                                                if (status === "skipped") return "–"
                                                                return (stepIndex + 1).toString()
                                                            }
                                                            font.pixelSize: status === "pending" ? 10 : 13
                                                            font.bold: true
                                                            color: "#fff"
                                                            visible: status !== "running"
                                                        }

                                                        // Spinning indicator for running
                                                        Rectangle {
                                                            visible: status === "running"
                                                            anchors.centerIn: parent
                                                            width: 14
                                                            height: 14
                                                            radius: 7
                                                            color: "transparent"
                                                            border.width: 2
                                                            border.color: "#fff"

                                                            Rectangle {
                                                                width: 6
                                                                height: 2
                                                                radius: 1
                                                                color: "#fff"
                                                                anchors.centerIn: parent

                                                                RotationAnimation on rotation {
                                                                    running: status === "running"
                                                                    from: 0
                                                                    to: 360
                                                                    duration: 600
                                                                    loops: Animation.Infinite
                                                                }
                                                            }
                                                        }
                                                    }

                                                    // Step type icon
                                                    Rectangle {
                                                        width: 28
                                                        height: 28
                                                        radius: 6
                                                        color: {
                                                            if (type === "click") return "#e94560"
                                                            if (type === "input" || type === "change" || type === "type") return "#4ecca3"
                                                            if (type === "keydown" || type === "press") return "#ffc93c"
                                                            return "#7b68ee"
                                                        }

                                                        Text {
                                                            anchors.centerIn: parent
                                                            text: {
                                                                if (type === "click") return "●"
                                                                if (type === "input" || type === "change" || type === "type") return "✎"
                                                                if (type === "keydown" || type === "press") return "⌨"
                                                                if (type === "hover") return "◎"
                                                                return "■"
                                                            }
                                                            font.pixelSize: 12
                                                            color: "#fff"
                                                        }
                                                    }

                                                    // Step info
                                                    ColumnLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 2

                                                        Text {
                                                            text: "Step " + (stepIndex + 1) + ": " + type.charAt(0).toUpperCase() + type.slice(1)
                                                            font.pixelSize: 13
                                                            font.bold: true
                                                            color: "#e0e0e0"
                                                        }

                                                        Text {
                                                            visible: locator && status !== "pending"
                                                            text: locator ? locator.substring(0, 50) + (locator.length > 50 ? "..." : "") : ""
                                                            font.pixelSize: 10
                                                            color: "#666"
                                                            Layout.fillWidth: true
                                                            elide: Text.ElideRight
                                                        }
                                                    }

                                                    // Duration
                                                    Rectangle {
                                                        visible: duration > 0
                                                        width: durationText.width + 12
                                                        height: 22
                                                        radius: 4
                                                        color: "#0a1a30"

                                                        Text {
                                                            id: durationText
                                                            anchors.centerIn: parent
                                                            text: duration + " ms"
                                                            font.pixelSize: 11
                                                            font.family: "Consolas"
                                                            color: duration > 3000 ? "#ffc93c" : "#4ecca3"
                                                        }
                                                    }

                                                    // AI Recovery Tier indicator (only for healed steps)
                                                    Rectangle {
                                                        visible: status === "passed" && recoveryTier > 0
                                                        width: tierText.width + 14
                                                        height: 22
                                                        radius: 4
                                                        color: {
                                                            if (recoveryTier === 1) return "#1a2a40"  // Healing
                                                            if (recoveryTier === 2) return "#2a1a40"  // CV
                                                            if (recoveryTier === 3) return "#401a2a"  // LLM
                                                            return "#1a1a2a"
                                                        }
                                                        border.width: 1
                                                        border.color: {
                                                            if (recoveryTier === 1) return "#4a9eff"  // Healing - blue
                                                            if (recoveryTier === 2) return "#9b59b6"  // CV - purple
                                                            if (recoveryTier === 3) return "#e67e22"  // LLM - orange
                                                            return "#555"
                                                        }

                                                        Row {
                                                            id: tierText
                                                            anchors.centerIn: parent
                                                            spacing: 4

                                                            Text {
                                                                text: {
                                                                    if (recoveryTier === 1) return "⚡"
                                                                    if (recoveryTier === 2) return "👁"
                                                                    if (recoveryTier === 3) return "🤖"
                                                                    return ""
                                                                }
                                                                font.pixelSize: 10
                                                            }

                                                            Text {
                                                                text: {
                                                                    if (recoveryTier === 1) return "Healed"
                                                                    if (recoveryTier === 2) return "CV"
                                                                    if (recoveryTier === 3) return "LLM"
                                                                    return ""
                                                                }
                                                                font.pixelSize: 10
                                                                font.bold: true
                                                                color: {
                                                                    if (recoveryTier === 1) return "#4a9eff"
                                                                    if (recoveryTier === 2) return "#9b59b6"
                                                                    if (recoveryTier === 3) return "#e67e22"
                                                                    return "#888"
                                                                }
                                                            }
                                                        }

                                                        ToolTip.visible: tierMouse.containsMouse
                                                        ToolTip.text: {
                                                            if (recoveryTier === 1) return "Recovered using selector healing (Tier 1)"
                                                            if (recoveryTier === 2) return "Recovered using computer vision (Tier 2)"
                                                            if (recoveryTier === 3) return "Recovered using LLM reasoning (Tier 3)"
                                                            return ""
                                                        }
                                                        ToolTip.delay: 300

                                                        MouseArea {
                                                            id: tierMouse
                                                            anchors.fill: parent
                                                            hoverEnabled: true
                                                        }
                                                    }
                                                }

                                                // Error message (only for failed steps)
                                                Rectangle {
                                                    visible: status === "failed" && error && error.length > 0
                                                    Layout.fillWidth: true
                                                    height: errorContent.height + 16
                                                    radius: 4
                                                    color: "#2a0a0a"
                                                    border.color: "#e94560"
                                                    border.width: 1

                                                    Column {
                                                        id: errorContent
                                                        anchors.left: parent.left
                                                        anchors.right: parent.right
                                                        anchors.verticalCenter: parent.verticalCenter
                                                        anchors.margins: 8
                                                        spacing: 4

                                                        // Tier failure indicator
                                                        Row {
                                                            visible: recoveryTier > 0
                                                            spacing: 4

                                                            Text {
                                                                text: "Failed after trying:"
                                                                font.pixelSize: 10
                                                                color: "#888"
                                                            }

                                                            Repeater {
                                                                model: recoveryTier + 1

                                                                Rectangle {
                                                                    width: tierLabel.width + 8
                                                                    height: 16
                                                                    radius: 3
                                                                    color: {
                                                                        if (index === 0) return "#1a2530"
                                                                        if (index === 1) return "#1a2540"
                                                                        if (index === 2) return "#251a40"
                                                                        if (index === 3) return "#401a25"
                                                                        return "#1a1a25"
                                                                    }

                                                                    Text {
                                                                        id: tierLabel
                                                                        anchors.centerIn: parent
                                                                        text: {
                                                                            if (index === 0) return "Direct"
                                                                            if (index === 1) return "Heal"
                                                                            if (index === 2) return "CV"
                                                                            if (index === 3) return "LLM"
                                                                            return ""
                                                                        }
                                                                        font.pixelSize: 9
                                                                        color: "#888"
                                                                    }
                                                                }
                                                            }
                                                        }

                                                        Text {
                                                            id: errorText
                                                            width: parent.width
                                                            text: "⚠ " + (error || "Unknown error")
                                                            font.pixelSize: 11
                                                            color: "#ff6b6b"
                                                            wrapMode: Text.WordWrap
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                        // Empty state
                                        Column {
                                            anchors.centerIn: parent
                                            spacing: 12
                                            visible: replayResultsModel.rowCount() === 0

                                            Rectangle {
                                                width: 48
                                                height: 48
                                                radius: 24
                                                color: "#1a2a45"
                                                anchors.horizontalCenter: parent.horizontalCenter

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: window.isReplaying ? "◐" : "▶"
                                                    font.pixelSize: 20
                                                    color: window.isReplaying ? "#4a9eff" : "#666"

                                                    RotationAnimation on rotation {
                                                        running: window.isReplaying
                                                        from: 0
                                                        to: 360
                                                        duration: 1000
                                                        loops: Animation.Infinite
                                                    }
                                                }
                                            }

                                            Text {
                                                text: window.isReplaying ? "Initializing..." : "No Results Yet"
                                                font.pixelSize: 14
                                                font.bold: true
                                                color: "#888"
                                                anchors.horizontalCenter: parent.horizontalCenter
                                            }

                                            Text {
                                                text: window.isReplaying ? "Preparing test execution" : "Select a workflow and click\nStart Replay to begin"
                                                font.pixelSize: 12
                                                color: "#555"
                                                horizontalAlignment: Text.AlignHCenter
                                                anchors.horizontalCenter: parent.horizontalCenter
                                            }
                                        }
                                    }
                                }

                                // Status bar
                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 48
                                    radius: 6
                                    color: {
                                        if (window.isReplaying) return "#152535"
                                        if (replayTab.failedCount > 0) return "#251515"
                                        if (replayTab.passedCount > 0) return "#152520"
                                        return "#0f3460"
                                    }
                                    border.width: 1
                                    border.color: {
                                        if (window.isReplaying) return "#4a9eff"
                                        if (replayTab.failedCount > 0) return "#e94560"
                                        if (replayTab.passedCount > 0) return "#4ecca3"
                                        return "transparent"
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        spacing: 12

                                        Rectangle {
                                            width: 32
                                            height: 32
                                            radius: 16
                                            color: {
                                                if (window.isReplaying) return "#4a9eff"
                                                if (replayTab.failedCount > 0) return "#e94560"
                                                if (replayTab.passedCount > 0) return "#4ecca3"
                                                return "#3a3a4a"
                                            }

                                            Text {
                                                anchors.centerIn: parent
                                                text: {
                                                    if (window.isReplaying) return ""
                                                    if (replayTab.failedCount > 0) return "!"
                                                    if (replayTab.passedCount > 0) return "✓"
                                                    return "○"
                                                }
                                                font.pixelSize: 14
                                                font.bold: true
                                                color: "#fff"
                                                visible: !window.isReplaying
                                            }

                                            // Spinning indicator when replaying
                                            Rectangle {
                                                visible: window.isReplaying
                                                anchors.centerIn: parent
                                                width: 16
                                                height: 16
                                                radius: 8
                                                color: "transparent"
                                                border.width: 2
                                                border.color: "#fff"

                                                Rectangle {
                                                    width: 6
                                                    height: 2
                                                    radius: 1
                                                    color: "#fff"
                                                    anchors.centerIn: parent

                                                    RotationAnimation on rotation {
                                                        running: window.isReplaying
                                                        from: 0
                                                        to: 360
                                                        duration: 700
                                                        loops: Animation.Infinite
                                                    }
                                                }
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 1

                                            Text {
                                                text: {
                                                    if (window.isReplaying) return "Executing Test..."
                                                    if (replayResultsModel.rowCount() === 0) return "Ready to Run"
                                                    if (replayTab.failedCount > 0) return "Test Failed"
                                                    return "Test Passed"
                                                }
                                                font.pixelSize: 13
                                                font.bold: true
                                                color: {
                                                    if (window.isReplaying) return "#4a9eff"
                                                    if (replayTab.failedCount > 0) return "#e94560"
                                                    if (replayTab.passedCount > 0) return "#4ecca3"
                                                    return "#888"
                                                }
                                            }
                                            Text {
                                                text: replayResultsModel.get_summary()
                                                font.pixelSize: 11
                                                color: "#666"
                                            }
                                        }

                                        // Duration display
                                        Rectangle {
                                            visible: replayTab.totalDuration > 0
                                            width: totalDurText.width + 14
                                            height: 26
                                            radius: 4
                                            color: "#0a1525"

                                            Text {
                                                id: totalDurText
                                                anchors.centerIn: parent
                                                text: (replayTab.totalDuration / 1000).toFixed(1) + "s"
                                                font.pixelSize: 12
                                                font.family: "Consolas"
                                                color: "#888"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // Tab 3: Runs History
        Item {
            id: runsTab

            RunsView {
                anchors.fill: parent

                onExecutionRerun: (workflowId) => {
                    // Find workflow path and trigger replay
                    statusLabel.text = "Rerun requested for workflow: " + workflowId
                }
            }
        }

        // Tab 4: ML Insights
        Item {
            id: mlInsightsTab

            MLInsightsView {
                anchors.fill: parent
            }
        }

        // Tab 5: Settings
        Item {
            id: settingsTab

            ScrollView {
                anchors.fill: parent
                anchors.margins: 20
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: 24

                    // Settings Header
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16

                        Rectangle {
                            width: 48
                            height: 48
                            radius: 12
                            color: "#0f3460"

                            Text {
                                anchors.centerIn: parent
                                text: "⚙"
                                font.pixelSize: 24
                            }
                        }

                        ColumnLayout {
                            spacing: 4

                            Text {
                                text: "Settings"
                                font.pixelSize: 24
                                font.bold: true
                                color: "#e0e0e0"
                            }

                            Text {
                                text: "Configure replay, browser, and AI engine options"
                                font.pixelSize: 13
                                color: "#888"
                            }
                        }

                        Item { Layout.fillWidth: true }

                        Button {
                            text: "Reset to Defaults"
                            implicitWidth: 140
                            implicitHeight: 36

                            background: Rectangle {
                                radius: 6
                                color: parent.hovered ? "#3a2a35" : "#2a2a35"
                                border.width: 1
                                border.color: "#e94560"
                            }

                            contentItem: Text {
                                text: "Reset to Defaults"
                                font.pixelSize: 12
                                color: "#e94560"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }

                            onClicked: appSettings.resetToDefaults()
                        }
                    }

                    // Replay Settings Section
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: replaySettingsContent.height + 40
                        radius: 12
                        color: "#16213e"

                        ColumnLayout {
                            id: replaySettingsContent
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 20
                            spacing: 16

                            RowLayout {
                                spacing: 10

                                Text {
                                    text: "▶"
                                    font.pixelSize: 16
                                    color: "#4ecca3"
                                }

                                Text {
                                    text: "Replay Settings"
                                    font.pixelSize: 16
                                    font.bold: true
                                    color: "#e0e0e0"
                                }
                            }

                            // Max AI Tier
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Max AI Tier"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Limit which recovery tiers can be used"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                ComboBox {
                                    id: maxTierCombo
                                    implicitWidth: 200
                                    model: ["Direct Only", "+ Healing (Tier 1)", "+ Computer Vision (Tier 2)", "+ LLM (Tier 3)"]
                                    currentIndex: appSettings.maxTier

                                    background: Rectangle {
                                        radius: 6
                                        color: "#0f3460"
                                        border.color: maxTierCombo.hovered ? "#4ecca3" : "#1a2a45"
                                    }

                                    contentItem: Text {
                                        text: maxTierCombo.displayText
                                        font.pixelSize: 13
                                        color: "#e0e0e0"
                                        verticalAlignment: Text.AlignVCenter
                                        leftPadding: 12
                                    }

                                    onCurrentIndexChanged: appSettings.maxTier = currentIndex
                                }
                            }

                            // Page Load Timeout
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Page Load Timeout"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Max time to wait for page load"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                RowLayout {
                                    spacing: 8

                                    SpinBox {
                                        id: pageLoadTimeoutSpin
                                        from: 10
                                        to: 300
                                        value: appSettings.pageLoadTimeout
                                        editable: true
                                        implicitWidth: 100

                                        background: Rectangle {
                                            radius: 6
                                            color: "#0f3460"
                                        }

                                        contentItem: TextInput {
                                            text: pageLoadTimeoutSpin.textFromValue(pageLoadTimeoutSpin.value, pageLoadTimeoutSpin.locale)
                                            font.pixelSize: 13
                                            color: "#e0e0e0"
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                            readOnly: !pageLoadTimeoutSpin.editable
                                            validator: pageLoadTimeoutSpin.validator
                                        }

                                        onValueChanged: appSettings.pageLoadTimeout = value
                                    }

                                    Text {
                                        text: "seconds"
                                        font.pixelSize: 12
                                        color: "#888"
                                    }
                                }
                            }

                            // Step Timeout
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Step Timeout"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Default timeout per step"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                RowLayout {
                                    spacing: 8

                                    SpinBox {
                                        id: stepTimeoutSpin
                                        from: 1
                                        to: 60
                                        value: appSettings.stepTimeout
                                        editable: true
                                        implicitWidth: 100

                                        background: Rectangle {
                                            radius: 6
                                            color: "#0f3460"
                                        }

                                        contentItem: TextInput {
                                            text: stepTimeoutSpin.textFromValue(stepTimeoutSpin.value, stepTimeoutSpin.locale)
                                            font.pixelSize: 13
                                            color: "#e0e0e0"
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                            readOnly: !stepTimeoutSpin.editable
                                            validator: stepTimeoutSpin.validator
                                        }

                                        onValueChanged: appSettings.stepTimeout = value
                                    }

                                    Text {
                                        text: "seconds"
                                        font.pixelSize: 12
                                        color: "#888"
                                    }
                                }
                            }

                            // Stability Wait
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Stability Wait"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Time to wait for page stability"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                RowLayout {
                                    spacing: 8

                                    SpinBox {
                                        id: stabilityTimeoutSpin
                                        from: 1
                                        to: 30
                                        value: appSettings.stabilityTimeout
                                        editable: true
                                        implicitWidth: 100

                                        background: Rectangle {
                                            radius: 6
                                            color: "#0f3460"
                                        }

                                        contentItem: TextInput {
                                            text: stabilityTimeoutSpin.textFromValue(stabilityTimeoutSpin.value, stabilityTimeoutSpin.locale)
                                            font.pixelSize: 13
                                            color: "#e0e0e0"
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                            readOnly: !stabilityTimeoutSpin.editable
                                            validator: stabilityTimeoutSpin.validator
                                        }

                                        onValueChanged: appSettings.stabilityTimeout = value
                                    }

                                    Text {
                                        text: "seconds"
                                        font.pixelSize: 12
                                        color: "#888"
                                    }
                                }
                            }
                        }
                    }

                    // Browser Settings Section
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: browserSettingsContent.height + 40
                        radius: 12
                        color: "#16213e"

                        ColumnLayout {
                            id: browserSettingsContent
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 20
                            spacing: 16

                            RowLayout {
                                spacing: 10

                                Text {
                                    text: "🌐"
                                    font.pixelSize: 16
                                }

                                Text {
                                    text: "Browser Settings"
                                    font.pixelSize: 16
                                    font.bold: true
                                    color: "#e0e0e0"
                                }
                            }

                            // Browser Type
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Browser Type"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Browser engine for replay"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                ComboBox {
                                    id: browserTypeCombo
                                    implicitWidth: 200
                                    model: ["chromium", "firefox", "webkit"]
                                    currentIndex: model.indexOf(appSettings.browserType)

                                    background: Rectangle {
                                        radius: 6
                                        color: "#0f3460"
                                        border.color: browserTypeCombo.hovered ? "#4ecca3" : "#1a2a45"
                                    }

                                    contentItem: Text {
                                        text: browserTypeCombo.displayText
                                        font.pixelSize: 13
                                        color: "#e0e0e0"
                                        verticalAlignment: Text.AlignVCenter
                                        leftPadding: 12
                                    }

                                    onCurrentTextChanged: appSettings.browserType = currentText
                                }
                            }

                            // Headless Mode
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Headless Mode"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Run browser without UI (for CI/CD)"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Switch {
                                    id: headlessModeSwitch
                                    checked: appSettings.headlessMode

                                    indicator: Rectangle {
                                        width: 48
                                        height: 26
                                        radius: 13
                                        color: headlessModeSwitch.checked ? "#4ecca3" : "#2a3a50"

                                        Rectangle {
                                            x: headlessModeSwitch.checked ? parent.width - width - 3 : 3
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: 20
                                            height: 20
                                            radius: 10
                                            color: "#fff"

                                            Behavior on x { NumberAnimation { duration: 150 } }
                                        }
                                    }

                                    onCheckedChanged: appSettings.headlessMode = checked
                                }
                            }

                            // Keep Browser Open
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Keep Browser Open"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Keep browser open after replay"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Switch {
                                    id: keepBrowserOpenSwitch
                                    checked: appSettings.keepBrowserOpen

                                    indicator: Rectangle {
                                        width: 48
                                        height: 26
                                        radius: 13
                                        color: keepBrowserOpenSwitch.checked ? "#4ecca3" : "#2a3a50"

                                        Rectangle {
                                            x: keepBrowserOpenSwitch.checked ? parent.width - width - 3 : 3
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: 20
                                            height: 20
                                            radius: 10
                                            color: "#fff"

                                            Behavior on x { NumberAnimation { duration: 150 } }
                                        }
                                    }

                                    onCheckedChanged: appSettings.keepBrowserOpen = checked
                                }
                            }
                        }
                    }

                    // AI Engine Settings Section
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: aiSettingsContent.height + 40
                        radius: 12
                        color: "#16213e"

                        ColumnLayout {
                            id: aiSettingsContent
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 20
                            spacing: 16

                            RowLayout {
                                spacing: 10

                                Text {
                                    text: "🤖"
                                    font.pixelSize: 16
                                }

                                Text {
                                    text: "AI Engine Settings"
                                    font.pixelSize: 16
                                    font.bold: true
                                    color: "#e0e0e0"
                                }
                            }

                            // Ollama Model
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Ollama Model"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "LLM model for Tier 3 recovery"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Rectangle {
                                    width: 200
                                    height: 36
                                    radius: 6
                                    color: "#0f3460"
                                    border.color: ollamaModelInput.activeFocus ? "#4ecca3" : "#1a2a45"

                                    TextInput {
                                        id: ollamaModelInput
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        font.pixelSize: 13
                                        color: "#e0e0e0"
                                        text: appSettings.ollamaModel
                                        selectByMouse: true
                                        verticalAlignment: TextInput.AlignVCenter

                                        onTextChanged: appSettings.ollamaModel = text
                                    }
                                }
                            }

                            // LLM Timeout
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "LLM Timeout"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Max time for LLM requests"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                RowLayout {
                                    spacing: 8

                                    SpinBox {
                                        id: llmTimeoutSpin
                                        from: 5
                                        to: 120
                                        value: appSettings.llmTimeout
                                        editable: true
                                        implicitWidth: 100

                                        background: Rectangle {
                                            radius: 6
                                            color: "#0f3460"
                                        }

                                        contentItem: TextInput {
                                            text: llmTimeoutSpin.textFromValue(llmTimeoutSpin.value, llmTimeoutSpin.locale)
                                            font.pixelSize: 13
                                            color: "#e0e0e0"
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                            readOnly: !llmTimeoutSpin.editable
                                            validator: llmTimeoutSpin.validator
                                        }

                                        onValueChanged: appSettings.llmTimeout = value
                                    }

                                    Text {
                                        text: "seconds"
                                        font.pixelSize: 12
                                        color: "#888"
                                    }
                                }
                            }

                            // CV Match Threshold
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "CV Match Threshold"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Confidence for visual matching"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                RowLayout {
                                    spacing: 8

                                    Slider {
                                        id: cvThresholdSlider
                                        from: 50
                                        to: 100
                                        value: appSettings.cvThreshold
                                        stepSize: 5
                                        implicitWidth: 150

                                        background: Rectangle {
                                            y: cvThresholdSlider.height / 2 - height / 2
                                            height: 6
                                            radius: 3
                                            color: "#0f3460"

                                            Rectangle {
                                                width: cvThresholdSlider.visualPosition * parent.width
                                                height: parent.height
                                                radius: 3
                                                color: "#9b59b6"
                                            }
                                        }

                                        handle: Rectangle {
                                            x: cvThresholdSlider.visualPosition * (cvThresholdSlider.width - width)
                                            y: cvThresholdSlider.height / 2 - height / 2
                                            width: 18
                                            height: 18
                                            radius: 9
                                            color: "#fff"
                                        }

                                        onValueChanged: appSettings.cvThreshold = value
                                    }

                                    Text {
                                        text: appSettings.cvThreshold + "%"
                                        font.pixelSize: 12
                                        color: "#9b59b6"
                                        font.bold: true
                                    }
                                }
                            }

                            // Healing Threshold
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Healing Threshold"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Similarity for selector healing"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                RowLayout {
                                    spacing: 8

                                    Slider {
                                        id: healingThresholdSlider
                                        from: 50
                                        to: 100
                                        value: appSettings.healingThreshold
                                        stepSize: 5
                                        implicitWidth: 150

                                        background: Rectangle {
                                            y: healingThresholdSlider.height / 2 - height / 2
                                            height: 6
                                            radius: 3
                                            color: "#0f3460"

                                            Rectangle {
                                                width: healingThresholdSlider.visualPosition * parent.width
                                                height: parent.height
                                                radius: 3
                                                color: "#4a9eff"
                                            }
                                        }

                                        handle: Rectangle {
                                            x: healingThresholdSlider.visualPosition * (healingThresholdSlider.width - width)
                                            y: healingThresholdSlider.height / 2 - height / 2
                                            width: 18
                                            height: 18
                                            radius: 9
                                            color: "#fff"
                                        }

                                        onValueChanged: appSettings.healingThreshold = value
                                    }

                                    Text {
                                        text: appSettings.healingThreshold + "%"
                                        font.pixelSize: 12
                                        color: "#4a9eff"
                                        font.bold: true
                                    }
                                }
                            }
                        }
                    }

                    // Recording Settings Section
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: recordingSettingsContent.height + 40
                        radius: 12
                        color: "#16213e"

                        ColumnLayout {
                            id: recordingSettingsContent
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 20
                            spacing: 16

                            RowLayout {
                                spacing: 10

                                Text {
                                    text: "⚫"
                                    font.pixelSize: 16
                                    color: "#e94560"
                                }

                                Text {
                                    text: "Recording Settings"
                                    font.pixelSize: 16
                                    font.bold: true
                                    color: "#e0e0e0"
                                }
                            }

                            // WebSocket Port
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "WebSocket Port"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Port for browser extension"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                SpinBox {
                                    id: wsPortSpin
                                    from: 1024
                                    to: 65535
                                    value: appSettings.websocketPort
                                    editable: true
                                    implicitWidth: 120

                                    background: Rectangle {
                                        radius: 6
                                        color: "#0f3460"
                                    }

                                    contentItem: TextInput {
                                        text: wsPortSpin.textFromValue(wsPortSpin.value, wsPortSpin.locale)
                                        font.pixelSize: 13
                                        color: "#e0e0e0"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        readOnly: !wsPortSpin.editable
                                        validator: wsPortSpin.validator
                                    }

                                    onValueChanged: appSettings.websocketPort = value
                                }
                            }

                            // Auto-capture Screenshots
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Auto-capture Screenshots"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Save element screenshots during recording"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Switch {
                                    id: autoCaptureSwitch
                                    checked: appSettings.autoCaptureScreenshots

                                    indicator: Rectangle {
                                        width: 48
                                        height: 26
                                        radius: 13
                                        color: autoCaptureSwitch.checked ? "#4ecca3" : "#2a3a50"

                                        Rectangle {
                                            x: autoCaptureSwitch.checked ? parent.width - width - 3 : 3
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: 20
                                            height: 20
                                            radius: 10
                                            color: "#fff"

                                            Behavior on x { NumberAnimation { duration: 150 } }
                                        }
                                    }

                                    onCheckedChanged: appSettings.autoCaptureScreenshots = checked
                                }
                            }

                            // Auto-save on Stop
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Auto-save on Stop"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Automatically save when recording stops"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Switch {
                                    id: autoSaveSwitch
                                    checked: appSettings.autoSaveOnStop

                                    indicator: Rectangle {
                                        width: 48
                                        height: 26
                                        radius: 13
                                        color: autoSaveSwitch.checked ? "#4ecca3" : "#2a3a50"

                                        Rectangle {
                                            x: autoSaveSwitch.checked ? parent.width - width - 3 : 3
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: 20
                                            height: 20
                                            radius: 10
                                            color: "#fff"

                                            Behavior on x { NumberAnimation { duration: 150 } }
                                        }
                                    }

                                    onCheckedChanged: appSettings.autoSaveOnStop = checked
                                }
                            }
                        }
                    }

                    // Storage Settings Section
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: storageSettingsContent.height + 40
                        radius: 12
                        color: "#16213e"

                        ColumnLayout {
                            id: storageSettingsContent
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 20
                            spacing: 16

                            RowLayout {
                                spacing: 10

                                Text {
                                    text: "📁"
                                    font.pixelSize: 16
                                }

                                Text {
                                    text: "Storage Settings"
                                    font.pixelSize: 16
                                    font.bold: true
                                    color: "#e0e0e0"
                                }
                            }

                            // Workflows Directory
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Workflows Directory"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Where tests are saved"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Rectangle {
                                    width: 250
                                    height: 36
                                    radius: 6
                                    color: "#0f3460"
                                    border.color: workflowsDirInput.activeFocus ? "#4ecca3" : "#1a2a45"

                                    TextInput {
                                        id: workflowsDirInput
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        font.pixelSize: 13
                                        color: "#e0e0e0"
                                        text: appSettings.workflowsDirectory
                                        selectByMouse: true
                                        verticalAlignment: TextInput.AlignVCenter

                                        onTextChanged: appSettings.workflowsDirectory = text
                                    }
                                }
                            }

                            // Screenshots Directory
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Screenshots Directory"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Where screenshots are stored"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Rectangle {
                                    width: 250
                                    height: 36
                                    radius: 6
                                    color: "#0f3460"
                                    border.color: screenshotsDirInput.activeFocus ? "#4ecca3" : "#1a2a45"

                                    TextInput {
                                        id: screenshotsDirInput
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        font.pixelSize: 13
                                        color: "#e0e0e0"
                                        text: appSettings.screenshotsDirectory
                                        selectByMouse: true
                                        verticalAlignment: TextInput.AlignVCenter

                                        onTextChanged: appSettings.screenshotsDirectory = text
                                    }
                                }
                            }
                        }
                    }

                    // Appearance Settings Section
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: appearanceSettingsContent.height + 40
                        radius: 12
                        color: "#16213e"

                        ColumnLayout {
                            id: appearanceSettingsContent
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 20
                            spacing: 16

                            RowLayout {
                                spacing: 10

                                Text {
                                    text: "🎨"
                                    font.pixelSize: 16
                                }

                                Text {
                                    text: "Appearance"
                                    font.pixelSize: 16
                                    font.bold: true
                                    color: "#e0e0e0"
                                }
                            }

                            // Show Tier Badges
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.preferredWidth: 200
                                    spacing: 4

                                    Text {
                                        text: "Show Tier Badges"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: "Display AI tier on replay results"
                                        font.pixelSize: 11
                                        color: "#666"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Switch {
                                    id: showTierBadgesSwitch
                                    checked: appSettings.showTierBadges

                                    indicator: Rectangle {
                                        width: 48
                                        height: 26
                                        radius: 13
                                        color: showTierBadgesSwitch.checked ? "#4ecca3" : "#2a3a50"

                                        Rectangle {
                                            x: showTierBadgesSwitch.checked ? parent.width - width - 3 : 3
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: 20
                                            height: 20
                                            radius: 10
                                            color: "#fff"

                                            Behavior on x { NumberAnimation { duration: 150 } }
                                        }
                                    }

                                    onCheckedChanged: appSettings.showTierBadges = checked
                                }
                            }
                        }
                    }

                    // Version info
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "Auton8 Capture Pro v1.0.0"
                        font.pixelSize: 11
                        color: "#555"
                        Layout.topMargin: 10
                    }

                    // Spacer at bottom
                    Item {
                        Layout.fillHeight: true
                        Layout.minimumHeight: 20
                    }
                }
            }
        }
    }

    // New Test Wizard Dialog
    NewTestWizard {
        id: newTestWizard

        onTestCreated: (name, url) => {
            // Store the test name for later use
            window.pendingTestName = name
            // Clear everything and switch to Record tab
            window.isEditMode = false
            window.editingWorkflowPath = ""
            // Clear timeline via controller (ensures proper cleanup)
            controller.clear_timeline()
            window.currentTab = 1
            // Set the URL and focus
            Qt.callLater(function() {
                urlInput.text = url
                urlInput.forceActiveFocus()
            })
        }
    }
    
    // Delete Confirmation Dialog
    Dialog {
        id: deleteConfirmDialog
        property string workflowPath: ""
        
        title: "Delete Workflow"
        modal: true
        width: 400
        height: 180
        anchors.centerIn: parent
        
        background: Rectangle {
            radius: 12
            color: "#16213e"
            border.color: "#c73e1d"
            border.width: 2
        }
        
        contentItem: ColumnLayout {
            spacing: 16
            
            Text {
                text: "⚠️ Are you sure you want to delete this workflow?"
                font.pixelSize: 14
                color: "#e0e0e0"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            
            Text {
                text: "This action cannot be undone."
                font.pixelSize: 12
                color: "#c73e1d"
            }
        }
        
        footer: DialogButtonBox {
            background: Rectangle {
                color: "#16213e"
            }
            
            Button {
                text: "Cancel"
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                background: Rectangle {
                    radius: 6
                    color: parent.hovered ? "#2a4a70" : "#0f3460"
                }
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 14
                    color: "#e0e0e0"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: deleteConfirmDialog.close()
            }
            
            Button {
                text: "Delete"
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                background: Rectangle {
                    radius: 6
                    color: parent.hovered ? "#a32e17" : "#c73e1d"
                }
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 14
                    font.bold: true
                    color: "#fff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: {
                    controller.delete_workflow(deleteConfirmDialog.workflowPath)
                    deleteConfirmDialog.close()
                }
            }
        }
    }

    // Instruction step component
    component InstructionStep: RowLayout {
        property string number: "1"
        property string text: ""
        spacing: 14

        Rectangle {
            width: 32
            height: 32
            radius: 16
            color: "#e94560"

            Text {
                anchors.centerIn: parent
                text: parent.parent.number
                font.pixelSize: 14
                font.bold: true
                color: "#fff"
            }
        }

        Text {
            Layout.fillWidth: true
            text: parent.text
            font.pixelSize: 14
            color: "#ccc"
            wrapMode: Text.WordWrap
        }
    }

    // Tab button component
    component TabButton: Rectangle {
        property string text: ""
        property bool active: false
        signal clicked()

        width: 120
        height: 42
        radius: 8
        color: active ? "#e94560" : (mouseArea.containsMouse ? "#2a4a70" : "transparent")

        Behavior on color {
            ColorAnimation { duration: 200 }
        }

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

    // Timeline Add Step Dialog (for Recording tab) - Comprehensive version
    Popup {
        id: timelineAddMenu
        property int stepIndex: -1
        property string selectedType: ""

        width: 380
        height: selectedType === "" ? 240 : 320
        modal: true
        anchors.centerIn: Overlay.overlay

        onClosed: {
            selectedType = ""
            tlSelectorInput.text = ""
            tlValueInput.text = ""
            tlWaitTimeInput.text = "1000"
            tlKeyInput.text = ""
        }

        background: Rectangle {
            color: "#16213e"
            border.color: "#4ecca3"
            border.width: 2
            radius: 10
        }

        contentItem: ColumnLayout {
            spacing: 10
            anchors.margins: 12

            Text {
                text: timelineAddMenu.selectedType === "" ?
                    "Add Step After #" + (timelineAddMenu.stepIndex + 1) :
                    "Configure " + timelineAddMenu.selectedType.charAt(0).toUpperCase() + timelineAddMenu.selectedType.slice(1)
                font.pixelSize: 15
                font.bold: true
                color: "#e0e0e0"
                Layout.alignment: Qt.AlignHCenter
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: "#2a4a70" }

            // Step Type Selection
            GridLayout {
                visible: timelineAddMenu.selectedType === ""
                columns: 4
                rowSpacing: 8
                columnSpacing: 8
                Layout.alignment: Qt.AlignHCenter

                Repeater {
                    model: [
                        {type: "click", label: "Click", icon: "●", color: "#e94560"},
                        {type: "input", label: "Input", icon: "✎", color: "#4ecca3"},
                        {type: "keydown", label: "Key", icon: "⌨", color: "#ffc93c"},
                        {type: "wait", label: "Wait", icon: "⏳", color: "#7b68ee"}
                    ]

                    Rectangle {
                        id: tlTypeRect
                        width: 80
                        height: 55
                        radius: 6
                        property bool isHovered: false
                        color: isHovered ? modelData.color : "#0f3460"
                        border.color: modelData.color
                        border.width: 2

                        ColumnLayout {
                            anchors.centerIn: parent
                            spacing: 2
                            Text { text: modelData.icon; font.pixelSize: 18; color: "#fff"; Layout.alignment: Qt.AlignHCenter }
                            Text { text: modelData.label; font.pixelSize: 11; font.bold: true; color: "#fff"; Layout.alignment: Qt.AlignHCenter }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onContainsMouseChanged: tlTypeRect.isHovered = containsMouse
                            onClicked: timelineAddMenu.selectedType = modelData.type
                        }
                    }
                }
            }

            // Configuration fields
            ColumnLayout {
                visible: timelineAddMenu.selectedType !== ""
                spacing: 10
                Layout.fillWidth: true

                // Selector (for click, input, keydown)
                ColumnLayout {
                    visible: timelineAddMenu.selectedType !== "wait"
                    spacing: 4
                    Layout.fillWidth: true

                    Text { text: "Selector"; font.pixelSize: 12; font.bold: true; color: "#4ecca3" }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 34
                        radius: 4
                        color: "#0f3460"
                        border.color: tlSelectorInput.activeFocus ? "#4ecca3" : "#2a4a70"

                        TextInput {
                            id: tlSelectorInput
                            anchors.fill: parent
                            anchors.margins: 8
                            color: "#e0e0e0"
                            font.pixelSize: 12
                            font.family: "Consolas"
                            clip: true
                            verticalAlignment: TextInput.AlignVCenter

                            Text {
                                anchors.fill: parent
                                text: "CSS selector, e.g., #btn, .input"
                                color: "#666"
                                font.pixelSize: 11
                                visible: !tlSelectorInput.text && !tlSelectorInput.activeFocus
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                }

                // Value (for input)
                ColumnLayout {
                    visible: timelineAddMenu.selectedType === "input"
                    spacing: 4
                    Layout.fillWidth: true

                    Text { text: "Value to Input"; font.pixelSize: 12; font.bold: true; color: "#4ecca3" }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 34
                        radius: 4
                        color: "#0f3460"
                        border.color: tlValueInput.activeFocus ? "#4ecca3" : "#2a4a70"

                        TextInput {
                            id: tlValueInput
                            anchors.fill: parent
                            anchors.margins: 8
                            color: "#e0e0e0"
                            font.pixelSize: 12
                            clip: true
                            verticalAlignment: TextInput.AlignVCenter

                            Text {
                                anchors.fill: parent
                                text: "Text to type..."
                                color: "#666"
                                font.pixelSize: 11
                                visible: !tlValueInput.text && !tlValueInput.activeFocus
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                }

                // Key (for keydown)
                ColumnLayout {
                    visible: timelineAddMenu.selectedType === "keydown"
                    spacing: 4
                    Layout.fillWidth: true

                    Text { text: "Key"; font.pixelSize: 12; font.bold: true; color: "#4ecca3" }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 34
                        radius: 4
                        color: "#0f3460"
                        border.color: tlKeyInput.activeFocus ? "#4ecca3" : "#2a4a70"

                        TextInput {
                            id: tlKeyInput
                            anchors.fill: parent
                            anchors.margins: 8
                            color: "#e0e0e0"
                            font.pixelSize: 12
                            clip: true
                            verticalAlignment: TextInput.AlignVCenter

                            Text {
                                anchors.fill: parent
                                text: "Enter, Tab, Escape..."
                                color: "#666"
                                font.pixelSize: 11
                                visible: !tlKeyInput.text && !tlKeyInput.activeFocus
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                }

                // Wait time (for wait)
                ColumnLayout {
                    visible: timelineAddMenu.selectedType === "wait"
                    spacing: 4
                    Layout.fillWidth: true

                    Text { text: "Wait Time (ms)"; font.pixelSize: 12; font.bold: true; color: "#4ecca3" }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 34
                        radius: 4
                        color: "#0f3460"
                        border.color: tlWaitTimeInput.activeFocus ? "#4ecca3" : "#2a4a70"

                        TextInput {
                            id: tlWaitTimeInput
                            anchors.fill: parent
                            anchors.margins: 8
                            color: "#e0e0e0"
                            font.pixelSize: 12
                            text: "1000"
                            validator: IntValidator { bottom: 0; top: 60000 }
                            verticalAlignment: TextInput.AlignVCenter
                        }
                    }
                }
            }

            Item { Layout.fillHeight: true }

            // Action buttons
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: 6
                    color: tlBackMouse.containsMouse ? "#2a4a70" : "#0f3460"

                    Text {
                        anchors.centerIn: parent
                        text: timelineAddMenu.selectedType === "" ? "Cancel" : "← Back"
                        font.pixelSize: 12
                        color: "#e0e0e0"
                    }

                    MouseArea {
                        id: tlBackMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (timelineAddMenu.selectedType === "") {
                                timelineAddMenu.close()
                            } else {
                                timelineAddMenu.selectedType = ""
                            }
                        }
                    }
                }

                Rectangle {
                    visible: timelineAddMenu.selectedType !== ""
                    Layout.fillWidth: true
                    height: 36
                    radius: 6
                    color: tlAddBtnMouse.containsMouse ? "#3ad98a" : "#4ecca3"

                    Text {
                        anchors.centerIn: parent
                        text: "Add Step"
                        font.pixelSize: 12
                        font.bold: true
                        color: "#000"
                    }

                    MouseArea {
                        id: tlAddBtnMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            var target = ""
                            if (timelineAddMenu.selectedType === "wait") {
                                target = "Wait " + tlWaitTimeInput.text + "ms"
                            } else if (timelineAddMenu.selectedType === "input") {
                                target = tlSelectorInput.text + " → " + tlValueInput.text
                            } else if (timelineAddMenu.selectedType === "keydown") {
                                target = tlSelectorInput.text + " [" + tlKeyInput.text + "]"
                            } else {
                                target = tlSelectorInput.text
                            }
                            timelineModel.addStep(timelineAddMenu.stepIndex, timelineAddMenu.selectedType, target)
                            timelineAddMenu.close()
                        }
                    }
                }
            }
        }
    }

    // Timeline Delete Confirmation Dialog (for Recording tab)
    Popup {
        id: timelineDeleteDialog
        property int stepIndex: -1
        property string stepType: ""

        width: 320
        height: 160
        modal: true
        anchors.centerIn: Overlay.overlay

        background: Rectangle {
            color: "#16213e"
            radius: 12
            border.color: "#e94560"
            border.width: 2
        }

        contentItem: ColumnLayout {
            spacing: 16

            Text {
                text: "Delete Step?"
                font.pixelSize: 18
                font.bold: true
                color: "#e0e0e0"
                Layout.alignment: Qt.AlignHCenter
            }

            Text {
                text: "Delete " + timelineDeleteDialog.stepType + " step #" + (timelineDeleteDialog.stepIndex + 1) + "?"
                font.pixelSize: 14
                color: "#888"
                Layout.alignment: Qt.AlignHCenter
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Button {
                    Layout.fillWidth: true
                    text: "Cancel"
                    onClicked: timelineDeleteDialog.close()

                    background: Rectangle {
                        radius: 6
                        color: parent.hovered ? "#2a4a70" : "#0f3460"
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "#e0e0e0"
                        font.pixelSize: 14
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Button {
                    Layout.fillWidth: true
                    text: "Delete"
                    onClicked: {
                        timelineModel.deleteStep(timelineDeleteDialog.stepIndex)
                        timelineDeleteDialog.close()
                    }

                    background: Rectangle {
                        radius: 6
                        color: parent.hovered ? "#ff5a7a" : "#e94560"
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "#fff"
                        font.pixelSize: 14
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }

    // Edit Step Dialog
    Popup {
        id: timelineEditDialog
        property int stepIndex: -1
        property string stepType: ""
        property string stepTarget: ""

        width: 420
        height: 280
        modal: true
        anchors.centerIn: Overlay.overlay

        onOpened: {
            editTypeCombo.currentIndex = ["click", "input", "change", "keydown", "submit", "scroll", "wait"].indexOf(stepType)
            if (editTypeCombo.currentIndex < 0) editTypeCombo.currentIndex = 0
            editTargetInput.text = stepTarget
        }

        background: Rectangle {
            color: "#16213e"
            radius: 12
            border.color: "#ffc93c"
            border.width: 2
        }

        contentItem: ColumnLayout {
            spacing: 16
            anchors.margins: 20

            Text {
                text: "Edit Step #" + (timelineEditDialog.stepIndex + 1)
                font.pixelSize: 18
                font.bold: true
                color: "#e0e0e0"
                Layout.alignment: Qt.AlignHCenter
            }

            // Step type
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Text {
                    text: "Step Type"
                    font.pixelSize: 12
                    color: "#888"
                }

                ComboBox {
                    id: editTypeCombo
                    Layout.fillWidth: true
                    model: ["click", "input", "change", "keydown", "submit", "scroll", "wait"]

                    background: Rectangle {
                        radius: 6
                        color: "#0f3460"
                        border.color: "#2a4a70"
                    }

                    contentItem: Text {
                        leftPadding: 12
                        text: editTypeCombo.displayText
                        font.pixelSize: 14
                        color: "#e0e0e0"
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            // Target/Selector
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Text {
                    text: "Target/Selector"
                    font.pixelSize: 12
                    color: "#888"
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 40
                    radius: 6
                    color: "#0f3460"
                    border.color: editTargetInput.activeFocus ? "#ffc93c" : "#2a4a70"

                    TextInput {
                        id: editTargetInput
                        anchors.fill: parent
                        anchors.margins: 12
                        font.pixelSize: 14
                        font.family: "Consolas"
                        color: "#e0e0e0"
                        selectByMouse: true
                        verticalAlignment: TextInput.AlignVCenter
                        clip: true
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Button {
                    Layout.fillWidth: true
                    text: "Cancel"
                    onClicked: timelineEditDialog.close()

                    background: Rectangle {
                        radius: 6
                        color: parent.hovered ? "#2a4a70" : "#0f3460"
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "#e0e0e0"
                        font.pixelSize: 14
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Button {
                    Layout.fillWidth: true
                    text: "Save"
                    onClicked: {
                        timelineModel.updateStep(timelineEditDialog.stepIndex, editTypeCombo.currentText, editTargetInput.text)
                        timelineEditDialog.close()
                    }

                    background: Rectangle {
                        radius: 6
                        color: parent.hovered ? "#e6b336" : "#ffc93c"
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "#1a1a2e"
                        font.pixelSize: 14
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }

    // Connections to controller signals
    Connections {
        target: controller
        function onStatusMessage(msg) {
            statusLabel.text = msg
        }
        function onReplayStateChanged(running) {
            window.isReplaying = running
        }
        function onRecordingStateChanged(recording) {
            window.isRecording = recording
        }
        function onWorkflowCreated(path) {
            window.selectedWorkflowPath = path
        }
        function onReplayStepResult(result) {
            // Update summary counts
            if (result.status === "passed") {
                replayTab.passedCount++
                replayTab.totalDuration += result.duration
            } else if (result.status === "failed") {
                replayTab.failedCount++
                replayTab.totalDuration += result.duration
            }
        }
        function onReplayCompleted(success, error, totalDuration) {
            replayTab.totalDuration = totalDuration
            if (!success && error) {
                statusLabel.text = "Replay failed: " + error
            }
        }
        function onWorkflowLoadedForEdit(path, baseUrl, stepCount) {
            // Set edit mode and populate URL
            window.isEditMode = true
            window.editingWorkflowPath = path
            urlInput.text = baseUrl
        }
    }
    
    // Initialize on startup
    Component.onCompleted: {
        controller.refresh_workflow_list()
        statusLabel.text = "Ready - Test Library loaded"
    }
}
