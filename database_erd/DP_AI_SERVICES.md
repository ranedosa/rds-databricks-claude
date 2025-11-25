# AI Services Database (dp_ai_services)

**Generated:** 2025-11-25
**Database:** dp_ai_services (Microservice)
**Schemas Documented:** agent (Agent Management), checkpoint (LangGraph Checkpointing)
**Tables Documented:** 7 tables (3 agent management + 4 checkpoint storage)

---

## Overview

This database is part of the AI services microservice that manages AI agents, their configurations, and execution state. It provides agent versioning, A/B testing infrastructure, prompt management, and LangGraph checkpoint persistence for stateful agent workflows.

**Purpose:** AI agent configuration management and stateful workflow orchestration

**Key Features:**
- Agent versioning and variant management (A/B testing)
- Prompt versioning and provider management
- LangGraph checkpoint persistence (stateful workflows)
- MLflow experiment tracking integration
- Multi-region and multi-provider support (AWS, Ollama)
- Champion/challenger model deployment pattern

**Technology Stack:**
- LangGraph for agent workflow orchestration
- MLflow for experiment tracking
- Python-based AI services (Alembic migrations)
- JSONB for flexible configuration storage

---

## Table of Contents

1. [Agent Management Schema (agent)](#agent-management-schema-agent)
   - agents
   - agent_variants
   - agent_node_configs
2. [Checkpoint Schema (checkpoint)](#checkpoint-schema-checkpoint)
   - checkpoints
   - checkpoint_writes
   - checkpoint_blobs
   - checkpoint_migrations
3. [Cross-Database Relationships](#cross-database-relationships)

---

## Agent Management Schema (agent)

### Entity Relationship Diagram

```
agents (1) ←→ (N) agent_variants
     ↓
agent_node_configs (N)
```

---

### agents

**Purpose:** Master catalog of AI agents with type classification

**Primary Key:** id (uuid, auto-generated)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| name | varchar(100) | NO | - | Agent name (e.g., "income_extractor", "fraud_detector") |
| agent_type | enum | NO | - | Agent type classification |
| description | text | YES | - | Agent purpose and capabilities |
| is_active | boolean | YES | - | Whether agent is currently active |
| created_at | timestamp | YES | - | Agent creation timestamp |
| updated_at | timestamp | YES | - | Agent update timestamp |

#### Business Logic

**Agent Types (Inferred):**
- **extraction:** Data extraction agents (income, assets, dates)
- **classification:** Document classification agents
- **validation:** Data validation and verification agents
- **analysis:** Complex analysis agents (fraud detection, risk assessment)
- **orchestration:** Workflow coordination agents

**Agent Lifecycle:**
1. Agent created with initial configuration
2. Multiple variants created for A/B testing
3. Champion variant serves production traffic
4. Challenger variants tested with sample_rate
5. Best performing variant promoted to champion
6. Deactivated when deprecated (is_active = false)

#### Query Examples

```sql
-- List all active agents
SELECT
    id,
    name,
    agent_type,
    description,
    created_at
FROM agent.agents
WHERE is_active = true
ORDER BY name;

-- Agents by type
SELECT
    agent_type,
    COUNT(*) as agent_count,
    COUNT(*) FILTER (WHERE is_active = true) as active_count
FROM agent.agents
GROUP BY agent_type
ORDER BY agent_count DESC;
```

---

### agent_variants

**Purpose:** Agent versions/variants for A/B testing and gradual rollout

**Primary Key:** id (uuid, auto-generated)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| agent_id | uuid | NO | - | FK → agents.id |
| variant_name | varchar(50) | NO | - | Variant identifier (e.g., "v1", "v2", "champion") |
| version | varchar(50) | YES | - | Version number (e.g., "1.0.0", "2024-11-25") |
| description | text | YES | - | Variant changes and improvements |
| is_champion | boolean | YES | - | Whether this is the production variant |
| is_active | boolean | YES | - | Whether variant is currently enabled |
| run_in_background | boolean | YES | - | Run async without blocking |
| sample_rate | double precision | YES | - | Traffic percentage (0.0-1.0) for A/B testing |
| aws_region | varchar(50) | YES | - | AWS region for model deployment |
| aws_profile | varchar(100) | YES | - | AWS profile for credentials |
| ollama_base_url | varchar(500) | YES | - | Ollama API endpoint (local LLM option) |
| extra_config | jsonb | YES | - | Additional configuration parameters |
| mlflow_experiment_id | varchar(200) | YES | - | MLflow experiment for tracking |
| created_at | timestamp | YES | - | Variant creation timestamp |
| updated_at | timestamp | YES | - | Variant update timestamp |

#### Relationships

**Belongs to:**
- **agents** (agent_id) - Parent agent

**Has many:**
- **agent_node_configs** (agent_variant_id) - Node configurations for this variant

#### Business Logic

**Champion/Challenger Pattern:**
- **Champion:** is_champion=true, sample_rate=0.9 (90% traffic)
- **Challenger:** is_champion=false, sample_rate=0.1 (10% traffic)
- Compare performance metrics in MLflow
- Promote challenger to champion if better performance

**Sample Rate Usage:**
- 0.0 = Disabled (shadow mode for testing)
- 0.05 = 5% canary deployment
- 0.1 = 10% A/B test
- 0.5 = 50/50 split test
- 1.0 = 100% traffic (single active variant)

**Multi-Provider Support:**
- **AWS Bedrock:** aws_region, aws_profile specified
- **Ollama:** ollama_base_url for local/self-hosted LLMs
- **extra_config:** Provider-specific parameters (temperature, max_tokens, etc.)

**MLflow Integration:**
- Track experiments, runs, metrics
- Compare variant performance
- Model registry for deployment
- Experiment reproducibility

#### Query Examples

```sql
-- Champion and challenger variants
SELECT
    a.name as agent_name,
    av.variant_name,
    av.version,
    av.is_champion,
    av.sample_rate,
    av.mlflow_experiment_id
FROM agent.agent_variants av
JOIN agent.agents a ON av.agent_id = a.id
WHERE av.is_active = true
ORDER BY a.name, av.is_champion DESC;

-- Variant configuration
SELECT
    av.variant_name,
    av.aws_region,
    av.ollama_base_url,
    av.extra_config->>'model_id' as model,
    av.extra_config->>'temperature' as temperature,
    av.extra_config->>'max_tokens' as max_tokens
FROM agent.agent_variants av
WHERE av.agent_id = 'uuid-here';

-- Traffic distribution
SELECT
    a.name as agent_name,
    av.variant_name,
    av.sample_rate,
    av.sample_rate * 100 as traffic_percent
FROM agent.agent_variants av
JOIN agent.agents a ON av.agent_id = a.id
WHERE av.is_active = true
    AND av.sample_rate > 0
ORDER BY a.name, av.sample_rate DESC;
```

---

### agent_node_configs

**Purpose:** Individual node configurations within agent workflow graphs with prompt versioning

**Primary Key:** id (uuid, auto-generated)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| agent_variant_id | uuid | NO | - | FK → agent_variants.id |
| node_name | varchar(100) | NO | - | Node identifier in workflow graph |
| description | text | YES | - | Node purpose and function |
| prompt_key | varchar(100) | NO | - | Prompt identifier for retrieval |
| prompt_version | integer | NO | - | Prompt version number |
| prompt_provider | varchar(50) | NO | - | Prompt storage provider (langfuse, internal, etc.) |
| is_active | boolean | YES | - | Whether node is currently active |
| created_at | timestamp | YES | - | Node creation timestamp |
| updated_at | timestamp | YES | - | Node update timestamp |

#### Relationships

**Belongs to:**
- **agent_variants** (agent_variant_id) - Parent variant

#### Business Logic

**Workflow Nodes:**
Agent workflows consist of multiple nodes:
- **Input node:** Parse and validate input
- **Extraction node:** Extract structured data from documents
- **Validation node:** Validate extracted data
- **Analysis node:** Perform analysis/classification
- **Output node:** Format and return results

**Prompt Versioning:**
- Each node has versioned prompts
- Enables prompt A/B testing
- Rollback to previous versions if needed
- Track prompt performance via MLflow

**Prompt Providers:**
- **langfuse:** Langfuse prompt management platform
- **internal:** Internal prompt storage
- **s3:** S3-based prompt storage
- **database:** Database-stored prompts

**Prompt Key Format:**
- Examples: "income_extraction_v1", "fraud_classification_v2"
- Links to external prompt management system
- Version controlled separately from code

#### Query Examples

```sql
-- Nodes for variant
SELECT
    anc.node_name,
    anc.description,
    anc.prompt_key,
    anc.prompt_version,
    anc.prompt_provider
FROM agent.agent_node_configs anc
WHERE anc.agent_variant_id = 'uuid-here'
    AND anc.is_active = true
ORDER BY anc.node_name;

-- Prompt versions in use
SELECT
    a.name as agent_name,
    av.variant_name,
    anc.node_name,
    anc.prompt_key,
    anc.prompt_version
FROM agent.agent_node_configs anc
JOIN agent.agent_variants av ON anc.agent_variant_id = av.id
JOIN agent.agents a ON av.agent_id = a.id
WHERE anc.is_active = true
ORDER BY a.name, av.variant_name, anc.node_name;

-- Prompt provider distribution
SELECT
    prompt_provider,
    COUNT(*) as node_count,
    COUNT(DISTINCT agent_variant_id) as variant_count
FROM agent.agent_node_configs
WHERE is_active = true
GROUP BY prompt_provider
ORDER BY node_count DESC;
```

---

## Checkpoint Schema (checkpoint)

### Purpose

LangGraph checkpoint persistence for stateful agent workflows. Checkpoints enable:
- Workflow state recovery after failures
- Human-in-the-loop workflows (pause/resume)
- Workflow branching and replay
- Time-travel debugging

**LangGraph:** Framework for building stateful agent workflows with nodes and edges

---

### checkpoints

**Purpose:** Main checkpoint storage for workflow state snapshots

**Primary Key:** Composite (thread_id, checkpoint_ns, checkpoint_id)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| thread_id | text | NO | - | Workflow thread identifier (unique per workflow execution) |
| checkpoint_ns | text | NO | - | Checkpoint namespace (agent/workflow identifier) |
| checkpoint_id | text | NO | - | Checkpoint identifier (sequential or UUID) |
| parent_checkpoint_id | text | YES | - | Parent checkpoint for branching/replay |
| type | text | YES | - | Checkpoint type (snapshot, branch, etc.) |
| checkpoint | jsonb | NO | - | Complete workflow state (nodes, edges, data) |
| metadata | jsonb | NO | - | Checkpoint metadata (timestamp, reason, user) |

#### Business Logic

**Checkpoint Purpose:**
- Save complete workflow state at specific points
- Resume workflows after interruption
- Branch workflows for experimentation
- Time-travel to previous states

**Thread Management:**
- thread_id identifies unique workflow execution
- Multiple checkpoints per thread (history)
- Parent-child relationships for branching

**Checkpoint Content (JSONB):**
```json
{
  "nodes": {
    "input": {"status": "completed", "data": {...}},
    "extraction": {"status": "completed", "data": {...}},
    "validation": {"status": "in_progress", "data": {...}}
  },
  "edges": [...],
  "current_node": "validation",
  "variables": {...}
}
```

**Metadata (JSONB):**
```json
{
  "timestamp": "2024-11-25T10:30:00Z",
  "reason": "human_review_required",
  "user_id": "reviewer-123",
  "agent_variant_id": "uuid"
}
```

#### Query Examples

```sql
-- Latest checkpoint for thread
SELECT
    checkpoint_id,
    type,
    checkpoint->>'current_node' as current_node,
    metadata->>'reason' as checkpoint_reason,
    metadata->>'timestamp' as checkpoint_time
FROM checkpoint.checkpoints
WHERE thread_id = 'thread-123'
    AND checkpoint_ns = 'income_extraction'
ORDER BY checkpoint_id DESC
LIMIT 1;

-- Checkpoint history for workflow
SELECT
    checkpoint_id,
    parent_checkpoint_id,
    type,
    checkpoint->>'current_node' as node,
    metadata->>'timestamp' as created_at
FROM checkpoint.checkpoints
WHERE thread_id = 'thread-123'
ORDER BY checkpoint_id ASC;
```

---

### checkpoint_writes

**Purpose:** Individual write operations within checkpoints (incremental state updates)

**Primary Key:** Composite (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| thread_id | text | NO | - | Workflow thread identifier |
| checkpoint_ns | text | NO | - | Checkpoint namespace |
| checkpoint_id | text | NO | - | Associated checkpoint |
| task_id | text | NO | - | Task/node identifier |
| idx | integer | NO | - | Write sequence index |
| channel | text | NO | - | Data channel/stream identifier |
| type | text | YES | - | Write type (update, append, delete) |
| blob | bytea | NO | - | Serialized write data (binary) |
| task_path | text | NO | - | Task path in workflow graph |

#### Business Logic

**Incremental Updates:**
- Instead of storing full state repeatedly, store deltas
- Blob contains serialized state change
- Replay writes to reconstruct checkpoint

**Channels:**
Different data streams in workflow:
- **messages:** User/agent message history
- **state:** Workflow state variables
- **errors:** Error history
- **metrics:** Performance metrics

**Write Types:**
- **update:** Update existing data
- **append:** Add to list/history
- **delete:** Remove data

#### Query Examples

```sql
-- Writes for checkpoint
SELECT
    task_id,
    idx,
    channel,
    type,
    LENGTH(blob) as blob_size,
    task_path
FROM checkpoint.checkpoint_writes
WHERE thread_id = 'thread-123'
    AND checkpoint_id = 'checkpoint-456'
ORDER BY idx ASC;

-- Write volume by channel
SELECT
    channel,
    COUNT(*) as write_count,
    SUM(LENGTH(blob)) as total_bytes
FROM checkpoint.checkpoint_writes
WHERE checkpoint_ns = 'income_extraction'
GROUP BY channel
ORDER BY total_bytes DESC;
```

---

### checkpoint_blobs

**Purpose:** Large binary blob storage for checkpoint data (separate from main checkpoint table)

**Primary Key:** Composite (thread_id, checkpoint_ns, channel, version)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| thread_id | text | NO | - | Workflow thread identifier |
| checkpoint_ns | text | NO | - | Checkpoint namespace |
| channel | text | NO | - | Data channel identifier |
| version | text | NO | - | Blob version |
| type | text | NO | - | Blob content type |
| blob | bytea | YES | - | Binary blob data |

#### Business Logic

**Purpose:**
- Store large binary data separately from main checkpoints
- Optimize checkpoint table size
- Version blob data independently

**Blob Types:**
- **model_state:** ML model checkpoints
- **document:** Large document data
- **image:** Image data
- **embedding:** Vector embeddings

#### Query Examples

```sql
-- Blobs for thread
SELECT
    channel,
    version,
    type,
    LENGTH(blob) as blob_size
FROM checkpoint.checkpoint_blobs
WHERE thread_id = 'thread-123'
    AND checkpoint_ns = 'income_extraction'
ORDER BY version DESC;

-- Storage usage by namespace
SELECT
    checkpoint_ns,
    COUNT(*) as blob_count,
    SUM(LENGTH(blob)) / 1024 / 1024 as total_mb
FROM checkpoint.checkpoint_blobs
GROUP BY checkpoint_ns
ORDER BY total_mb DESC;
```

---

### checkpoint_migrations

**Purpose:** Track checkpoint schema migrations

**Primary Key:** v (integer, auto-increment)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| v | integer | NO | AUTO | Migration version number |

#### Business Logic

**Purpose:**
- Track applied checkpoint schema migrations
- Similar to Alembic migrations for application schema
- Ensures checkpoint schema compatibility

---

## Cross-Database Relationships

### Integration with Other Microservices

**Implicit Relationships:**

While there are no explicit foreign keys to other databases, agents process data from:

**agent execution likely links to:**
- **fraud_postgresql.proof.id** - Documents being analyzed
- **fraud_postgresql.applicants.id** - Applicants being processed
- **dp_income_validation.calculations.id** - Income calculations
- **dp_document_intelligence.asset_verifications.id** - Asset verifications

**Integration Pattern:**
Agents receive work via:
1. Message queue (Kafka, SQS, etc.)
2. API calls with document/applicant IDs
3. Workflow orchestration (Temporal)

Agents store results in:
1. Source microservice databases
2. MLflow for metrics/experiments
3. Checkpoint database for workflow state

### Multi-Database Query Pattern

Since agent executions are tracked via external systems (MLflow, Temporal), cross-database queries typically go through:
- **MLflow:** Experiment tracking, metrics, model versions
- **Temporal:** Workflow execution history
- **Application logs:** Execution traces

Checkpoint data can be joined with MLflow experiments via metadata:

```sql
-- Checkpoints with MLflow experiment info
SELECT
    c.thread_id,
    c.checkpoint_id,
    c.checkpoint_ns,
    c.metadata->>'agent_variant_id' as variant_id,
    av.mlflow_experiment_id,
    av.variant_name
FROM checkpoint.checkpoints c
JOIN agent.agent_variants av
    ON c.metadata->>'agent_variant_id' = av.id::text
WHERE c.checkpoint_ns = 'income_extraction';
```

---

## Performance Considerations

### Recommended Indexes

**agents:**
- Index on name (lookups by name)
- Index on agent_type (filtering by type)
- Index on is_active (active agent queries)

**agent_variants:**
- Index on agent_id (FK lookup)
- Composite index (is_champion, is_active) for production variant queries
- Index on mlflow_experiment_id (MLflow integration)

**agent_node_configs:**
- Index on agent_variant_id (FK lookup)
- Composite index (prompt_key, prompt_version) for prompt lookups

**checkpoints:**
- Composite index (thread_id, checkpoint_id) for checkpoint retrieval
- Index on checkpoint_ns for namespace queries
- GIN index on checkpoint JSONB for state queries

**checkpoint_writes:**
- Composite index (thread_id, checkpoint_id) for write retrieval
- Index on channel for channel queries

**checkpoint_blobs:**
- Composite index (thread_id, checkpoint_ns, channel) for blob retrieval

---

## Summary

### Key Features

**Agent Management:**
- Agent catalog with type classification
- Variant management for A/B testing
- Champion/challenger deployment pattern
- Sample rate-based traffic routing
- MLflow experiment integration

**Configuration Management:**
- Multi-provider support (AWS, Ollama)
- Flexible JSONB configuration
- Prompt versioning and management
- Node-level configuration granularity

**Workflow State Management:**
- LangGraph checkpoint persistence
- Stateful workflow execution
- Pause/resume capabilities
- Workflow branching and replay
- Incremental state updates

**Experiment Tracking:**
- MLflow integration
- Variant performance comparison
- Prompt version tracking
- Model registry integration

### Integration Points

**With other microservices:**
- Processes documents from fraud_postgresql
- Generates calculations for dp_income_validation
- Creates asset verifications for dp_document_intelligence
- Provides ML scores for av_postgres

**External Integrations:**
- **MLflow:** Experiment tracking and model registry
- **LangGraph:** Workflow orchestration framework
- **Langfuse:** Prompt management (via prompt_provider)
- **AWS Bedrock:** Managed AI models
- **Ollama:** Self-hosted LLM inference

---

## Related Documentation

- [DP_INCOME_VALIDATION.md](DP_INCOME_VALIDATION.md) - Income calculation service
- [DP_DOCUMENT_INTELLIGENCE.md](DP_DOCUMENT_INTELLIGENCE.md) - Asset verification service
- [AV_POSTGRES.md](AV_POSTGRES.md) - ML fraud detection service
- [FRAUD_DETECTION_WORKFLOW.md](FRAUD_DETECTION_WORKFLOW.md) - Main fraud workflow
- [README.md](README.md) - Project overview

---

**Generated:** 2025-11-25
**Database:** dp_ai_services
**Tables Documented:** 7 (agents, agent_variants, agent_node_configs, checkpoints, checkpoint_writes, checkpoint_blobs, checkpoint_migrations)
**Cross-Database Links:** Implicit via agent execution (document_id, applicant_id processed through agents)
