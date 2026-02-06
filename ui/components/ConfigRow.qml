import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4
import QtQuick.Effects

/**
 * ConfigRow - Single configuration row with label and input control
 */
Item {
    id: root

    property string label: "Setting"
    property string inputType: "text"  // text, number, checkbox, dropdown, expression
    property var value: ""
    property var options: []  // For dropdown: [{value: "x", label: "X"}]
    property string placeholder: ""
    property string tooltip: ""
    property int minValue: 0
    property int maxValue: 999999
    property bool readOnly: false
    property bool recommended: false
    property var defaultValue: undefined

    signal valueModified(var newValue)

    width: parent ? parent.width : 400
    height: 38

    function isModified() {
        if (defaultValue === undefined) return false
        return value !== defaultValue
    }

    // Hover background
    Rectangle {
        anchors.fill: parent
        radius: 6
        color: rowMouse.containsMouse ? "#ffffff08" : "transparent"
    }

    MouseArea {
        id: rowMouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    // Label on left
    Item {
        id: labelArea
        anchors.left: parent.left
        anchors.leftMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        width: 150
        height: parent.height

        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6

            // Expression indicator in label area
            Rectangle {
                visible: root.inputType === "expression"
                width: 18
                height: 18
                radius: 4
                color: "#0d3330"
                border.color: "#2dd4bf"
                border.width: 1
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: "fx"
                    font.pixelSize: 9
                    font.bold: true
                    color: "#2dd4bf"
                }
            }

            // Modified indicator
            Rectangle {
                visible: isModified()
                width: 6
                height: 6
                radius: 3
                color: "#3b82f6"
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: root.label
                font.pixelSize: 12
                font.weight: Font.Medium
                color: labelMouse.containsMouse ? "#f1f5f9" : "#94a3b8"
                anchors.verticalCenter: parent.verticalCenter

                Behavior on color { ColorAnimation { duration: 150 } }

                MouseArea {
                    id: labelMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: root.tooltip ? Qt.WhatsThisCursor : Qt.ArrowCursor

                    ToolTip {
                        visible: labelMouse.containsMouse && root.tooltip !== ""
                        text: root.tooltip
                        delay: 400
                        background: Rectangle {
                            color: "#1e293b"
                            border.color: "#334155"
                            radius: 6
                        }
                        contentItem: Text {
                            text: root.tooltip
                            font.pixelSize: 11
                            color: "#e2e8f0"
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            // Recommended star
            Text {
                visible: root.recommended
                text: "\u2605"
                font.pixelSize: 10
                color: "#f59e0b"
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    // Input area on right - takes remaining space
    Item {
        id: inputArea
        anchors.left: labelArea.right
        anchors.leftMargin: 12
        anchors.right: parent.right
        anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        height: 32

        // Text input
        Rectangle {
            id: textInputBox
            visible: root.inputType === "text"
            anchors.fill: parent
            color: textInput.activeFocus ? "#1e293b" : "#0f172a"
            radius: 6
            border.color: textInput.activeFocus ? "#3b82f6" : (textInputMouse.containsMouse ? "#475569" : "#334155")
            border.width: textInput.activeFocus ? 2 : 1

            Behavior on border.color { ColorAnimation { duration: 150 } }
            Behavior on color { ColorAnimation { duration: 150 } }

            MouseArea {
                id: textInputMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.IBeamCursor
                onClicked: textInput.forceActiveFocus()
            }

            TextInput {
                id: textInput
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                verticalAlignment: TextInput.AlignVCenter
                text: root.value || ""
                font.pixelSize: 12
                color: root.readOnly ? "#64748b" : "#f1f5f9"
                selectByMouse: true
                readOnly: root.readOnly
                clip: true
                selectionColor: "#3b82f6"
                selectedTextColor: "#ffffff"

                Text {
                    visible: !textInput.text && root.placeholder
                    text: root.placeholder
                    font.pixelSize: 12
                    color: "#64748b"
                    anchors.verticalCenter: parent.verticalCenter
                }

                onTextChanged: {
                    if (text !== root.value) root.valueModified(text)
                }
            }
        }

        // Number input
        Rectangle {
            id: numberInputBox
            visible: root.inputType === "number"
            anchors.fill: parent
            color: numInput.activeFocus ? "#1e293b" : "#0f172a"
            radius: 6
            border.color: numInput.activeFocus ? "#3b82f6" : (numInputMouse.containsMouse ? "#475569" : "#334155")
            border.width: numInput.activeFocus ? 2 : 1

            Behavior on border.color { ColorAnimation { duration: 150 } }
            Behavior on color { ColorAnimation { duration: 150 } }

            MouseArea {
                id: numInputMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.IBeamCursor
                onClicked: numInput.forceActiveFocus()
            }

            TextInput {
                id: numInput
                anchors.left: parent.left
                anchors.right: spinButtons.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.leftMargin: 12
                anchors.rightMargin: 4
                verticalAlignment: TextInput.AlignVCenter
                text: root.value !== undefined ? root.value.toString() : ""
                font.pixelSize: 12
                color: root.readOnly ? "#64748b" : "#f1f5f9"
                selectByMouse: true
                readOnly: root.readOnly
                validator: IntValidator { bottom: root.minValue; top: root.maxValue }
                clip: true
                selectionColor: "#3b82f6"
                selectedTextColor: "#ffffff"

                onTextChanged: {
                    var num = parseInt(text)
                    if (!isNaN(num) && num !== root.value) root.valueModified(num)
                }
            }

            Column {
                id: spinButtons
                anchors.right: parent.right
                anchors.rightMargin: 4
                anchors.verticalCenter: parent.verticalCenter
                width: 20
                height: 24
                visible: !root.readOnly

                Rectangle {
                    width: parent.width
                    height: parent.height / 2
                    color: upMouse.containsMouse ? "#475569" : "transparent"
                    radius: 3

                    Text {
                        anchors.centerIn: parent
                        text: "\u25B2"
                        font.pixelSize: 8
                        color: upMouse.containsMouse ? "#fff" : "#64748b"
                    }

                    MouseArea {
                        id: upMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            var num = parseInt(numInput.text) || 0
                            if (num < root.maxValue) root.valueModified(num + 1)
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: parent.height / 2
                    color: downMouse.containsMouse ? "#475569" : "transparent"
                    radius: 3

                    Text {
                        anchors.centerIn: parent
                        text: "\u25BC"
                        font.pixelSize: 8
                        color: downMouse.containsMouse ? "#fff" : "#64748b"
                    }

                    MouseArea {
                        id: downMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            var num = parseInt(numInput.text) || 0
                            if (num > root.minValue) root.valueModified(num - 1)
                        }
                    }
                }
            }
        }

        // Toggle switch
        Row {
            id: toggleRow
            visible: root.inputType === "checkbox"
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10

            Rectangle {
                id: toggleTrack
                width: 44
                height: 24
                radius: 12
                color: root.value ? "#22c55e" : "#475569"

                Rectangle {
                    width: 18
                    height: 18
                    radius: 9
                    x: root.value ? parent.width - width - 3 : 3
                    anchors.verticalCenter: parent.verticalCenter
                    color: "#ffffff"

                    Behavior on x { NumberAnimation { duration: 150 } }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: if (!root.readOnly) root.valueModified(!root.value)
                }

                Behavior on color { ColorAnimation { duration: 150 } }
            }

            Rectangle {
                width: 32
                height: 20
                radius: 4
                color: root.value ? "#22c55e30" : "#47556930"
                border.color: root.value ? "#22c55e" : "#475569"
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: root.value ? "ON" : "OFF"
                    font.pixelSize: 9
                    font.bold: true
                    color: root.value ? "#22c55e" : "#94a3b8"
                }
            }
        }

        // Dropdown
        ComboBox {
            id: dropdown
            visible: root.inputType === "dropdown"
            anchors.fill: parent
            model: root.options
            textRole: "label"
            valueRole: "value"
            font.pixelSize: 12
            enabled: !root.readOnly

            currentIndex: {
                for (var i = 0; i < root.options.length; i++) {
                    if (root.options[i].value === root.value) return i
                }
                return 0
            }

            background: Rectangle {
                color: dropdown.pressed ? "#1e293b" : (dropdown.hovered ? "#1e293b" : "#0f172a")
                radius: 6
                border.color: dropdown.pressed ? "#3b82f6" : (dropdown.hovered ? "#475569" : "#334155")
                border.width: dropdown.pressed ? 2 : 1

                Behavior on color { ColorAnimation { duration: 150 } }
                Behavior on border.color { ColorAnimation { duration: 150 } }
            }

            contentItem: Text {
                text: dropdown.displayText
                font.pixelSize: 12
                color: "#f1f5f9"
                verticalAlignment: Text.AlignVCenter
                leftPadding: 12
                rightPadding: 30
                elide: Text.ElideRight
            }

            indicator: Text {
                x: dropdown.width - width - 12
                anchors.verticalCenter: parent.verticalCenter
                text: "\u25BC"
                font.pixelSize: 8
                color: "#64748b"
            }

            popup: Popup {
                y: dropdown.height + 4
                width: dropdown.width
                implicitHeight: contentItem.implicitHeight + 8
                padding: 4

                background: Rectangle {
                    color: "#1e293b"
                    radius: 8
                    border.color: "#334155"
                    border.width: 1
                }

                contentItem: ListView {
                    clip: true
                    implicitHeight: Math.min(contentHeight, 200)
                    model: dropdown.popup.visible ? dropdown.delegateModel : null
                    currentIndex: dropdown.highlightedIndex
                    ScrollBar.vertical: ScrollBar {
                        policy: contentHeight > 200 ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
                    }
                }
            }

            delegate: ItemDelegate {
                width: dropdown.width - 8
                height: 32
                highlighted: dropdown.highlightedIndex === index

                background: Rectangle {
                    color: highlighted ? "#3b82f6" : (hovered ? "#334155" : "transparent")
                    radius: 4
                }

                contentItem: Text {
                    text: modelData.label
                    color: highlighted ? "#ffffff" : "#e2e8f0"
                    font.pixelSize: 12
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 8
                }
            }

            onActivated: function(index) {
                if (root.options[index]) root.valueModified(root.options[index].value)
            }
        }

        // Expression input
        Rectangle {
            id: expressionBox
            visible: root.inputType === "expression"
            anchors.fill: parent
            color: exprInput.activeFocus ? "#0d2818" : "#0a1612"
            radius: 6
            border.color: exprInput.activeFocus ? "#22c55e" : (exprInputMouse.containsMouse ? "#134e4a" : "#1e3a34")
            border.width: exprInput.activeFocus ? 2 : 1

            Behavior on border.color { ColorAnimation { duration: 150 } }
            Behavior on color { ColorAnimation { duration: 150 } }

            MouseArea {
                id: exprInputMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.IBeamCursor
                onClicked: exprInput.forceActiveFocus()
            }

            Row {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 8

                Rectangle {
                    width: 24
                    height: 18
                    radius: 4
                    color: "#134e4a"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "fx"
                        font.pixelSize: 10
                        font.bold: true
                        color: "#2dd4bf"
                    }
                }

                TextInput {
                    id: exprInput
                    width: parent.width - 40
                    height: parent.height
                    verticalAlignment: TextInput.AlignVCenter
                    text: root.value || ""
                    font.pixelSize: 12
                    font.family: "Consolas"
                    color: "#5eead4"
                    selectByMouse: true
                    readOnly: root.readOnly
                    clip: true
                    selectionColor: "#2dd4bf"
                    selectedTextColor: "#0a1612"

                    Text {
                        visible: !exprInput.text && root.placeholder
                        text: root.placeholder || "${variable}"
                        font.pixelSize: 12
                        color: "#2dd4bf50"
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    onTextChanged: {
                        if (text !== root.value) root.valueModified(text)
                    }
                }
            }
        }
    }
}
