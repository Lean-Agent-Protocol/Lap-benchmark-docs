#!/usr/bin/env python3
"""Generate realistic integration tasks — what a real user would ask an agent to do."""
import sys, os, yaml
sys.path.insert(0, '/data/workspace/lap-poc')

from core.compilers.openapi import compile_openapi
from core.compilers.asyncapi import compile_asyncapi
from core.compilers.graphql import compile_graphql
from core.compilers.postman import compile_postman
from core.compilers.protobuf import compile_protobuf

EXAMPLES = '/data/workspace/lap-poc/examples'

COMPILERS = {
    'openapi': compile_openapi,
    'asyncapi': compile_asyncapi,
    'graphql': compile_graphql,
    'postman': compile_postman,
    'protobuf': compile_protobuf,
}

# Realistic integration tasks per spec — what a user would actually ask
# Each task must be solvable using ONLY the documented endpoints/operations
TASKS = {
    # === OpenAPI ===
    "stripe-charges": {
        "type": "openapi",
        "path": f"{EXAMPLES}/stripe-charges.yaml",
        "tasks": [
            "I need to charge a customer $49.99 for their monthly subscription. Their customer ID is cus_ABC123. Write me the code to create the charge and then retrieve it to confirm it went through.",
            "A customer is disputing a charge. I need to pull up all charges for customer cus_XYZ789 from the last 30 days so I can find the one they're talking about. How do I do that?",
            "We need to refund a charge (ch_1234) partially — just $15 of the original $50. Walk me through how to do that with the API.",
        ]
    },
    "github-core": {
        "type": "openapi",
        "path": f"{EXAMPLES}/github-core.yaml",
        "tasks": [
            "I want to set up a new private repo called 'backend-api' under our org 'acme-corp', add a README, and invite my colleague (username: jsmith) as a collaborator. Walk me through the API calls.",
            "We need to automate our release process. Show me how to create a new release tagged v2.1.0 on the 'main' branch of repo 'acme-corp/backend-api' with release notes.",
            "I need to check all open pull requests on our repo and see which ones have passing CI checks. How do I get that info from the API?",
        ]
    },
    "discord": {
        "type": "openapi",
        "path": f"{EXAMPLES}/discord.yaml",
        "tasks": [
            "I'm building a bot that needs to send an embedded message with a title, description, and color to a specific channel. Then it should pin that message. Show me the API calls.",
            "I need to create a new text channel called 'announcements' in my server, set it so only admins can post, and send a welcome message to it.",
            "How do I set up the bot to react to a specific message with a custom emoji, then check who else reacted to it?",
        ]
    },
    "twitter": {
        "type": "openapi",
        "path": f"{EXAMPLES}/twitter.yaml",
        "tasks": [
            "I want to build a monitoring tool that searches for tweets mentioning our brand '@acmecorp' in the last hour, and for each tweet, check the author's follower count. Show me how.",
            "I need to post a tweet, then create a thread by replying to my own tweet with additional context. Walk me through the API calls.",
            "Set up a filtered stream to track tweets containing 'product launch' OR 'new release' in real-time. Show me how to create the rules and connect to the stream.",
        ]
    },
    "resend": {
        "type": "openapi",
        "path": f"{EXAMPLES}/resend.yaml",
        "tasks": [
            "I need to send a welcome email to a new user (john@example.com) with HTML content, then check if it was delivered successfully. Show me the full flow.",
            "Set up a new sending domain 'mail.acme.com' and create an API key specifically for the marketing team with sending-only permissions.",
            "I need to add a contact to our 'newsletter' audience list and then send a batch of emails to all contacts in that list. How?",
        ]
    },
    "launchdarkly": {
        "type": "openapi",
        "path": f"{EXAMPLES}/launchdarkly.yaml",
        "tasks": [
            "I need to create a new boolean feature flag called 'new-checkout-flow' in our 'production' environment, and set it to serve 'true' for users in the 'beta-testers' segment.",
            "We're doing a gradual rollout of a feature. Show me how to set up a percentage rollout that serves the new feature to 25% of users, then how to bump it to 50%.",
            "I need to audit who changed the 'dark-mode' flag in the last week and what they changed. How do I pull that from the API?",
        ]
    },
    "petstore": {
        "type": "openapi",
        "path": f"{EXAMPLES}/petstore.yaml",
        "tasks": [
            "I run a pet store and need to add 3 new pets to the inventory — a dog, a cat, and a parrot. Then I want to look up all available pets by status. Show me the API calls.",
            "A customer wants to place an order for pet ID 42. Create the order and then check its status. Also show me how to delete the order if the customer cancels.",
            "I need to update a pet's status from 'available' to 'sold' after a purchase, and upload a photo of the pet. Walk me through it.",
        ]
    },
    "snyk": {
        "type": "openapi",
        "path": f"{EXAMPLES}/snyk.yaml",
        "tasks": [
            "I just joined a new org and need to get a security overview. Show me how to list all projects in my org, then pull the aggregated vulnerability issues for the most critical project.",
            "We need to integrate our GitHub repo with Snyk for automated scanning. Walk me through setting up the integration and importing the repo as a new project.",
            "I need to generate a report of all high-severity vulnerabilities across our organization's projects and check which ones have available fixes. How do I do this with the API?",
        ]
    },
    "hetzner": {
        "type": "openapi",
        "path": f"{EXAMPLES}/hetzner.yaml",
        "tasks": [
            "I need to spin up a new Ubuntu server in the Falkenstein datacenter with 4 CPUs and 8GB RAM, attach a 100GB volume, and assign a floating IP. Walk me through all the API calls.",
            "Set up a load balancer for my 3 existing servers (IDs: 101, 102, 103) with health checks on port 443 and round-robin algorithm. Then add a target pointing to each server.",
            "I want to create a firewall that allows SSH (port 22) only from my office IP (203.0.113.0/24), allows HTTP/HTTPS from anywhere, and blocks everything else. Then apply it to all my servers.",
        ]
    },
    "plaid": {
        "type": "openapi",
        "path": f"{EXAMPLES}/plaid.yaml",
        "tasks": [
            "I'm building a fintech app and need to connect a user's bank account. Walk me through the full flow: creating a link token, exchanging the public token, and then fetching their recent transactions.",
            "I need to verify a user's identity for KYC compliance. Show me how to create an identity verification session and retrieve the results.",
            "Set up recurring transaction monitoring for a user — get their access token, fetch recurring transactions, and set up a webhook to be notified of new ones.",
        ]
    },

    # === AsyncAPI ===
    "async-smart-home": {
        "type": "asyncapi",
        "path": f"{EXAMPLES}/asyncapi/smart-home.yaml",
        "tasks": [
            "I want to monitor the temperature in my living room and automatically turn on the AC when it goes above 25°C. Show me which channels to subscribe to and what messages to publish.",
            "Set up a security monitoring system — subscribe to security events and trigger an alert when motion is detected. What's the message format I should expect?",
        ]
    },
    "async-food-delivery": {
        "type": "asyncapi",
        "path": f"{EXAMPLES}/asyncapi/food-delivery.yaml",
        "tasks": [
            "I'm building the restaurant side of a food delivery app. Show me which events I need to subscribe to for incoming orders and how to publish order status updates.",
            "I need to track a delivery in real-time. What channels give me driver location updates and order status changes? Show me the message schemas.",
        ]
    },
    "async-ecommerce-kafka": {
        "type": "asyncapi",
        "path": f"{EXAMPLES}/asyncapi/ecommerce-kafka.yaml",
        "tasks": [
            "I'm building an order fulfillment service. Show me how to subscribe to new orders and payment confirmations, and what consumer group settings I should use for Kafka.",
            "I need to set up inventory tracking that reacts to order events. Which channels should I consume from and what are the message schemas?",
        ]
    },
    "async-notifications": {
        "type": "asyncapi",
        "path": f"{EXAMPLES}/asyncapi/notifications.yaml",
        "tasks": [
            "I'm building a notification service that needs to handle email, push, and SMS notifications. Show me the available channels and how to publish notifications.",
            "How do I subscribe to notification delivery status updates? I need to track whether each notification was actually delivered.",
        ]
    },

    # === GraphQL ===
    "gql-github": {
        "type": "graphql",
        "path": f"{EXAMPLES}/graphql/github.graphql",
        "tasks": [
            "I need to build a dashboard that shows a user's profile, their top 5 repos by stars, and open issues across all repos. Write me the GraphQL queries.",
            "I want to search for all repos related to 'machine learning' with more than 1000 stars, and for each, get the primary language and last commit date. Show the query.",
        ]
    },
    "gql-analytics": {
        "type": "graphql",
        "path": f"{EXAMPLES}/graphql/analytics.graphql",
        "tasks": [
            "I need to build a dashboard showing page views and unique visitors for the last 30 days, broken down by day. Write the GraphQL query.",
            "Show me how to query top converting pages and user session data for funnel analysis. Include all available metrics.",
        ]
    },
    "gql-shopify": {
        "type": "graphql",
        "path": f"{EXAMPLES}/graphql/shopify.graphql",
        "tasks": [
            "I need to create a new product with variants (sizes S/M/L) and set inventory levels. Write the GraphQL mutations and follow-up queries to verify.",
            "Build me a query that gets all orders from the last week with their line items, customer info, and fulfillment status. I need it for our shipping dashboard.",
        ]
    },
    "gql-wordpress": {
        "type": "graphql",
        "path": f"{EXAMPLES}/graphql/wordpress.graphql",
        "tasks": [
            "I'm building a headless frontend and need to fetch the latest 10 blog posts with their featured images, categories, author info, and comment counts. Write the query.",
            "I need to create a new post with specific categories and tags, then query it back to confirm. Show me the mutations and queries.",
        ]
    },

    # === Postman ===
    "postman-slack": {
        "type": "postman",
        "path": f"{EXAMPLES}/postman/slack-api.json",
        "tasks": [
            "I need to send a formatted message with attachments to a Slack channel, then pin it. Show me the API calls with proper authentication.",
            "Set up a new channel called 'incident-response', invite specific users to it, and post an initial message. Walk me through each API call.",
        ]
    },
    "postman-crud": {
        "type": "postman",
        "path": f"{EXAMPLES}/postman/crud-api.json",
        "tasks": [
            "I need to create a new resource, update some of its fields, fetch it to verify the changes, and then delete it. Show me the full CRUD lifecycle with the API.",
            "How do I list all resources with pagination and filtering? Then show me how to bulk update specific ones.",
        ]
    },
    "postman-openstack": {
        "type": "postman",
        "path": f"{EXAMPLES}/postman/openstack-compute.json",
        "tasks": [
            "I need to launch a new VM instance with a specific flavor and image, attach a security group, and then check its status until it's active. Show me all the API calls.",
            "I want to create a snapshot of a running server for backup, then list all my snapshots. Also show me how to resize the server to a bigger flavor.",
        ]
    },
    "postman-cisco": {
        "type": "postman",
        "path": f"{EXAMPLES}/postman/cisco-nso.json",
        "tasks": [
            "I need to configure a new network device in NSO — add it to the device list, sync its configuration, and verify it's reachable. Walk me through the API calls.",
            "Show me how to create a service instance and deploy a configuration change to multiple devices. Include the rollback steps if something goes wrong.",
        ]
    },

    # === Protobuf ===
    "proto-chat": {
        "type": "protobuf",
        "path": f"{EXAMPLES}/protobuf/chat.proto",
        "tasks": [
            "I'm implementing a chat client. Show me how to create a room, join it, send messages, and stream incoming messages. What are the RPC calls and message formats?",
            "I need to implement typing indicators and read receipts. What RPC methods are available for presence/status features? Show the message structures.",
        ]
    },
    "proto-payments": {
        "type": "protobuf",
        "path": f"{EXAMPLES}/protobuf/payments.proto",
        "tasks": [
            "I need to process a credit card payment for $99.99, then check its status and issue a partial refund. Show me the gRPC calls and request message structures.",
            "How do I set up a recurring payment (subscription) and handle payment method updates? Show me the relevant RPC methods and their request/response types.",
        ]
    },
    "proto-google-storage": {
        "type": "protobuf",
        "path": f"{EXAMPLES}/protobuf/google_storage.proto",
        "tasks": [
            "I need to create a new Cloud Storage bucket with versioning enabled, upload an object to it, then set a lifecycle policy to auto-delete objects older than 90 days. Show me the gRPC calls.",
            "Walk me through downloading an object with range reads (I only need bytes 1000-2000), and how to compose multiple objects into one. Show the full request/response flow.",
        ]
    },
    "proto-google-datacatalog": {
        "type": "protobuf",
        "path": f"{EXAMPLES}/protobuf/google_datacatalog.proto",
        "tasks": [
            "I need to register a new data source in Data Catalog — create an entry group, add entries for our BigQuery tables, and tag them with metadata. Show me the gRPC API calls.",
            "I want to search our data catalog for all tables related to 'customer' data, then check their tags and access policies. Show me the RPC calls and request structures.",
        ]
    },
}

# Validate: every task spec exists in our benchmark docs
BENCH_DIR = '/data/workspace/lap-benchmark-docs'
errors = []
for name, spec in TASKS.items():
    ctype = spec['type']
    # Check verbose file exists
    for ext in ['.yaml', '.json', '.graphql', '.proto']:
        vpath = os.path.join(BENCH_DIR, 'verbose', f'{name}{ext}')
        if os.path.exists(vpath):
            break
    else:
        errors.append(f"No verbose file for {name}")
    # Check doclean file exists
    dpath = os.path.join(BENCH_DIR, 'doclean', f'{name}.doclean')
    if not os.path.exists(dpath):
        errors.append(f"No doclean file for {name}")

if errors:
    print("ERRORS:")
    for e in errors:
        print(f"  ❌ {e}")

# Validate tasks are actually possible by checking endpoints exist
for name, spec in TASKS.items():
    ctype = spec['type']
    compiler = COMPILERS[ctype]
    try:
        result = compiler(spec['path'])
        ep_count = len(result.endpoints)
        print(f"✅ {name} ({ctype}): {len(spec['tasks'])} tasks, {ep_count} endpoints")
    except Exception as e:
        print(f"❌ {name} ({ctype}): compile error: {e}")

# Write YAML
output_path = '/data/workspace/lap-benchmark-docs/benchmark_tasks.yaml'
with open(output_path, 'w') as f:
    yaml.dump(TASKS, f, default_flow_style=False, width=120, allow_unicode=True)

total = sum(len(v['tasks']) for v in TASKS.values())
print(f"\nTotal: {total} tasks across {len(TASKS)} specs")
print(f"Written to: {output_path}")
