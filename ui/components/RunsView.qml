import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4

Item {
    id: runsView

    // Signals
    signal executionSelected(string executionId)
    signal executionRerun(string workflowId)

    // Stats cards at top
    RowLayout {
        id: statsRow
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        spacing: 16

        // Total Runs
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            radius: 12
            color: "#1e2a3a"

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 4

                Text {
                    text: executionHistoryModel ? executionHistoryModel.totalRuns : 0
                    font.pixelSize: 32
                    font.bold: true
                    color: "#e0e0e0"
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "Total Runs"
                    font.pixelSize: 12
                    color: "#888"
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // Pass Rate
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            radius: 12
            color: "#1e2a3a"

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 4

                Text {
                    text: (executionHistoryModel ? executionHistoryModel.passRate.toFixed(1) : "0") + "%"
                    font.pixelSize: 32
                    font.bold: true
                    color: "#4ecca3"
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "Pass Rate"
                    font.pixelSize: 12
                    color: "#888"
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // Passed
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            radius: 12
            color: "#1e2a3a"

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 4

                Text {
                    text: executionHistoryModel ? executionHistoryModel.passedRuns : 0
                    font.pixelSize: 32
                    font.bold: true
                    color: "#4ecca3"
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "Passed"
                    font.pixelSize: 12
                    color: "#888"
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // Failed
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            radius: 12
            color: "#1e2a3a"

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 4

                Text {
                    text: executionHistoryModel ? executionHistoryModel.failedRuns : 0
                    font.pixelSize: 32
                    font.bold: true
                    color: "#e74c3c"
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "Failed"
                    font.pixelSize: 12
                    color: "#888"
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // Healed
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            radius: 12
            color: "#1e2a3a"

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 4

                Text {
                    text: executionHistoryModel ? executionHistoryModel.totalHealed : 0
                    font.pixelSize: 32
                    font.bold: true
                    color: "#f39c12"
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "Healed Steps"
                    font.pixelSize: 12
                    color: "#888"
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }
    }

    // Filter bar
    Rectangle {
        id: filterBar
        anchors.top: statsRow.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        anchors.topMargin: 16
        height: 50
        radius: 8
        color: "#1e2a3a"

        RowLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12

            // Status filter
            ComboBox {
                id: statusFilter
                Layout.preferredWidth: 150
                model: ["All Status", "Passed", "Failed", "Running"]

                background: Rectangle {
                    radius: 6
                    color: "#2a3a4a"
                    border.color: statusFilter.activeFocus ? "#4ecca3" : "#3a4a5a"
                }

                contentItem: Text {
                    text: statusFilter.displayText
                    color: "#e0e0e0"
                    font.pixelSize: 13
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 10
                }

                onCurrentTextChanged: {
                    if (currentText === "All Status") {
                        executionHistoryModel.set_status_filter("")
                    } else if (currentText === "Passed") {
                        executionHistoryModel.set_status_filter("completed")
                    } else if (currentText === "Failed") {
                        executionHistoryModel.set_status_filter("failed")
                    } else if (currentText === "Running") {
                        executionHistoryModel.set_status_filter("running")
                    }
                }
            }

            // Workflow filter (placeholder)
            ComboBox {
                id: workflowFilter
                Layout.preferredWidth: 200
                model: ["All Workflows"]

                background: Rectangle {
                    radius: 6
                    color: "#2a3a4a"
                    border.color: workflowFilter.activeFocus ? "#4ecca3" : "#3a4a5a"
                }

                contentItem: Text {
                    text: workflowFilter.displayText
                    color: "#e0e0e0"
                    font.pixelSize: 13
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 10
                }
            }

            Item { Layout.fillWidth: true }

            // Refresh button
            Button {
                text: "Refresh"
                Layout.preferredHeight: 32

                background: Rectangle {
                    radius: 6
                    color: parent.hovered ? "#3a4a5a" : "#2a3a4a"
                }

                contentItem: Text {
                    text: parent.text
                    color: "#e0e0e0"
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onClicked: {
                    if (executionHistoryModel) {
                        executionHistoryModel.load_history()
                    }
                }
            }
        }
    }

    // Split view: List + Details
    SplitView {
        anchors.top: filterBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 20
        anchors.topMargin: 16
        orientation: Qt.Horizontal

        // Executions list
        Rectangle {
            SplitView.preferredWidth: 500
            SplitView.minimumWidth: 300
            color: "#1e2a3a"
            radius: 12

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 8

                // Header
                Text {
                    text: "Execution History"
                    font.pixelSize: 16
                    font.bold: true
                    color: "#e0e0e0"
                }

                // List
                ListView {
                    id: executionsList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 8
                    model: executionHistoryModel

                    delegate: Rectangle {
                        width: executionsList.width
                        height: 80
                        radius: 8
                        color: ListView.isCurrentItem ? "#2a4a6a" : (mouseArea.containsMouse ? "#2a3a4a" : "#232f3e")

                        MouseArea {
                            id: mouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                executionsList.currentIndex = index
                                loadExecutionDetails(model.id)
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 12

                            // Status indicator
                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: {
                                    if (model.status === "completed" && model.failedSteps === 0) return "#4ecca3"
                                    if (model.status === "failed" || model.failedSteps > 0) return "#e74c3c"
                                    if (model.status === "running") return "#3498db"
                                    return "#888"
                                }
                            }

                            // Info
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                Text {
                                    text: model.workflowName || "Unknown Workflow"
                                    font.pixelSize: 14
                                    font.bold: true
                                    color: "#e0e0e0"
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }

                                RowLayout {
                                    spacing: 8

                                    Text {
                                        text: model.displayDate + " " + model.displayTime
                                        font.pixelSize: 11
                                        color: "#888"
                                    }

                                    Text {
                                        text: "|"
                                        font.pixelSize: 11
                                        color: "#555"
                                    }

                                    Text {
                                        text: model.displayDuration
                                        font.pixelSize: 11
                                        color: "#888"
                                    }
                                }

                                RowLayout {
                                    spacing: 8

                                    Text {
                                        text: model.passedSteps + " passed"
                                        font.pixelSize: 11
                                        color: "#4ecca3"
                                    }

                                    Text {
                                        text: model.failedSteps > 0 ? (model.failedSteps + " failed") : ""
                                        font.pixelSize: 11
                                        color: "#e74c3c"
                                        visible: model.failedSteps > 0
                                    }

                                    Text {
                                        text: model.healedSteps > 0 ? (model.healedSteps + " healed") : ""
                                        font.pixelSize: 11
                                        color: "#f39c12"
                                        visible: model.healedSteps > 0
                                    }
                                }
                            }

                            // Status badge
                            Rectangle {
                                width: statusText.width + 16
                                height: 24
                                radius: 12
                                color: {
                                    if (model.status === "completed" && model.failedSteps === 0) return "#1a4a3a"
                                    if (model.status === "failed" || model.failedSteps > 0) return "#4a1a1a"
                                    if (model.status === "running") return "#1a3a4a"
                                    return "#2a2a2a"
                                }

                                Text {
                                    id: statusText
                                    anchors.centerIn: parent
                                    text: {
                                        if (model.status === "completed" && model.failedSteps === 0) return "Passed"
                                        if (model.status === "failed" || model.failedSteps > 0) return "Failed"
                                        if (model.status === "running") return "Running"
                                        return model.status
                                    }
                                    font.pixelSize: 11
                                    color: {
                                        if (model.status === "completed" && model.failedSteps === 0) return "#4ecca3"
                                        if (model.status === "failed" || model.failedSteps > 0) return "#e74c3c"
                                        if (model.status === "running") return "#3498db"
                                        return "#888"
                                    }
                                }
                            }
                        }
                    }

                    // Empty state
                    Text {
                        anchors.centerIn: parent
                        text: "No executions yet\nRun a workflow to see results here"
                        font.pixelSize: 14
                        color: "#666"
                        horizontalAlignment: Text.AlignHCenter
                        visible: executionsList.count === 0
                    }
                }
            }
        }

        // Execution details panel
        Rectangle {
            SplitView.fillWidth: true
            SplitView.minimumWidth: 400
            color: "#1e2a3a"
            radius: 12

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                // Header
                RowLayout {
                    Layout.fillWidth: true

                    Text {
                        text: "Execution Details"
                        font.pixelSize: 16
                        font.bold: true
                        color: "#e0e0e0"
                    }

                    Item { Layout.fillWidth: true }

                    Button {
                        text: "Rerun"
                        visible: selectedExecution !== null

                        background: Rectangle {
                            radius: 6
                            color: parent.hovered ? "#3a5a4a" : "#2a4a3a"
                        }

                        contentItem: Text {
                            text: parent.text
                            color: "#4ecca3"
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }

                        onClicked: {
                            if (selectedExecution) {
                                executionRerun(selectedExecution.workflow_id)
                            }
                        }
                    }
                }

                // Selected execution info
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 80
                    radius: 8
                    color: "#232f3e"
                    visible: selectedExecution !== null

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 16

                        ColumnLayout {
                            spacing: 4

                            Text {
                                text: selectedExecution ? selectedExecution.workflow_name : ""
                                font.pixelSize: 16
                                font.bold: true
                                color: "#e0e0e0"
                            }

                            Text {
                                text: selectedExecution ? ("Started: " + selectedExecution.started_at) : ""
                                font.pixelSize: 11
                                color: "#888"
                            }
                        }

                        Item { Layout.fillWidth: true }

                        ColumnLayout {
                            spacing: 4

                            Text {
                                text: selectedExecution ? (selectedExecution.duration_ms + "ms") : ""
                                font.pixelSize: 14
                                color: "#e0e0e0"
                                Layout.alignment: Qt.AlignRight
                            }

                            Text {
                                text: selectedExecution ? (selectedExecution.total_steps + " steps") : ""
                                font.pixelSize: 11
                                color: "#888"
                                Layout.alignment: Qt.AlignRight
                            }
                        }
                    }
                }

                // Steps list
                Text {
                    text: "Step Results"
                    font.pixelSize: 14
                    font.bold: true
                    color: "#e0e0e0"
                    visible: selectedExecution !== null
                }

                ListView {
                    id: stepsListView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 6
                    model: selectedExecutionSteps
                    visible: selectedExecution !== null

                    delegate: Rectangle {
                        width: stepsListView.width
                        height: 60
                        radius: 6
                        color: "#232f3e"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 10

                            // Step number
                            Rectangle {
                                width: 28
                                height: 28
                                radius: 14
                                color: {
                                    if (modelData.status === "passed") return "#1a4a3a"
                                    if (modelData.status === "failed") return "#4a1a1a"
                                    if (modelData.was_healed) return "#4a3a1a"
                                    return "#2a2a2a"
                                }

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.step_index + 1
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: {
                                        if (modelData.status === "passed") return "#4ecca3"
                                        if (modelData.status === "failed") return "#e74c3c"
                                        if (modelData.was_healed) return "#f39c12"
                                        return "#888"
                                    }
                                }
                            }

                            // Step info
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                RowLayout {
                                    spacing: 8

                                    Text {
                                        text: modelData.step_name || modelData.step_type
                                        font.pixelSize: 13
                                        color: "#e0e0e0"
                                    }

                                    // Tier badge
                                    Rectangle {
                                        width: tierText.width + 8
                                        height: 18
                                        radius: 4
                                        color: {
                                            if (modelData.tier_used === 0) return "#2a3a2a"
                                            if (modelData.tier_used === 1) return "#3a3a2a"
                                            if (modelData.tier_used === 2) return "#2a3a3a"
                                            if (modelData.tier_used === 3) return "#3a2a3a"
                                            return "#2a2a2a"
                                        }
                                        visible: modelData.tier_name !== undefined

                                        Text {
                                            id: tierText
                                            anchors.centerIn: parent
                                            text: modelData.tier_name || ("Tier " + modelData.tier_used)
                                            font.pixelSize: 10
                                            color: "#aaa"
                                        }
                                    }

                                    // Healed badge
                                    Rectangle {
                                        width: healedText.width + 8
                                        height: 18
                                        radius: 4
                                        color: "#4a3a1a"
                                        visible: modelData.was_healed

                                        Text {
                                            id: healedText
                                            anchors.centerIn: parent
                                            text: "Healed"
                                            font.pixelSize: 10
                                            color: "#f39c12"
                                        }
                                    }
                                }

                                Text {
                                    text: modelData.error_message || ""
                                    font.pixelSize: 11
                                    color: "#e74c3c"
                                    visible: modelData.error_message
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: modelData.was_healed ? ("Healed: " + modelData.healing_strategy) : ""
                                    font.pixelSize: 11
                                    color: "#f39c12"
                                    visible: modelData.was_healed
                                }
                            }

                            // Duration
                            Text {
                                text: modelData.duration_ms ? (modelData.duration_ms + "ms") : ""
                                font.pixelSize: 12
                                color: "#888"
                            }

                            // Status icon
                            Text {
                                text: {
                                    if (modelData.status === "passed") return "\u2713"
                                    if (modelData.status === "failed") return "\u2717"
                                    if (modelData.status === "skipped") return "\u23ED"
                                    return "\u2022"
                                }
                                font.pixelSize: 18
                                color: {
                                    if (modelData.status === "passed") return "#4ecca3"
                                    if (modelData.status === "failed") return "#e74c3c"
                                    return "#888"
                                }
                            }
                        }
                    }
                }

                // Empty state for details
                Text {
                    anchors.centerIn: parent
                    text: "Select an execution to view details"
                    font.pixelSize: 14
                    color: "#666"
                    visible: selectedExecution === null
                }
            }
        }
    }

    // Properties for selected execution
    property var selectedExecution: null
    property var selectedExecutionSteps: []

    function loadExecutionDetails(executionId) {
        if (executionHistoryModel) {
            var execution = executionHistoryModel.get_execution(executionId)
            if (execution) {
                selectedExecution = execution
                selectedExecutionSteps = execution.steps || []
            }
        }
    }

    Component.onCompleted: {
        if (executionHistoryModel) {
            executionHistoryModel.load_history()
        }
    }
}
