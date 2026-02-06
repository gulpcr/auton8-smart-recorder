import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4

/**
 * Selector Lookup Component
 *
 * Provides selector picker functionality with:
 * - Browse selectors from current workflow steps
 * - Common selector templates
 * - Selector validation
 * - Type-specific suggestions
 */
Popup {
    id: selectorLookup

    property string selectedSelector: ""
    property string selectedType: "css"
    property int forStepIndex: -1

    // Callback when selector is selected
    signal selectorSelected(string selectorType, string selectorValue)

    width: 600
    height: 500
    modal: true
    anchors.centerIn: Overlay.overlay
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        color: "#16213e"
        radius: 12
        border.color: "#4ecca3"
        border.width: 2
    }

    contentItem: ColumnLayout {
        spacing: 12

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Text {
                text: "🎯 Selector Lookup"
                font.pixelSize: 18
                font.bold: true
                color: "#e0e0e0"
            }

            Item { Layout.fillWidth: true }

            Rectangle {
                width: 28
                height: 28
                radius: 14
                color: closeMouse.containsMouse ? "#e94560" : "#0f3460"

                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    font.pixelSize: 14
                    color: "#fff"
                }

                MouseArea {
                    id: closeMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: selectorLookup.close()
                }
            }
        }

        // Tab bar for different sources
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Repeater {
                model: [
                    {id: "workflow", label: "📋 From Workflow", color: "#4ecca3"},
                    {id: "templates", label: "📝 Templates", color: "#7b68ee"},
                    {id: "common", label: "⭐ Common", color: "#ffc93c"}
                ]

                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: 6
                    color: tabView.currentTab === modelData.id ? modelData.color : "#0f3460"
                    border.color: modelData.color
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        font.pixelSize: 12
                        font.bold: tabView.currentTab === modelData.id
                        color: tabView.currentTab === modelData.id ? "#000" : "#fff"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: tabView.currentTab = modelData.id
                    }
                }
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: "#2a4a70" }

        // Search box
        Rectangle {
            Layout.fillWidth: true
            height: 40
            radius: 6
            color: "#0f3460"
            border.color: searchInput.activeFocus ? "#4ecca3" : "#2a4a70"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8

                Text {
                    text: "🔍"
                    font.pixelSize: 14
                }

                TextInput {
                    id: searchInput
                    Layout.fillWidth: true
                    color: "#e0e0e0"
                    font.pixelSize: 13
                    clip: true
                    selectByMouse: true

                    Text {
                        visible: !searchInput.text
                        text: "Search selectors..."
                        color: "#666"
                        font.pixelSize: 13
                    }
                }
            }
        }

        // Tab content
        Item {
            id: tabView
            Layout.fillWidth: true
            Layout.fillHeight: true

            property string currentTab: "workflow"

            // From Workflow Tab
            Rectangle {
                anchors.fill: parent
                visible: tabView.currentTab === "workflow"
                color: "#0a1525"
                radius: 8

                ListView {
                    id: workflowSelectorList
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    spacing: 4

                    model: {
                        // Get selectors from stepDetailModel
                        var selectors = []
                        var count = stepDetailModel.getStepCount()
                        for (var i = 0; i < count; i++) {
                            try {
                                var stepJson = stepDetailModel.getStepData(i)
                                if (!stepJson) continue
                                var step = JSON.parse(stepJson)
                                if (step && step.selectors) {
                                    var stepSelectors = step.selectors
                                    for (var j = 0; j < stepSelectors.length; j++) {
                                        var sel = stepSelectors[j]
                                        if (searchInput.text === "" ||
                                            sel.value.toLowerCase().indexOf(searchInput.text.toLowerCase()) !== -1) {
                                            selectors.push({
                                                stepIndex: i,
                                                stepType: step.type,
                                                stepName: step.name,
                                                type: sel.type,
                                                value: sel.value,
                                                score: sel.score || 0.5
                                            })
                                        }
                                    }
                                }
                            } catch(e) {}
                        }
                        return selectors
                    }

                    delegate: Rectangle {
                        width: workflowSelectorList.width
                        height: 50
                        radius: 6
                        color: selectorItemMouse.containsMouse ? "#1a3a50" : "#0f2535"
                        border.color: selectorItemMouse.containsMouse ? "#4ecca3" : "transparent"

                        MouseArea {
                            id: selectorItemMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                selectorLookup.selectedType = modelData.type
                                selectorLookup.selectedSelector = modelData.value
                                selectorLookup.selectorSelected(modelData.type, modelData.value)
                                selectorLookup.close()
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 8

                            // Step badge
                            Rectangle {
                                width: 24
                                height: 24
                                radius: 12
                                color: "#4ecca3"

                                Text {
                                    anchors.centerIn: parent
                                    text: (modelData.stepIndex + 1).toString()
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: "#000"
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                RowLayout {
                                    spacing: 6

                                    Rectangle {
                                        width: 35
                                        height: 16
                                        radius: 3
                                        color: "#1a2a3a"

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.type
                                            font.pixelSize: 9
                                            font.bold: true
                                            color: "#ffc93c"
                                        }
                                    }

                                    Text {
                                        text: modelData.stepName || modelData.stepType
                                        font.pixelSize: 10
                                        color: "#888"
                                    }
                                }

                                Text {
                                    text: modelData.value
                                    font.pixelSize: 11
                                    font.family: "Consolas"
                                    color: "#e0e0e0"
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }
                            }

                            // Score
                            Rectangle {
                                width: 36
                                height: 18
                                radius: 3
                                color: modelData.score >= 0.8 ? "#1a4a30" : "#3a3a1a"

                                Text {
                                    anchors.centerIn: parent
                                    text: (modelData.score * 100).toFixed(0) + "%"
                                    font.pixelSize: 9
                                    font.bold: true
                                    color: modelData.score >= 0.8 ? "#4ecca3" : "#ffc93c"
                                }
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: workflowSelectorList.count === 0
                        text: "No selectors found in workflow"
                        color: "#666"
                        font.pixelSize: 13
                    }
                }
            }

            // Templates Tab
            Rectangle {
                anchors.fill: parent
                visible: tabView.currentTab === "templates"
                color: "#0a1525"
                radius: 8

                ListView {
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    spacing: 4

                    model: [
                        {category: "Form Elements", items: [
                            {type: "css", value: "input[type='text']", desc: "Text input"},
                            {type: "css", value: "input[type='email']", desc: "Email input"},
                            {type: "css", value: "input[type='password']", desc: "Password input"},
                            {type: "css", value: "button[type='submit']", desc: "Submit button"},
                            {type: "css", value: "select", desc: "Dropdown select"},
                            {type: "css", value: "textarea", desc: "Text area"}
                        ]},
                        {category: "Navigation", items: [
                            {type: "css", value: "a[href*='login']", desc: "Login link"},
                            {type: "css", value: "a[href*='logout']", desc: "Logout link"},
                            {type: "css", value: "nav a", desc: "Nav links"},
                            {type: "css", value: ".nav-item", desc: "Nav item"}
                        ]},
                        {category: "Common Patterns", items: [
                            {type: "css", value: "#${id}", desc: "By ID"},
                            {type: "css", value: ".${class}", desc: "By class"},
                            {type: "css", value: "[data-testid='${name}']", desc: "By test ID"},
                            {type: "css", value: "[aria-label='${label}']", desc: "By ARIA label"},
                            {type: "xpath", value: "//button[contains(text(),'${text}')]", desc: "Button by text"},
                            {type: "xpath", value: "//input[@placeholder='${placeholder}']", desc: "Input by placeholder"}
                        ]}
                    ]

                    delegate: ColumnLayout {
                        width: parent ? parent.width : 0
                        spacing: 4

                        Text {
                            text: modelData.category
                            font.pixelSize: 12
                            font.bold: true
                            color: "#7b68ee"
                            topPadding: 8
                        }

                        Repeater {
                            model: modelData.items

                            Rectangle {
                                Layout.fillWidth: true
                                height: 36
                                radius: 4
                                color: templateMouse.containsMouse ? "#1a3a50" : "#0f2535"

                                MouseArea {
                                    id: templateMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        selectorLookup.selectedType = modelData.type
                                        selectorLookup.selectedSelector = modelData.value
                                        selectorLookup.selectorSelected(modelData.type, modelData.value)
                                        selectorLookup.close()
                                    }
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 8

                                    Rectangle {
                                        width: 40
                                        height: 18
                                        radius: 3
                                        color: "#1a2a3a"

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.type
                                            font.pixelSize: 9
                                            color: "#ffc93c"
                                        }
                                    }

                                    Text {
                                        text: modelData.value
                                        font.pixelSize: 11
                                        font.family: "Consolas"
                                        color: "#e0e0e0"
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        text: modelData.desc
                                        font.pixelSize: 10
                                        color: "#888"
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Common Tab
            Rectangle {
                anchors.fill: parent
                visible: tabView.currentTab === "common"
                color: "#0a1525"
                radius: 8

                GridLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 8

                    Repeater {
                        model: [
                            {type: "css", value: "#login-btn", desc: "Login Button", icon: "🔐"},
                            {type: "css", value: "#submit", desc: "Submit Button", icon: "✓"},
                            {type: "css", value: ".btn-primary", desc: "Primary Button", icon: "🔵"},
                            {type: "css", value: ".btn-secondary", desc: "Secondary Button", icon: "⚪"},
                            {type: "css", value: "input[name='username']", desc: "Username Field", icon: "👤"},
                            {type: "css", value: "input[name='password']", desc: "Password Field", icon: "🔑"},
                            {type: "css", value: "input[name='email']", desc: "Email Field", icon: "📧"},
                            {type: "css", value: ".search-input", desc: "Search Box", icon: "🔍"},
                            {type: "css", value: ".nav-menu", desc: "Navigation Menu", icon: "☰"},
                            {type: "css", value: ".modal", desc: "Modal Dialog", icon: "📦"},
                            {type: "css", value: ".dropdown", desc: "Dropdown", icon: "▼"},
                            {type: "css", value: ".alert", desc: "Alert Box", icon: "⚠️"}
                        ]

                        Rectangle {
                            Layout.fillWidth: true
                            height: 60
                            radius: 6
                            color: commonMouse.containsMouse ? "#1a3a50" : "#0f2535"
                            border.color: commonMouse.containsMouse ? "#ffc93c" : "transparent"

                            MouseArea {
                                id: commonMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    selectorLookup.selectedType = modelData.type
                                    selectorLookup.selectedSelector = modelData.value
                                    selectorLookup.selectorSelected(modelData.type, modelData.value)
                                    selectorLookup.close()
                                }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10

                                Text {
                                    text: modelData.icon
                                    font.pixelSize: 20
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Text {
                                        text: modelData.desc
                                        font.pixelSize: 11
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: modelData.value
                                        font.pixelSize: 9
                                        font.family: "Consolas"
                                        color: "#888"
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: "#2a4a70" }

        // Manual input section
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: "Or enter manually:"
                font.pixelSize: 12
                font.bold: true
                color: "#9aa8b8"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                ComboBox {
                    id: manualTypeCombo
                    model: ["css", "xpath", "id", "name", "text", "aria", "data"]
                    implicitWidth: 90

                    background: Rectangle {
                        color: "#0f3460"
                        radius: 4
                        border.color: "#2a4a70"
                    }

                    contentItem: Text {
                        text: manualTypeCombo.currentText
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
                    border.color: manualInput.activeFocus ? "#4ecca3" : "#2a4a70"

                    TextInput {
                        id: manualInput
                        anchors.fill: parent
                        anchors.margins: 8
                        color: "#e0e0e0"
                        font.pixelSize: 12
                        font.family: "Consolas"
                        clip: true
                        selectByMouse: true

                        Text {
                            visible: !manualInput.text
                            text: "Enter selector..."
                            color: "#666"
                            font.pixelSize: 12
                        }
                    }
                }

                Rectangle {
                    width: 80
                    height: 36
                    radius: 4
                    color: useBtnMouse.containsMouse ? "#3dcc93" : "#4ecca3"

                    Text {
                        anchors.centerIn: parent
                        text: "Use"
                        font.pixelSize: 12
                        font.bold: true
                        color: "#000"
                    }

                    MouseArea {
                        id: useBtnMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (manualInput.text) {
                                selectorLookup.selectorSelected(manualTypeCombo.currentText, manualInput.text)
                                selectorLookup.close()
                            }
                        }
                    }
                }
            }
        }
    }
}
