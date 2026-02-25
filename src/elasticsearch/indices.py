"""
Elasticsearch index mappings for Meridian.
Each index is designed to maximally use ES capabilities:
  - dense_vector fields  → vector/semantic search
  - keyword + text       → hybrid search
  - geo_point            → geo queries
  - date + numeric       → ES|QL time-series analytics
"""

INDICES = {
    "meridian-entities": {
        "mappings": {
            "properties": {
                "entity_id": {"type": "keyword"},
                "name": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "name_vector": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine",
                },
                "aliases": {"type": "keyword"},
                "entity_type": {"type": "keyword"},  # company | person | foundation
                "jurisdiction": {"type": "keyword"},
                "registration_number": {"type": "keyword"},
                "registered_address": {"type": "text"},
                "incorporation_date": {"type": "date"},
                "dissolution_date": {"type": "date"},
                "status": {"type": "keyword"},  # active | dissolved | suspended
                "parent_entity_id": {"type": "keyword"},
                "subsidiary_ids": {"type": "keyword"},
                "officer_ids": {"type": "keyword"},
                "sic_codes": {"type": "keyword"},
                "industry": {"type": "keyword"},
                "geo_location": {"type": "geo_point"},
                "country_code": {"type": "keyword"},
                "risk_score": {"type": "float"},
                "risk_flags": {"type": "keyword"},
                "data_sources": {"type": "keyword"},
                "ingested_at": {"type": "date"},
                "updated_at": {"type": "date"},
            }
        },
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    },

    "meridian-filings": {
        "mappings": {
            "properties": {
                "filing_id": {"type": "keyword"},
                "entity_id": {"type": "keyword"},
                "entity_name": {"type": "keyword"},
                "filing_type": {"type": "keyword"},  # 10-K | 10-Q | 8-K | ...
                "filing_date": {"type": "date"},
                "period_of_report": {"type": "date"},
                "title": {"type": "text"},
                "description": {"type": "text"},
                "content_summary": {"type": "text"},
                "content_vector": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine",
                },
                "revenue": {"type": "float"},
                "net_income": {"type": "float"},
                "total_assets": {"type": "float"},
                "total_debt": {"type": "float"},
                "auditor": {"type": "keyword"},
                "auditor_opinion": {"type": "keyword"},  # clean | qualified | adverse | disclaimer
                "going_concern": {"type": "boolean"},
                "restatement": {"type": "boolean"},
                "source": {"type": "keyword"},
                "source_url": {"type": "keyword"},
                "ingested_at": {"type": "date"},
            }
        },
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    },

    "meridian-legal": {
        "mappings": {
            "properties": {
                "case_id": {"type": "keyword"},
                "entity_ids": {"type": "keyword"},
                "entity_names": {"type": "keyword"},
                "case_type": {"type": "keyword"},  # civil | criminal | regulatory | sanction
                "case_name": {"type": "text"},
                "case_summary": {"type": "text"},
                "summary_vector": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine",
                },
                "court": {"type": "keyword"},
                "jurisdiction": {"type": "keyword"},
                "filed_date": {"type": "date"},
                "resolved_date": {"type": "date"},
                "status": {"type": "keyword"},  # active | resolved | appealed
                "outcome": {"type": "keyword"},  # settled | dismissed | judgment_plaintiff | judgment_defendant
                "settlement_amount": {"type": "float"},
                "penalty_amount": {"type": "float"},
                "allegations": {"type": "keyword"},
                "regulator": {"type": "keyword"},  # SEC | DOJ | FTC | FDA | ...
                "is_sanction": {"type": "boolean"},
                "sanction_list": {"type": "keyword"},  # OFAC | EU | UN
                "source": {"type": "keyword"},
                "source_url": {"type": "keyword"},
                "ingested_at": {"type": "date"},
            }
        },
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    },

    "meridian-news": {
        "mappings": {
            "properties": {
                "article_id": {"type": "keyword"},
                "entity_ids": {"type": "keyword"},
                "entity_names": {"type": "keyword"},
                "title": {"type": "text"},
                "content": {"type": "text"},
                "content_vector": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine",
                },
                "source_name": {"type": "keyword"},
                "source_url": {"type": "keyword"},
                "published_at": {"type": "date"},
                "sentiment_score": {"type": "float"},  # -1.0 to 1.0
                "sentiment_label": {"type": "keyword"},  # positive | negative | neutral
                "topics": {"type": "keyword"},
                "geo_location": {"type": "geo_point"},
                "country_code": {"type": "keyword"},
                "language": {"type": "keyword"},
                "ingested_at": {"type": "date"},
            }
        },
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    },

    "meridian-executives": {
        "mappings": {
            "properties": {
                "person_id": {"type": "keyword"},
                "full_name": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "name_vector": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine",
                },
                "aliases": {"type": "keyword"},
                "current_entity_id": {"type": "keyword"},
                "current_title": {"type": "keyword"},
                "employment_history": {
                    "type": "nested",
                    "properties": {
                        "entity_id": {"type": "keyword"},
                        "entity_name": {"type": "keyword"},
                        "title": {"type": "keyword"},
                        "start_date": {"type": "date"},
                        "end_date": {"type": "date"},
                        "outcome": {"type": "keyword"},  # resigned | fired | company_failed
                    },
                },
                "nationalities": {"type": "keyword"},
                "countries_of_residence": {"type": "keyword"},
                "is_pep": {"type": "boolean"},  # Politically Exposed Person
                "pep_details": {"type": "text"},
                "is_sanctioned": {"type": "boolean"},
                "risk_flags": {"type": "keyword"},
                "risk_score": {"type": "float"},
                "bio_summary": {"type": "text"},
                "data_sources": {"type": "keyword"},
                "ingested_at": {"type": "date"},
            }
        },
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    },

    "meridian-investigations": {
        "mappings": {
            "properties": {
                "investigation_id": {"type": "keyword"},
                "target_name": {"type": "keyword"},
                "target_entity_id": {"type": "keyword"},
                "status": {"type": "keyword"},  # running | complete | error
                "started_at": {"type": "date"},
                "completed_at": {"type": "date"},
                "overall_risk_score": {"type": "float"},
                "risk_level": {"type": "keyword"},  # LOW | MEDIUM | HIGH | CRITICAL
                "agent_findings": {
                    "type": "nested",
                    "properties": {
                        "agent_name": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "findings": {"type": "text"},
                        "risk_contribution": {"type": "float"},
                        "red_flags": {"type": "keyword"},
                        "completed_at": {"type": "date"},
                    },
                },
                "summary": {"type": "text"},
                "red_flags": {"type": "keyword"},
                "recommended_actions": {"type": "text"},
                "report_url": {"type": "keyword"},
                "requested_by": {"type": "keyword"},
            }
        },
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    },
}


async def create_all_indices(es_client):
    """Create all Meridian indices if they don't exist."""
    for index_name, config in INDICES.items():
        exists = await es_client.indices.exists(index=index_name)
        if not exists:
            await es_client.indices.create(
                index=index_name,
                mappings=config["mappings"],
                settings=config["settings"],
            )
            print(f"  Created index: {index_name}")
        else:
            print(f"  Index already exists: {index_name}")
