import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4

/**
 * Step Detail Panel - Complete version with all features
 */
Item {
    id: root

    property string workflowPath: ""

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        // Header
        Rectangle {
            Layout.fillWidth: true
            height: 40
            color: "#0f3460"
            radius: 6

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                Text {
                    text: stepDetailModel.getStepCount() > 0 ? stepDetailModel.getWorkflowName() : "Select a Workflow"
                    font.pixelSize: 16
                    font.bold: true
                    color: "#e0e0e0"
                    Layout.fillWidth: true
                }

                Text {
                    text: stepDetailModel.getStepCount() + " steps"
                    font.pixelSize: 12
                    color: "#4ecca3"
                    visible: stepDetailModel.getStepCount() > 0
                }
            }
        }

        // Step list
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#0f3460"
            radius: 6

            Text {
                anchors.centerIn: parent
                text: "Click a workflow to see steps"
                color: "#666"
                visible: stepListView.count === 0
            }

            ListView {
                id: stepListView
                anchors.fill: parent
                anchors.margins: 8
                model: stepDetailModel
                clip: true
                spacing: 6

                delegate: Rectangle {
                    id: stepRow
                    width: stepListView.width
                    height: isExpanded ? Math.max(expandedContent.height + 80, 180) : 60
                    radius: 8
                    color: mouseArea.containsMouse ? "#1a4a80" : "#16213e"
                    border.color: isExpanded ? "#e94560" : "#2a4a70"
                    border.width: isExpanded ? 2 : 1
                    z: isExpanded ? 100 : 0  // Bring expanded step to front

                    property bool isExpanded: false

                    Behavior on height { NumberAnimation { duration: 150 } }

                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: stepRow.isExpanded = !stepRow.isExpanded
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        // Header row
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            // Step number
                            Rectangle {
                                width: 28
                                height: 28
                                radius: 14
                                color: model.type === "click" ? "#e94560" : (model.type === "input" ? "#4ecca3" : "#7b68ee")

                                Text {
                                    anchors.centerIn: parent
                                    text: (model.stepIndex + 1).toString()
                                    font.bold: true
                                    font.pixelSize: 11
                                    color: "white"
                                }
                            }

                            // Step info
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1

                                Text {
                                    text: model.type ? (model.type.charAt(0).toUpperCase() + model.type.slice(1)) : "Step"
                                    font.pixelSize: 13
                                    font.bold: true
                                    color: "#e0e0e0"
                                }

                                Text {
                                    text: model.semanticIntent || model.targetText || "No target"
                                    font.pixelSize: 10
                                    color: model.semanticIntent ? "#4ecca3" : "#888"
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }

                            // Screenshot icon
                            Rectangle {
                                visible: model.hasScreenshot
                                width: 26
                                height: 26
                                radius: 5
                                color: ssMouseArea.containsMouse ? "#4ecca3" : "#0f3460"

                                Text {
                                    anchors.centerIn: parent
                                    text: "📷"
                                    font.pixelSize: 12
                                }

                                MouseArea {
                                    id: ssMouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        screenshotPopup.imagePath = model.screenshotPath
                                        screenshotPopup.open()
                                    }
                                }
                            }

                            // Selector count
                            Rectangle {
                                visible: model.selectorCount > 0
                                width: 40
                                height: 20
                                radius: 10
                                color: "#0f3460"

                                Text {
                                    anchors.centerIn: parent
                                    text: model.selectorCount + "s"
                                    font.pixelSize: 9
                                    color: "#888"
                                }
                            }

                            // Configure step button
                            Rectangle {
                                width: 24
                                height: 24
                                radius: 4
                                color: configBtnMouse.containsMouse ? "#7b9aff" : "#0f3460"

                                Text {
                                    anchors.centerIn: parent
                                    text: "⚙"
                                    font.pixelSize: 14
                                    color: model.hasConfig ? "#4ecca3" : "#fff"
                                }

                                MouseArea {
                                    id: configBtnMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        stepConfigPopup.stepIndex = model.stepIndex
                                        stepConfigPopup.stepType = model.type
                                        stepConfigPopup.stepName = model.name || model.type
                                        stepConfigPopup.stepDescription = model.description || ""
                                        stepConfigPopup.currentConfig = model.config ? JSON.parse(model.config) : null
                                        stepConfigPopup.open()
                                    }
                                }

                                ToolTip {
                                    visible: configBtnMouse.containsMouse
                                    text: "Configure step"
                                    delay: 500
                                }
                            }

                            // Add step button
                            Rectangle {
                                width: 24
                                height: 24
                                radius: 4
                                color: addBtnMouse.containsMouse ? "#4ecca3" : "#0f3460"

                                Text {
                                    anchors.centerIn: parent
                                    text: "+"
                                    font.pixelSize: 16
                                    font.bold: true
                                    color: "#fff"
                                }

                                MouseArea {
                                    id: addBtnMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        addStepMenu.stepIndex = model.stepIndex
                                        addStepMenu.open()
                                    }
                                }
                            }

                            // Delete step button
                            Rectangle {
                                width: 24
                                height: 24
                                radius: 4
                                color: delBtnMouse.containsMouse ? "#e94560" : "#0f3460"

                                Text {
                                    anchors.centerIn: parent
                                    text: "×"
                                    font.pixelSize: 18
                                    font.bold: true
                                    color: "#fff"
                                }

                                MouseArea {
                                    id: delBtnMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        deleteConfirmDialog.stepIndex = model.stepIndex
                                        deleteConfirmDialog.stepType = model.type
                                        deleteConfirmDialog.open()
                                    }
                                }
                            }

                            // Expand arrow
                            Text {
                                text: stepRow.isExpanded ? "▲" : "▼"
                                font.pixelSize: 10
                                color: "#666"
                            }
                        }

                        // Expanded content - scrollable
                        Flickable {
                            id: expandedFlickable
                            visible: stepRow.isExpanded
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            contentHeight: expandedContent.height
                            clip: true
                            flickableDirection: Flickable.VerticalFlick
                            boundsBehavior: Flickable.StopAtBounds

                            ScrollBar.vertical: ScrollBar {
                                active: true
                                policy: ScrollBar.AsNeeded
                            }

                            ColumnLayout {
                                id: expandedContent
                                width: expandedFlickable.width
                                spacing: 8

                                Rectangle { Layout.fillWidth: true; height: 1; color: "#2a4a70" }

                            // AI Activity Section
                            Rectangle {
                                visible: model.semanticIntent || model.visualHash
                                Layout.fillWidth: true
                                height: aiCol.height + 12
                                radius: 6
                                color: "#0a1a2a"

                                ColumnLayout {
                                    id: aiCol
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: 6
                                    spacing: 4

                                    Text {
                                        text: "🤖 AI Analysis"
                                        font.pixelSize: 11
                                        font.bold: true
                                        color: "#7b68ee"
                                    }

                                    Text {
                                        visible: model.semanticIntent && model.semanticIntent !== ""
                                        text: "Intent: " + (model.semanticIntent || "")
                                        font.pixelSize: 10
                                        color: "#4ecca3"
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }

                                    Text {
                                        visible: model.visualHash && model.visualHash !== ""
                                        text: "Visual Hash: " + (model.visualHash || "").substring(0, 20) + "..."
                                        font.pixelSize: 9
                                        color: "#888"
                                    }
                                }
                            }

                            // Selectors Section Header
                            RowLayout {
                                visible: model.selectorCount > 0
                                Layout.fillWidth: true
                                spacing: 8

                                Text {
                                    text: "🎯 Selectors (click to set primary)"
                                    font.pixelSize: 11
                                    font.bold: true
                                    color: "#4ecca3"
                                }

                                Item { Layout.fillWidth: true }

                                // Add new selector button
                                Rectangle {
                                    width: 70
                                    height: 20
                                    radius: 4
                                    color: addSelMouse.containsMouse ? "#4ecca3" : "#0f3460"

                                    Text {
                                        anchors.centerIn: parent
                                        text: "+ Add"
                                        font.pixelSize: 10
                                        color: "#fff"
                                    }

                                    MouseArea {
                                        id: addSelMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            editSelectorDialog.stepIndex = model.stepIndex
                                            editSelectorDialog.selectorType = "css"
                                            editSelectorDialog.selectorValue = ""
                                            editSelectorDialog.open()
                                        }
                                    }
                                }
                            }

                            Repeater {
                                model: {
                                    try {
                                        return JSON.parse(selectors || "[]")
                                    } catch(e) {
                                        return []
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 36
                                    radius: 5
                                    color: selectorMouse.containsMouse ? "#2a4a70" : (modelData.is_primary ? "#1a3a4a" : "#0a1a2a")
                                    border.color: modelData.is_primary ? "#4ecca3" : "transparent"
                                    border.width: modelData.is_primary ? 2 : 0

                                    MouseArea {
                                        id: selectorMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            // Use model.stepIndex from the ListView delegate
                                            stepDetailModel.setPrimarySelector(model.stepIndex, index)
                                        }
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        spacing: 6

                                        // Primary indicator
                                        Rectangle {
                                            width: 14
                                            height: 14
                                            radius: 7
                                            color: modelData.is_primary ? "#4ecca3" : "#333"
                                            border.color: "#4ecca3"
                                            border.width: 1

                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData.is_primary ? "✓" : ""
                                                font.pixelSize: 8
                                                color: "#fff"
                                            }
                                        }

                                        // Type
                                        Rectangle {
                                            width: 35
                                            height: 16
                                            radius: 3
                                            color: "#1a2a3a"

                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData.type || "css"
                                                font.pixelSize: 8
                                                font.bold: true
                                                color: "#ffc93c"
                                            }
                                        }

                                        // Value
                                        Text {
                                            text: modelData.value || ""
                                            font.pixelSize: 9
                                            font.family: "Consolas"
                                            color: "#ccc"
                                            elide: Text.ElideMiddle
                                            Layout.fillWidth: true
                                        }

                                        // Score
                                        Rectangle {
                                            width: 36
                                            height: 16
                                            radius: 3
                                            color: (modelData.score || 0) >= 0.8 ? "#1a4a30" : "#3a3a1a"

                                            Text {
                                                anchors.centerIn: parent
                                                text: ((modelData.score || 0) * 100).toFixed(0) + "%"
                                                font.pixelSize: 9
                                                font.bold: true
                                                color: (modelData.score || 0) >= 0.8 ? "#4ecca3" : "#ffc93c"
                                            }
                                        }
                                    }
                                }
                            }

                        }
                        }  // Close Flickable
                    }
                }
            }
        }
    }

    // Screenshot Popup
    Popup {
        id: screenshotPopup
        property string imagePath: ""

        width: 500
        height: 400
        modal: true
        anchors.centerIn: Overlay.overlay

        background: Rectangle {
            color: "#16213e"
            radius: 12
            border.color: "#e94560"
            border.width: 2
        }

        contentItem: ColumnLayout {
            spacing: 10

            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: "📷 Element Screenshot"
                    font.pixelSize: 14
                    font.bold: true
                    color: "#e0e0e0"
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    width: 24
                    height: 24
                    radius: 12
                    color: closeMouse.containsMouse ? "#e94560" : "#0f3460"

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: "#fff"
                    }

                    MouseArea {
                        id: closeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: screenshotPopup.close()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#0f3460"
                radius: 8

                Image {
                    anchors.fill: parent
                    anchors.margins: 10
                    source: screenshotPopup.imagePath ? "file:///" + screenshotPopup.imagePath : ""
                    fillMode: Image.PreserveAspectFit

                    Text {
                        anchors.centerIn: parent
                        visible: parent.status === Image.Error
                        text: "Could not load image"
                        color: "#666"
                    }
                }
            }

            Text {
                text: screenshotPopup.imagePath
                font.pixelSize: 8
                color: "#555"
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
        }
    }

    // Add Step Dialog - Comprehensive with all step details
    Popup {
        id: addStepMenu
        property int stepIndex: -1
        property string selectedType: ""
        property string selectedCategory: ""

        width: 500
        height: selectedType === "" ? 520 : 400
        modal: true
        anchors.centerIn: Overlay.overlay

        onClosed: {
            selectedType = ""
            selectedCategory = ""
            selectorInput.text = ""
            valueInput.text = ""
            waitTimeInput.text = "1000"
            waitTypeCombo.currentIndex = 0
            keyInput.text = ""
        }

        background: Rectangle {
            color: "#16213e"
            border.color: "#4ecca3"
            border.width: 2
            radius: 12
        }

        contentItem: ColumnLayout {
            spacing: 12
            anchors.margins: 16

            // Header
            Text {
                text: addStepMenu.selectedType === "" ?
                    "Add Step After #" + (addStepMenu.stepIndex + 1) :
                    "Configure " + addStepMenu.selectedType.charAt(0).toUpperCase() + addStepMenu.selectedType.slice(1) + " Step"
                font.pixelSize: 16
                font.bold: true
                color: "#e0e0e0"
                Layout.alignment: Qt.AlignHCenter
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: "#2a4a70" }

            // Step Type Selection (shown when no type selected)
            ScrollView {
                visible: addStepMenu.selectedType === ""
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                ColumnLayout {
                    width: parent.width
                    spacing: 12

                    // Interactions Category
                    Text {
                        text: "🖱️ Interactions"
                        font.pixelSize: 13
                        font.bold: true
                        color: "#e94560"
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: [
                                {type: "click", label: "Click", color: "#e94560"},
                                {type: "dblclick", label: "Double Click", color: "#e94560"},
                                {type: "contextmenu", label: "Right Click", color: "#e94560"},
                                {type: "hover", label: "Hover", color: "#e94560"},
                                {type: "scroll", label: "Scroll", color: "#e94560"},
                                {type: "dragTo", label: "Drag To", color: "#e94560"}
                            ]

                            Rectangle {
                                width: 90
                                height: 36
                                radius: 6
                                property bool isHovered: false
                                color: isHovered ? modelData.color : "#0f3460"
                                border.color: modelData.color
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: "#fff"
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onContainsMouseChanged: parent.isHovered = containsMouse
                                    onClicked: addStepMenu.selectedType = modelData.type
                                }
                            }
                        }
                    }

                    // Input Category
                    Text {
                        text: "⌨️ Input"
                        font.pixelSize: 13
                        font.bold: true
                        color: "#4ecca3"
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: [
                                {type: "input", label: "Type Text", color: "#4ecca3"},
                                {type: "press", label: "Press Key", color: "#4ecca3"},
                                {type: "selectOption", label: "Select", color: "#4ecca3"},
                                {type: "check", label: "Check", color: "#4ecca3"},
                                {type: "uncheck", label: "Uncheck", color: "#4ecca3"},
                                {type: "submit", label: "Submit", color: "#4ecca3"}
                            ]

                            Rectangle {
                                width: 90
                                height: 36
                                radius: 6
                                property bool isHovered: false
                                color: isHovered ? modelData.color : "#0f3460"
                                border.color: modelData.color
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: isHovered ? "#000" : "#fff"
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onContainsMouseChanged: parent.isHovered = containsMouse
                                    onClicked: addStepMenu.selectedType = modelData.type
                                }
                            }
                        }
                    }

                    // Frame/Window Category
                    Text {
                        text: "🪟 Frame & Window"
                        font.pixelSize: 13
                        font.bold: true
                        color: "#ffc93c"
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: [
                                {type: "switchFrame", label: "Switch Frame", color: "#ffc93c"},
                                {type: "switchMainFrame", label: "Main Frame", color: "#ffc93c"},
                                {type: "switchParentFrame", label: "Parent Frame", color: "#ffc93c"},
                                {type: "switchWindow", label: "Switch Window", color: "#ffc93c"},
                                {type: "switchNewWindow", label: "New Window", color: "#ffc93c"},
                                {type: "closeWindow", label: "Close Window", color: "#ffc93c"}
                            ]

                            Rectangle {
                                width: 90
                                height: 36
                                radius: 6
                                property bool isHovered: false
                                color: isHovered ? modelData.color : "#0f3460"
                                border.color: modelData.color
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: isHovered ? "#000" : "#fff"
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onContainsMouseChanged: parent.isHovered = containsMouse
                                    onClicked: addStepMenu.selectedType = modelData.type
                                }
                            }
                        }
                    }

                    // Dialog Category
                    Text {
                        text: "💬 Dialogs"
                        font.pixelSize: 13
                        font.bold: true
                        color: "#ff9800"
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: [
                                {type: "handleAlert", label: "Handle Alert", color: "#ff9800"},
                                {type: "handleConfirm", label: "Handle Confirm", color: "#ff9800"},
                                {type: "handlePrompt", label: "Handle Prompt", color: "#ff9800"}
                            ]

                            Rectangle {
                                width: 100
                                height: 36
                                radius: 6
                                property bool isHovered: false
                                color: isHovered ? modelData.color : "#0f3460"
                                border.color: modelData.color
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: isHovered ? "#000" : "#fff"
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onContainsMouseChanged: parent.isHovered = containsMouse
                                    onClicked: addStepMenu.selectedType = modelData.type
                                }
                            }
                        }
                    }

                    // Variables Category
                    Text {
                        text: "📦 Variables"
                        font.pixelSize: 13
                        font.bold: true
                        color: "#7b68ee"
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: [
                                {type: "storeVariable", label: "Store Variable", color: "#7b68ee"},
                                {type: "storeText", label: "Store Text", color: "#7b68ee"},
                                {type: "storeValue", label: "Store Value", color: "#7b68ee"},
                                {type: "storeAttribute", label: "Store Attr", color: "#7b68ee"},
                                {type: "assertVariable", label: "Assert Var", color: "#7b68ee"}
                            ]

                            Rectangle {
                                width: 90
                                height: 36
                                radius: 6
                                property bool isHovered: false
                                color: isHovered ? modelData.color : "#0f3460"
                                border.color: modelData.color
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: "#fff"
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onContainsMouseChanged: parent.isHovered = containsMouse
                                    onClicked: addStepMenu.selectedType = modelData.type
                                }
                            }
                        }
                    }

                    // Wait & Assert Category
                    Text {
                        text: "⏳ Wait & Assert"
                        font.pixelSize: 13
                        font.bold: true
                        color: "#00bcd4"
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: [
                                {type: "wait", label: "Wait (ms)", color: "#00bcd4"},
                                {type: "waitForElement", label: "Wait Element", color: "#00bcd4"},
                                {type: "waitForNavigation", label: "Wait Nav", color: "#00bcd4"},
                                {type: "assertText", label: "Assert Text", color: "#00bcd4"},
                                {type: "assertVisible", label: "Assert Visible", color: "#00bcd4"},
                                {type: "assertEnabled", label: "Assert Enabled", color: "#00bcd4"},
                                {type: "screenshot", label: "Screenshot", color: "#00bcd4"}
                            ]

                            Rectangle {
                                width: 90
                                height: 36
                                radius: 6
                                property bool isHovered: false
                                color: isHovered ? modelData.color : "#0f3460"
                                border.color: modelData.color
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: isHovered ? "#000" : "#fff"
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onContainsMouseChanged: parent.isHovered = containsMouse
                                    onClicked: addStepMenu.selectedType = modelData.type
                                }
                            }
                        }
                    }
                }
            }

            // Step Configuration (shown when type is selected)
            ColumnLayout {
                visible: addStepMenu.selectedType !== ""
                spacing: 12
                Layout.fillWidth: true

                // Define which actions need selectors
                property var needsSelector: [
                    "click", "dblclick", "contextmenu", "hover", "scroll", "dragTo",
                    "input", "selectOption", "check", "uncheck", "submit",
                    "switchFrame", "storeText", "storeValue", "storeAttribute",
                    "waitForElement", "assertText", "assertVisible", "assertEnabled", "assertChecked"
                ]
                // Define which actions need a value input
                property var needsValue: [
                    "input", "storeVariable", "assertVariable", "wait", "waitForNavigation",
                    "handlePrompt", "switchWindow", "switchFrameByName", "switchFrameByIndex",
                    "switchWindowByIndex", "screenshot", "press", "waitForUrl"
                ]

                // Selector Type & Value (for actions that need element selection)
                ColumnLayout {
                    visible: parent.needsSelector.indexOf(addStepMenu.selectedType) !== -1
                    spacing: 6
                    Layout.fillWidth: true

                    Text {
                        text: "Element Selector"
                        font.pixelSize: 12
                        font.bold: true
                        color: "#4ecca3"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        ComboBox {
                            id: selectorTypeCombo
                            model: ["css", "xpath", "id", "name", "text", "aria", "data"]
                            implicitWidth: 80

                            background: Rectangle {
                                color: "#0f3460"
                                radius: 4
                                border.color: "#2a4a70"
                            }
                            contentItem: Text {
                                text: selectorTypeCombo.currentText
                                color: "#e0e0e0"
                                font.pixelSize: 12
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 8
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 36
                            radius: 4
                            color: "#0f3460"
                            border.color: selectorInput.activeFocus ? "#4ecca3" : "#2a4a70"

                            TextInput {
                                id: selectorInput
                                anchors.fill: parent
                                anchors.margins: 8
                                anchors.rightMargin: 36
                                color: "#e0e0e0"
                                font.pixelSize: 12
                                font.family: "Consolas"
                                clip: true
                                verticalAlignment: TextInput.AlignVCenter

                                Text {
                                    anchors.fill: parent
                                    text: "e.g., #submit-btn, .login-form input"
                                    color: "#666"
                                    font.pixelSize: 12
                                    visible: !selectorInput.text && !selectorInput.activeFocus
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }

                            // Selector lookup button
                            Rectangle {
                                anchors.right: parent.right
                                anchors.rightMargin: 4
                                anchors.verticalCenter: parent.verticalCenter
                                width: 28
                                height: 28
                                radius: 4
                                color: selectorLookupBtnMouse.containsMouse ? "#4ecca3" : "#1a3a50"

                                Text {
                                    anchors.centerIn: parent
                                    text: "🎯"
                                    font.pixelSize: 14
                                }

                                MouseArea {
                                    id: selectorLookupBtnMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: selectorLookupPopup.open()
                                }

                                ToolTip {
                                    visible: selectorLookupBtnMouse.containsMouse
                                    text: "Browse selectors"
                                    delay: 300
                                }
                            }
                        }
                    }
                }

                // Generic Value Input (for actions that need a value)
                ColumnLayout {
                    visible: parent.needsValue.indexOf(addStepMenu.selectedType) !== -1
                    spacing: 6
                    Layout.fillWidth: true

                    Text {
                        text: {
                            var t = addStepMenu.selectedType
                            if (t === "input") return "Text to Type"
                            if (t === "storeVariable") return "Variable (name=value)"
                            if (t === "assertVariable") return "Assertion (name==value)"
                            if (t === "wait" || t === "waitForNavigation") return "Timeout (ms)"
                            if (t === "handlePrompt") return "Prompt Response Text"
                            if (t === "switchWindow") return "Window Title/URL Pattern"
                            if (t === "switchFrameByName") return "Frame Name or ID"
                            if (t === "switchFrameByIndex" || t === "switchWindowByIndex") return "Index (0-based)"
                            if (t === "screenshot") return "Filename"
                            if (t === "press") return "Key (e.g., Enter, Tab, Escape)"
                            if (t === "waitForUrl") return "URL Pattern"
                            return "Value"
                        }
                        font.pixelSize: 12
                        font.bold: true
                        color: "#4ecca3"
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 36
                        radius: 4
                        color: "#0f3460"
                        border.color: valueInput.activeFocus ? "#4ecca3" : "#2a4a70"

                        TextInput {
                            id: valueInput
                            anchors.fill: parent
                            anchors.margins: 8
                            anchors.rightMargin: 36
                            color: "#e0e0e0"
                            font.pixelSize: 12
                            clip: true
                            verticalAlignment: TextInput.AlignVCenter
                            text: {
                                var t = addStepMenu.selectedType
                                if (t === "wait" || t === "waitForNavigation") return "1000"
                                if (t === "storeVariable") return "myVar=value"
                                if (t === "assertVariable") return "myVar==expectedValue"
                                if (t === "screenshot") return "screenshot.png"
                                if (t === "press") return "Enter"
                                if (t === "switchFrameByIndex" || t === "switchWindowByIndex") return "0"
                                return ""
                            }

                            Text {
                                anchors.fill: parent
                                text: {
                                    var t = addStepMenu.selectedType
                                    if (t === "input") return "Text to type..."
                                    if (t === "storeVariable") return "variableName=value"
                                    if (t === "assertVariable") return "variableName==expected"
                                    return "Enter value..."
                                }
                                color: "#666"
                                font.pixelSize: 12
                                visible: !valueInput.text && !valueInput.activeFocus
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        // Variable helper button
                        Rectangle {
                            anchors.right: parent.right
                            anchors.rightMargin: 4
                            anchors.verticalCenter: parent.verticalCenter
                            width: 28
                            height: 28
                            radius: 4
                            color: varHelperBtnMouse.containsMouse ? "#7b68ee" : "#1a3a50"

                            Text {
                                anchors.centerIn: parent
                                text: "📦"
                                font.pixelSize: 14
                            }

                            MouseArea {
                                id: varHelperBtnMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: variableHelperPopup.open()
                            }

                            ToolTip {
                                visible: varHelperBtnMouse.containsMouse
                                text: "Browse variables & expressions"
                                delay: 300
                            }
                        }
                    }
                }

                // Dialog action type (accept/dismiss)
                ColumnLayout {
                    visible: addStepMenu.selectedType === "handleAlert" || addStepMenu.selectedType === "handleConfirm"
                    spacing: 6
                    Layout.fillWidth: true

                    property bool acceptSelected: true

                    Text {
                        text: "Action"
                        font.pixelSize: 12
                        font.bold: true
                        color: "#4ecca3"
                    }

                    RowLayout {
                        spacing: 12

                        Rectangle {
                            width: 100
                            height: 36
                            radius: 6
                            color: parent.parent.acceptSelected ? "#4ecca3" : "#0f3460"
                            border.color: "#4ecca3"

                            Text {
                                anchors.centerIn: parent
                                text: "Accept"
                                font.pixelSize: 12
                                font.bold: true
                                color: parent.parent.parent.acceptSelected ? "#000" : "#fff"
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: parent.parent.parent.acceptSelected = true
                            }
                        }

                        Rectangle {
                            width: 100
                            height: 36
                            radius: 6
                            color: !parent.parent.acceptSelected ? "#e94560" : "#0f3460"
                            border.color: "#e94560"

                            Text {
                                anchors.centerIn: parent
                                text: "Dismiss"
                                font.pixelSize: 12
                                font.bold: true
                                color: "#fff"
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: parent.parent.parent.acceptSelected = false
                            }
                        }
                    }
                }

                // No configuration needed message
                Text {
                    visible: {
                        var t = addStepMenu.selectedType
                        var noConfig = ["switchMainFrame", "switchParentFrame", "closeWindow", "switchNewWindow", "waitForNavigation"]
                        return noConfig.indexOf(t) !== -1
                    }
                    text: "This action requires no additional configuration."
                    font.pixelSize: 12
                    font.italic: true
                    color: "#888"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }

                // Help text for certain actions
                Text {
                    visible: addStepMenu.selectedType === "storeVariable" || addStepMenu.selectedType === "assertVariable"
                    text: addStepMenu.selectedType === "storeVariable" ?
                        "Use ${variableName} in other steps to reference this value." :
                        "Operators: == (equals), != (not equals)"
                    font.pixelSize: 10
                    color: "#7b68ee"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
            }

            Item { Layout.fillHeight: true }

            // Action Buttons
            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    height: 40
                    radius: 6
                    color: backBtnMouse.containsMouse ? "#2a4a70" : "#0f3460"

                    Text {
                        anchors.centerIn: parent
                        text: addStepMenu.selectedType === "" ? "Cancel" : "← Back"
                        font.pixelSize: 13
                        color: "#e0e0e0"
                    }

                    MouseArea {
                        id: backBtnMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (addStepMenu.selectedType === "") {
                                addStepMenu.close()
                            } else {
                                addStepMenu.selectedType = ""
                            }
                        }
                    }
                }

                Rectangle {
                    visible: addStepMenu.selectedType !== ""
                    Layout.fillWidth: true
                    height: 40
                    radius: 6
                    color: addBtnMouse.containsMouse ? "#3ad98a" : "#4ecca3"

                    Text {
                        anchors.centerIn: parent
                        text: "Add Step"
                        font.pixelSize: 13
                        font.bold: true
                        color: "#000"
                    }

                    MouseArea {
                        id: addBtnMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            var stepData = {
                                type: addStepMenu.selectedType,
                                selectorType: selectorTypeCombo.currentText,
                                selector: selectorInput.text,
                                value: valueInput.text
                            }
                            console.log("Adding step:", JSON.stringify(stepData))
                            controller.add_step_full(addStepMenu.stepIndex, JSON.stringify(stepData))
                            addStepMenu.close()
                        }
                    }
                }
            }
        }
    }

    // Step Configuration Popup
    Popup {
        id: stepConfigPopup
        property int stepIndex: -1
        property string stepType: ""
        property string stepName: ""
        property string stepDescription: ""
        property var currentConfig: null

        width: 850
        height: 720
        modal: true
        anchors.centerIn: Overlay.overlay
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: "#16213e"
            radius: 12
            border.color: "#7b9aff"
            border.width: 2
        }

        contentItem: ColumnLayout {
            spacing: 12

            // Header
            RowLayout {
                Layout.fillWidth: true
                Layout.margins: 16
                Layout.bottomMargin: 0

                Text {
                    text: "⚙️ Configure Step"
                    font.pixelSize: 16
                    font.bold: true
                    color: "#e0e0e0"
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: stepConfigPopup.stepName + " (" + stepConfigPopup.stepType + ")"
                    font.pixelSize: 12
                    color: "#7b9aff"
                }

                Rectangle {
                    width: 28
                    height: 28
                    radius: 14
                    color: closeConfigMouse.containsMouse ? "#e94560" : "#0f3460"

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.pixelSize: 14
                        color: "#fff"
                    }

                    MouseArea {
                        id: closeConfigMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: stepConfigPopup.close()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                height: 1
                color: "#2a4a70"
            }

            // Step Name and Description
            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                spacing: 8

                // Step Name
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: "Step Name"
                        font.pixelSize: 11
                        font.bold: true
                        color: "#9aa8b8"
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 32
                        radius: 6
                        color: "#1a2a3a"
                        border.color: stepNameInput.activeFocus ? "#4a9eff" : "#2a3a4a"
                        border.width: 1

                        TextInput {
                            id: stepNameInput
                            anchors.fill: parent
                            anchors.margins: 8
                            text: stepConfigPopup.stepName
                            font.pixelSize: 12
                            color: "#e0e8f0"
                            selectByMouse: true
                            clip: true

                            onTextChanged: {
                                stepConfigPopup.stepName = text
                            }
                        }
                    }
                }

                // Step Description
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: "Description (optional)"
                        font.pixelSize: 11
                        font.bold: true
                        color: "#9aa8b8"
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 60
                        radius: 6
                        color: "#1a2a3a"
                        border.color: stepDescInput.activeFocus ? "#4a9eff" : "#2a3a4a"
                        border.width: 1

                        Flickable {
                            id: descFlickable
                            anchors.fill: parent
                            anchors.margins: 8
                            contentHeight: stepDescInput.contentHeight
                            clip: true

                            TextEdit {
                                id: stepDescInput
                                width: descFlickable.width
                                text: stepConfigPopup.stepDescription
                                font.pixelSize: 11
                                color: "#c0c8d0"
                                wrapMode: TextEdit.Wrap
                                selectByMouse: true

                                Text {
                                    visible: !stepDescInput.text
                                    text: "Describe what this step does..."
                                    font.pixelSize: 11
                                    color: "#5a6a7a"
                                }

                                onTextChanged: {
                                    stepConfigPopup.stepDescription = text
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                height: 1
                color: "#2a4a70"
            }

            // Scrollable config content
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 16
                Layout.topMargin: 0
                color: "#0a1525"
                radius: 8

                Flickable {
                    id: configFlickable
                    anchors.fill: parent
                    anchors.margins: 8
                    anchors.rightMargin: 24
                    contentHeight: configPanelInPopup.height
                    clip: true
                    flickableDirection: Flickable.VerticalFlick
                    boundsBehavior: Flickable.StopAtBounds

                    StepConfigPanel {
                        id: configPanelInPopup
                        width: configFlickable.width
                        stepType: stepConfigPopup.stepType
                        stepConfig: stepConfigPopup.currentConfig
                        onConfigChanged: function(config) {
                            stepConfigPopup.currentConfig = config
                        }
                    }
                }

                // Always visible scrollbar
                ScrollBar {
                    id: configScrollBar
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: 4
                    width: 8
                    policy: ScrollBar.AlwaysOn
                    orientation: Qt.Vertical
                    size: configFlickable.height / configFlickable.contentHeight
                    position: configFlickable.visibleArea.yPosition

                    background: Rectangle {
                        color: "#1a2a3a"
                        radius: 4
                    }

                    contentItem: Rectangle {
                        implicitWidth: 8
                        radius: 4
                        color: configScrollBar.pressed ? "#6ab0ff" : (configScrollBar.hovered ? "#5aa0ef" : "#4a90df")
                    }

                    onPositionChanged: {
                        if (pressed) {
                            configFlickable.contentY = position * configFlickable.contentHeight
                        }
                    }
                }

                // Connect flickable to scrollbar
                Connections {
                    target: configFlickable
                    function onContentYChanged() {
                        if (!configScrollBar.pressed) {
                            configScrollBar.position = configFlickable.contentY / configFlickable.contentHeight
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                height: 1
                color: "#2a4a70"
            }

            // Footer buttons
            RowLayout {
                Layout.fillWidth: true
                Layout.margins: 16
                Layout.topMargin: 8
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: 6
                    color: resetMouse.containsMouse ? "#3a4a5a" : "#2a3a4a"

                    Text {
                        anchors.centerIn: parent
                        text: "Reset to Defaults"
                        font.pixelSize: 12
                        color: "#aaa"
                    }

                    MouseArea {
                        id: resetMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            stepConfigPopup.currentConfig = null
                            stepDetailModel.updateStepConfig(stepConfigPopup.stepIndex, "")
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: 6
                    color: saveMouse.containsMouse ? "#5ab0ff" : "#4a9eff"

                    Text {
                        anchors.centerIn: parent
                        text: "Save Configuration"
                        font.pixelSize: 12
                        font.bold: true
                        color: "#fff"
                    }

                    MouseArea {
                        id: saveMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            // Save name and description
                            stepDetailModel.updateStepField(stepConfigPopup.stepIndex, "name", stepConfigPopup.stepName)
                            stepDetailModel.updateStepField(stepConfigPopup.stepIndex, "description", stepConfigPopup.stepDescription)

                            // Save config
                            if (stepConfigPopup.currentConfig) {
                                stepDetailModel.updateStepConfig(
                                    stepConfigPopup.stepIndex,
                                    JSON.stringify(stepConfigPopup.currentConfig)
                                )
                            }
                            stepConfigPopup.close()
                        }
                    }
                }
            }
        }
    }

    // Delete Confirmation Dialog
    Popup {
        id: deleteConfirmDialog
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
            anchors.margins: 16

            Text {
                text: "🗑️ Delete Step?"
                font.pixelSize: 16
                font.bold: true
                color: "#e0e0e0"
                Layout.alignment: Qt.AlignHCenter
            }

            Text {
                text: "Are you sure you want to delete step " + (deleteConfirmDialog.stepIndex + 1) + " (" + deleteConfirmDialog.stepType + ")?"
                font.pixelSize: 13
                color: "#aaa"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: 6
                    color: cancelDelMouse.containsMouse ? "#2a4a70" : "#0f3460"

                    Text {
                        anchors.centerIn: parent
                        text: "Cancel"
                        color: "#e0e0e0"
                        font.pixelSize: 13
                    }

                    MouseArea {
                        id: cancelDelMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: deleteConfirmDialog.close()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: 6
                    color: confirmDelMouse.containsMouse ? "#ff4560" : "#e94560"

                    Text {
                        anchors.centerIn: parent
                        text: "Delete"
                        color: "#fff"
                        font.bold: true
                        font.pixelSize: 13
                    }

                    MouseArea {
                        id: confirmDelMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            controller.delete_step(deleteConfirmDialog.stepIndex)
                            deleteConfirmDialog.close()
                        }
                    }
                }
            }
        }
    }

    // Edit Selector Dialog
    Popup {
        id: editSelectorDialog
        property int stepIndex: -1
        property string selectorType: "css"
        property string selectorValue: ""

        width: 450
        height: 220
        modal: true
        anchors.centerIn: Overlay.overlay

        background: Rectangle {
            color: "#16213e"
            radius: 12
            border.color: "#4ecca3"
            border.width: 2
        }

        contentItem: ColumnLayout {
            spacing: 12
            anchors.margins: 16

            Text {
                text: "✎ Edit Selector"
                font.pixelSize: 16
                font.bold: true
                color: "#e0e0e0"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    text: "Type:"
                    color: "#aaa"
                    font.pixelSize: 12
                }

                ComboBox {
                    id: editSelectorTypeCombo
                    model: ["css", "xpath", "id", "name", "text"]
                    currentIndex: 0
                    Layout.preferredWidth: 100

                    background: Rectangle {
                        color: "#0f3460"
                        radius: 4
                        border.color: "#2a4a70"
                    }

                    contentItem: Text {
                        text: editSelectorTypeCombo.currentText
                        color: "#e0e0e0"
                        font.pixelSize: 12
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: 8
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 36
                radius: 6
                color: "#0f3460"
                border.color: "#2a4a70"

                TextInput {
                    id: selectorValueInput
                    anchors.fill: parent
                    anchors.margins: 8
                    text: editSelectorDialog.selectorValue
                    color: "#e0e0e0"
                    font.pixelSize: 12
                    font.family: "Consolas"
                    clip: true
                    selectByMouse: true
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: 6
                    color: cancelEditMouse.containsMouse ? "#2a4a70" : "#0f3460"

                    Text {
                        anchors.centerIn: parent
                        text: "Cancel"
                        color: "#e0e0e0"
                        font.pixelSize: 13
                    }

                    MouseArea {
                        id: cancelEditMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: editSelectorDialog.close()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: 6
                    color: saveEditMouse.containsMouse ? "#3dcc93" : "#4ecca3"

                    Text {
                        anchors.centerIn: parent
                        text: "Save"
                        color: "#fff"
                        font.bold: true
                        font.pixelSize: 13
                    }

                    MouseArea {
                        id: saveEditMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            controller.update_step_selector(editSelectorDialog.stepIndex, editSelectorTypeCombo.currentText, selectorValueInput.text)
                            editSelectorDialog.close()
                        }
                    }
                }
            }
        }
    }

    // Selector Lookup Popup
    SelectorLookup {
        id: selectorLookupPopup

        onSelectorSelected: function(selectorType, selectorValue) {
            // Update the selector input fields in Add Step dialog
            var typeIndex = selectorTypeCombo.model.indexOf(selectorType)
            if (typeIndex >= 0) {
                selectorTypeCombo.currentIndex = typeIndex
            }
            selectorInput.text = selectorValue
        }
    }

    // Variable Helper Popup
    VariableHelper {
        id: variableHelperPopup

        onVariableSelected: function(variable) {
            // Insert variable at cursor position in value input
            var curPos = valueInput.cursorPosition
            var text = valueInput.text
            valueInput.text = text.slice(0, curPos) + variable + text.slice(curPos)
            valueInput.cursorPosition = curPos + variable.length
        }

        onExpressionSelected: function(expression) {
            valueInput.text = expression
        }
    }

    onWorkflowPathChanged: {
        if (workflowPath && workflowPath !== "") {
            controller.load_workflow_steps(workflowPath)
        }
    }
}
