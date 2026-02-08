#!/usr/bin/env python3
"""Compile all benchmark docs across all formats."""
import sys, os, shutil
sys.path.insert(0, '/data/workspace/lap-poc')

EXAMPLES = '/data/workspace/lap-poc/examples'
VERBOSE = '/data/workspace/lap-benchmark-docs/verbose'
DOCLEAN = '/data/workspace/lap-benchmark-docs/doclean'

SPECS = [
    # AsyncAPI
    ("async-smart-home", f"{EXAMPLES}/asyncapi/smart-home.yaml", "asyncapi", ".yaml"),
    ("async-food-delivery", f"{EXAMPLES}/asyncapi/food-delivery.yaml", "asyncapi", ".yaml"),
    ("async-ecommerce-kafka", f"{EXAMPLES}/asyncapi/ecommerce-kafka.yaml", "asyncapi", ".yaml"),
    ("async-notifications", f"{EXAMPLES}/asyncapi/notifications.yaml", "asyncapi", ".yaml"),
    # GraphQL
    ("gql-github", f"{EXAMPLES}/graphql/github.graphql", "graphql", ".graphql"),
    ("gql-analytics", f"{EXAMPLES}/graphql/analytics.graphql", "graphql", ".graphql"),
    ("gql-shopify", f"{EXAMPLES}/graphql/shopify.graphql", "graphql", ".graphql"),
    ("gql-wordpress", f"{EXAMPLES}/graphql/wordpress.graphql", "graphql", ".graphql"),
    # Postman
    ("postman-slack", f"{EXAMPLES}/postman/slack-api.json", "postman", ".json"),
    ("postman-crud", f"{EXAMPLES}/postman/crud-api.json", "postman", ".json"),
    ("postman-openstack", f"{EXAMPLES}/postman/openstack-compute.json", "postman", ".json"),
    ("postman-cisco", f"{EXAMPLES}/postman/cisco-nso.json", "postman", ".json"),
    # Protobuf
    ("proto-chat", f"{EXAMPLES}/protobuf/chat.proto", "protobuf", ".proto"),
    ("proto-payments", f"{EXAMPLES}/protobuf/payments.proto", "protobuf", ".proto"),
    ("proto-google-storage", f"{EXAMPLES}/protobuf/google_storage.proto", "protobuf", ".proto"),
    ("proto-google-datacatalog", f"{EXAMPLES}/protobuf/google_datacatalog.proto", "protobuf", ".proto"),
]

from core.compilers.asyncapi import compile_asyncapi
from core.compilers.graphql import compile_graphql
from core.compilers.postman import compile_postman
from core.compilers.protobuf import compile_protobuf

COMPILERS = {
    'asyncapi': compile_asyncapi,
    'graphql': compile_graphql,
    'postman': compile_postman,
    'protobuf': compile_protobuf,
}

for name, src, ctype, vext in SPECS:
    verbose_dst = os.path.join(VERBOSE, f"{name}{vext}")
    doclean_dst = os.path.join(DOCLEAN, f"{name}.doclean")
    
    # Copy verbose
    shutil.copy2(src, verbose_dst)
    
    # Compile doclean
    try:
        compiler = COMPILERS[ctype]
        result = compiler(src)
        doclean_text = result.to_doclean()
        with open(doclean_dst, 'w') as f:
            f.write(doclean_text)
        v_size = os.path.getsize(verbose_dst)
        d_size = os.path.getsize(doclean_dst)
        ratio = v_size / d_size if d_size > 0 else 0
        print(f"✅ {name} ({ctype}): {v_size:,} → {d_size:,} ({ratio:.1f}x)")
    except Exception as e:
        print(f"❌ {name} ({ctype}): {e}")
