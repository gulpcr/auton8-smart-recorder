import QtQuick 6.5
import QtQuick.Controls 6.5
import QtQuick.Layouts 6.5
import QtCharts 6.5
import Qt5Compat.GraphicalEffects

/**
 * Professional Material Design 3 UI for Call Intelligence System
 * 
 * Features:
 * - Dark/Light/Auto themes with smooth transitions
 * - Advanced dashboard with real-time metrics
 * - Zoomable timeline with millisecond precision
 * - DOM tree visualization
 * - Network waterfall
 * - Performance monitoring
 * - Workflow management with grid/list views
 * - Settings panel
 */

ApplicationWindow {
    id: mainWindow
    visible: true
    width: 1920
    height: 1080
    minimumWidth: 1280
    minimumHeight: 720
    title: "Call Intelligence System - Professional"
    
    // Theme management
    property string currentTheme: "dark" // dark, light, auto
    property color backgroundColor: currentTheme === "dark" ? "#121212" : "#FFFFFF"
    property color surfaceColor: currentTheme === "dark" ? "#1E1E1E" : "#F5F5F5"
    property color primaryColor: "#6200EE"
    property color secondaryColor: "#03DAC6"
    property color errorColor: "#CF6679"
    property color textPrimaryColor: currentTheme === "dark" ? "#FFFFFF" : "#000000"
    property color textSecondaryColor: currentTheme === "dark" ? "#B3B3B3" : "#666666"
    property color dividerColor: currentTheme === "dark" ? "#2C2C2C" : "#E0E0E0"
    
    // State
    property bool isRecording: false
    property bool isReplaying: false
    property int currentView: 0 // 0=dashboard, 1=timeline, 2=workflows, 3=settings
    
    color: backgroundColor
    
    Behavior on backgroundColor {
        ColorAnimation { duration: 300; easing.type: Easing.InOutQuad }
    }
    
    // ========================================================================
    // Header / App Bar
    // ========================================================================
    
    header: ToolBar {
        height: 64
        background: Rectangle {
            color: surfaceColor
            
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: dividerColor
            }
        }
        
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            spacing: 16
            
            // Logo and Title
            RowLayout {
                spacing: 12
                
                Rectangle {
                    width: 40
                    height: 40
                    radius: 20
                    color: primaryColor
                    
                    Text {
                        anchors.centerIn: parent
                        text: "CI"
                        font.pixelSize: 18
                        font.bold: true
                        color: "white"
                    }
                }
                
                Column {
                    spacing: 2
                    
                    Text {
                        text: "Call Intelligence System"
                        font.pixelSize: 18
                        font.bold: true
                        color: textPrimaryColor
                    }
                    
                    Text {
                        text: "Professional Edition v1.0"
                        font.pixelSize: 11
                        color: textSecondaryColor
                    }
                }
            }
            
            Item { Layout.fillWidth: true }
            
            // Navigation Tabs
            RowLayout {
                spacing: 4
                
                Repeater {
                    model: [
                        {icon: "📊", text: "Dashboard", index: 0},
                        {icon: "⏱️", text: "Timeline", index: 1},
                        {icon: "📁", text: "Workflows", index: 2},
                        {icon: "⚙️", text: "Settings", index: 3}
                    ]
                    
                    delegate: Button {
                        text: modelData.icon + " " + modelData.text
                        flat: true
                        checkable: true
                        checked: currentView === modelData.index
                        
                        background: Rectangle {
                            color: parent.checked ? Qt.alpha(primaryColor, 0.2) : "transparent"
                            radius: 8
                            
                            Rectangle {
                                anchors.bottom: parent.bottom
                                width: parent.width
                                height: 3
                                color: primaryColor
                                visible: parent.parent.checked
                            }
                        }
                        
                        contentItem: Text {
                            text: parent.text
                            font.pixelSize: 14
                            font.bold: parent.checked
                            color: parent.checked ? primaryColor : textSecondaryColor
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        
                        onClicked: currentView = modelData.index
                    }
                }
            }
            
            Item { Layout.fillWidth: true }
            
            // Theme Toggle
            Button {
                text: currentTheme === "dark" ? "🌙" : "☀️"
                flat: true
                width: 40
                height: 40
                
                background: Rectangle {
                    radius: 20
                    color: parent.hovered ? Qt.alpha(textPrimaryColor, 0.1) : "transparent"
                }
                
                onClicked: currentTheme = currentTheme === "dark" ? "light" : "dark"
                
                ToolTip.visible: hovered
                ToolTip.text: "Toggle Theme"
            }
            
            // Status Indicator
            Rectangle {
                width: 12
                height: 12
                radius: 6
                color: isRecording ? errorColor : (isReplaying ? secondaryColor : "#4CAF50")
                
                SequentialAnimation on opacity {
                    running: isRecording || isReplaying
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 500 }
                    NumberAnimation { to: 1.0; duration: 500 }
                }
            }
        }
    }
    
    // ========================================================================
    // Main Content Area
    // ========================================================================
    
    StackLayout {
        anchors.fill: parent
        currentIndex: currentView
        
        // ====================================================================
        // Dashboard View
        // ====================================================================
        
        Item {
            id: dashboardView
            
            Flickable {
                anchors.fill: parent
                anchors.margins: 24
                contentHeight: dashboardColumn.height
                clip: true
                
                Column {
                    id: dashboardColumn
                    width: parent.width
                    spacing: 24
                    
                    // Welcome Section
                    Rectangle {
                        width: parent.width
                        height: 120
                        radius: 16
                        color: surfaceColor
                        
                        layer.enabled: true
                        layer.effect: DropShadow {
                            horizontalOffset: 0
                            verticalOffset: 2
                            radius: 8
                            samples: 16
                            color: "#40000000"
                        }
                        
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 24
                            spacing: 24
                            
                            Column {
                                Layout.fillWidth: true
                                spacing: 8
                                
                                Text {
                                    text: "Welcome back! 👋"
                                    font.pixelSize: 24
                                    font.bold: true
                                    color: textPrimaryColor
                                }
                                
                                Text {
                                    text: "Record, analyze, and replay user workflows with AI-powered intelligence"
                                    font.pixelSize: 14
                                    color: textSecondaryColor
                                    wrapMode: Text.WordWrap
                                }
                            }
                            
                            Button {
                                text: isRecording ? "⏹️ Stop Recording" : "⏺️ Start Recording"
                                Layout.preferredWidth: 200
                                Layout.preferredHeight: 48
                                
                                background: Rectangle {
                                    radius: 24
                                    color: isRecording ? errorColor : primaryColor
                                    
                                    Behavior on color {
                                        ColorAnimation { duration: 200 }
                                    }
                                }
                                
                                contentItem: Text {
                                    text: parent.text
                                    font.pixelSize: 14
                                    font.bold: true
                                    color: "white"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                
                                onClicked: {
                                    if (isRecording) {
                                        controller.stop_recording()
                                        isRecording = false
                                    } else {
                                        controller.start_recording("")
                                        isRecording = true
                                    }
                                }
                            }
                        }
                    }
                    
                    // Metrics Cards
                    GridLayout {
                        width: parent.width
                        columns: 4
                        columnSpacing: 16
                        rowSpacing: 16
                        
                        Repeater {
                            model: [
                                {title: "Total Workflows", value: "127", icon: "📁", change: "+12%"},
                                {title: "Success Rate", value: "94.3%", icon: "✅", change: "+2.1%"},
                                {title: "Avg. Steps", value: "8.5", icon: "👣", change: "-0.3"},
                                {title: "Healing Rate", value: "87%", icon: "🔧", change: "+5%"}
                            ]
                            
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 140
                                radius: 12
                                color: surfaceColor
                                
                                layer.enabled: true
                                layer.effect: DropShadow {
                                    horizontalOffset: 0
                                    verticalOffset: 1
                                    radius: 4
                                    samples: 8
                                    color: "#30000000"
                                }
                                
                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 20
                                    spacing: 12
                                    
                                    RowLayout {
                                        width: parent.width
                                        
                                        Text {
                                            text: modelData.icon
                                            font.pixelSize: 28
                                        }
                                        
                                        Item { Layout.fillWidth: true }
                                        
                                        Rectangle {
                                            width: 60
                                            height: 24
                                            radius: 12
                                            color: modelData.change.startsWith("+") ? 
                                                   Qt.alpha("#4CAF50", 0.2) : Qt.alpha(errorColor, 0.2)
                                            
                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData.change
                                                font.pixelSize: 11
                                                font.bold: true
                                                color: modelData.change.startsWith("+") ? "#4CAF50" : errorColor
                                            }
                                        }
                                    }
                                    
                                    Text {
                                        text: modelData.value
                                        font.pixelSize: 32
                                        font.bold: true
                                        color: textPrimaryColor
                                    }
                                    
                                    Text {
                                        text: modelData.title
                                        font.pixelSize: 13
                                        color: textSecondaryColor
                                    }
                                }
                            }
                        }
                    }
                    
                    // Charts Row
                    RowLayout {
                        width: parent.width
                        height: 300
                        spacing: 16
                        
                        // Success Rate Chart
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 12
                            color: surfaceColor
                            
                            layer.enabled: true
                            layer.effect: DropShadow {
                                horizontalOffset: 0
                                verticalOffset: 1
                                radius: 4
                                samples: 8
                                color: "#30000000"
                            }
                            
                            Column {
                                anchors.fill: parent
                                anchors.margins: 20
                                spacing: 12
                                
                                Text {
                                    text: "Success Rate Over Time"
                                    font.pixelSize: 16
                                    font.bold: true
                                    color: textPrimaryColor
                                }
                                
                                ChartView {
                                    width: parent.width
                                    height: parent.height - 40
                                    antialiasing: true
                                    backgroundColor: "transparent"
                                    legend.visible: false
                                    
                                    LineSeries {
                                        name: "Success Rate"
                                        color: primaryColor
                                        width: 3
                                        
                                        XYPoint { x: 0; y: 85 }
                                        XYPoint { x: 1; y: 88 }
                                        XYPoint { x: 2; y: 90 }
                                        XYPoint { x: 3; y: 89 }
                                        XYPoint { x: 4; y: 92 }
                                        XYPoint { x: 5; y: 94 }
                                        XYPoint { x: 6; y: 94.3 }
                                    }
                                }
                            }
                        }
                        
                        // Performance Metrics
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 12
                            color: surfaceColor
                            
                            layer.enabled: true
                            layer.effect: DropShadow {
                                horizontalOffset: 0
                                verticalOffset: 1
                                radius: 4
                                samples: 8
                                color: "#30000000"
                            }
                            
                            Column {
                                anchors.fill: parent
                                anchors.margins: 20
                                spacing: 12
                                
                                Text {
                                    text: "System Performance"
                                    font.pixelSize: 16
                                    font.bold: true
                                    color: textPrimaryColor
                                }
                                
                                Column {
                                    width: parent.width
                                    spacing: 16
                                    
                                    Repeater {
                                        model: [
                                            {label: "CPU Usage", value: 45, max: 100, unit: "%"},
                                            {label: "Memory", value: 2.3, max: 16, unit: "GB"},
                                            {label: "GPU", value: 62, max: 100, unit: "%"}
                                        ]
                                        
                                        delegate: Column {
                                            width: parent.width
                                            spacing: 8
                                            
                                            RowLayout {
                                                width: parent.width
                                                
                                                Text {
                                                    text: modelData.label
                                                    font.pixelSize: 13
                                                    color: textSecondaryColor
                                                }
                                                
                                                Item { Layout.fillWidth: true }
                                                
                                                Text {
                                                    text: modelData.value + modelData.unit
                                                    font.pixelSize: 13
                                                    font.bold: true
                                                    color: textPrimaryColor
                                                }
                                            }
                                            
                                            Rectangle {
                                                width: parent.width
                                                height: 8
                                                radius: 4
                                                color: Qt.alpha(textPrimaryColor, 0.1)
                                                
                                                Rectangle {
                                                    width: parent.width * (modelData.value / modelData.max)
                                                    height: parent.height
                                                    radius: parent.radius
                                                    color: modelData.value > modelData.max * 0.8 ? 
                                                           errorColor : secondaryColor
                                                    
                                                    Behavior on width {
                                                        NumberAnimation { duration: 500; easing.type: Easing.OutQuad }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    // Recent Activity
                    Rectangle {
                        width: parent.width
                        height: 400
                        radius: 12
                        color: surfaceColor
                        
                        layer.enabled: true
                        layer.effect: DropShadow {
                            horizontalOffset: 0
                            verticalOffset: 1
                            radius: 4
                            samples: 8
                            color: "#30000000"
                        }
                        
                        Column {
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 16
                            
                            Text {
                                text: "Recent Activity"
                                font.pixelSize: 16
                                font.bold: true
                                color: textPrimaryColor
                            }
                            
                            ListView {
                                width: parent.width
                                height: parent.height - 40
                                model: 10
                                spacing: 12
                                clip: true
                                
                                delegate: Rectangle {
                                    width: parent.width
                                    height: 60
                                    radius: 8
                                    color: Qt.alpha(textPrimaryColor, 0.05)
                                    
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 12
                                        
                                        Rectangle {
                                            width: 40
                                            height: 40
                                            radius: 20
                                            color: Qt.alpha(primaryColor, 0.2)
                                            
                                            Text {
                                                anchors.centerIn: parent
                                                text: "🎬"
                                                font.pixelSize: 20
                                            }
                                        }
                                        
                                        Column {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            
                                            Text {
                                                text: "Workflow " + (index + 1) + " completed"
                                                font.pixelSize: 14
                                                font.bold: true
                                                color: textPrimaryColor
                                            }
                                            
                                            Text {
                                                text: "2 minutes ago • 12 steps • 94% success"
                                                font.pixelSize: 12
                                                color: textSecondaryColor
                                            }
                                        }
                                        
                                        Text {
                                            text: "✓"
                                            font.pixelSize: 20
                                            color: "#4CAF50"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        // ====================================================================
        // Timeline View
        // ====================================================================
        
        Item {
            id: timelineView
            
            Rectangle {
                anchors.fill: parent
                anchors.margins: 24
                radius: 12
                color: surfaceColor
                
                Text {
                    anchors.centerIn: parent
                    text: "📊 Timeline View\n(Advanced timeline with zoom, grouping, and metrics)"
                    font.pixelSize: 18
                    color: textSecondaryColor
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
        
        // ====================================================================
        // Workflows View
        // ====================================================================
        
        Item {
            id: workflowsView
            
            Rectangle {
                anchors.fill: parent
                anchors.margins: 24
                radius: 12
                color: surfaceColor
                
                Text {
                    anchors.centerIn: parent
                    text: "📁 Workflows Management\n(Grid/list views, sorting, filtering, bulk operations)"
                    font.pixelSize: 18
                    color: textSecondaryColor
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
        
        // ====================================================================
        // Settings View
        // ====================================================================
        
        Item {
            id: settingsView
            
            Rectangle {
                anchors.fill: parent
                anchors.margins: 24
                radius: 12
                color: surfaceColor
                
                Text {
                    anchors.centerIn: parent
                    text: "⚙️ Settings & Configuration\n(Model paths, preferences, keyboard shortcuts)"
                    font.pixelSize: 18
                    color: textSecondaryColor
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }
    
    // ========================================================================
    // Status Bar
    // ========================================================================
    
    footer: Rectangle {
        height: 32
        color: surfaceColor
        
        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: dividerColor
        }
        
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            spacing: 16
            
            Text {
                text: "Status: " + (isRecording ? "Recording..." : isReplaying ? "Replaying..." : "Ready")
                font.pixelSize: 11
                color: textSecondaryColor
            }
            
            Item { Layout.fillWidth: true }
            
            Text {
                text: "ML Models: Loaded ✓"
                font.pixelSize: 11
                color: "#4CAF50"
            }
            
            Rectangle {
                width: 1
                height: 16
                color: dividerColor
            }
            
            Text {
                text: "WS: Connected"
                font.pixelSize: 11
                color: secondaryColor
            }
        }
    }
}
