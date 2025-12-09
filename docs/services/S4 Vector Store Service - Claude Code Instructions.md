---
updated: 2025-10-04, 19:40
---
 
## Vector Store Service - Claude Code Instructions

### Context & Objective

You're building the **Vector Store Service** for Scout, a centralized abstraction layer managing all vector database operations. This service handles embedding generation, similarity search, and index management across all modules requiring semantic operations.

### Module Specifications

**Purpose**: Provide a unified interface for vector storage and retrieval, managing embeddings for user profiles, job requirements, and cached responses with optimized similarity search capabilities.

**Key Responsibilities**:
1. Manage ChromaDB collections for different data types
2. Generate and cache embeddings using sentence-transformers
3. Perform similarity searches with metadata filtering
4. Handle batch operations for efficiency
5. Maintain index optimization and garbage collection
6. Provide cross-collection search capabilities

### Technical Requirements

**Dependencies**:
- ChromaDB for vector storage
- Sentence-transformers for embeddings
- NumPy for vector operations
- FAISS as optional secondary index
- Asyncio for concurrent operations
- LRU cache for embedding reuse

**File Structure**:
```
scout/
├── app/
│   ├── services/
│   │   ├── vector_store.py
│   │   ├── vector_operations/
│   │   │   ├── __init__.py
│   │   │   ├── embeddings.py
│   │   │   ├── similarity.py
│   │   │   └── indexing.py
│   │   └── vector_config.py
│   ├── models/
│   │   └── vectors.py
│   └── utils/
│       └── vector_utils.py
├── data/
│   ├── vectors/
│   │   ├── chroma/
│   │   └── embeddings_cache/
└── tests/
    └── test_vector_store.py
```

### Data Models Requirements

Create comprehensive models in `app/models/vectors.py`:
- VectorEntry model with id, embedding, metadata, timestamp
- CollectionConfig for collection-specific settings
- SearchQuery with text, filters, top_k, threshold
- SearchResult with matches, scores, metadata
- BatchOperation for bulk inserts/updates
- IndexStats for performance monitoring
- EmbeddingCache for reuse optimization

### Core Service Implementation Requirements

The main Vector Store Service should include:

**Collection Management**:
- Dynamic collection creation with configurable dimensions
- Collection metadata tracking (size, last update, performance stats)
- Cross-collection search for comprehensive results
- Collection versioning for backward compatibility
- Automatic cleanup of stale embeddings

**Embedding Operations**:
- Batch embedding generation with progress tracking
- Embedding caching with TTL management
- Multiple embedding models support
- Dimension reduction options for large vectors
- Incremental embedding updates

**Search Functionality**:
- Configurable similarity metrics (cosine, L2, inner product)
- Metadata filtering with complex queries
- Hybrid search combining vector and keyword matching
- Result re-ranking strategies
- Approximate nearest neighbor optimization

**Performance Optimization**:
- Connection pooling for concurrent access
- Batch size optimization based on available memory
- Index partitioning for large collections
- Query result caching
- Asynchronous index updates

### Integration Requirements

**With Collector Module**:
- Store user profile embeddings
- Index experiences and skills
- Support profile versioning
- Enable incremental updates

**With Analyzer Module**:
- Provide fast similarity search
- Support multi-criteria matching
- Enable threshold-based filtering
- Return relevance explanations

**With Cache Service**:
- Store semantic cache embeddings
- Enable similarity-based cache retrieval
- Manage cache invalidation

### Critical Implementation Details

**Embedding Strategy**:
- Use all-MiniLM-L6-v2 as primary model (384 dimensions)
- Cache embeddings for frequently accessed content
- Batch processing for efficiency (optimal batch size: 32)
- Normalize embeddings for cosine similarity

**Collection Structure**:
- `user_experiences`: Professional experiences with rich metadata
- `user_skills`: Skills with proficiency levels
- `job_requirements`: Parsed job requirements
- `semantic_cache`: LLM response embeddings
- `documents`: Generated document embeddings

**Search Optimization**:
- Pre-filter by metadata before vector search
- Use IVF index for collections >10,000 entries
- Implement query expansion for better recall
- Cache frequent query patterns

**Data Persistence**:
- ChromaDB persistent storage in `data/vectors/chroma`
- Backup strategy for disaster recovery
- Migration scripts for schema updates
- Data validation before insertion

### Testing Requirements

1. **Embedding Tests**: Consistency, performance, caching
2. **Search Tests**: Accuracy, speed, filtering, edge cases
3. **Collection Tests**: Creation, updates, deletion, migration
4. **Performance Tests**: Batch operations, concurrent access, memory usage
5. **Integration Tests**: Module interactions, error propagation

### Success Criteria

- Embedding generation: <100ms for single, <1s for batch of 100
- Search latency: <50ms for 10k vectors
- Memory efficiency: <2GB for 100k vectors
- Search accuracy: >90% recall@10
- Cache hit rate: >60% for repeated queries
- Concurrent operations: Support 20+ simultaneous searches

### Edge Cases to Handle

- Duplicate embeddings detection
- Malformed vectors handling
- Collection size limits
- Memory overflow prevention
- Concurrent write conflicts
- Index corruption recovery
- Dimension mismatch errors
- Empty query handling
- Network disconnection resilience
- Garbage collection during high load

---

## Strategic Questions for Implementation

**51. Should we implement vector quantization to reduce memory usage for large-scale deployment?**
*Recommendation: No for PoC, but design interfaces to allow future addition of quantization without breaking changes.*

**52. Should we support multiple embedding models simultaneously for different use cases?**
*Recommendation: Yes - Design with model abstraction from start; use MiniLM for general, consider specialized models for technical terms.*

**53. Should we implement incremental indexing or rebuild indexes completely on updates?**
*Recommendation: Incremental for PoC with <10k vectors, plan for FAISS migration with full rebuilds for production scale.*

**54. Should vector searches return explanation data about why matches were found?**
*Recommendation: Yes - Include metadata about matching dimensions/features to help users understand and trust results.*

**55. Should we implement vector clustering for improved search performance?**
*Recommendation: Not for PoC, but structure code to enable IVF/HNSW clustering when scaling beyond 50k vectors.*

**56. Should the Vector Store support multi-tenancy for future SaaS deployment?**
*Recommendation: Design with tenant isolation in mind using collection prefixes, but single-tenant implementation for PoC.*

**57. Should we implement automatic embedding refresh when the model changes?**
*Recommendation: Yes - Version embeddings with model identifier and provide migration utilities for model updates.*

**58. Should vector operations be synchronous or asynchronous by default?**
*Recommendation: Async by default with sync wrappers where needed - better for concurrent operations and UI responsiveness.*

**59. Should we implement distributed vector storage across multiple ChromaDB instances?**
*Recommendation: No for PoC, but design service interface to abstract storage backend for future distribution.*

**60. Should we support custom similarity metrics beyond cosine similarity?**
*Recommendation: Yes - Implement pluggable similarity functions; start with cosine, add Euclidean and dot product.*