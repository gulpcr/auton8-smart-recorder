import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4

/**
 * NewTestWizard - Dialog to enter test name and URL together
 * After entering both, closes and starts recording
 */
Dialog {
    id: root

    property string testName: ""
    property string testUrl: ""

    signal testCreated(string name, string url)

    title: ""
    modal: true
    width: 460
    height: 340
    anchors.centerIn: parent

    background: Rectangle {
        radius: 12
        color: "#16213e"
        border.color: "#2a4a70"
        border.width: 1
    }

    header: Item {
        implicitHeight: 50

        Text {
            anchors.centerIn: parent
            text: "New Test"
            font.pixelSize: 18
            font.bold: true
            color: "#e0e0e0"
        }
    }

    contentItem: ColumnLayout {
        spacing: 14

        // Test Name Section
        ColumnLayout {
            spacing: 6
            Layout.fillWidth: true

            Text {
                text: "Test Name"
                font.pixelSize: 13
                font.bold: true
                color: "#e0e0e0"
            }

            Rectangle {
                Layout.fillWidth: true
                height: 42
                radius: 6
                color: "#0f3460"
                border.color: nameInput.activeFocus ? "#e94560" : "#1a2a45"
                border.width: 1

                TextInput {
                    id: nameInput
                    anchors.fill: parent
                    anchors.margins: 12
                    font.pixelSize: 14
                    color: "#e0e0e0"
                    selectByMouse: true
                    verticalAlignment: TextInput.AlignVCenter
                    text: testName
                    onTextChanged: testName = text

                    Keys.onReturnPressed: urlInput.forceActiveFocus()

                    Text {
                        anchors.fill: parent
                        verticalAlignment: Text.AlignVCenter
                        text: "e.g., User Login Flow"
                        color: "#555"
                        font.pixelSize: 14
                        visible: !nameInput.text && !nameInput.activeFocus
                    }
                }
            }

            // Quick templates
            Flow {
                Layout.fillWidth: true
                spacing: 6

                Repeater {
                    model: ["User Login", "Add to Cart", "Submit Form", "Search"]

                    Rectangle {
                        width: suggestText.width + 12
                        height: 24
                        radius: 4
                        color: suggestMouseArea.containsMouse ? "#2a4a70" : "#1a2a40"

                        Text {
                            id: suggestText
                            anchors.centerIn: parent
                            text: modelData
                            font.pixelSize: 11
                            color: "#888"
                        }

                        MouseArea {
                            id: suggestMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: nameInput.text = modelData
                        }
                    }
                }
            }
        }

        // URL Section
        ColumnLayout {
            spacing: 6
            Layout.fillWidth: true

            Text {
                text: "Starting URL"
                font.pixelSize: 13
                font.bold: true
                color: "#e0e0e0"
            }

            Rectangle {
                Layout.fillWidth: true
                height: 42
                radius: 6
                color: "#0f3460"
                border.color: urlInput.activeFocus ? "#e94560" : "#1a2a45"
                border.width: 1

                TextInput {
                    id: urlInput
                    anchors.fill: parent
                    anchors.margins: 12
                    font.pixelSize: 14
                    color: "#e0e0e0"
                    selectByMouse: true
                    verticalAlignment: TextInput.AlignVCenter
                    text: testUrl
                    onTextChanged: testUrl = text

                    Keys.onReturnPressed: {
                        if (testName.trim().length > 0 && testUrl.trim().length > 0) {
                            root.testCreated(testName, testUrl)
                            root.close()
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
            }

            Text {
                text: "The browser will open to this URL when recording starts"
                font.pixelSize: 11
                color: "#666"
            }
        }
    }

    footer: DialogButtonBox {
        background: Rectangle {
            color: "#16213e"
        }

        Button {
            text: "Cancel"
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            implicitWidth: 80
            implicitHeight: 36

            background: Rectangle {
                radius: 4
                color: parent.hovered ? "#1a2a45" : "transparent"
                border.width: 1
                border.color: "#2a3a50"
            }

            contentItem: Text {
                text: "Cancel"
                font.pixelSize: 13
                color: "#888"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            onClicked: root.close()
        }

        Button {
            id: startBtn
            text: "Start Recording"
            enabled: testName.trim().length > 0 && testUrl.trim().length > 0
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            implicitWidth: 130
            implicitHeight: 36

            background: Rectangle {
                radius: 4
                color: startBtn.enabled ? (startBtn.hovered ? "#d63e5c" : "#e94560") : "#2a2a3a"
            }

            contentItem: Row {
                anchors.centerIn: parent
                spacing: 6

                Text {
                    text: "\u25CF"
                    font.pixelSize: 10
                    color: startBtn.enabled ? "#fff" : "#555"
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "Start Recording"
                    font.pixelSize: 13
                    font.bold: true
                    color: startBtn.enabled ? "#fff" : "#555"
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            onClicked: {
                root.testCreated(testName, testUrl)
                root.close()
            }
        }
    }

    onOpened: {
        testName = ""
        testUrl = ""
        nameInput.forceActiveFocus()
    }
}
