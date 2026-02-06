"""
Variable Sharing Example

Demonstrates how to use the global variable registry to share
variables between workflows (test cases).

Usage:
    python -m examples.variable_sharing_example
"""

import json
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from recorder.services.global_variable_registry import (
    get_global_registry,
    GlobalVariable,
    VariableType,
    reset_global_registry
)


def demo_basic_usage():
    """Demonstrate basic variable storage and retrieval."""
    print("\n" + "="*60)
    print("DEMO: Basic Variable Storage")
    print("="*60)

    # Reset registry for clean demo
    reset_global_registry()
    registry = get_global_registry()

    # Set variables with different types
    registry.set("username", "test_user", group="auth")
    registry.set("user_id", 12345, var_type=VariableType.NUMBER, group="auth")
    registry.set("is_admin", True, var_type=VariableType.BOOLEAN, group="auth")
    registry.set("api_key", "sk-secret-123", masked=True, group="credentials")

    # Retrieve variables
    print(f"\nUsername: {registry.get('username')}")
    print(f"User ID: {registry.get('user_id')}")
    print(f"Is Admin: {registry.get('is_admin')}")
    print(f"API Key (masked): {registry.get('api_key')}")

    # List by group
    print("\n--- Auth Variables ---")
    for var in registry.list_all(group="auth"):
        print(f"  {var.name} = {var.value} ({var.type.value})")

    print("\n--- All Groups ---")
    for group in registry.list_groups():
        print(f"  - {group}")


def demo_cross_workflow_sharing():
    """Demonstrate how variables flow between workflows."""
    print("\n" + "="*60)
    print("DEMO: Cross-Workflow Variable Sharing")
    print("="*60)

    reset_global_registry()
    registry = get_global_registry()

    # Simulate Workflow 1: Login Test (exports authToken, userId)
    print("\n--- Workflow 1: Login Test ---")

    # These would normally be extracted from page elements
    auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    user_id = "user_42"
    session_id = "sess_abc123"

    # Export to global registry
    registry.set("authToken", auth_token, group="auth", created_by="Login Test")
    registry.set("userId", user_id, group="auth", created_by="Login Test")
    registry.set("sessionId", session_id, group="auth", created_by="Login Test")

    print(f"  Exported: authToken, userId, sessionId")

    # Simulate Workflow 2: Add to Cart (imports auth, exports cartId)
    print("\n--- Workflow 2: Add to Cart ---")

    # Import required variables
    token = registry.get("authToken")
    uid = registry.get("userId")
    print(f"  Imported authToken: {token[:20]}...")
    print(f"  Imported userId: {uid}")

    if not token or not uid:
        print("  ERROR: Required variables not found!")
        return

    # Simulate cart creation (would normally be from API response)
    cart_id = "cart_789"
    cart_total = 299.99

    # Export to global registry
    registry.set("cartId", cart_id, group="cart", created_by="Add to Cart")
    registry.set("cartTotal", cart_total, group="cart", created_by="Add to Cart")
    print(f"  Exported: cartId={cart_id}, cartTotal=${cart_total}")

    # Simulate Workflow 3: Checkout (imports all)
    print("\n--- Workflow 3: Checkout ---")

    # Import all needed variables
    token = registry.get("authToken")
    cart_id = registry.get("cartId")
    total = registry.get("cartTotal")

    print(f"  Imported authToken: {token[:20]}...")
    print(f"  Imported cartId: {cart_id}")
    print(f"  Imported cartTotal: ${total}")

    # Show final state
    print("\n--- Global Registry State ---")
    for var in registry.list_all():
        display_value = str(var.value)[:30] + "..." if len(str(var.value)) > 30 else var.value
        print(f"  [{var.group}] {var.name} = {display_value} (from: {var.createdBy})")


def demo_workflow_json_examples():
    """Show example workflow JSON configurations."""
    print("\n" + "="*60)
    print("DEMO: Workflow JSON Examples")
    print("="*60)

    login_workflow = {
        "version": "1.0",
        "metadata": {"name": "Login Test"},
        "variables": {
            "imports": [],
            "exports": [
                {"variableName": "authToken", "group": "auth"},
                {"variableName": "userId", "group": "auth"}
            ]
        },
        "steps": [
            {
                "id": "1",
                "type": "type",
                "name": "Enter username",
                "target": {"locators": [{"type": "css", "value": "#username", "score": 0.9}]},
                "input": {"value": "${env.TEST_USERNAME}"}
            },
            {
                "id": "2",
                "type": "storeVariable",
                "name": "Store auth token",
                "target": {"locators": [{"type": "css", "value": "meta[name='auth-token']", "score": 0.9}]},
                "config": {
                    "variable": {
                        "variableName": "authToken",
                        "source": "element_attribute",
                        "attributeName": "content",
                        "scope": "test"
                    }
                }
            }
        ]
    }

    cart_workflow = {
        "version": "1.0",
        "metadata": {"name": "Add to Cart"},
        "variables": {
            "imports": [
                {"globalName": "authToken", "required": True},
                {"globalName": "userId", "required": True}
            ],
            "exports": [
                {"variableName": "cartId", "group": "cart"}
            ]
        },
        "steps": [
            {
                "id": "1",
                "type": "click",
                "name": "Add to cart",
                "target": {"locators": [{"type": "css", "value": ".add-to-cart", "score": 0.9}]}
            },
            {
                "id": "2",
                "type": "storeVariable",
                "name": "Store cart ID",
                "target": {"locators": [{"type": "css", "value": ".cart", "score": 0.9}]},
                "config": {
                    "variable": {
                        "variableName": "cartId",
                        "source": "element_attribute",
                        "attributeName": "data-cart-id",
                        "scope": "test"
                    }
                }
            }
        ]
    }

    print("\n--- Login Workflow (exports auth) ---")
    print(json.dumps(login_workflow, indent=2))

    print("\n--- Add to Cart Workflow (imports auth, exports cart) ---")
    print(json.dumps(cart_workflow, indent=2))


def demo_expression_evaluation():
    """Demonstrate expression evaluation with variables."""
    print("\n" + "="*60)
    print("DEMO: Expression Evaluation")
    print("="*60)

    from recorder.services.expression_engine import (
        SafeExpressionEvaluator,
        VariableStore as ExprVarStore
    )

    # Set up variables
    var_store = ExprVarStore()
    var_store.set("price", 49.99)
    var_store.set("quantity", 3)
    var_store.set("discount", 10.00)
    var_store.set("taxRate", 0.08)

    evaluator = SafeExpressionEvaluator(var_store)

    # Example expressions
    expressions = [
        "${price} * ${quantity}",
        "${price} * ${quantity} - ${discount}",
        "(${price} * ${quantity} - ${discount}) * (1 + ${taxRate})",
        "round((${price} * ${quantity} - ${discount}) * (1 + ${taxRate}), 2)",
    ]

    print("\nVariables:")
    print(f"  price = $49.99")
    print(f"  quantity = 3")
    print(f"  discount = $10.00")
    print(f"  taxRate = 8%")

    print("\nEvaluations:")
    for expr in expressions:
        try:
            result, used_vars = evaluator.evaluate(expr)
            print(f"  {expr}")
            print(f"    = {result}")
        except Exception as e:
            print(f"  {expr}")
            print(f"    ERROR: {e}")


def demo_persistence():
    """Demonstrate variable persistence."""
    print("\n" + "="*60)
    print("DEMO: Variable Persistence")
    print("="*60)

    from pathlib import Path
    import tempfile

    # Use temp file for demo
    temp_path = Path(tempfile.gettempdir()) / "demo_variables.json"

    reset_global_registry()
    from recorder.services.global_variable_registry import GlobalVariableRegistry

    # Create registry with custom path
    registry = GlobalVariableRegistry(temp_path)

    # Set some variables
    registry.set("persistent_var", "I survive restarts", persistent=True)
    registry.set("runtime_var", "I disappear", persistent=False)

    print(f"\nSaved to: {temp_path}")
    print(f"Persistent: {registry.get('persistent_var')}")
    print(f"Runtime: {registry.get('runtime_var')}")

    # Simulate restart by creating new registry
    print("\n--- Simulating restart ---")
    registry2 = GlobalVariableRegistry(temp_path)

    print(f"After restart:")
    print(f"  persistent_var: {registry2.get('persistent_var')}")
    print(f"  runtime_var: {registry2.get('runtime_var', 'NOT FOUND')}")

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


if __name__ == "__main__":
    demo_basic_usage()
    demo_cross_workflow_sharing()
    demo_expression_evaluation()
    demo_persistence()
    demo_workflow_json_examples()

    print("\n" + "="*60)
    print("All demos completed!")
    print("="*60)
