"""
Embedding Service — True GraphRAG entry point.

Uses sentence-transformers locally (no API key, no cost) to embed
project descriptions and RFP text. Stores vectors in Neo4j vector index.
Semantic similarity search finds the most relevant projects first,
then graph traversal enriches results with connected engineers.

This is what separates GraphRAG from plain graph retrieval:
  Vector search  → finds semantically similar projects (entry point)
  Graph traversal → finds engineers connected to those projects (enrichment)
"""

from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.db.neo4j_db import db
from app.core.logging import logger

EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # 80MB, fast, good quality, runs on CPU
VECTOR_DIMENSION = 384                   # dimension of all-MiniLM-L6-v2 output
INDEX_NAME = "project_embeddings"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
    return SentenceTransformer(EMBEDDING_MODEL)


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def create_vector_index() -> None:
    """
    Create Neo4j vector index on Project nodes.
    Safe to call multiple times — uses IF NOT EXISTS.
    Requires Neo4j 5.11+.
    """
    query = """
    CREATE VECTOR INDEX project_embeddings IF NOT EXISTS
    FOR (p:Project) ON (p.embedding)
    OPTIONS {indexConfig: {
        `vector.dimensions`: 384,
        `vector.similarity_function`: 'cosine'
    }}
    """
    try:
        db.run_query(query)
        logger.info("Vector index '%s' ready.", INDEX_NAME)
    except Exception as e:
        logger.warning("Vector index creation: %s", e)


def embed_all_projects() -> int:
    """
    Compute and store embeddings for all Project nodes.
    Called during database seeding.
    Returns number of projects embedded.
    """
    projects = db.run_query("MATCH (p:Project) RETURN p.id AS id, p.name AS name, p.description AS description")
    model = get_embedding_model()
    count = 0
    for p in projects:
        text = f"{p['name']}. {p.get('description', '')}"
        embedding = model.encode(text, normalize_embeddings=True).tolist()
        db.run_query(
            "MATCH (p:Project {id: $pid}) SET p.embedding = $embedding",
            {"pid": p["id"], "embedding": embedding}
        )
        count += 1
    logger.info("Embedded %d projects into Neo4j.", count)
    return count


def semantic_search_projects(rfp_text: str, top_k: int = 5) -> list[dict]:
    """
    TRUE GraphRAG step 1: vector similarity search.

    Embeds the RFP text and finds the top-k most semantically similar
    projects in Neo4j using the vector index.

    Returns project nodes ranked by cosine similarity to the RFP.
    """
    query_vector = embed_text(rfp_text)

    cypher = """
    CALL db.index.vector.queryNodes($index_name, $top_k, $query_vector)
    YIELD node AS project, score
    RETURN project.id   AS id,
           project.name AS name,
           score
    ORDER BY score DESC
    """
    try:
        results = db.run_query(cypher, {
            "index_name": INDEX_NAME,
            "top_k": top_k,
            "query_vector": query_vector,
        })
        logger.info("Semantic search found %d similar projects.", len(results))
        return results
    except Exception as e:
        logger.warning("Semantic search failed (index may not be ready): %s", e)
        return []


def graphrag_find_engineers_from_projects(project_ids: list[str]) -> list[dict]:
    """
    TRUE GraphRAG step 2: graph traversal from semantically found projects.

    Starting from projects found by vector similarity, traverse the graph
    to find engineers who worked on those projects, plus their full context.

    Vector search gave us the entry nodes.
    Graph traversal gives us the connected engineers.
    This two-step process is what defines GraphRAG.
    """
    if not project_ids:
        return []

    cypher = """
    UNWIND $project_ids AS pid
    MATCH (eng:Engineer)-[:WORKED_ON]->(p:Project {id: pid})
    OPTIONAL MATCH (eng)-[sr:HAS_SKILL]->(s:Skill)
    OPTIONAL MATCH (eng)-[:HOLDS_CERT]->(c:Certification)
    OPTIONAL MATCH (p)-[:FOR_CLIENT]->(cl:Client)-[:IN_SECTOR]->(sec:Sector)
    OPTIONAL MATCH (p)-[:REQUIRED_COMPLIANCE]->(cf:ComplianceFramework)
    WITH eng,
         collect(DISTINCT p.name)          AS semantic_projects,
         collect(DISTINCT {skill: s.name, proficiency: sr.proficiency}) AS skills,
         collect(DISTINCT c.name)          AS certifications,
         collect(DISTINCT cl.name)         AS clients,
         collect(DISTINCT sec.name)        AS sectors,
         collect(DISTINCT cf.name)         AS compliance_experience,
         count(DISTINCT p)                 AS project_count
    RETURN eng.id          AS id,
           eng.name        AS name,
           eng.city        AS city,
           eng.years_exp   AS years_exp,
           eng.languages   AS languages,
           semantic_projects,
           skills,
           certifications,
           clients,
           sectors,
           compliance_experience,
           project_count
    ORDER BY project_count DESC
    """
    results = db.run_query(cypher, {"project_ids": project_ids})
    logger.info(
        "GraphRAG traversal from %d projects → %d engineers.",
        len(project_ids), len(results)
    )
    return results
