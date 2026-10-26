
import json
import os

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from mcp.server.mcpserver import MCPServer


mcp = MCPServer(
    "Kubernetes Health Monitor",
    
)

try:
    config.load_incluster_config()
except config.ConfigException:
    config.load_kube_config()

kube_configuration = client.Configuration.get_default_copy()
kube_configuration.retries = 0
core = client.CoreV1Api(api_client=client.ApiClient(configuration=kube_configuration))
REQUEST_TIMEOUT = 5


def summarize_pod(pod):
    """Extract useful health information from a Kubernetes Pod."""
    statuses = pod.status.container_statuses or []

    containers = []
    for item in statuses:
        state = item.state
        state_name = "unknown"
        reason = None

        if state:
            if state.running:
                state_name = "running"
            elif state.waiting:
                state_name = "waiting"
                reason = state.waiting.reason
            elif state.terminated:
                state_name = "terminated"
                reason = state.terminated.reason

        containers.append({
            "name": item.name,
            "ready": item.ready,
            "state": state_name,
            "reason": reason,
            "restart_count": item.restart_count,
        })

    ready = (
        len(statuses) > 0
        and all(item.ready for item in statuses)
    )

    return {
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "phase": pod.status.phase,
        "node": pod.spec.node_name,
        "pod_ip": pod.status.pod_ip,
        "ready": ready,
        "containers": containers,
        "total_restarts": sum(
            item.restart_count for item in statuses
        ),
    }


@mcp.tool()
def get_cluster_health() -> str:
    """Report Kubernetes API access, node readiness and pod health."""
    try:
        nodes = core.list_node(_request_timeout=REQUEST_TIMEOUT).items
        pods = core.list_pod_for_all_namespaces(_request_timeout=REQUEST_TIMEOUT).items

        node_results = []
        for node in nodes:
            ready_condition = next(
                (
                    condition
                    for condition in (node.status.conditions or [])
                    if condition.type == "Ready"
                ),
                None,
            )

            is_ready = (
                ready_condition is not None
                and ready_condition.status == "True"
            )

            node_results.append({
                "name": node.metadata.name,
                "ready": is_ready,
            })

        pod_results = [summarize_pod(pod) for pod in pods]

        unhealthy = [
            pod for pod in pod_results
            if pod["phase"] not in ("Running", "Succeeded")
            or (
                pod["phase"] == "Running"
                and not pod["ready"]
            )
        ]

        return json.dumps({
            "api_accessible": True,
            "all_nodes_ready": (
                bool(node_results)
                and all(node["ready"] for node in node_results)
            ),
            "nodes": node_results,
            "total_pods": len(pod_results),
            "unhealthy_pod_count": len(unhealthy),
            "unhealthy_pods": unhealthy,
        }, indent=2)

    except ApiException as exc:
        return json.dumps({
            "api_accessible": False,
            "status_code": exc.status,
            "error": exc.reason,
        }, indent=2)

    except Exception as exc:
        return json.dumps({
            "api_accessible": False,
            "error": str(exc),
        }, indent=2)


@mcp.tool()
def get_pod_details(
    pod_name: str,
    namespace: str = "default",
) -> str:
    """Get pod phase, readiness, container states and restart counts."""
    try:
        pod = core.read_namespaced_pod(
            name=pod_name,
            namespace=namespace,
            _request_timeout=REQUEST_TIMEOUT,
        )
        return json.dumps(summarize_pod(pod), indent=2)

    except ApiException as exc:
        return json.dumps({
            "error": exc.reason,
            "status_code": exc.status,
            "pod_name": pod_name,
            "namespace": namespace,
        }, indent=2)

    except Exception as exc:
        return json.dumps({"error": str(exc)}, indent=2)


@mcp.tool()
def list_unhealthy_pods(
    namespace: str = "",
) -> str:
    """List pending, failed, or unready pods.
    Pass a namespace to filter results, or an empty string for all namespaces.
    """
    try:
        if namespace:
            pods = core.list_namespaced_pod(
                namespace=namespace,
                _request_timeout=REQUEST_TIMEOUT,
            ).items
        else:
            pods = core.list_pod_for_all_namespaces(
                _request_timeout=REQUEST_TIMEOUT
            ).items

        results = []
        for pod in pods:
            summary = summarize_pod(pod)

            unhealthy = (
                summary["phase"] not in ("Running", "Succeeded")
                or (
                    summary["phase"] == "Running"
                    and not summary["ready"]
                )
            )

            if unhealthy:
                results.append(summary)

        return json.dumps({
            "namespace_filter": namespace or "all",
            "count": len(results),
            "pods": results,
        }, indent=2)

    except ApiException as exc:
        return json.dumps({
            "error": exc.reason,
            "status_code": exc.status,
        }, indent=2)

    except Exception as exc:
        return json.dumps({"error": str(exc)}, indent=2)


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8001"))
    allowed_hosts = [
        item.strip() for item in os.getenv("ALLOWED_HOSTS", "").split(",") if item.strip()
    ]
    transport_security = None
    if allowed_hosts:
        from mcp.server.transport_security import TransportSecuritySettings

        transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
        )
    mcp.run(transport="streamable-http",
    host=host,
    port=port,
    transport_security=transport_security,
    )
