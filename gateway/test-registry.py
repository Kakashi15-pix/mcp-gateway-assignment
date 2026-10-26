
from registry import (
    ServerAlreadyExistsError,
    ServerRegistry,
    ServerNotFoundError,
)

registry = ServerRegistry()

print("Existing servers:")
print(registry.list_servers())

print("\nRegistering a temporary test server...")

try:
    server = registry.register_server(
        server_id="registry-test",
        name="Registry Test Server",
        url=os.environ["TEST_MCP_URL"],
        description="Temporary server for testing database persistence",
    )
    print("Registered:", server["id"])

except ServerAlreadyExistsError:
    print("Test server already exists; retrieving it.")
    print(registry.get_server("registry-test"))

print("\nDisabling test server...")
print(registry.set_enabled("registry-test", False))

print("\nRe-enabling test server...")
print(registry.set_enabled("registry-test", True))

print("\nDeleting test server...")
registry.delete_server("registry-test")

try:
    registry.get_server("registry-test")
except ServerNotFoundError:
    print("PASS: Test server was deleted successfully.")
