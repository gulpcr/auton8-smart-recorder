import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4

/**
 * Variable Helper Component
 *
 * Provides variable picker and expression builder with:
 * - Browse available variables from workflow
 * - Global variables from registry
 * - Expression templates and builder
 * - Variable operations (math, string, etc.)
 */
Popup {
    id: variableHelper

    property string selectedVariable: ""
    property string selectedExpression: ""

    // Callback when variable/expression is selected
    signal variableSelected(string variable)
    signal expressionSelected(string expression)

    width: 650
    height: 550
    modal: true
    anchors.centerIn: Overlay.overlay
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        color: "#16213e"
        radius: 12
        border.color: "#7b68ee"
        border.width: 2
    }

    contentItem: ColumnLayout {
        spacing: 12

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Text {
                text: "📦 Variable Helper"
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
                    onClicked: variableHelper.close()
                }
            }
        }

        // Tab bar
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Repeater {
                model: [
                    {id: "variables", label: "📋 Variables", color: "#7b68ee"},
                    {id: "expressions", label: "🔢 Expressions", color: "#4ecca3"},
                    {id: "functions", label: "ƒ Functions", color: "#ffc93c"}
                ]

                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: 6
                    color: varTabView.currentTab === modelData.id ? modelData.color : "#0f3460"
                    border.color: modelData.color
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        font.pixelSize: 12
                        font.bold: varTabView.currentTab === modelData.id
                        color: varTabView.currentTab === modelData.id ? "#000" : "#fff"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: varTabView.currentTab = modelData.id
                    }
                }
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: "#2a4a70" }

        // Tab content
        Item {
            id: varTabView
            Layout.fillWidth: true
            Layout.fillHeight: true

            property string currentTab: "variables"

            // Variables Tab
            Rectangle {
                anchors.fill: parent
                visible: varTabView.currentTab === "variables"
                color: "#0a1525"
                radius: 8

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12

                    // Scope filter
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Text {
                            text: "Scope:"
                            font.pixelSize: 12
                            color: "#9aa8b8"
                        }

                        Repeater {
                            model: [
                                {id: "all", label: "All"},
                                {id: "test", label: "Test"},
                                {id: "suite", label: "Suite"},
                                {id: "global", label: "Global"},
                                {id: "env", label: "Env"}
                            ]

                            Rectangle {
                                width: 60
                                height: 26
                                radius: 4
                                color: scopeFilter.currentScope === modelData.id ? "#7b68ee" : "#0f3460"
                                border.color: "#7b68ee"

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.pixelSize: 10
                                    color: "#fff"
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: scopeFilter.currentScope = modelData.id
                                }
                            }
                        }

                        Item {
                            id: scopeFilter
                            property string currentScope: "all"
                        }
                    }

                    // Variable list
                    ListView {
                        id: variableList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4

                        model: {
                            var vars = []

                            // Add built-in/common variables
                            var builtIn = [
                                {name: "env.BASE_URL", scope: "env", value: "Environment base URL", type: "string"},
                                {name: "env.TEST_USER", scope: "env", value: "Test username", type: "string"},
                                {name: "env.TEST_PASSWORD", scope: "env", value: "Test password", type: "secret"}
                            ]

                            // Add example workflow variables
                            var workflow = [
                                {name: "authToken", scope: "test", value: "Authentication token", type: "string"},
                                {name: "userId", scope: "test", value: "Current user ID", type: "string"},
                                {name: "cartId", scope: "suite", value: "Shopping cart ID", type: "string"},
                                {name: "totalPrice", scope: "test", value: "Calculated total", type: "number"}
                            ]

                            // Filter by scope
                            var all = builtIn.concat(workflow)
                            if (scopeFilter.currentScope === "all") {
                                return all
                            }
                            return all.filter(function(v) {
                                return v.scope === scopeFilter.currentScope
                            })
                        }

                        delegate: Rectangle {
                            width: variableList.width
                            height: 44
                            radius: 6
                            color: varItemMouse.containsMouse ? "#1a3a50" : "#0f2535"
                            border.color: varItemMouse.containsMouse ? "#7b68ee" : "transparent"

                            MouseArea {
                                id: varItemMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    var varRef = "${" + modelData.name + "}"
                                    variableHelper.selectedVariable = varRef
                                    variableHelper.variableSelected(varRef)
                                    variableHelper.close()
                                }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10

                                // Scope badge
                                Rectangle {
                                    width: 50
                                    height: 20
                                    radius: 4
                                    color: {
                                        if (modelData.scope === "env") return "#2a4a30"
                                        if (modelData.scope === "global") return "#4a2a4a"
                                        if (modelData.scope === "suite") return "#3a3a2a"
                                        return "#1a3a4a"
                                    }

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.scope
                                        font.pixelSize: 9
                                        font.bold: true
                                        color: {
                                            if (modelData.scope === "env") return "#4ecca3"
                                            if (modelData.scope === "global") return "#e94560"
                                            if (modelData.scope === "suite") return "#ffc93c"
                                            return "#7b68ee"
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Text {
                                        text: "${" + modelData.name + "}"
                                        font.pixelSize: 12
                                        font.family: "Consolas"
                                        font.bold: true
                                        color: "#e0e0e0"
                                    }

                                    Text {
                                        text: modelData.value
                                        font.pixelSize: 10
                                        color: "#888"
                                    }
                                }

                                // Type badge
                                Rectangle {
                                    width: 50
                                    height: 18
                                    radius: 3
                                    color: "#1a2a3a"

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.type
                                        font.pixelSize: 9
                                        color: modelData.type === "secret" ? "#e94560" : "#888"
                                    }
                                }

                                // Copy button
                                Rectangle {
                                    width: 30
                                    height: 30
                                    radius: 4
                                    color: copyMouse.containsMouse ? "#4ecca3" : "#0f3460"

                                    Text {
                                        anchors.centerIn: parent
                                        text: "📋"
                                        font.pixelSize: 12
                                    }

                                    MouseArea {
                                        id: copyMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            // Copy to clipboard would go here
                                            var varRef = "${" + modelData.name + "}"
                                            variableHelper.variableSelected(varRef)
                                            variableHelper.close()
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Expressions Tab
            Rectangle {
                anchors.fill: parent
                visible: varTabView.currentTab === "expressions"
                color: "#0a1525"
                radius: 8

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12

                    // Expression builder
                    Text {
                        text: "Build Expression"
                        font.pixelSize: 14
                        font.bold: true
                        color: "#4ecca3"
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 60
                        radius: 6
                        color: "#0f2535"
                        border.color: exprInput.activeFocus ? "#4ecca3" : "#2a4a70"

                        TextEdit {
                            id: exprInput
                            anchors.fill: parent
                            anchors.margins: 10
                            color: "#e0e0e0"
                            font.pixelSize: 13
                            font.family: "Consolas"
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true

                            Text {
                                visible: !exprInput.text
                                text: "e.g., ${price} * ${quantity} + ${shipping}"
                                color: "#666"
                                font.pixelSize: 13
                                font.family: "Consolas"
                            }
                        }
                    }

                    // Quick insert buttons
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Repeater {
                            model: ["+", "-", "*", "/", "(", ")", "==", "!=", ">", "<"]

                            Rectangle {
                                width: 36
                                height: 32
                                radius: 4
                                color: opMouse.containsMouse ? "#4ecca3" : "#1a2a3a"

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.pixelSize: 14
                                    font.bold: true
                                    color: "#fff"
                                }

                                MouseArea {
                                    id: opMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: exprInput.text += " " + modelData + " "
                                }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#2a4a70" }

                    // Expression templates
                    Text {
                        text: "Templates"
                        font.pixelSize: 12
                        font.bold: true
                        color: "#9aa8b8"
                    }

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4

                        model: [
                            {expr: "${price} * ${quantity}", desc: "Subtotal calculation"},
                            {expr: "${subtotal} + ${tax} + ${shipping}", desc: "Total with tax & shipping"},
                            {expr: "${total} - ${discount}", desc: "Apply discount"},
                            {expr: "${price} * (1 - ${discountPercent}/100)", desc: "Percentage discount"},
                            {expr: "round(${value}, 2)", desc: "Round to 2 decimals"},
                            {expr: "${count} + 1", desc: "Increment counter"},
                            {expr: "concat(${firstName}, ' ', ${lastName})", desc: "Combine names"},
                            {expr: "upper(${text})", desc: "Convert to uppercase"},
                            {expr: "${value} >= ${threshold}", desc: "Comparison check"}
                        ]

                        delegate: Rectangle {
                            width: parent ? parent.width : 0
                            height: 40
                            radius: 4
                            color: exprMouse.containsMouse ? "#1a3a50" : "#0f2535"

                            MouseArea {
                                id: exprMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    exprInput.text = modelData.expr
                                }
                                onDoubleClicked: {
                                    variableHelper.expressionSelected(modelData.expr)
                                    variableHelper.close()
                                }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 12

                                Text {
                                    text: modelData.expr
                                    font.pixelSize: 11
                                    font.family: "Consolas"
                                    color: "#4ecca3"
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: modelData.desc
                                    font.pixelSize: 10
                                    color: "#888"
                                }
                            }
                        }
                    }

                    // Use expression button
                    Rectangle {
                        Layout.fillWidth: true
                        height: 40
                        radius: 6
                        color: useExprMouse.containsMouse ? "#3dcc93" : "#4ecca3"

                        Text {
                            anchors.centerIn: parent
                            text: "Use Expression"
                            font.pixelSize: 13
                            font.bold: true
                            color: "#000"
                        }

                        MouseArea {
                            id: useExprMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (exprInput.text) {
                                    variableHelper.expressionSelected(exprInput.text)
                                    variableHelper.close()
                                }
                            }
                        }
                    }
                }
            }

            // Functions Tab
            Rectangle {
                anchors.fill: parent
                visible: varTabView.currentTab === "functions"
                color: "#0a1525"
                radius: 8

                ListView {
                    anchors.fill: parent
                    anchors.margins: 12
                    clip: true
                    spacing: 8

                    model: [
                        {category: "Math Functions", items: [
                            {fn: "abs(x)", desc: "Absolute value"},
                            {fn: "round(x, decimals)", desc: "Round number"},
                            {fn: "min(a, b, ...)", desc: "Minimum value"},
                            {fn: "max(a, b, ...)", desc: "Maximum value"},
                            {fn: "sum(list)", desc: "Sum of values"},
                            {fn: "avg(list)", desc: "Average of values"}
                        ]},
                        {category: "String Functions", items: [
                            {fn: "upper(s)", desc: "Convert to uppercase"},
                            {fn: "lower(s)", desc: "Convert to lowercase"},
                            {fn: "strip(s)", desc: "Remove whitespace"},
                            {fn: "concat(a, b, ...)", desc: "Join strings"},
                            {fn: "replace(s, old, new)", desc: "Replace text"},
                            {fn: "len(s)", desc: "String length"}
                        ]},
                        {category: "Type Conversion", items: [
                            {fn: "int(x)", desc: "Convert to integer"},
                            {fn: "float(x)", desc: "Convert to float"},
                            {fn: "str(x)", desc: "Convert to string"},
                            {fn: "number(s)", desc: "Extract number from string"}
                        ]},
                        {category: "String Checks", items: [
                            {fn: "contains(s, sub)", desc: "Check if contains substring"},
                            {fn: "startswith(s, prefix)", desc: "Check prefix"},
                            {fn: "endswith(s, suffix)", desc: "Check suffix"}
                        ]}
                    ]

                    delegate: ColumnLayout {
                        width: parent ? parent.width : 0
                        spacing: 6

                        Text {
                            text: modelData.category
                            font.pixelSize: 13
                            font.bold: true
                            color: "#ffc93c"
                            topPadding: 8
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 8
                            rowSpacing: 4

                            Repeater {
                                model: modelData.items

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 36
                                    radius: 4
                                    color: fnMouse.containsMouse ? "#1a3a50" : "#0f2535"

                                    MouseArea {
                                        id: fnMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            // Insert function at cursor in expression builder
                                            if (varTabView.currentTab !== "expressions") {
                                                varTabView.currentTab = "expressions"
                                            }
                                            exprInput.text += modelData.fn
                                        }
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        spacing: 8

                                        Text {
                                            text: modelData.fn
                                            font.pixelSize: 11
                                            font.family: "Consolas"
                                            font.bold: true
                                            color: "#e0e0e0"
                                            Layout.preferredWidth: 140
                                        }

                                        Text {
                                            text: modelData.desc
                                            font.pixelSize: 10
                                            color: "#888"
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: "#2a4a70" }

        // Quick variable input
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: "Quick:"
                font.pixelSize: 12
                color: "#9aa8b8"
            }

            Rectangle {
                Layout.fillWidth: true
                height: 36
                radius: 4
                color: "#0f3460"
                border.color: quickVarInput.activeFocus ? "#7b68ee" : "#2a4a70"

                TextInput {
                    id: quickVarInput
                    anchors.fill: parent
                    anchors.margins: 8
                    color: "#e0e0e0"
                    font.pixelSize: 12
                    font.family: "Consolas"
                    clip: true
                    selectByMouse: true

                    Text {
                        visible: !quickVarInput.text
                        text: "Type variable name or expression..."
                        color: "#666"
                        font.pixelSize: 12
                    }
                }
            }

            Rectangle {
                width: 100
                height: 36
                radius: 4
                color: insertVarMouse.containsMouse ? "#8b78ee" : "#7b68ee"

                Text {
                    anchors.centerIn: parent
                    text: "Insert ${...}"
                    font.pixelSize: 11
                    font.bold: true
                    color: "#fff"
                }

                MouseArea {
                    id: insertVarMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (quickVarInput.text) {
                            var varRef = "${" + quickVarInput.text + "}"
                            variableHelper.variableSelected(varRef)
                            variableHelper.close()
                        }
                    }
                }
            }
        }
    }
}
