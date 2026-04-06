"""
Data seeder: populates Neo4j with realistic simulated offshoring data.
Also creates the vector index and embeds project descriptions for true GraphRAG.
Idempotent — safe to run multiple times (uses MERGE).
"""

from app.db.neo4j_db import db
from app.core.logging import logger

# ── Raw Seed Data ──────────────────────────────────────────────────────────────

ENGINEERS = [
    {"id": "eng001", "name": "Youssef El Amrani", "city": "Casablanca", "years_exp": 6, "languages": ["French", "English", "Arabic"]},
    {"id": "eng002", "name": "Sara Benali",       "city": "Rabat",       "years_exp": 4, "languages": ["French", "English"]},
    {"id": "eng003", "name": "Mehdi Tazi",         "city": "Casablanca", "years_exp": 8, "languages": ["French", "English", "Spanish"]},
    {"id": "eng004", "name": "Amina Chraibi",      "city": "Rabat",       "years_exp": 3, "languages": ["French", "Arabic"]},
    {"id": "eng005", "name": "Karim Idrissi",      "city": "Marrakech",  "years_exp": 5, "languages": ["French", "English"]},
    {"id": "eng006", "name": "Fatima Zahra Ould",  "city": "Casablanca", "years_exp": 7, "languages": ["French", "English", "German"]},
    {"id": "eng007", "name": "Omar Bennani",       "city": "Rabat",       "years_exp": 2, "languages": ["French", "English"]},
    {"id": "eng008", "name": "Nadia Filali",       "city": "Casablanca", "years_exp": 9, "languages": ["French", "English", "Spanish"]},
]

SKILLS = [
    "Python", "FastAPI", "Django", "Java", "Spring Boot",
    "SAP", "SAP S/4HANA", "React", "Angular", "Vue.js",
    "Data Engineering", "Machine Learning", "DevOps", "Kubernetes",
    "Azure", "AWS", "GCP", "PostgreSQL", "MongoDB", "GDPR Compliance",
    "ISO 27001", "Agile/Scrum", "Cybersecurity", "Power BI", "Salesforce",
]

CERTIFICATIONS = [
    {"name": "AWS Solutions Architect", "issuer": "Amazon"},
    {"name": "Azure Data Engineer",     "issuer": "Microsoft"},
    {"name": "GCP Professional",        "issuer": "Google"},
    {"name": "SAP S/4HANA Certified",   "issuer": "SAP"},
    {"name": "Certified Scrum Master",  "issuer": "Scrum Alliance"},
    {"name": "CISSP",                   "issuer": "ISC2"},
    {"name": "ISO 27001 Lead Auditor",  "issuer": "BSI"},
    {"name": "Salesforce Admin",        "issuer": "Salesforce"},
]

ESN_FIRMS = [
    {"id": "esn001", "name": "CGI Morocco",      "city": "Casablanca", "size": "large"},
    {"id": "esn002", "name": "Capgemini Maroc",  "city": "Casablanca", "size": "large"},
    {"id": "esn003", "name": "SQLI Maroc",       "city": "Rabat",      "size": "medium"},
    {"id": "esn004", "name": "Devoteam Maroc",   "city": "Casablanca", "size": "medium"},
    {"id": "esn005", "name": "NearShore Makers", "city": "Rabat",      "size": "small"},
]

SECTORS = ["Banking & Finance", "Insurance", "Retail", "Telecom", "Healthcare", "Energy", "Public Sector"]

COMPLIANCE_FRAMEWORKS = ["GDPR", "ISO 27001", "PCI-DSS", "SOC 2", "HDS (French Health Data)"]

CLIENTS = [
    {"id": "cli001", "name": "BNP Paribas",       "country": "France",  "sector": "Banking & Finance"},
    {"id": "cli002", "name": "AXA Group",         "country": "France",  "sector": "Insurance"},
    {"id": "cli003", "name": "Orange SA",         "country": "France",  "sector": "Telecom"},
    {"id": "cli004", "name": "Santander",         "country": "Spain",   "sector": "Banking & Finance"},
    {"id": "cli005", "name": "Decathlon",         "country": "France",  "sector": "Retail"},
    {"id": "cli006", "name": "Allianz",           "country": "Germany", "sector": "Insurance"},
    {"id": "cli007", "name": "Telefonica",        "country": "Spain",   "sector": "Telecom"},
    {"id": "cli008", "name": "TotalEnergies",     "country": "France",  "sector": "Energy"},
]

# Projects now include rich descriptions — these are what get embedded for GraphRAG
PROJECTS = [
    {
        "id": "prj001", "name": "Core Banking Modernization",
        "description": "End-to-end modernization of core banking infrastructure for a major French bank. "
                       "Migration from legacy COBOL systems to Java Spring Boot microservices with SAP S/4HANA integration. "
                       "Full GDPR and PCI-DSS compliance. French-speaking team required for daily client communication.",
        "client_id": "cli001", "esn_id": "esn001",
        "duration_months": 18, "team_size": 8,
        "engineer_ids": ["eng001", "eng003", "eng006"],
        "skill_names": ["Java", "Spring Boot", "SAP S/4HANA", "PostgreSQL"],
        "compliance_names": ["GDPR", "PCI-DSS"],
    },
    {
        "id": "prj002", "name": "Digital Insurance Platform",
        "description": "Cloud-native insurance policy management platform built on Azure. "
                       "Python FastAPI backend, React frontend, GDPR-compliant data architecture. "
                       "ISO 27001 certified delivery process for a French insurance group.",
        "client_id": "cli002", "esn_id": "esn002",
        "duration_months": 12, "team_size": 5,
        "engineer_ids": ["eng002", "eng005"],
        "skill_names": ["Python", "FastAPI", "React", "Azure", "GDPR Compliance"],
        "compliance_names": ["GDPR", "ISO 27001"],
    },
    {
        "id": "prj003", "name": "5G Network Analytics Dashboard",
        "description": "Real-time analytics platform for 5G network performance monitoring. "
                       "Data engineering pipeline on AWS, Power BI dashboards for operations teams. "
                       "ISO 27001 security controls for a French telecom operator.",
        "client_id": "cli003", "esn_id": "esn003",
        "duration_months": 9, "team_size": 4,
        "engineer_ids": ["eng002", "eng007"],
        "skill_names": ["Python", "Data Engineering", "Power BI", "AWS"],
        "compliance_names": ["ISO 27001"],
    },
    {
        "id": "prj004", "name": "SAP S/4HANA Migration",
        "description": "Large-scale migration of ERP systems to SAP S/4HANA for a Spanish bank. "
                       "Full GDPR compliance and SOC 2 certification. "
                       "Certified SAP consultants required. French and Spanish communication.",
        "client_id": "cli004", "esn_id": "esn001",
        "duration_months": 24, "team_size": 10,
        "engineer_ids": ["eng001", "eng003", "eng008"],
        "skill_names": ["SAP", "SAP S/4HANA", "Java", "GDPR Compliance"],
        "compliance_names": ["GDPR", "SOC 2"],
    },
    {
        "id": "prj005", "name": "E-Commerce Platform Rebuild",
        "description": "Complete rebuild of e-commerce platform using React and Vue.js frontend, "
                       "Python backend, MongoDB database. Agile delivery methodology. "
                       "GDPR-compliant customer data handling for a French retail giant.",
        "client_id": "cli005", "esn_id": "esn004",
        "duration_months": 10, "team_size": 6,
        "engineer_ids": ["eng004", "eng005", "eng007"],
        "skill_names": ["React", "Vue.js", "Python", "MongoDB", "Agile/Scrum"],
        "compliance_names": ["GDPR"],
    },
    {
        "id": "prj006", "name": "Cyber Risk Management Platform",
        "description": "Enterprise cybersecurity risk assessment and management platform. "
                       "ISO 27001 and GDPR compliance for a German insurance group. "
                       "CISSP-certified security architects required. Azure cloud infrastructure.",
        "client_id": "cli006", "esn_id": "esn002",
        "duration_months": 14, "team_size": 5,
        "engineer_ids": ["eng006", "eng008"],
        "skill_names": ["Cybersecurity", "Python", "Azure", "ISO 27001"],
        "compliance_names": ["ISO 27001", "GDPR"],
    },
    {
        "id": "prj007", "name": "CRM Salesforce Integration",
        "description": "Salesforce CRM integration and customization for customer experience management. "
                       "Python REST API integrations, Agile/Scrum delivery. "
                       "GDPR compliance for a Spanish telecom company.",
        "client_id": "cli007", "esn_id": "esn005",
        "duration_months": 6, "team_size": 3,
        "engineer_ids": ["eng004", "eng007"],
        "skill_names": ["Salesforce", "Python", "REST APIs"],
        "compliance_names": ["GDPR"],
    },
    {
        "id": "prj008", "name": "Cloud Migration & DevOps",
        "description": "Full cloud migration and DevOps transformation for an energy company. "
                       "Kubernetes orchestration, GCP infrastructure, Python automation scripts. "
                       "ISO 27001 and SOC 2 compliant deployment pipeline.",
        "client_id": "cli008", "esn_id": "esn003",
        "duration_months": 8, "team_size": 4,
        "engineer_ids": ["eng001", "eng005"],
        "skill_names": ["DevOps", "Kubernetes", "GCP", "Python"],
        "compliance_names": ["ISO 27001", "SOC 2"],
    },
]

ENGINEER_SKILLS = [
    ("eng001", "Java",            "expert"),
    ("eng001", "Spring Boot",     "expert"),
    ("eng001", "SAP S/4HANA",     "advanced"),
    ("eng001", "DevOps",          "intermediate"),
    ("eng001", "Kubernetes",      "intermediate"),
    ("eng002", "Python",          "expert"),
    ("eng002", "FastAPI",         "expert"),
    ("eng002", "React",           "advanced"),
    ("eng002", "Azure",           "advanced"),
    ("eng002", "Data Engineering","intermediate"),
    ("eng002", "Power BI",        "intermediate"),
    ("eng003", "SAP",             "expert"),
    ("eng003", "SAP S/4HANA",     "expert"),
    ("eng003", "Java",            "advanced"),
    ("eng003", "GDPR Compliance", "advanced"),
    ("eng004", "React",           "advanced"),
    ("eng004", "Vue.js",          "expert"),
    ("eng004", "Python",          "intermediate"),
    ("eng004", "Salesforce",      "intermediate"),
    ("eng004", "Agile/Scrum",     "advanced"),
    ("eng005", "Python",          "advanced"),
    ("eng005", "DevOps",          "advanced"),
    ("eng005", "Kubernetes",      "advanced"),
    ("eng005", "GCP",             "advanced"),
    ("eng005", "Agile/Scrum",     "expert"),
    ("eng006", "Cybersecurity",   "expert"),
    ("eng006", "ISO 27001",       "expert"),
    ("eng006", "Python",          "advanced"),
    ("eng006", "Azure",           "advanced"),
    ("eng006", "Java",            "intermediate"),
    ("eng007", "Python",          "advanced"),
    ("eng007", "Data Engineering","advanced"),
    ("eng007", "Power BI",        "intermediate"),
    ("eng007", "Agile/Scrum",     "intermediate"),
    ("eng007", "Salesforce",      "intermediate"),
    ("eng008", "SAP S/4HANA",     "expert"),
    ("eng008", "SAP",             "expert"),
    ("eng008", "GDPR Compliance", "expert"),
    ("eng008", "Cybersecurity",   "advanced"),
    ("eng008", "ISO 27001",       "advanced"),
]

ENGINEER_CERTS = [
    ("eng001", "Certified Scrum Master"),
    ("eng002", "Azure Data Engineer"),
    ("eng002", "AWS Solutions Architect"),
    ("eng003", "SAP S/4HANA Certified"),
    ("eng005", "GCP Professional"),
    ("eng005", "Certified Scrum Master"),
    ("eng006", "CISSP"),
    ("eng006", "ISO 27001 Lead Auditor"),
    ("eng008", "SAP S/4HANA Certified"),
    ("eng008", "ISO 27001 Lead Auditor"),
    ("eng004", "Salesforce Admin"),
]

ENGINEER_ESN = [
    ("eng001", "esn001"),
    ("eng002", "esn002"),
    ("eng003", "esn001"),
    ("eng004", "esn005"),
    ("eng005", "esn003"),
    ("eng006", "esn002"),
    ("eng007", "esn003"),
    ("eng008", "esn004"),
]


# ── Seeder Functions ───────────────────────────────────────────────────────────

def _clear_graph() -> None:
    db.run_query("MATCH (n) DETACH DELETE n")
    logger.info("Graph cleared.")


def _create_constraints() -> None:
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Engineer) REQUIRE e.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Certification) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (f:ESNFirm) REQUIRE f.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (cl:Client) REQUIRE cl.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (cf:ComplianceFramework) REQUIRE cf.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (sec:Sector) REQUIRE sec.name IS UNIQUE",
    ]
    for c in constraints:
        db.run_query(c)
    logger.info("Constraints created.")


def _seed_engineers() -> None:
    for e in ENGINEERS:
        db.run_query(
            """
            MERGE (eng:Engineer {id: $id})
            SET eng.name = $name, eng.city = $city,
                eng.years_exp = $years_exp, eng.languages = $languages
            """,
            e,
        )
    logger.info("Seeded %d engineers.", len(ENGINEERS))


def _seed_skills() -> None:
    for skill in SKILLS:
        db.run_query("MERGE (:Skill {name: $name})", {"name": skill})
    logger.info("Seeded %d skills.", len(SKILLS))


def _seed_certifications() -> None:
    for cert in CERTIFICATIONS:
        db.run_query(
            "MERGE (:Certification {name: $name, issuer: $issuer})", cert
        )
    logger.info("Seeded %d certifications.", len(CERTIFICATIONS))


def _seed_sectors() -> None:
    for sector in SECTORS:
        db.run_query("MERGE (:Sector {name: $name})", {"name": sector})
    logger.info("Seeded %d sectors.", len(SECTORS))


def _seed_compliance_frameworks() -> None:
    for cf in COMPLIANCE_FRAMEWORKS:
        db.run_query("MERGE (:ComplianceFramework {name: $name})", {"name": cf})
    logger.info("Seeded %d compliance frameworks.", len(COMPLIANCE_FRAMEWORKS))


def _seed_esn_firms() -> None:
    for firm in ESN_FIRMS:
        db.run_query(
            """
            MERGE (f:ESNFirm {id: $id})
            SET f.name = $name, f.city = $city, f.size = $size
            """,
            firm,
        )
    logger.info("Seeded %d ESN firms.", len(ESN_FIRMS))


def _seed_clients() -> None:
    for client in CLIENTS:
        db.run_query(
            """
            MERGE (cl:Client {id: $id})
            SET cl.name = $name, cl.country = $country, cl.sector = $sector
            WITH cl
            MATCH (s:Sector {name: $sector})
            MERGE (cl)-[:IN_SECTOR]->(s)
            """,
            client,
        )
    logger.info("Seeded %d clients.", len(CLIENTS))


def _seed_projects() -> None:
    for p in PROJECTS:
        db.run_query(
            """
            MERGE (proj:Project {id: $id})
            SET proj.name = $name, proj.duration_months = $duration_months,
                proj.team_size = $team_size, proj.description = $description
            WITH proj
            MATCH (cl:Client {id: $client_id})
            MERGE (proj)-[:FOR_CLIENT]->(cl)
            WITH proj
            MATCH (f:ESNFirm {id: $esn_id})
            MERGE (proj)-[:DELIVERED_BY]->(f)
            """,
            {
                "id": p["id"], "name": p["name"],
                "description": p.get("description", p["name"]),
                "duration_months": p["duration_months"],
                "team_size": p["team_size"],
                "client_id": p["client_id"],
                "esn_id": p["esn_id"],
            },
        )
        for skill_name in p["skill_names"]:
            db.run_query(
                """
                MATCH (proj:Project {id: $pid}), (s:Skill {name: $sname})
                MERGE (proj)-[:REQUIRED_SKILL]->(s)
                """,
                {"pid": p["id"], "sname": skill_name},
            )
        for cf_name in p["compliance_names"]:
            db.run_query(
                """
                MATCH (proj:Project {id: $pid}), (cf:ComplianceFramework {name: $cfname})
                MERGE (proj)-[:REQUIRED_COMPLIANCE]->(cf)
                """,
                {"pid": p["id"], "cfname": cf_name},
            )
        for eng_id in p["engineer_ids"]:
            db.run_query(
                """
                MATCH (eng:Engineer {id: $eid}), (proj:Project {id: $pid})
                MERGE (eng)-[:WORKED_ON]->(proj)
                """,
                {"eid": eng_id, "pid": p["id"]},
            )
    logger.info("Seeded %d projects.", len(PROJECTS))


def _seed_engineer_skills() -> None:
    for eng_id, skill_name, proficiency in ENGINEER_SKILLS:
        db.run_query(
            """
            MATCH (eng:Engineer {id: $eid}), (s:Skill {name: $sname})
            MERGE (eng)-[r:HAS_SKILL]->(s)
            SET r.proficiency = $proficiency
            """,
            {"eid": eng_id, "sname": skill_name, "proficiency": proficiency},
        )
    logger.info("Seeded %d engineer-skill relationships.", len(ENGINEER_SKILLS))


def _seed_engineer_certifications() -> None:
    for eng_id, cert_name in ENGINEER_CERTS:
        db.run_query(
            """
            MATCH (eng:Engineer {id: $eid}), (c:Certification {name: $cname})
            MERGE (eng)-[:HOLDS_CERT]->(c)
            """,
            {"eid": eng_id, "cname": cert_name},
        )
    logger.info("Seeded %d engineer-certification relationships.", len(ENGINEER_CERTS))


def _seed_engineer_esn() -> None:
    for eng_id, esn_id in ENGINEER_ESN:
        db.run_query(
            """
            MATCH (eng:Engineer {id: $eid}), (f:ESNFirm {id: $fid})
            MERGE (eng)-[:WORKS_AT]->(f)
            """,
            {"eid": eng_id, "fid": esn_id},
        )
    logger.info("Seeded %d engineer-ESN relationships.", len(ENGINEER_ESN))


def _seed_embeddings() -> None:
    """Create vector index and embed all project descriptions for true GraphRAG."""
    try:
        from app.services.embedding_service import create_vector_index, embed_all_projects
        create_vector_index()
        count = embed_all_projects()
        logger.info("GraphRAG embeddings ready: %d projects embedded.", count)
    except Exception as e:
        logger.warning("Embedding step failed (non-fatal): %s", e)


def seed_database(clear_first: bool = True) -> dict:
    """Main entry point for seeding. Returns a summary."""
    logger.info("Starting database seed...")
    if clear_first:
        _clear_graph()

    _create_constraints()
    _seed_skills()
    _seed_certifications()
    _seed_sectors()
    _seed_compliance_frameworks()
    _seed_esn_firms()
    _seed_engineers()
    _seed_clients()
    _seed_projects()
    _seed_engineer_skills()
    _seed_engineer_certifications()
    _seed_engineer_esn()
    _seed_embeddings()

    summary = db.run_query(
        """
        MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count
        ORDER BY label
        """
    )
    logger.info("Database seeding complete. Summary: %s", summary)
    return {"status": "seeded", "node_counts": summary}
