# LAP Benchmark v2 - Spec Registry & Task Review

## Grand Totals

| Metric | Value |
|--------|-------|
| Total specs | 50 |
| Formats | 5 (OpenAPI, AsyncAPI, GraphQL, Postman, Protobuf) |
| Specs per format | 10 |
| Total tasks | 100 (2 per spec) |
| Compiled variants | 194 (47 x 4 tiers + 3 GraphQL x 2 tiers) |
| Full benchmark runs | 388 |
| Pilot benchmark runs | 48 (6 specs x 4 tiers x 2 tasks) |

### Size Totals by Format

| Format | Source (KB) | Pretty (KB) | Minified (KB) | Std LAP (KB) | Lean LAP (KB) | Lean Ratio |
|--------|------------|-------------|---------------|-------------|--------------|------------|
| OpenAPI (10) | 21,690.3 | 21,690.3 | 21,381.6 | 2,852.1 | 1,486.4 | 14.6x |
| AsyncAPI (10) | 81.2 | 81.2 | 81.5 | 17.0 | 11.6 | 7.0x |
| GraphQL (10) | 4,857.6 | 4,857.6 | 4,119.6 | 1,033.6 | 850.8 | 5.7x* |
| Postman (10) | 1,711.5 | 1,711.5 | 1,236.7 | 202.3 | 127.7 | 13.4x |
| Protobuf (10) | 644.4 | 644.4 | 132.2 | 35.6 | 33.7 | 19.1x |
| **TOTAL (50)** | **29,005.0** | **29,005.0** | **26,951.6** | **4,140.6** | **2,510.2** | **11.6x** |

*GraphQL ratio excludes 3 specs (github-gql, shopify-gql, yelp-gql) that fail LAP compilation due to introspection JSON / duplicate field issues.

### Compression Ratio Highlights

| Best LAP Lean | Ratio | Worst LAP Lean | Ratio |
|---------------|-------|----------------|-------|
| websocket-gemini | 43.5x | digitalocean | 2.7x |
| slack | 39.6x | correlation-id | 12.4x |
| google-pubsub | 59.6x | google-vision | 9.9x |
| postman-echo | 25.8x | sap-postman | 14.6x |
| google-storage | 30.4x | google-billing | 14.6x |

---

## Full Spec List

### OpenAPI (10 specs)

| # | Spec | Domain | Size | Source KB | Pretty KB | Mini KB | Std LAP KB | Lean LAP KB | Lean Ratio |
|---|------|--------|------|----------|----------|--------|-----------|------------|------------|
| 1 | petstore | demo | small | 22.6 | 22.6 | 23.0 | 6.0 | 3.8 | 5.9x |
| 2 | stripe | payments | large | 5,910.1 | 5,910.1 | 5,623.5 | 586.4 | 422.6 | 14.0x |
| 3 | twilio | comms | large | 1,823.0 | 1,823.0 | 1,455.1 | 159.1 | 72.9 | 25.0x |
| 4 | github-rest | devtools | large | 8,749.6 | 8,749.6 | 8,890.4 | 1,278.7 | 699.5 | 12.5x |
| 5 | digitalocean | cloud | medium | 88.9 | 88.9 | 88.6 | 32.7 | 32.7 | 2.7x |
| 6 | slack | messaging | large | 1,208.3 | 1,208.3 | 631.5 | 82.4 | 30.5 | 39.6x |
| 7 | spotify | media | medium | 278.9 | 278.9 | 286.9 | 64.7 | 17.7 | 15.8x |
| 8 | box | storage | large | 1,700.4 | 1,700.4 | 1,409.9 | 299.8 | 70.1 | 24.3x |
| 9 | plaid | fintech | large | 2,803.3 | 2,803.3 | 2,865.0 | 320.2 | 124.2 | 22.6x |
| 10 | resend | email | medium | 105.2 | 105.2 | 107.6 | 21.9 | 12.3 | 8.6x |

### AsyncAPI (10 specs)

| # | Spec | Domain | Size | Source KB | Pretty KB | Mini KB | Std LAP KB | Lean LAP KB | Lean Ratio |
|---|------|--------|------|----------|----------|--------|-----------|------------|------------|
| 1 | streetlights | iot | small | 6.2 | 6.2 | 6.3 | 2.2 | 1.5 | 4.1x |
| 2 | slack-rtm | messaging | small | 24.6 | 24.6 | 25.4 | 8.9 | 6.3 | 3.9x |
| 3 | adeo-kafka | ecommerce | small | 10.1 | 10.1 | 9.9 | 1.1 | 0.4 | 25.3x |
| 4 | social-media | social | small | 2.5 | 2.5 | 2.5 | 0.4 | 0.4 | 6.3x |
| 5 | gitter-streaming | chat | small | 5.2 | 5.2 | 5.3 | 0.4 | 0.3 | 17.3x |
| 6 | websocket-gemini | crypto | small | 8.7 | 8.7 | 8.2 | 0.3 | 0.2 | 43.5x |
| 7 | kraken-websocket | crypto | small | 12.8 | 12.8 | 12.8 | 1.7 | 1.0 | 12.8x |
| 8 | correlation-id | patterns | small | 6.2 | 6.2 | 6.2 | 0.9 | 0.5 | 12.4x |
| 9 | operation-security | security | small | 3.4 | 3.4 | 3.4 | 0.6 | 0.6 | 5.7x |
| 10 | rpc-server | microservices | small | 1.5 | 1.5 | 1.5 | 0.5 | 0.4 | 3.8x |

### GraphQL (10 specs)

| # | Spec | Domain | Size | Source KB | Pretty KB | Mini KB | Std LAP KB | Lean LAP KB | Lean Ratio |
|---|------|--------|------|----------|----------|--------|-----------|------------|------------|
| 1 | github-gql | devtools | large | 1,195.2 | 1,195.2 | 1,142.5 | -- | -- | N/A |
| 2 | swapi-gql | demo | small | 35.0 | 35.0 | 34.1 | 6.5 | 4.9 | 7.1x |
| 3 | yelp-gql | local | small | 97.8 | 97.8 | 51.9 | -- | -- | N/A |
| 4 | shopify-gql | ecommerce | medium | 399.1 | 399.1 | 199.7 | -- | -- | N/A |
| 5 | artsy-gql | art | large | 688.8 | 688.8 | 384.3 | 337.6 | 309.0 | 2.2x |
| 6 | linear-gql | project-mgmt | large | 864.3 | 864.3 | 822.9 | 240.3 | 196.8 | 4.4x |
| 7 | saleor-gql | ecommerce | large | 941.9 | 941.9 | 899.2 | 296.2 | 203.1 | 4.6x |
| 8 | elastic-gql | search | medium | 326.4 | 326.4 | 300.8 | 56.5 | 56.5 | 5.8x |
| 9 | coral-gql | social | medium | 249.1 | 249.1 | 228.1 | 69.9 | 56.0 | 4.4x |
| 10 | unraid-gql | infra | small | 59.9 | 59.9 | 56.1 | 26.6 | 24.5 | 2.4x |

*github-gql, yelp-gql, shopify-gql: LAP compilation fails (introspection JSON format / duplicate fields). Only pretty + minified tiers available. Pending LAP compiler fix.

### Postman (10 specs)

| # | Spec | Domain | Size | Source KB | Pretty KB | Mini KB | Std LAP KB | Lean LAP KB | Lean Ratio |
|---|------|--------|------|----------|----------|--------|-----------|------------|------------|
| 1 | twilio-postman | comms | small | 10.8 | 10.8 | 8.4 | 1.1 | 0.8 | 13.5x |
| 2 | postman-echo | demo | small | 15.5 | 15.5 | 5.9 | 0.9 | 0.6 | 25.8x |
| 3 | adobe-postman | marketing | small | 36.6 | 36.6 | 27.9 | 6.7 | 1.7 | 21.5x |
| 4 | sap-postman | enterprise | medium | 436.7 | 436.7 | 329.2 | 37.2 | 30.0 | 14.6x |
| 5 | stripe-postman | payments | medium | 170.7 | 170.7 | 92.4 | 26.4 | 20.2 | 8.5x |
| 6 | azure-devops-postman | devops | large | 386.5 | 386.5 | 277.4 | 51.9 | 30.3 | 12.8x |
| 7 | auth0-postman | auth | medium | 70.6 | 70.6 | 50.9 | 9.0 | 6.9 | 10.2x |
| 8 | braintree-postman | payments | medium | 123.7 | 123.7 | 89.7 | 7.3 | 5.1 | 24.3x |
| 9 | influxdb-postman | monitoring | medium | 230.1 | 230.1 | 174.4 | 21.0 | 15.3 | 15.0x |
| 10 | akeneo-postman | ecommerce | medium | 230.3 | 230.3 | 180.5 | 40.8 | 16.8 | 13.7x |

### Protobuf (10 specs)

| # | Spec | Domain | Size | Source KB | Pretty KB | Mini KB | Std LAP KB | Lean LAP KB | Lean Ratio |
|---|------|--------|------|----------|----------|--------|-----------|------------|------------|
| 1 | google-storage | cloud | medium | 136.7 | 136.7 | 33.0 | 4.8 | 4.5 | 30.4x |
| 2 | google-pubsub | messaging | medium | 107.2 | 107.2 | 15.6 | 2.2 | 1.8 | 59.6x |
| 3 | google-vision | ai | medium | 36.6 | 36.6 | 8.8 | 3.8 | 3.7 | 9.9x |
| 4 | google-datacatalog | data | medium | 84.9 | 84.9 | 18.8 | 6.7 | 6.5 | 13.1x |
| 5 | google-translate | ai | medium | 76.8 | 76.8 | 14.5 | 3.7 | 3.5 | 21.9x |
| 6 | google-spanner | database | medium | 61.3 | 61.3 | 10.2 | 3.4 | 3.3 | 18.6x |
| 7 | google-firestore | database | medium | 45.7 | 45.7 | 9.4 | 4.0 | 3.7 | 12.4x |
| 8 | google-talent | hr | medium | 43.8 | 43.8 | 5.8 | 2.0 | 2.0 | 21.9x |
| 9 | google-language | ai | medium | 31.0 | 31.0 | 8.9 | 3.5 | 3.3 | 9.4x |
| 10 | google-billing | billing | small | 20.4 | 20.4 | 7.2 | 1.5 | 1.4 | 14.6x |

---

## Task Manifest Review

Each task asks the agent to identify 2 endpoints and their parameters from the API documentation.
Scoring: 60% endpoint identification, 30% parameter accuracy, 10% code quality.

### Rating Key
- OK = Task is well-formed, endpoints are distinct, params are meaningful
- WARN = Minor issue (see note)
- PROBLEM = Task needs rework before benchmark run

---

### OpenAPI Tasks

#### 1. petstore -- OK
- **t1**: `POST /pet` + `GET /pet/findByStatus` -- Add pet, find by status. Classic CRUD + query.
- **t2**: `POST /store/order` + `GET /store/order/{orderId}` -- Place order, retrieve by ID. Good.

#### 2. stripe -- OK
- **t1**: `POST /v1/customers` + `GET /v1/charges` -- Create customer, list charges. 5+3 params.
- **t2**: `POST /v1/products` + `GET /v1/products/search` -- Create product, search. 4+2 params.

#### 3. twilio -- OK
- **t1**: `POST .../Messages.json` + `GET .../Messages/{Sid}.json` -- Send SMS, get details. Good.
- **t2**: `POST .../Calls.json` + `GET .../Calls/{CallSid}/Recordings.json` -- Make call, list recordings. Good.

#### 4. github-rest -- OK
- **t1**: `GET .../issues` + `POST .../issues` -- List then create issue. 6+6 params.
- **t2**: `GET .../repos/{owner}/{repo}` + `GET .../pulls` -- Repo details + PRs. Good.

#### 5. digitalocean -- OK
- **t1**: `POST /v2/droplets` + `GET /v2/droplets/{droplet_id}` -- Create + get droplet. Good.
- **t2**: `POST .../records` + `GET .../records` -- Create + list DNS records. Good.

#### 6. slack -- OK
- **t1**: `POST /chat.postMessage` + `GET /conversations.history` -- Post + get history. Good.
- **t2**: `POST /conversations.create` + `GET /conversations.list` -- Create + list channels. Good.

#### 7. spotify -- OK
- **t1**: `GET /albums/{id}` + `GET /albums/{id}/tracks` -- Album details + tracks. Good.
- **t2**: `GET /artists/{id}` + `GET /artists/{id}/top-tracks` -- Artist + top tracks. Good.

#### 8. box -- OK
- **t1**: `GET /files/{file_id}` + `GET /files/{file_id}/collaborations` -- File info + collabs. Good.
- **t2**: `GET /folders/{folder_id}` + `GET /folders/{folder_id}/items` -- Folder info + items. Good.

#### 9. plaid -- OK
- **t1**: `POST /accounts/get` + `POST /transactions/get` -- Get accounts + transactions. Good.
- **t2**: `POST /link/token/create` + `POST /institutions/get` -- Init link + list institutions. Good.

#### 10. resend -- OK
- **t1**: `POST /emails` + `GET /emails/{email_id}` -- Send email + get details. Good.
- **t2**: `POST /domains` + `POST /domains/{domain_id}/verify` -- Create domain + verify. Good.

**OpenAPI verdict: All 10 OK.** Good variety of CRUD, search, and workflow patterns.

---

### AsyncAPI Tasks

#### 11. streetlights -- OK
- **t1**: `SUBSCRIBE .../lighting/measured` + `PUBLISH .../turn.on` -- Monitor + command. Good.
- **t2**: `PUBLISH .../turn.off` + `PUBLISH .../dim` -- Two different commands. Good.

#### 12. slack-rtm -- OK
- **t1**: `PUBLISH / outgoingMessage` + `SUBSCRIBE / message` -- Send + receive. Good.
- **t2**: `SUBSCRIBE / memberJoinedChannel` + `SUBSCRIBE / channelCreated` -- Two events. Good.

#### 13. adeo-kafka -- WARN
- **t1**: PUBLISH request + SUBSCRIBE response -- Good request-reply pattern.
- **t2**: SUBSCRIBE request + PUBLISH response -- Same endpoints, just reversed roles.
- Note: t1 and t2 use identical endpoints with identical params, only the PUBLISH/SUBSCRIBE roles swap. Low differentiation, but the role reversal (client vs server perspective) does test a different understanding.

#### 14. social-media -- OK
- **t1**: `SUBSCRIBE like/comment` + `PUBLISH comment/liked` -- Frontend to backend. Good.
- **t2**: `SUBSCRIBE comment/{commentId}/changed` + `PUBLISH update/comment/likes` -- Backend to frontend. Different channels.

#### 15. gitter-streaming -- WARN
- **t1**: chatMessage + heartbeat -- Two different message types. Good.
- **t2**: chatMessage + chatMessage -- Same endpoint listed twice with different param subsets. The scorer may not handle duplicate endpoints well. Needs review of scorer logic.

#### 16. websocket-gemini -- PROBLEM
- **t1**: `PUBLISH /v1/marketdata/{symbol} marketData` x2 -- Same endpoint twice, payload fields.
- **t2**: Same endpoint x2 -- Same endpoint twice, query params.
- Note: The spec has only ONE channel with ONE message type. Both tasks target the same endpoint. t1 vs t2 differ only by which fields within the payload or binding the agent identifies. The scorer expects distinct endpoints in target_endpoints. This will likely score identically for t1 and t2, wasting a run.

#### 17. kraken-websocket -- OK
- **t1**: `SUBSCRIBE / ping` + `SUBSCRIBE / subscribe` -- Client-side operations. Good.
- **t2**: `PUBLISH / systemStatus` + `PUBLISH / subscriptionStatus` -- Server-side events. Good.

#### 18. correlation-id -- PROBLEM
- **t1**: `SUBSCRIBE .../lighting/measured` + `PUBLISH .../dim` -- Same as streetlights.
- **t2**: Identical endpoints and params as t1 -- Only description changes ("different streetlight").
- Note: t1 and t2 are IDENTICAL in target_endpoints and expected_params. This is a wasted task.

#### 19. operation-security -- WARN
- **t1**: `PUBLISH AUTHORIZATION_REVOCATION message` x2 -- Same endpoint twice. Params: metadata, notification, headers.
- **t2**: Same endpoint x2 -- Different params: username, userId, revokeReason, revocationDate.
- Note: Spec has only ONE channel with ONE message. t1 targets outer fields, t2 targets nested fields. Same duplicate-endpoint concern as websocket-gemini.

#### 20. rpc-server -- WARN
- **t1**: `SUBSCRIBE rpc_queue sum` + `PUBLISH {queue} sendSumResult` -- Server perspective.
- **t2**: `PUBLISH {queue} sendSumResult` + `SUBSCRIBE rpc_queue sum` -- Reversed order, same params.
- Note: Same as adeo-kafka -- identical endpoints/params, just swapped order.

**AsyncAPI verdict: 4 OK, 3 WARN, 2 PROBLEM.** Several specs are too small (1-2 channels) to create 2 distinct tasks. correlation-id and websocket-gemini need rework.

---

### GraphQL Tasks

#### 21. github-gql -- OK (only pretty+mini tiers)
- **t1**: `QUERY repository` + `MUTATION createIssue` -- Read + write. Good.
- **t2**: `QUERY search` + `QUERY user` -- Two distinct queries. Good.

#### 22. swapi-gql -- OK
- **t1**: `QUERY allFilms` + `QUERY person` -- List + detail lookup. Good.
- **t2**: `QUERY allPlanets` + `QUERY starship` -- Different entity types. Good.

#### 23. yelp-gql -- OK (only pretty+mini tiers)
- **t1**: `QUERY search` + `QUERY reviews` -- Search businesses + reviews. Rich params.
- **t2**: `QUERY business` + `QUERY event_search` -- Lookup + event search. Good.

#### 24. shopify-gql -- OK (only pretty+mini tiers)
- **t1**: `MUTATION customerCreate` + `MUTATION customerAccessTokenCreate` -- Auth flow. Good.
- **t2**: `QUERY customer` + `MUTATION checkoutCreate` -- Profile + checkout. Good.

#### 25. artsy-gql -- OK
- **t1**: `QUERY artist` + `QUERY auctionResultsByArtistsConnection` -- Rich params. Good.
- **t2**: `QUERY artworksConnection` + `MUTATION commerceCreateOrderWithArtwork` -- Browse + order. Good.

#### 26. linear-gql -- OK
- **t1**: `QUERY issue` + `MUTATION issueUpdate` -- Read + update. Good.
- **t2**: `QUERY project` + `MUTATION projectCreate` -- Read + create. Good.

#### 27. saleor-gql -- OK
- **t1**: `QUERY product` + `QUERY order` -- Two distinct queries, 5+2 params. Good.
- **t2**: `MUTATION productCreate` + `MUTATION updateWarehouse` -- Two distinct mutations. Good.

#### 28. elastic-gql -- WARN
- **t1**: `QUERY elastic77` + `QUERY elastic68` -- Both take single `host` param.
- **t2**: `QUERY elastic56` + `QUERY elastic77` -- Again single `host` param.
- Note: This schema has only 3 root queries, all with only `host` as param. Tasks are trivially simple. Both tasks overlap on `elastic77`. Very little for the agent to demonstrate.

#### 29. coral-gql -- OK
- **t1**: `QUERY comments` + `QUERY stories` -- Rich params (6+5). Good.
- **t2**: `MUTATION createComment` + `MUTATION createCommentFlag` -- Two mutations. Good.

#### 30. unraid-gql -- OK
- **t1**: `QUERY apiKey` + `QUERY logFile` -- Two distinct queries, 1+3 params. Good.
- **t2**: `MUTATION createNotification` + `MUTATION renameDockerFolder` -- Two mutations. Good.

**GraphQL verdict: 9 OK, 1 WARN.** elastic-gql tasks are trivially simple due to minimal schema surface.

---

### Postman Tasks

#### 31. twilio-postman -- WARN
- **t1**: `POST /v1/Commands` + `GET /v1/Commands/{Command_Sid}` -- Send + get. Good.
- **t2**: `POST /v1/RatePlans` + `GET /v1/RatePlans` -- Create + list. But POST has EMPTY params []. The collection may not have documented body params. Scorer will give 0% on param accuracy for that endpoint.

#### 32. postman-echo -- WARN
- **t1**: `POST /post` (param: `yo`) + `GET /status/200` (no params) -- Trivial echo API.
- **t2**: `PUT /status/201` (param: `yo`) + `GET /path/to/document` (no params) -- Also trivial.
- Note: This is a demo/echo API. Tasks are extremely shallow. Useful as a baseline but won't differentiate agent quality.

#### 33. adobe-postman -- OK
- **t1**: `POST .../batches` + `PUT .../files/:filePath` -- Create batch + upload file. Good.
- **t2**: `POST .../collection/:CONNECTION_ID` + `GET .../preview` -- Stream + preview. Good.

#### 34. sap-postman -- OK
- **t1**: `POST .../LeadCollection` + `GET .../LeadCollection` -- Create + query lead. 9+3 params. Good.
- **t2**: `POST .../SalesOrderCollection` + `GET .../SalesOrderCollection` -- Create + query order. Good.

#### 35. stripe-postman -- OK
- **t1**: `POST /v1/charges` + `POST /v1/customers` -- Create charge + customer. Good.
- **t2**: `POST /v1/payment_intents` + `POST /v1/refunds` -- Intent + refund. Good.

#### 36. azure-devops-postman -- OK
- **t1**: `POST .../packaging/feeds` + `GET .../build/builds` -- Create feed + list builds. Good.
- **t2**: `POST .../build/builds` + `GET .../build/definitions/{id}` -- Queue build + get definition. Good.

#### 37. auth0-postman -- OK
- **t1**: `POST .../connections` + `POST .../rules` -- Create connection + rule. 4+5 params. Good.
- **t2**: `POST .../users` + `POST .../client-grants` -- Create user + grant. 8+3 params. Good.

#### 38. braintree-postman -- WARN
- **t1**: `POST /graphql [CreateCustomer]` + `POST /graphql [ChargePaymentMethod]` -- Both `query`+`variables`.
- **t2**: `POST /graphql [AuthorizePaymentMethod]` + `POST /graphql [CaptureTransaction]` -- Same.
- Note: All 4 endpoints are `POST /graphql`. Differentiation is only by operation name in brackets. Scorer identifies endpoints by path -- it may treat all 4 as the same endpoint. Need to verify scorer handles this pattern.

#### 39. influxdb-postman -- OK
- **t1**: `POST .../write` + `POST .../query/analyze` -- Write data + analyze query. Good.
- **t2**: `POST .../setup` + `GET .../buckets` -- Setup instance + list buckets. Good (GET has no params, but setup has 7).

#### 40. akeneo-postman -- OK
- **t1**: `POST .../families` + `POST .../products` -- Create family + product. 6+6 params. Good.
- **t2**: `POST .../catalogs` + `GET .../catalogs` -- Create + list catalogs. Good.

**Postman verdict: 7 OK, 3 WARN.** braintree-postman needs scorer validation for GraphQL-over-REST. postman-echo is trivially simple. twilio-postman t2 has empty params.

---

### Protobuf Tasks

#### 41. google-storage -- OK
- **t1**: `RPC CreateBucket` + `RPC ListObjects` -- Create bucket + list. 5+7 params. Good.
- **t2**: `RPC GetObject` + `RPC UpdateObject` -- Read + update. 7+5 params. Good.

#### 42. google-pubsub -- OK
- **t1**: `RPC Publish` + `RPC ListTopics` -- Publish + list. Good.
- **t2**: `RPC Pull` + `RPC Acknowledge` -- Pull + ack. Good message consumption flow.

#### 43. google-vision -- OK
- **t1**: `RPC BatchAnnotateImages` + `RPC BatchAnnotateFiles` -- Sync image + file annotation. Good.
- **t2**: `RPC AsyncBatchAnnotateImages` + `RPC AsyncBatchAnnotateFiles` -- Async variants. Good.

#### 44. google-datacatalog -- OK
- **t1**: `RPC SearchCatalog` + `RPC CreateEntryGroup` -- Search + organize. Good.
- **t2**: `RPC CreateTagTemplate` + `RPC CreateTag` -- Define schema + attach tag. Good workflow.

#### 45. google-translate -- OK
- **t1**: `RPC TranslateText` + `RPC DetectLanguage` -- Core translation features. 6+4 params. Good.
- **t2**: `RPC CreateGlossary` + `RPC ListGlossaries` -- Glossary CRUD. Good.

#### 46. google-spanner -- OK
- **t1**: `RPC ExecuteSql` + `RPC Commit` -- Execute + commit. Transaction pattern. Good.
- **t2**: `RPC CreateSession` + `RPC Read` -- Session + read. 2+7 params. Good.

#### 47. google-firestore -- OK
- **t1**: `RPC RunQuery` + `RPC BatchGetDocuments` -- Query + batch get. Good.
- **t2**: `RPC CreateDocument` + `RPC Commit` -- Create + commit. Good.

#### 48. google-talent -- OK
- **t1**: `RPC CreateJob` + `RPC ListJobs` -- Create + list. Good.
- **t2**: `RPC SearchJobs` + `RPC GetJob` -- Search + get. 6+1 params. Good.

#### 49. google-language -- OK
- **t1**: `RPC AnalyzeSentiment` + `RPC AnalyzeEntities` -- Two analysis types. Good.
- **t2**: `RPC ClassifyText` + `RPC AnnotateText` -- Classify + annotate. Good.

#### 50. google-billing -- OK
- **t1**: `RPC CreateBillingAccount` + `RPC ListBillingAccounts` -- CRUD. Good.
- **t2**: `RPC GetProjectBillingInfo` + `RPC UpdateProjectBillingInfo` -- Get + update. Good.

**Protobuf verdict: All 10 OK.** Clean RPC patterns with good param variety.

---

## Issues Summary

### Must Fix (2 PROBLEM tasks)

| Spec | Issue | Fix Needed |
|------|-------|------------|
| correlation-id | t1 and t2 have identical endpoints + params | Rewrite t2 with different channel focus, or accept reduced value |
| websocket-gemini | Both tasks target same endpoint x2 | Spec too small for 2 distinct tasks. Consider rewriting tasks to focus on different aspects |

### Should Review (6 WARN tasks)

| Spec | Issue | Impact |
|------|-------|--------|
| adeo-kafka | t1/t2 same endpoints, roles swapped | Low differentiation, moderate impact |
| gitter-streaming | t2 lists same endpoint twice | Scorer may not handle duplicate endpoints |
| operation-security | Same endpoint listed twice in both tasks | Same concern as websocket-gemini |
| rpc-server | t1/t2 same endpoints, order swapped | Low differentiation |
| elastic-gql | Only 1-param queries, trivially simple | Won't differentiate agent quality |
| postman-echo | Trivially simple demo API | Only useful as a baseline |
| twilio-postman | t2 POST /v1/RatePlans has empty params | 0% param score for that endpoint |
| braintree-postman | All endpoints are POST /graphql | Scorer may treat as same endpoint |

### Root Cause

The AsyncAPI issues are systemic: many AsyncAPI specs are small examples (1-3 channels) that don't have enough surface area for 2 meaningfully distinct tasks. The original AsyncAPI examples repo was the only reliable source, and these tend to be demonstration specs.

### Recommendation

1. **Fix correlation-id + websocket-gemini** tasks before running
2. **Verify scorer handles** duplicate endpoints in target_endpoints (gitter, operation-security)
3. **Verify scorer handles** bracket-suffixed endpoints like `POST /graphql [CreateCustomer]` (braintree)
4. **Accept** that some specs (elastic-gql, postman-echo) are inherently simpler -- they serve as "easy" baselines
5. **Consider** dropping adeo-kafka/rpc-server t2 duplication by picking a different endpoint pair if available
