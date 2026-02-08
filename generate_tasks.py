#!/usr/bin/env python3
"""Generate benchmark tasks from actual compiled specs — only possible tasks."""
import sys, os, json, yaml, random
sys.path.insert(0, '/data/workspace/lap-poc')

from core.compilers.openapi import compile_openapi
from core.compilers.asyncapi import compile_asyncapi
from core.compilers.graphql import compile_graphql
from core.compilers.postman import compile_postman
from core.compilers.protobuf import compile_protobuf

EXAMPLES = '/data/workspace/lap-poc/examples'

SPECS = {
    # OpenAPI
    "stripe-charges": ("openapi", f"{EXAMPLES}/stripe-charges.yaml"),
    "github-core": ("openapi", f"{EXAMPLES}/github-core.yaml"),
    "discord": ("openapi", f"{EXAMPLES}/discord.yaml"),
    "twitter": ("openapi", f"{EXAMPLES}/twitter.yaml"),
    "resend": ("openapi", f"{EXAMPLES}/resend.yaml"),
    "launchdarkly": ("openapi", f"{EXAMPLES}/launchdarkly.yaml"),
    "petstore": ("openapi", f"{EXAMPLES}/petstore.yaml"),
    "snyk": ("openapi", f"{EXAMPLES}/snyk.yaml"),
    "hetzner": ("openapi", f"{EXAMPLES}/hetzner.yaml"),
    "plaid": ("openapi", f"{EXAMPLES}/plaid.yaml"),
    # AsyncAPI
    "async-smart-home": ("asyncapi", f"{EXAMPLES}/asyncapi/smart-home.yaml"),
    "async-food-delivery": ("asyncapi", f"{EXAMPLES}/asyncapi/food-delivery.yaml"),
    "async-ecommerce-kafka": ("asyncapi", f"{EXAMPLES}/asyncapi/ecommerce-kafka.yaml"),
    "async-notifications": ("asyncapi", f"{EXAMPLES}/asyncapi/notifications.yaml"),
    # GraphQL
    "gql-github": ("graphql", f"{EXAMPLES}/graphql/github.graphql"),
    "gql-analytics": ("graphql", f"{EXAMPLES}/graphql/analytics.graphql"),
    "gql-shopify": ("graphql", f"{EXAMPLES}/graphql/shopify.graphql"),
    "gql-wordpress": ("graphql", f"{EXAMPLES}/graphql/wordpress.graphql"),
    # Postman
    "postman-slack": ("postman", f"{EXAMPLES}/postman/slack-api.json"),
    "postman-crud": ("postman", f"{EXAMPLES}/postman/crud-api.json"),
    "postman-openstack": ("postman", f"{EXAMPLES}/postman/openstack-compute.json"),
    "postman-cisco": ("postman", f"{EXAMPLES}/postman/cisco-nso.json"),
    # Protobuf
    "proto-chat": ("protobuf", f"{EXAMPLES}/protobuf/chat.proto"),
    "proto-payments": ("protobuf", f"{EXAMPLES}/protobuf/payments.proto"),
    "proto-google-storage": ("protobuf", f"{EXAMPLES}/protobuf/google_storage.proto"),
    "proto-google-datacatalog": ("protobuf", f"{EXAMPLES}/protobuf/google_datacatalog.proto"),
}

COMPILERS = {
    'openapi': compile_openapi,
    'asyncapi': compile_asyncapi,
    'graphql': compile_graphql,
    'postman': compile_postman,
    'protobuf': compile_protobuf,
}

# Task templates per doc type
OPENAPI_TEMPLATES = [
    "What HTTP method and path would you use to {action}? List the required parameters.",
    "Show me how to call the endpoint for {action}. Include the full URL path and required headers.",
    "What parameters does the {method} {path} endpoint accept? Which are required?",
    "Write a curl command to {action} using the {api_name} API.",
    "What's the authentication method for this API? How would you {action}?",
]

ASYNCAPI_TEMPLATES = [
    "What channel would you subscribe to for {summary}? What's the message payload schema?",
    "List all available channels and their message types.",
    "What protocol does the {channel} channel use? What are the required fields in the payload?",
    "How would you publish a message to {channel}? Show the expected payload structure.",
]

GRAPHQL_TEMPLATES = [
    "Write a GraphQL query to {summary}. Include all available fields.",
    "What arguments does the {name} query/mutation accept? Which are required?",
    "Show me how to query {name} with filtering. List the return type fields.",
    "What types are available in this schema? List their fields.",
]

POSTMAN_TEMPLATES = [
    "What's the full URL and method for {summary}? List required parameters.",
    "Show me how to call {method} {path}. Include headers and body if needed.",
    "What endpoints are available under the {path_prefix} path? Summarize each.",
    "Write a curl command to {action} using this API.",
]

PROTOBUF_TEMPLATES = [
    "What RPC method would you use to {summary}? What's the request message structure?",
    "List all available RPC methods in the {service} service.",
    "What fields does the {message} message contain? Which are required?",
    "Show me how to call {method} {path}. What's the request/response pair?",
]

def generate_tasks_for_spec(name, ctype, spec_path):
    """Generate 3-5 tasks per spec based on actual endpoints."""
    compiler = COMPILERS[ctype]
    result = compiler(spec_path)
    endpoints = result.endpoints
    
    if not endpoints:
        return []
    
    tasks = []
    
    # Task 1: Always ask to list/summarize available endpoints
    if ctype == 'openapi':
        tasks.append(f"List all available API endpoints in the {result.api_name} API with their HTTP methods and brief descriptions.")
    elif ctype == 'asyncapi':
        tasks.append(f"List all available channels in the {result.api_name} spec with their publish/subscribe operations and message types.")
    elif ctype == 'graphql':
        tasks.append(f"List all available queries and mutations in this GraphQL schema with their arguments and return types.")
    elif ctype == 'postman':
        tasks.append(f"List all available API endpoints in the {result.api_name} collection with their methods and descriptions.")
    elif ctype == 'protobuf':
        tasks.append(f"List all available RPC methods in this protobuf service definition with their request/response message types.")
    
    # Task 2-4: Pick specific endpoints and ask about them
    sample_size = min(3, len(endpoints))
    sampled = random.sample(endpoints, sample_size)
    
    for ep in sampled:
        if ctype == 'openapi':
            summary = ep.summary or f"the {ep.method.upper()} {ep.path} endpoint"
            tasks.append(f"How do I call the {ep.method.upper()} {ep.path} endpoint? What parameters does it require and what does it return?")
        elif ctype == 'asyncapi':
            tasks.append(f"What is the message schema for the '{ep.path}' channel? List all fields and their types.")
        elif ctype == 'graphql':
            op_name = ep.path.lstrip('/')
            tasks.append(f"Write a complete GraphQL query/mutation for '{op_name}'. Show all available arguments and return fields.")
        elif ctype == 'postman':
            tasks.append(f"How do I call {ep.method.upper()} {ep.path}? Show the required headers, parameters, and example request body if applicable.")
        elif ctype == 'protobuf':
            rpc_name = ep.path.split('/')[-1] if '/' in ep.path else ep.path
            tasks.append(f"What are the request and response message structures for the '{rpc_name}' RPC method? List all fields with their types.")
    
    # Task 5: Ask about auth/base URL/connection details
    if result.base_url:
        if ctype == 'openapi':
            tasks.append(f"What is the base URL for this API and what authentication method does it use? How would I authenticate a request?")
        elif ctype == 'asyncapi':
            tasks.append(f"What server/broker does this API connect to and what protocol does it use?")
        elif ctype == 'postman':
            tasks.append(f"What is the base URL for this API collection and what authentication is required?")
    
    return tasks[:5]  # Cap at 5 per spec


# Generate all tasks
all_tasks = {}
for name, (ctype, path) in sorted(SPECS.items()):
    try:
        tasks = generate_tasks_for_spec(name, ctype, path)
        all_tasks[name] = {
            "type": ctype,
            "tasks": tasks,
            "task_count": len(tasks)
        }
        print(f"✅ {name} ({ctype}): {len(tasks)} tasks")
    except Exception as e:
        print(f"❌ {name} ({ctype}): {e}")

# Write YAML
output_path = '/data/workspace/lap-benchmark-docs/benchmark_tasks.yaml'
with open(output_path, 'w') as f:
    yaml.dump(all_tasks, f, default_flow_style=False, width=120, allow_unicode=True)

total = sum(v['task_count'] for v in all_tasks.values())
print(f"\nTotal: {total} tasks across {len(all_tasks)} specs")
print(f"Written to: {output_path}")
