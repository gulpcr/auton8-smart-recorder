import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4

Item {
    id: mlInsightsView

    // ML Stats from model
    property int selectorSamples: mlStatsModel ? mlStatsModel.selectorSamples : 0
    property bool selectorTrained: mlStatsModel ? mlStatsModel.selectorTrained : false
    property int healingSamples: mlStatsModel ? mlStatsModel.healingSamples : 0
    property bool healingTrained: mlStatsModel ? mlStatsModel.healingTrained : false
    property bool visionReady: mlStatsModel ? mlStatsModel.visionReady : false
    property bool llmAvailable: mlStatsModel ? mlStatsModel.llmAvailable : false
    property string llmModel: mlStatsModel ? mlStatsModel.llmModel : ""

    ScrollView {
        anchors.fill: parent
        anchors.margins: 20
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 20

            // Header
            Text {
                text: "ML Model Status & Insights"
                font.pixelSize: 24
                font.bold: true
                color: "#e0e0e0"
            }

            // Model Status Cards
            Text {
                text: "Model Status"
                font.pixelSize: 16
                font.bold: true
                color: "#aaa"
                Layout.topMargin: 10
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 4
                rowSpacing: 16
                columnSpacing: 16

                // Selector Model Card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 160
                    radius: 12
                    color: "#1e2a3a"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true

                            Text {
                                text: "Selector Ranker"
                                font.pixelSize: 14
                                font.bold: true
                                color: "#e0e0e0"
                            }

                            Item { Layout.fillWidth: true }

                            Rectangle {
                                width: 12
                                height: 12
                                radius: 6
                                color: selectorTrained ? "#4ecca3" : "#f39c12"
                            }
                        }

                        Text {
                            text: selectorTrained ? "Trained" : "Training..."
                            font.pixelSize: 12
                            color: selectorTrained ? "#4ecca3" : "#f39c12"
                        }

                        Item { Layout.fillHeight: true }

                        RowLayout {
                            Layout.fillWidth: true

                            ColumnLayout {
                                spacing: 2

                                Text {
                                    text: selectorSamples
                                    font.pixelSize: 24
                                    font.bold: true
                                    color: "#e0e0e0"
                                }
                                Text {
                                    text: "samples"
                                    font.pixelSize: 11
                                    color: "#888"
                                }
                            }

                            Item { Layout.fillWidth: true }

                            ColumnLayout {
                                spacing: 2

                                Text {
                                    text: "50"
                                    font.pixelSize: 24
                                    font.bold: true
                                    color: "#888"
                                }
                                Text {
                                    text: "needed"
                                    font.pixelSize: 11
                                    color: "#888"
                                }
                            }
                        }

                        // Progress bar
                        Rectangle {
                            Layout.fillWidth: true
                            height: 4
                            radius: 2
                            color: "#2a3a4a"

                            Rectangle {
                                width: parent.width * Math.min(selectorSamples / 50, 1.0)
                                height: parent.height
                                radius: 2
                                color: selectorTrained ? "#4ecca3" : "#f39c12"
                            }
                        }
                    }
                }

                // Healing Model Card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 160
                    radius: 12
                    color: "#1e2a3a"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true

                            Text {
                                text: "Healing Engine"
                                font.pixelSize: 14
                                font.bold: true
                                color: "#e0e0e0"
                            }

                            Item { Layout.fillWidth: true }

                            Rectangle {
                                width: 12
                                height: 12
                                radius: 6
                                color: healingTrained ? "#4ecca3" : "#f39c12"
                            }
                        }

                        Text {
                            text: healingTrained ? "Trained" : "Training..."
                            font.pixelSize: 12
                            color: healingTrained ? "#4ecca3" : "#f39c12"
                        }

                        Item { Layout.fillHeight: true }

                        RowLayout {
                            Layout.fillWidth: true

                            ColumnLayout {
                                spacing: 2

                                Text {
                                    text: healingSamples
                                    font.pixelSize: 24
                                    font.bold: true
                                    color: "#e0e0e0"
                                }
                                Text {
                                    text: "samples"
                                    font.pixelSize: 11
                                    color: "#888"
                                }
                            }

                            Item { Layout.fillWidth: true }

                            ColumnLayout {
                                spacing: 2

                                Text {
                                    text: "100"
                                    font.pixelSize: 24
                                    font.bold: true
                                    color: "#888"
                                }
                                Text {
                                    text: "needed"
                                    font.pixelSize: 11
                                    color: "#888"
                                }
                            }
                        }

                        // Progress bar
                        Rectangle {
                            Layout.fillWidth: true
                            height: 4
                            radius: 2
                            color: "#2a3a4a"

                            Rectangle {
                                width: parent.width * Math.min(healingSamples / 100, 1.0)
                                height: parent.height
                                radius: 2
                                color: healingTrained ? "#4ecca3" : "#f39c12"
                            }
                        }
                    }
                }

                // Computer Vision Card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 160
                    radius: 12
                    color: "#1e2a3a"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true

                            Text {
                                text: "Computer Vision"
                                font.pixelSize: 14
                                font.bold: true
                                color: "#e0e0e0"
                            }

                            Item { Layout.fillWidth: true }

                            Rectangle {
                                width: 12
                                height: 12
                                radius: 6
                                color: visionReady ? "#4ecca3" : "#888"
                            }
                        }

                        Text {
                            text: visionReady ? "Ready" : "Not Available"
                            font.pixelSize: 12
                            color: visionReady ? "#4ecca3" : "#888"
                        }

                        Item { Layout.fillHeight: true }

                        Text {
                            text: "Tier 2 Recovery"
                            font.pixelSize: 12
                            color: "#888"
                        }

                        Text {
                            text: "Template Matching\nPerceptual Hashing\nOCR Detection"
                            font.pixelSize: 11
                            color: "#666"
                            lineHeight: 1.3
                        }
                    }
                }

                // LLM Card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 160
                    radius: 12
                    color: "#1e2a3a"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true

                            Text {
                                text: "LLM Engine"
                                font.pixelSize: 14
                                font.bold: true
                                color: "#e0e0e0"
                            }

                            Item { Layout.fillWidth: true }

                            Rectangle {
                                width: 12
                                height: 12
                                radius: 6
                                color: llmAvailable ? "#4ecca3" : "#e74c3c"
                            }
                        }

                        Text {
                            text: llmAvailable ? "Connected" : "Offline"
                            font.pixelSize: 12
                            color: llmAvailable ? "#4ecca3" : "#e74c3c"
                        }

                        Item { Layout.fillHeight: true }

                        Text {
                            text: "Tier 3 Recovery"
                            font.pixelSize: 12
                            color: "#888"
                        }

                        Text {
                            text: llmAvailable ? ("Model: " + llmModel) : "Configure Ollama in Settings"
                            font.pixelSize: 11
                            color: "#666"
                        }
                    }
                }
            }

            // Tiered Execution Overview
            Text {
                text: "Tiered Execution Strategy"
                font.pixelSize: 16
                font.bold: true
                color: "#aaa"
                Layout.topMargin: 20
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 200
                radius: 12
                color: "#1e2a3a"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 0

                    // Tier 0
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Rectangle {
                            width: 60
                            height: 60
                            radius: 30
                            color: "#2a4a3a"
                            Layout.alignment: Qt.AlignHCenter

                            Text {
                                anchors.centerIn: parent
                                text: "0"
                                font.pixelSize: 24
                                font.bold: true
                                color: "#4ecca3"
                            }
                        }

                        Text {
                            text: "Playwright"
                            font.pixelSize: 14
                            font.bold: true
                            color: "#e0e0e0"
                            Layout.alignment: Qt.AlignHCenter
                        }

                        Text {
                            text: "Direct selector\nexecution"
                            font.pixelSize: 11
                            color: "#888"
                            horizontalAlignment: Text.AlignHCenter
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }

                    // Arrow
                    Text {
                        text: "\u2192"
                        font.pixelSize: 24
                        color: "#555"
                    }

                    // Tier 1
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Rectangle {
                            width: 60
                            height: 60
                            radius: 30
                            color: "#4a4a2a"
                            Layout.alignment: Qt.AlignHCenter

                            Text {
                                anchors.centerIn: parent
                                text: "1"
                                font.pixelSize: 24
                                font.bold: true
                                color: "#f39c12"
                            }
                        }

                        Text {
                            text: "Healing"
                            font.pixelSize: 14
                            font.bold: true
                            color: "#e0e0e0"
                            Layout.alignment: Qt.AlignHCenter
                        }

                        Text {
                            text: "Fallback selectors\nML prediction"
                            font.pixelSize: 11
                            color: "#888"
                            horizontalAlignment: Text.AlignHCenter
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }

                    // Arrow
                    Text {
                        text: "\u2192"
                        font.pixelSize: 24
                        color: "#555"
                    }

                    // Tier 2
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Rectangle {
                            width: 60
                            height: 60
                            radius: 30
                            color: "#2a3a4a"
                            Layout.alignment: Qt.AlignHCenter

                            Text {
                                anchors.centerIn: parent
                                text: "2"
                                font.pixelSize: 24
                                font.bold: true
                                color: "#3498db"
                            }
                        }

                        Text {
                            text: "Computer Vision"
                            font.pixelSize: 14
                            font.bold: true
                            color: "#e0e0e0"
                            Layout.alignment: Qt.AlignHCenter
                        }

                        Text {
                            text: "Visual matching\nOCR detection"
                            font.pixelSize: 11
                            color: "#888"
                            horizontalAlignment: Text.AlignHCenter
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }

                    // Arrow
                    Text {
                        text: "\u2192"
                        font.pixelSize: 24
                        color: "#555"
                    }

                    // Tier 3
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Rectangle {
                            width: 60
                            height: 60
                            radius: 30
                            color: "#3a2a4a"
                            Layout.alignment: Qt.AlignHCenter

                            Text {
                                anchors.centerIn: parent
                                text: "3"
                                font.pixelSize: 24
                                font.bold: true
                                color: "#9b59b6"
                            }
                        }

                        Text {
                            text: "LLM"
                            font.pixelSize: 14
                            font.bold: true
                            color: "#e0e0e0"
                            Layout.alignment: Qt.AlignHCenter
                        }

                        Text {
                            text: "AI reasoning\nContext analysis"
                            font.pixelSize: 11
                            color: "#888"
                            horizontalAlignment: Text.AlignHCenter
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }
            }

            // Healing Strategies
            Text {
                text: "Healing Strategies"
                font.pixelSize: 16
                font.bold: true
                color: "#aaa"
                Layout.topMargin: 20
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 3
                rowSpacing: 12
                columnSpacing: 12

                Repeater {
                    model: [
                        { name: "Selector Fallback", desc: "Try alternative selectors (ID, class, xpath)", color: "#4ecca3" },
                        { name: "Visual Match", desc: "Find element by screenshot similarity", color: "#3498db" },
                        { name: "Text Fuzzy", desc: "Match by text content with fuzzy matching", color: "#f39c12" },
                        { name: "Position Based", desc: "Find element near original coordinates", color: "#e74c3c" },
                        { name: "Structural Similarity", desc: "Match by DOM structure patterns", color: "#9b59b6" },
                        { name: "ML Prediction", desc: "XGBoost predicts best strategy", color: "#1abc9c" }
                    ]

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 80
                        radius: 8
                        color: "#232f3e"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 12

                            Rectangle {
                                width: 6
                                height: parent.height - 24
                                radius: 3
                                color: modelData.color
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                Text {
                                    text: modelData.name
                                    font.pixelSize: 13
                                    font.bold: true
                                    color: "#e0e0e0"
                                }

                                Text {
                                    text: modelData.desc
                                    font.pixelSize: 11
                                    color: "#888"
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }
            }

            // Training Info
            Text {
                text: "How Training Works"
                font.pixelSize: 16
                font.bold: true
                color: "#aaa"
                Layout.topMargin: 20
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: infoColumn.height + 32
                radius: 12
                color: "#1e2a3a"

                ColumnLayout {
                    id: infoColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 16
                    spacing: 12

                    InfoRow {
                        number: "1"
                        title: "Record & Replay"
                        description: "Each replay attempt collects training data about selector success/failure"
                    }

                    InfoRow {
                        number: "2"
                        title: "Feature Extraction"
                        description: "Element fingerprints are converted to ML features (depth, siblings, attributes, etc.)"
                    }

                    InfoRow {
                        number: "3"
                        title: "Model Training"
                        description: "After collecting enough samples (50+ for selector, 100+ for healing), models auto-train"
                    }

                    InfoRow {
                        number: "4"
                        title: "Prediction"
                        description: "Trained models rank selectors and predict best healing strategies for new elements"
                    }
                }
            }

            Item { Layout.preferredHeight: 20 }
        }
    }

    // Info row component
    component InfoRow: RowLayout {
        property string number: "1"
        property string title: ""
        property string description: ""

        Layout.fillWidth: true
        spacing: 12

        Rectangle {
            width: 28
            height: 28
            radius: 14
            color: "#2a4a3a"

            Text {
                anchors.centerIn: parent
                text: number
                font.pixelSize: 14
                font.bold: true
                color: "#4ecca3"
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            Text {
                text: title
                font.pixelSize: 13
                font.bold: true
                color: "#e0e0e0"
            }

            Text {
                text: description
                font.pixelSize: 11
                color: "#888"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }
    }
}
