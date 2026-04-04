"""
GraphRAG Service — all Neo4j retrieval logic lives here.
This is the core differentiator vs. plain vector search.
"""

from app.db.neo4j_db import db
from app.core.logging import logger


class GraphRAGService:
    """
    Executes multi-hop Cypher queries that would be impossible with
    vector/semantic search alone. Retrieves structured, relational context
    for the LLM agents.
    """

    def find_engineers_by_skills(
        self, skill_names: list[str], min_proficiency: str = "intermediate"
    ) -> list[dict]:
        """
        Multi-hop: Engineer → HAS_SKILL → Skill (with proficiency filter).
        Returns engineers with skill match count for scoring.
        """
        proficiency_rank = {"intermediate": 1, "advanced": 2, "expert": 3}
        min_rank = proficiency_rank.get(min_proficiency, 1)

        query = """
        UNWIND $skills AS skillName
        MATCH (eng:Engineer)-[r:HAS_SKILL]->(s:Skill {name: skillName})
        WHERE CASE r.proficiency
            WHEN 'expert' THEN 3
            WHEN 'advanced' THEN 2
            WHEN 'intermediate' THEN 1
            ELSE 0
        END >= $min_rank
        WITH eng, collect(DISTINCT s.name) AS matchedSkills,
             count(DISTINCT s) AS matchCount
        RETURN eng.id AS id,
               eng.name AS name,
               eng.city AS city,
               eng.years_exp AS years_exp,
               eng.languages AS languages,
               matchedSkills,
               matchCount
        ORDER BY matchCount DESC
        """
        results = db.run_query(query, {"skills": skill_names, "min_rank": min_rank})
        logger.debug("Skill search returned %d engineers.", len(results))
        return results

    def find_engineers_by_compliance(self, frameworks: list[str]) -> list[dict]:
        """
        3-hop: Engineer → WORKED_ON → Project → REQUIRED_COMPLIANCE → ComplianceFramework.
        Finds engineers with hands-on compliance project experience.
        """
        query = """
        UNWIND $frameworks AS cfName
        MATCH (eng:Engineer)-[:WORKED_ON]->(p:Project)-[:REQUIRED_COMPLIANCE]->(cf:ComplianceFramework {name: cfName})
        WITH eng, collect(DISTINCT cf.name) AS complianceExp,
             collect(DISTINCT p.name) AS relevantProjects
        RETURN eng.id AS id,
               eng.name AS name,
               complianceExp,
               relevantProjects
        ORDER BY size(complianceExp) DESC
        """
        return db.run_query(query, {"frameworks": frameworks})

    def find_engineers_by_sector_experience(self, sector: str) -> list[dict]:
        """
        4-hop: Engineer → WORKED_ON → Project → FOR_CLIENT → Client → IN_SECTOR → Sector.
        The quintessential GraphRAG query — impossible with vector search.
        """
        query = """
        MATCH (eng:Engineer)-[:WORKED_ON]->(p:Project)-[:FOR_CLIENT]->(cl:Client)-[:IN_SECTOR]->(s:Sector {name: $sector})
        WITH eng, collect(DISTINCT cl.name) AS clients,
             collect(DISTINCT p.name) AS projects,
             count(DISTINCT p) AS projectCount
        RETURN eng.id AS id,
               eng.name AS name,
               clients,
               projects,
               projectCount
        ORDER BY projectCount DESC
        """
        return db.run_query(query, {"sector": sector})

    def find_engineers_by_certifications(self, cert_names: list[str]) -> list[dict]:
        """
        Engineer → HOLDS_CERT → Certification.
        """
        query = """
        UNWIND $certs AS certName
        MATCH (eng:Engineer)-[:HOLDS_CERT]->(c:Certification {name: certName})
        WITH eng, collect(DISTINCT c.name) AS heldCerts
        RETURN eng.id AS id,
               eng.name AS name,
               heldCerts
        ORDER BY size(heldCerts) DESC
        """
        return db.run_query(query, {"certs": cert_names})

    def get_engineer_full_profile(self, engineer_id: str) -> dict:
        """
        Full profile: skills, certs, projects, clients, compliance, ESN firm.
        """
        query = """
        MATCH (eng:Engineer {id: $eid})
        OPTIONAL MATCH (eng)-[sr:HAS_SKILL]->(s:Skill)
        OPTIONAL MATCH (eng)-[:HOLDS_CERT]->(c:Certification)
        OPTIONAL MATCH (eng)-[:WORKED_ON]->(p:Project)-[:FOR_CLIENT]->(cl:Client)
        OPTIONAL MATCH (p)-[:REQUIRED_COMPLIANCE]->(cf:ComplianceFramework)
        OPTIONAL MATCH (eng)-[:WORKS_AT]->(f:ESNFirm)
        RETURN eng.id AS id,
               eng.name AS name,
               eng.city AS city,
               eng.years_exp AS years_exp,
               eng.languages AS languages,
               collect(DISTINCT {skill: s.name, proficiency: sr.proficiency}) AS skills,
               collect(DISTINCT c.name) AS certifications,
               collect(DISTINCT p.name) AS projects,
               collect(DISTINCT cl.name) AS clients,
               collect(DISTINCT cf.name) AS compliance_experience,
               f.name AS firm
        """
        results = db.run_query(query, {"eid": engineer_id})
        return results[0] if results else {}

    def identify_skill_gaps(
        self, required_skills: list[str], engineer_ids: list[str]
    ) -> list[str]:
        """
        Finds required skills NOT covered by the proposed team.
        """
        if not engineer_ids:
            return required_skills

        query = """
        UNWIND $skills AS skillName
        MATCH (s:Skill {name: skillName})
        OPTIONAL MATCH (eng:Engineer)-[:HAS_SKILL]->(s)
        WHERE eng.id IN $engineer_ids
        WITH skillName, count(eng) AS coveredBy
        WHERE coveredBy = 0
        RETURN skillName AS uncovered_skill
        """
        results = db.run_query(
            query, {"skills": required_skills, "engineer_ids": engineer_ids}
        )
        return [r["uncovered_skill"] for r in results]

    def build_graph_visualization_data(self, engineer_ids: list[str]) -> dict:
        """
        Builds nodes + edges payload for the frontend graph visualization.
        Focuses on the subgraph around matched engineers.
        """
        query = """
        MATCH (eng:Engineer)
        WHERE eng.id IN $engineer_ids
        OPTIONAL MATCH (eng)-[sr:HAS_SKILL]->(s:Skill)
        OPTIONAL MATCH (eng)-[:HOLDS_CERT]->(c:Certification)
        OPTIONAL MATCH (eng)-[:WORKED_ON]->(p:Project)-[:FOR_CLIENT]->(cl:Client)
        OPTIONAL MATCH (eng)-[:WORKS_AT]->(f:ESNFirm)
        WITH eng, sr, s, c, p, cl, f
        RETURN
            collect(DISTINCT {
                id: eng.id, label: eng.name,
                type: 'Engineer', city: eng.city, exp: eng.years_exp
            }) AS engineers,
            collect(DISTINCT {id: s.name, label: s.name, type: 'Skill'}) AS skills,
            collect(DISTINCT {id: c.name, label: c.name, type: 'Certification'}) AS certs,
            collect(DISTINCT {id: p.id, label: p.name, type: 'Project'}) AS projects,
            collect(DISTINCT {id: cl.id, label: cl.name, type: 'Client'}) AS clients,
            collect(DISTINCT {id: f.id, label: f.name, type: 'ESNFirm'}) AS firms
        """
        raw = db.run_query(query, {"engineer_ids": engineer_ids})
        if not raw:
            return {"nodes": [], "edges": []}

        r = raw[0]
        nodes = []
        seen_ids = set()

        for group in ["engineers", "skills", "certs", "projects", "clients", "firms"]:
            for node in r.get(group, []):
                if node["id"] and node["id"] not in seen_ids:
                    nodes.append(node)
                    seen_ids.add(node["id"])

        # Fetch edges separately
        edge_query = """
        MATCH (eng:Engineer)
        WHERE eng.id IN $engineer_ids
        OPTIONAL MATCH (eng)-[sr:HAS_SKILL]->(s:Skill)
        OPTIONAL MATCH (eng)-[:HOLDS_CERT]->(c:Certification)
        OPTIONAL MATCH (eng)-[:WORKED_ON]->(p:Project)-[:FOR_CLIENT]->(cl:Client)
        OPTIONAL MATCH (eng)-[:WORKS_AT]->(f:ESNFirm)
        WITH collect({from: eng.id, to: s.name, label: sr.proficiency}) +
             collect({from: eng.id, to: c.name, label: 'certified'}) +
             collect({from: eng.id, to: p.id,   label: 'worked on'}) +
             collect({from: p.id,   to: cl.id,  label: 'for client'}) +
             collect({from: eng.id, to: f.id,   label: 'works at'}) AS allEdges
        UNWIND allEdges AS edge
        WITH edge WHERE edge.from IS NOT NULL AND edge.to IS NOT NULL
        RETURN DISTINCT edge.from AS source, edge.to AS target, edge.label AS label
        """
        edges_raw = db.run_query(edge_query, {"engineer_ids": engineer_ids})

        return {"nodes": nodes, "edges": edges_raw}
