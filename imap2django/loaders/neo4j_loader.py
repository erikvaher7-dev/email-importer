"""
Neo4j loader stub.
You can keep SQL as primary, or switch backend=neo4j in the command.

This file is intentionally minimal. It shows the pattern: MERGE by unique keys.
"""
from django.conf import settings

def load_neo4j(*args, **kwargs):
    from neo4j import GraphDatabase

    if not settings.NEO4J_URI:
        raise RuntimeError("Neo4j not configured. Set NEO4J_URI/USER/PASSWORD in .env")

    driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))

    account_email = kwargs["account_email"]
    provider = kwargs.get("provider", "")
    mailbox_name = kwargs["mailbox_name"]
    uid = kwargs["uid"]
    flags = kwargs.get("flags") or []
    internal_date = kwargs.get("internal_date")
    n = kwargs["normalized"]

    cypher = """
    MERGE (a:Account {email:$account_email})
      ON CREATE SET a.provider=$provider
    MERGE (m:Mailbox {key:$mailbox_key})
      ON CREATE SET m.name=$mailbox_name
    MERGE (a)-[:HAS_MAILBOX]->(m)

    MERGE (msg:Message {raw_sha256:$raw_sha256})
      ON CREATE SET msg.message_id=$message_id,
                    msg.content_fingerprint=$content_fingerprint,
                    msg.subject=$subject,
                    msg.subject_norm=$subject_norm,
                    msg.date=$date,
                    msg.internal_date=$internal_date,
                    msg.size=$size

    MERGE (m)-[c:CONTAINS {uid:$uid}]->(msg)
      SET c.flags=$flags
    """

    mailbox_key = f"{account_email}:{mailbox_name}"

    with driver.session() as session:
        session.run(
            cypher,
            account_email=account_email,
            provider=provider,
            mailbox_key=mailbox_key,
            mailbox_name=mailbox_name,
            raw_sha256=n.raw_sha256,
            message_id=n.message_id or None,
            content_fingerprint=n.content_fingerprint,
            subject=n.subject,
            subject_norm=n.subject_norm,
            date=str(n.date_dt) if n.date_dt else None,
            internal_date=str(internal_date) if internal_date else None,
            size=n.size,
            uid=int(uid),
            flags=list(flags),
        )
    driver.close()
