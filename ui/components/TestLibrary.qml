import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4

/**
 * Test Library - Main view for browsing, searching, and managing recorded tests
 */
Item {
    id: root

    // Signals
    signal testSelected(string path)
    signal testEdit(string path)
    signal testReplay(string path)
    signal testDuplicate(string path)
    signal testDelete(string path)
    signal exportTest(string path)
    signal uploadTest(string path)
    signal createNewTest()

    // Page header
    RowLayout {
        id: pageHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 48
        spacing: 16

        ColumnLayout {
            spacing: 2

            Text {
                text: "Test Library"
                font.pixelSize: 20
                font.bold: true
                color: "#e0e0e0"
            }

            Text {
                text: testLibraryModel.rowCount() + " tests saved"
                font.pixelSize: 12
                color: "#666"
            }
        }

        Item { Layout.fillWidth: true }

        Button {
            id: newTestBtn
            implicitWidth: 140
            implicitHeight: 38

            background: Rectangle {
                radius: 6
                color: newTestBtn.hovered ? "#d63e5c" : "#e94560"
            }

            contentItem: Row {
                anchors.centerIn: parent
                spacing: 6

                Text {
                    text: "+"
                    font.pixelSize: 16
                    font.bold: true
                    color: "#fff"
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "New Test"
                    font.pixelSize: 13
                    font.bold: true
                    color: "#fff"
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            onClicked: root.createNewTest()
        }
    }

    // Search bar
    Rectangle {
        id: searchBar
        anchors.top: pageHeader.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: 16
        height: 52
        color: "#16213e"
        radius: 8
        
        RowLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12
            
            // Search input
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 6
                color: "#0f3460"
                border.color: searchInput.activeFocus ? "#e94560" : "#2a4a70"
                border.width: 2
                
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8
                    
                    Text {
                        text: "\uD83D\uDD0D"  // 🔍
                        font.pixelSize: 18
                        color: "#888"
                    }
                    
                    TextInput {
                        id: searchInput
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        font.pixelSize: 14
                        color: "#e0e0e0"
                        selectByMouse: true
                        verticalAlignment: TextInput.AlignVCenter
                        clip: true
                        
                        onTextChanged: {
                            testLibraryModel.set_search_query(text)
                        }
                        
                        Text {
                            anchors.fill: parent
                            verticalAlignment: Text.AlignVCenter
                            text: "Search tests by name, tags, or URL..."
                            color: "#666"
                            font.pixelSize: 14
                            visible: !searchInput.text && !searchInput.activeFocus
                        }
                    }
                    
                    // Clear button
                    Rectangle {
                        width: 24
                        height: 24
                        radius: 12
                        color: clearBtnMouseArea.containsMouse ? "#e94560" : "transparent"
                        visible: searchInput.text.length > 0
                        
                        Text {
                            anchors.centerIn: parent
                            text: "\u2715"  // ✕
                            font.pixelSize: 12
                            color: "#e0e0e0"
                        }
                        
                        MouseArea {
                            id: clearBtnMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: searchInput.text = ""
                        }
                    }
                }
            }
            
            // Filter chips
            Row {
                spacing: 6
                
                FilterChip {
                    text: "Draft"
                    active: statusFilter.indexOf("draft") >= 0
                    count: testLibraryModel.get_status_counts()["draft"] || 0
                    onClicked: toggleStatusFilter("draft")
                }
                
                FilterChip {
                    text: "Ready"
                    active: statusFilter.indexOf("ready") >= 0
                    count: testLibraryModel.get_status_counts()["ready"] || 0
                    chipColor: "#4ecca3"
                    onClicked: toggleStatusFilter("ready")
                }
                
                FilterChip {
                    text: "Flaky"
                    active: statusFilter.indexOf("flaky") >= 0
                    count: testLibraryModel.get_status_counts()["flaky"] || 0
                    chipColor: "#ffc93c"
                    onClicked: toggleStatusFilter("flaky")
                }
                
                FilterChip {
                    text: "Broken"
                    active: statusFilter.indexOf("broken") >= 0
                    count: testLibraryModel.get_status_counts()["broken"] || 0
                    chipColor: "#c73e1d"
                    onClicked: toggleStatusFilter("broken")
                }
            }
            
            // Sort dropdown
            ComboBox {
                id: sortCombo
                implicitWidth: 140
                implicitHeight: 36
                model: ["Recently Updated", "Name A-Z", "Name Z-A", "Most Steps"]
                currentIndex: 0
                
                background: Rectangle {
                    radius: 6
                    color: "#0f3460"
                    border.color: "#2a4a70"
                }
                
                contentItem: Text {
                    leftPadding: 8
                    text: sortCombo.displayText
                    font.pixelSize: 13
                    color: "#e0e0e0"
                    verticalAlignment: Text.AlignVCenter
                }
                
                onCurrentIndexChanged: {
                    switch(currentIndex) {
                        case 0: testLibraryModel.set_sort("updatedAt", false); break
                        case 1: testLibraryModel.set_sort("name", true); break
                        case 2: testLibraryModel.set_sort("name", false); break
                        case 3: testLibraryModel.set_sort("stepCount", false); break
                    }
                }
            }
        }
    }
    
    // Test list
    Rectangle {
        id: testListContainer
        anchors.top: searchBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.topMargin: 16
        color: "transparent"
        
        // Empty state
        Rectangle {
            anchors.centerIn: parent
            width: 400
            height: 300
            color: "#16213e"
            radius: 12
            visible: testLibraryModel.rowCount() === 0 && searchInput.text === ""
            
            ColumnLayout {
                anchors.centerIn: parent
                spacing: 20
                width: parent.width - 40
                
                Text {
                    text: "\uD83D\uDCDD"  // 📝
                    font.pixelSize: 64
                    color: "#666"
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    text: "No Tests Yet"
                    font.pixelSize: 22
                    font.bold: true
                    color: "#e0e0e0"
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    text: "Record your first test to get started with automated testing"
                    font.pixelSize: 14
                    color: "#888"
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Button {
                    text: "+ Record New Test"
                    implicitHeight: 48
                    Layout.preferredWidth: 200
                    Layout.alignment: Qt.AlignHCenter
                    
                    background: Rectangle {
                        radius: 8
                        color: parent.hovered ? "#d63e5c" : "#e94560"
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 16
                        font.bold: true
                        color: "#fff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    
                    onClicked: root.createNewTest()
                }
                
                Text {
                    text: "Tip: Tests are automatically saved with all selectors and ML metadata"
                    font.pixelSize: 12
                    color: "#666"
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    Layout.topMargin: 10
                }
            }
        }
        
        // No search results
        Text {
            anchors.centerIn: parent
            visible: testLibraryModel.rowCount() === 0 && searchInput.text !== ""
            text: "No tests match your search\nTry different keywords or clear filters"
            font.pixelSize: 14
            color: "#666"
            horizontalAlignment: Text.AlignHCenter
        }
        
        // Test cards grid
        ScrollView {
            anchors.fill: parent
            visible: testLibraryModel.rowCount() > 0
            clip: true
            
            GridView {
                id: testGrid
                anchors.fill: parent
                anchors.margins: 8
                cellWidth: Math.floor(width / Math.max(1, Math.floor(width / 380)))
                cellHeight: 180
                model: testLibraryModel
                
                delegate: TestCard {
                    width: testGrid.cellWidth - 12
                    height: testGrid.cellHeight - 12
                    
                    testName: model.name
                    testStatus: model.status
                    testTags: model.tags
                    testSteps: model.stepCount
                    testUrl: model.baseUrl
                    testUpdated: model.updatedAt
                    testPath: model.path
                    testSuccessRate: model.successRate
                    testSuccessProjection: model.successProjection
                    
                    onClicked: root.testSelected(model.path)
                    onEdit: root.testEdit(model.path)
                    onReplay: root.testReplay(model.path)
                    onDuplicate: root.testDuplicate(model.path)
                    onDeleteTest: root.testDelete(model.path)
                    onExportTest: root.exportTest(model.path)
                    onUpload: root.uploadTest(model.path)
                }
            }
        }
    }
    
    // Status filter management
    property var statusFilter: []
    
    function toggleStatusFilter(status) {
        var index = statusFilter.indexOf(status)
        if (index >= 0) {
            statusFilter.splice(index, 1)
        } else {
            statusFilter.push(status)
        }
        statusFilter = statusFilter  // Trigger change
        testLibraryModel.set_status_filter(statusFilter)
    }
    
    // Format time ago
    function formatTimeAgo(isoTime) {
        if (!isoTime) return "Never"
        // Simple formatting - could be enhanced
        return isoTime.substring(0, 10)
    }
}
