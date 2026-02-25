#!/usr/bin/env python3
"""
Comprehensive data ingestion for MERIDIAN.
Loads real data from SEC EDGAR + GDELT, plus rich synthetic data
for multiple companies across all risk levels.

Usage:
  python scripts/ingest_all.py                  # load everything
  python scripts/ingest_all.py --real-only       # only real data
  python scripts/ingest_all.py --synthetic-only  # only synthetic data
"""
import asyncio
import argparse
import sys
import os
import json
import hashlib
from datetime import datetime, timezone, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.elasticsearch.client import get_es_client, close_es_client
from src.elasticsearch.indices import create_all_indices
from src.ingestion.sec_edgar import ingest_company as ingest_sec
from src.ingestion.gdelt_news import ingest_company_news


# ═══════════════════════════════════════════════════════════════
#  REAL COMPANIES — SEC EDGAR + GDELT News
# ═══════════════════════════════════════════════════════════════

REAL_COMPANIES = [
    {"name": "Tesla, Inc.", "cik": "1318605", "search_name": "Tesla"},
    {"name": "Meta Platforms, Inc.", "cik": "1326801", "search_name": "Meta Platforms"},
    {"name": "Wells Fargo & Company", "cik": "72971", "search_name": "Wells Fargo"},
    {"name": "Boeing Company", "cik": "12927", "search_name": "Boeing"},
    {"name": "Goldman Sachs Group Inc", "cik": "886982", "search_name": "Goldman Sachs"},
    {"name": "ExxonMobil Corporation", "cik": "34088", "search_name": "ExxonMobil"},
]


async def ingest_real_data():
    """Ingest real company data from SEC EDGAR and GDELT."""
    print("\n" + "=" * 60)
    print("  INGESTING REAL DATA (SEC EDGAR + GDELT)")
    print("=" * 60)

    for company in REAL_COMPANIES:
        print(f"\n--- {company['name']} ---")

        entity_id = f"sec-{company['cik']}"

        # SEC EDGAR (filings + entity)
        try:
            print("  [SEC EDGAR] Fetching filings...")
            await ingest_sec(company["name"], company["cik"])
        except Exception as e:
            print(f"  [SEC EDGAR] Error: {e}")

        # GDELT News
        try:
            print("  [GDELT] Fetching news articles...")
            await ingest_company_news(company["search_name"], entity_id, max_articles=30)
        except Exception as e:
            print(f"  [GDELT] Error: {e}")

        # Small delay between companies to be polite to APIs
        await asyncio.sleep(1)


# ═══════════════════════════════════════════════════════════════
#  SYNTHETIC DATA — Multiple companies across risk levels
# ═══════════════════════════════════════════════════════════════

def _date(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT00:00:00Z")


def _rand_date(min_days: int, max_days: int) -> str:
    return _date(random.randint(min_days, max_days))


SYNTHETIC_COMPANIES = [
    # ── 1. NEXUS GLOBAL HOLDINGS (existing, enhance) ─────────
    {
        "entities": [
            {
                "entity_id": "nexus-001",
                "name": "Nexus Global Holdings Ltd",
                "aliases": ["Nexus Global", "NGH", "Nexus Holdings"],
                "entity_type": "company",
                "jurisdiction": "BVI",
                "status": "active",
                "country_code": "VG",
                "industry": "Financial Services",
                "risk_score": 8.5,
                "risk_flags": ["Offshore jurisdiction", "Complex ownership", "Shell company indicators"],
                "data_sources": ["OpenCorporates", "ICIJ Offshore Leaks"],
                "incorporation_date": "2014-03-15T00:00:00Z",
                "subsidiary_ids": ["nexus-002", "nexus-003", "nexus-004", "nexus-005"],
            },
            {
                "entity_id": "nexus-002",
                "name": "Nexus Financial Services LLC",
                "aliases": ["NFS"],
                "entity_type": "company",
                "jurisdiction": "Delaware",
                "status": "active",
                "country_code": "US",
                "parent_entity_id": "nexus-001",
                "industry": "Financial Services",
                "data_sources": ["SEC EDGAR"],
            },
            {
                "entity_id": "nexus-003",
                "name": "Nexus Panama S.A.",
                "aliases": ["Nexus Panama"],
                "entity_type": "company",
                "jurisdiction": "Panama",
                "status": "active",
                "country_code": "PA",
                "parent_entity_id": "nexus-001",
                "risk_score": 7.0,
                "risk_flags": ["Panama jurisdiction", "Limited transparency"],
                "data_sources": ["Panama Registry"],
            },
            {
                "entity_id": "nexus-004",
                "name": "Nexus Technology Ltd",
                "aliases": ["NexusTech"],
                "entity_type": "company",
                "jurisdiction": "Cayman Islands",
                "status": "active",
                "country_code": "KY",
                "parent_entity_id": "nexus-001",
                "risk_score": 6.0,
                "risk_flags": ["Tax haven"],
                "data_sources": ["Cayman Registry"],
            },
            {
                "entity_id": "nexus-005",
                "name": "Nexus Commodity Trading DMCC",
                "aliases": ["Nexus DMCC"],
                "entity_type": "company",
                "jurisdiction": "Dubai",
                "status": "active",
                "country_code": "AE",
                "parent_entity_id": "nexus-001",
                "industry": "Commodity Trading",
                "data_sources": ["DMCC Registry"],
            },
        ],
        "executives": [
            {
                "person_id": "nexus-exec-001",
                "full_name": "Viktor Oleg Marchenko",
                "aliases": ["V. Marchenko", "Viktor Marchenko"],
                "current_entity_id": "nexus-001",
                "current_title": "CEO & Chairman",
                "nationalities": ["Ukrainian", "Cypriot"],
                "countries_of_residence": ["Cyprus", "UAE"],
                "is_pep": True,
                "pep_details": "Former advisor to Ukrainian Ministry of Finance (2008-2012)",
                "is_sanctioned": False,
                "risk_score": 7.5,
                "risk_flags": ["PEP", "Previous company failure", "Dual nationality in tax haven"],
                "bio_summary": "Former energy sector executive with ties to Ukrainian oligarch circles. Previous venture Meridian Capital Partners collapsed in 2019 with $45M in losses and ongoing SEC investigation.",
                "employment_history": [
                    {"entity_name": "Nexus Global Holdings", "title": "CEO", "start_date": "2020-01-01"},
                    {"entity_name": "Meridian Capital Partners", "title": "Managing Director", "start_date": "2015-06-01", "end_date": "2019-11-30", "outcome": "company_failed"},
                    {"entity_name": "Eastern Energy Corp", "title": "VP Finance", "start_date": "2008-03-01", "end_date": "2015-05-30", "outcome": "resigned"},
                ],
                "data_sources": ["LinkedIn", "OpenSanctions", "SEC EDGAR"],
            },
            {
                "person_id": "nexus-exec-002",
                "full_name": "Anastasia Kovalenko",
                "aliases": ["A. Kovalenko"],
                "current_entity_id": "nexus-001",
                "current_title": "CFO",
                "nationalities": ["Russian", "Cypriot"],
                "countries_of_residence": ["Cyprus"],
                "is_pep": False,
                "is_sanctioned": False,
                "risk_score": 5.0,
                "risk_flags": ["Limited background available", "Russian nationality"],
                "bio_summary": "Limited public background. Appointed CFO in 2021 with no prior public company experience. Previously worked at small accounting firms in Limassol, Cyprus.",
                "data_sources": ["Company filings"],
            },
            {
                "person_id": "nexus-exec-003",
                "full_name": "James Robert Chen",
                "current_entity_id": "nexus-002",
                "current_title": "VP Operations (US)",
                "nationalities": ["American"],
                "countries_of_residence": ["United States"],
                "is_pep": False,
                "is_sanctioned": False,
                "risk_score": 2.0,
                "bio_summary": "Experienced operations executive with 20+ years in financial services. Clean regulatory record.",
                "data_sources": ["LinkedIn", "SEC EDGAR"],
            },
        ],
        "filings": [
            {"filing_id": "nexus-f001", "entity_id": "nexus-002", "entity_name": "Nexus Global Holdings", "filing_type": "10-K", "filing_date": "2025-03-15T00:00:00Z", "revenue": 45000000, "net_income": -12000000, "total_assets": 180000000, "total_debt": 95000000, "auditor": "Parker & Associates LLP", "auditor_opinion": "qualified", "going_concern": True, "restatement": False, "source": "SEC EDGAR"},
            {"filing_id": "nexus-f002", "entity_id": "nexus-002", "entity_name": "Nexus Global Holdings", "filing_type": "10-K", "filing_date": "2024-03-15T00:00:00Z", "revenue": 62000000, "net_income": -3000000, "total_assets": 200000000, "total_debt": 78000000, "auditor": "Deloitte", "auditor_opinion": "clean", "going_concern": False, "restatement": False, "source": "SEC EDGAR"},
            {"filing_id": "nexus-f003", "entity_id": "nexus-002", "entity_name": "Nexus Global Holdings", "filing_type": "10-K", "filing_date": "2023-03-15T00:00:00Z", "revenue": 58000000, "net_income": 5000000, "total_assets": 175000000, "total_debt": 55000000, "auditor": "Deloitte", "auditor_opinion": "clean", "going_concern": False, "restatement": True, "source": "SEC EDGAR"},
            {"filing_id": "nexus-f004", "entity_id": "nexus-002", "entity_name": "Nexus Global Holdings", "filing_type": "10-K", "filing_date": "2022-03-15T00:00:00Z", "revenue": 72000000, "net_income": 8500000, "total_assets": 165000000, "total_debt": 42000000, "auditor": "Deloitte", "auditor_opinion": "clean", "going_concern": False, "restatement": False, "source": "SEC EDGAR"},
        ],
        "legal": [
            {"case_id": "nexus-l001", "entity_ids": ["nexus-001"], "entity_names": ["Nexus Global Holdings"], "case_type": "regulatory", "case_name": "SEC v. Nexus Financial Services LLC", "case_summary": "SEC investigation into potential securities fraud and misrepresentation of financial statements in 2023-2024 annual reports. Alleged inflation of revenue by $18M through related-party transactions.", "jurisdiction": "US Federal", "court": "SDNY", "filed_date": "2025-06-10T00:00:00Z", "status": "active", "regulator": "SEC", "is_sanction": False, "source": "SEC EDGAR", "allegations": ["Securities fraud", "Misrepresentation", "Related party transactions"]},
            {"case_id": "nexus-l002", "entity_ids": ["nexus-003"], "entity_names": ["Nexus Panama S.A.", "Nexus Global Holdings"], "case_type": "civil", "case_name": "Meridian Capital Partners Investors v. Marchenko et al.", "case_summary": "Class action by former investors of Meridian Capital Partners alleging misappropriation of funds. Settlement of $8.5M reached but compliance disputed.", "jurisdiction": "BVI", "court": "BVI Commercial Court", "filed_date": "2020-02-15T00:00:00Z", "resolved_date": "2023-08-01T00:00:00Z", "status": "resolved", "outcome": "settled", "settlement_amount": 8500000, "is_sanction": False, "source": "Court Records", "allegations": ["Misappropriation", "Breach of fiduciary duty"]},
            {"case_id": "nexus-l003", "entity_ids": ["nexus-001"], "entity_names": ["Nexus Global Holdings"], "case_type": "regulatory", "case_name": "FCA Review of Nexus UK Operations", "case_summary": "UK Financial Conduct Authority opened review into Nexus subsidiary operations in London. Concerns about AML compliance and customer due diligence procedures.", "jurisdiction": "UK", "court": "FCA", "filed_date": "2025-09-01T00:00:00Z", "status": "active", "regulator": "FCA", "is_sanction": False, "source": "FCA Register", "allegations": ["AML compliance failure", "Inadequate KYC"]},
            {"case_id": "nexus-l004", "entity_ids": ["nexus-001"], "entity_names": ["Nexus Global Holdings"], "case_type": "criminal", "case_name": "DOJ Investigation: Nexus Commodity Trading", "case_summary": "Department of Justice investigation into potential money laundering through Nexus DMCC commodity trading operations in Dubai. Suspicious wire transfers totaling $120M identified.", "jurisdiction": "US Federal", "court": "DOJ", "filed_date": "2025-11-15T00:00:00Z", "status": "active", "regulator": "DOJ", "is_sanction": False, "source": "DOJ Press Release", "allegations": ["Money laundering", "Wire fraud", "Suspicious transactions"]},
        ],
        "news": [
            {"title": "Nexus Global Holdings Under SEC Investigation for Alleged Revenue Inflation", "source_name": "Financial Times", "sentiment_score": -0.85, "sentiment_label": "negative", "published_at": _date(15)},
            {"title": "Former Meridian Capital Investors Sue Nexus CEO Viktor Marchenko", "source_name": "Bloomberg", "sentiment_score": -0.92, "sentiment_label": "negative", "published_at": _date(45)},
            {"title": "Nexus Holdings Reports 27% Revenue Decline in Latest Annual Filing", "source_name": "Reuters", "sentiment_score": -0.6, "sentiment_label": "negative", "published_at": _date(60)},
            {"title": "DOJ Opens Money Laundering Probe into Nexus Dubai Operations", "source_name": "Wall Street Journal", "sentiment_score": -0.95, "sentiment_label": "negative", "published_at": _date(5)},
            {"title": "Nexus Global Switches Auditors from Deloitte to Small BVI Firm", "source_name": "Accounting Today", "sentiment_score": -0.7, "sentiment_label": "negative", "published_at": _date(90)},
            {"title": "UK FCA Launches Review of Nexus Financial Operations", "source_name": "Financial Times", "sentiment_score": -0.55, "sentiment_label": "negative", "published_at": _date(30)},
            {"title": "Nexus Technology Arm Expands Crypto Services Despite Regulatory Heat", "source_name": "CoinDesk", "sentiment_score": -0.3, "sentiment_label": "negative", "published_at": _date(20)},
            {"title": "Analysis: How Nexus Global Built a Complex Web of Offshore Entities", "source_name": "ICIJ", "sentiment_score": -0.8, "sentiment_label": "negative", "published_at": _date(120)},
        ],
    },

    # ── 2. AURORA HEALTH SYSTEMS (low-medium risk, clean company) ─────
    {
        "entities": [
            {
                "entity_id": "aurora-001",
                "name": "Aurora Health Systems Inc",
                "aliases": ["Aurora Health", "AHS", "Aurora Healthcare"],
                "entity_type": "company",
                "jurisdiction": "Delaware",
                "status": "active",
                "country_code": "US",
                "industry": "Healthcare",
                "risk_score": 2.0,
                "data_sources": ["SEC EDGAR", "OpenCorporates"],
                "incorporation_date": "2005-07-20T00:00:00Z",
                "subsidiary_ids": ["aurora-002", "aurora-003"],
            },
            {
                "entity_id": "aurora-002",
                "name": "Aurora Pharmaceuticals LLC",
                "entity_type": "company",
                "jurisdiction": "New Jersey",
                "status": "active",
                "country_code": "US",
                "parent_entity_id": "aurora-001",
                "industry": "Pharmaceuticals",
            },
            {
                "entity_id": "aurora-003",
                "name": "Aurora Clinical Research GmbH",
                "entity_type": "company",
                "jurisdiction": "Germany",
                "status": "active",
                "country_code": "DE",
                "parent_entity_id": "aurora-001",
                "industry": "Clinical Research",
            },
        ],
        "executives": [
            {
                "person_id": "aurora-exec-001",
                "full_name": "Dr. Sarah Mitchell",
                "current_entity_id": "aurora-001",
                "current_title": "CEO",
                "nationalities": ["American"],
                "countries_of_residence": ["United States"],
                "is_pep": False,
                "is_sanctioned": False,
                "risk_score": 1.0,
                "bio_summary": "Harvard Medical School graduate with 25 years in healthcare leadership. Previously SVP at Johnson & Johnson. Clean regulatory record, well-respected in the industry.",
                "data_sources": ["LinkedIn", "SEC EDGAR"],
            },
            {
                "person_id": "aurora-exec-002",
                "full_name": "Michael Chen",
                "current_entity_id": "aurora-001",
                "current_title": "CFO",
                "nationalities": ["American"],
                "countries_of_residence": ["United States"],
                "is_pep": False,
                "is_sanctioned": False,
                "risk_score": 1.0,
                "bio_summary": "Former Deloitte audit partner, 15 years in healthcare finance. CPA with spotless professional record.",
                "data_sources": ["LinkedIn", "SEC EDGAR"],
            },
        ],
        "filings": [
            {"filing_id": "aurora-f001", "entity_id": "aurora-001", "entity_name": "Aurora Health Systems", "filing_type": "10-K", "filing_date": "2025-02-28T00:00:00Z", "revenue": 2800000000, "net_income": 340000000, "total_assets": 5200000000, "total_debt": 800000000, "auditor": "KPMG", "auditor_opinion": "clean", "going_concern": False, "restatement": False, "source": "SEC EDGAR"},
            {"filing_id": "aurora-f002", "entity_id": "aurora-001", "entity_name": "Aurora Health Systems", "filing_type": "10-K", "filing_date": "2024-02-28T00:00:00Z", "revenue": 2500000000, "net_income": 290000000, "total_assets": 4800000000, "total_debt": 850000000, "auditor": "KPMG", "auditor_opinion": "clean", "going_concern": False, "restatement": False, "source": "SEC EDGAR"},
            {"filing_id": "aurora-f003", "entity_id": "aurora-001", "entity_name": "Aurora Health Systems", "filing_type": "10-K", "filing_date": "2023-02-28T00:00:00Z", "revenue": 2200000000, "net_income": 250000000, "total_assets": 4400000000, "total_debt": 900000000, "auditor": "KPMG", "auditor_opinion": "clean", "going_concern": False, "restatement": False, "source": "SEC EDGAR"},
        ],
        "legal": [
            {"case_id": "aurora-l001", "entity_ids": ["aurora-001"], "entity_names": ["Aurora Health Systems"], "case_type": "civil", "case_name": "Smith v. Aurora Health Systems", "case_summary": "Minor product liability claim regarding medical device. Settled for $150K, standard for industry.", "jurisdiction": "US Federal", "court": "NJ District Court", "filed_date": "2024-04-01T00:00:00Z", "resolved_date": "2025-01-15T00:00:00Z", "status": "resolved", "outcome": "settled", "settlement_amount": 150000, "is_sanction": False, "source": "Court Records"},
        ],
        "news": [
            {"title": "Aurora Health Systems Reports Record Revenue Growth in 2025", "source_name": "Reuters", "sentiment_score": 0.8, "sentiment_label": "positive", "published_at": _date(10)},
            {"title": "Aurora Pharmaceuticals Wins FDA Approval for Breakthrough Cancer Treatment", "source_name": "STAT News", "sentiment_score": 0.9, "sentiment_label": "positive", "published_at": _date(30)},
            {"title": "Aurora Health CEO Named Healthcare Leader of the Year", "source_name": "Modern Healthcare", "sentiment_score": 0.7, "sentiment_label": "positive", "published_at": _date(60)},
            {"title": "Aurora Health Expands German Clinical Research Operations", "source_name": "Financial Times", "sentiment_score": 0.5, "sentiment_label": "positive", "published_at": _date(90)},
            {"title": "Minor Product Recall at Aurora Pharmaceuticals; Company Acts Swiftly", "source_name": "Bloomberg", "sentiment_score": -0.2, "sentiment_label": "neutral", "published_at": _date(120)},
        ],
    },

    # ── 3. CRIMSON MERIDIAN CAPITAL (very high risk, fraud indicators) ─────
    {
        "entities": [
            {
                "entity_id": "crimson-001",
                "name": "Crimson Meridian Capital Group",
                "aliases": ["Crimson Meridian", "CMC Group", "Crimson Capital"],
                "entity_type": "company",
                "jurisdiction": "Marshall Islands",
                "status": "active",
                "country_code": "MH",
                "industry": "Investment Management",
                "risk_score": 9.5,
                "risk_flags": ["Marshall Islands registration", "Shell company network", "Sanctioned jurisdiction links", "No physical office"],
                "data_sources": ["ICIJ", "OpenSanctions"],
                "incorporation_date": "2019-11-01T00:00:00Z",
                "subsidiary_ids": ["crimson-002", "crimson-003", "crimson-004", "crimson-005", "crimson-006"],
            },
            {
                "entity_id": "crimson-002",
                "name": "Crimson Holdings Seychelles Ltd",
                "entity_type": "company",
                "jurisdiction": "Seychelles",
                "status": "active",
                "country_code": "SC",
                "parent_entity_id": "crimson-001",
                "risk_score": 8.0,
                "risk_flags": ["Secrecy jurisdiction"],
            },
            {
                "entity_id": "crimson-003",
                "name": "Crimson Trade FZE",
                "entity_type": "company",
                "jurisdiction": "Dubai",
                "status": "active",
                "country_code": "AE",
                "parent_entity_id": "crimson-001",
                "industry": "Trading",
            },
            {
                "entity_id": "crimson-004",
                "name": "Red Star Investments Ltd",
                "entity_type": "company",
                "jurisdiction": "BVI",
                "status": "active",
                "country_code": "VG",
                "parent_entity_id": "crimson-001",
                "risk_score": 9.0,
                "risk_flags": ["BVI shell company", "Nominee directors only"],
            },
            {
                "entity_id": "crimson-005",
                "name": "Crimson Digital Assets AG",
                "entity_type": "company",
                "jurisdiction": "Switzerland",
                "status": "active",
                "country_code": "CH",
                "parent_entity_id": "crimson-001",
                "industry": "Cryptocurrency",
            },
            {
                "entity_id": "crimson-006",
                "name": "CMC Cyprus Services Ltd",
                "entity_type": "company",
                "jurisdiction": "Cyprus",
                "status": "suspended",
                "country_code": "CY",
                "parent_entity_id": "crimson-001",
                "risk_score": 7.0,
                "risk_flags": ["Suspended entity", "Cyprus license revoked"],
            },
        ],
        "executives": [
            {
                "person_id": "crimson-exec-001",
                "full_name": "Dmitri Volkov",
                "aliases": ["Dmitriy Volkov", "D. Volkov"],
                "current_entity_id": "crimson-001",
                "current_title": "Founder & Managing Director",
                "nationalities": ["Russian"],
                "countries_of_residence": ["UAE", "Montenegro"],
                "is_pep": True,
                "pep_details": "Former deputy to sanctioned Russian oligarch. Connected to Kremlin-linked entities through multiple shell companies.",
                "is_sanctioned": False,
                "risk_score": 9.5,
                "risk_flags": ["PEP", "Oligarch connections", "Sanctions evasion concerns", "Three previous company failures", "SEC enforcement target"],
                "bio_summary": "Russian financier with deep connections to sanctioned oligarch networks. Three previous companies collapsed under fraud allegations. Subject of FBI and Europol investigations.",
                "employment_history": [
                    {"entity_name": "Crimson Meridian Capital", "title": "Founder", "start_date": "2019-11-01"},
                    {"entity_name": "Volkov Capital Partners", "title": "CEO", "start_date": "2016-01-01", "end_date": "2019-06-30", "outcome": "company_failed"},
                    {"entity_name": "EuroTrade Global", "title": "Director", "start_date": "2012-06-01", "end_date": "2015-12-31", "outcome": "company_failed"},
                    {"entity_name": "Baltic Investment Group", "title": "VP", "start_date": "2008-01-01", "end_date": "2012-05-30", "outcome": "fired"},
                ],
                "data_sources": ["Interpol", "ICIJ", "OpenSanctions", "FBI"],
            },
            {
                "person_id": "crimson-exec-002",
                "full_name": "Hassan Al-Rashid",
                "current_entity_id": "crimson-003",
                "current_title": "Director, Dubai Operations",
                "nationalities": ["Emirati", "Lebanese"],
                "countries_of_residence": ["UAE"],
                "is_pep": False,
                "is_sanctioned": False,
                "risk_score": 6.0,
                "risk_flags": ["Known associate of sanctioned individuals"],
                "bio_summary": "Dubai-based trader with connections to sanctioned networks in the Middle East.",
                "data_sources": ["Company filings"],
            },
        ],
        "filings": [
            {"filing_id": "crimson-f001", "entity_id": "crimson-001", "entity_name": "Crimson Meridian Capital", "filing_type": "annual", "filing_date": "2025-06-30T00:00:00Z", "revenue": 180000000, "net_income": 45000000, "total_assets": 520000000, "total_debt": 340000000, "auditor": "Island Audit Services", "auditor_opinion": "qualified", "going_concern": True, "restatement": True, "source": "Marshall Islands Registry"},
            {"filing_id": "crimson-f002", "entity_id": "crimson-001", "entity_name": "Crimson Meridian Capital", "filing_type": "annual", "filing_date": "2024-06-30T00:00:00Z", "revenue": 310000000, "net_income": 89000000, "total_assets": 680000000, "total_debt": 290000000, "auditor": "PricewaterhouseCoopers", "auditor_opinion": "clean", "going_concern": False, "restatement": False, "source": "Company filing"},
            {"filing_id": "crimson-f003", "entity_id": "crimson-001", "entity_name": "Crimson Meridian Capital", "filing_type": "annual", "filing_date": "2023-06-30T00:00:00Z", "revenue": 290000000, "net_income": 75000000, "total_assets": 600000000, "total_debt": 250000000, "auditor": "PricewaterhouseCoopers", "auditor_opinion": "clean", "going_concern": False, "restatement": False, "source": "Company filing"},
        ],
        "legal": [
            {"case_id": "crimson-l001", "entity_ids": ["crimson-001"], "entity_names": ["Crimson Meridian Capital", "Crimson Meridian Capital Group"], "case_type": "criminal", "case_name": "DOJ v. Crimson Meridian Capital Group", "case_summary": "Federal indictment for wire fraud, money laundering, and sanctions evasion. Alleged $250M in illicit funds moved through shell company network spanning Marshall Islands, Seychelles, and BVI.", "jurisdiction": "US Federal", "court": "SDNY", "filed_date": "2025-08-15T00:00:00Z", "status": "active", "regulator": "DOJ", "is_sanction": False, "penalty_amount": 0, "source": "DOJ Press Release", "allegations": ["Wire fraud", "Money laundering", "Sanctions evasion"]},
            {"case_id": "crimson-l002", "entity_ids": ["crimson-001"], "entity_names": ["Crimson Meridian Capital", "Dmitri Volkov"], "case_type": "regulatory", "case_name": "SEC Enforcement: Crimson Digital Assets", "case_summary": "SEC charges Crimson Digital Assets with operating unregistered securities exchange. $50M in investor funds allegedly misappropriated through cryptocurrency schemes.", "jurisdiction": "US Federal", "court": "SEC", "filed_date": "2025-10-01T00:00:00Z", "status": "active", "regulator": "SEC", "penalty_amount": 50000000, "is_sanction": False, "source": "SEC EDGAR", "allegations": ["Unregistered securities", "Investor fraud", "Cryptocurrency fraud"]},
            {"case_id": "crimson-l003", "entity_ids": ["crimson-006"], "entity_names": ["CMC Cyprus Services", "Crimson Meridian Capital"], "case_type": "regulatory", "case_name": "CySEC License Revocation: CMC Cyprus", "case_summary": "Cyprus Securities and Exchange Commission revoked CMC Cyprus license for repeated AML violations, failure to report suspicious transactions, and providing false information to regulators.", "jurisdiction": "Cyprus", "court": "CySEC", "filed_date": "2025-04-01T00:00:00Z", "resolved_date": "2025-07-15T00:00:00Z", "status": "resolved", "outcome": "judgment_plaintiff", "penalty_amount": 2500000, "regulator": "CySEC", "is_sanction": False, "source": "CySEC Register", "allegations": ["AML violations", "False reporting", "License violations"]},
            {"case_id": "crimson-l004", "entity_ids": ["crimson-001"], "entity_names": ["Crimson Meridian Capital", "Red Star Investments"], "case_type": "sanction", "case_name": "OFAC Advisory: Crimson-Linked Entities", "case_summary": "OFAC issued advisory warning about Red Star Investments potential connections to sanctioned Russian entities. Ongoing investigation into sanctions circumvention.", "jurisdiction": "US", "court": "OFAC", "filed_date": "2025-12-01T00:00:00Z", "status": "active", "is_sanction": True, "sanction_list": "OFAC", "source": "US Treasury", "allegations": ["Sanctions circumvention", "Russian entity links"]},
        ],
        "news": [
            {"title": "DOJ Indicts Crimson Meridian Capital for $250M Money Laundering Scheme", "source_name": "Reuters", "sentiment_score": -0.98, "sentiment_label": "negative", "published_at": _date(3)},
            {"title": "FBI Raids Dubai Offices of Crimson Trade in International Fraud Probe", "source_name": "Bloomberg", "sentiment_score": -0.95, "sentiment_label": "negative", "published_at": _date(10)},
            {"title": "SEC Charges Crimson Digital Assets with $50M Cryptocurrency Fraud", "source_name": "Wall Street Journal", "sentiment_score": -0.9, "sentiment_label": "negative", "published_at": _date(25)},
            {"title": "Cyprus Regulator Revokes License of Crimson Meridian Subsidiary", "source_name": "Financial Times", "sentiment_score": -0.75, "sentiment_label": "negative", "published_at": _date(50)},
            {"title": "Investigative Report: Crimson Meridian's Web of Shell Companies", "source_name": "ICIJ", "sentiment_score": -0.88, "sentiment_label": "negative", "published_at": _date(80)},
            {"title": "Former Crimson Employees Allege Systematic Fraud in Whistleblower Filing", "source_name": "Politico", "sentiment_score": -0.85, "sentiment_label": "negative", "published_at": _date(40)},
            {"title": "Crimson Meridian Founder Volkov Linked to Sanctioned Russian Oligarch", "source_name": "The Guardian", "sentiment_score": -0.92, "sentiment_label": "negative", "published_at": _date(65)},
        ],
    },

    # ── 4. OMNIVAULT TECHNOLOGIES (medium risk, fintech) ─────
    {
        "entities": [
            {
                "entity_id": "omnivault-001",
                "name": "OmniVault Technologies Inc",
                "aliases": ["OmniVault", "OmniVault Tech", "OVT"],
                "entity_type": "company",
                "jurisdiction": "Delaware",
                "status": "active",
                "country_code": "US",
                "industry": "Financial Technology",
                "risk_score": 4.5,
                "data_sources": ["SEC EDGAR", "Crunchbase"],
                "incorporation_date": "2018-03-10T00:00:00Z",
                "subsidiary_ids": ["omnivault-002", "omnivault-003"],
            },
            {
                "entity_id": "omnivault-002",
                "name": "OmniVault Digital Ltd",
                "entity_type": "company",
                "jurisdiction": "Singapore",
                "status": "active",
                "country_code": "SG",
                "parent_entity_id": "omnivault-001",
                "industry": "Cryptocurrency Exchange",
            },
            {
                "entity_id": "omnivault-003",
                "name": "OmniVault EU B.V.",
                "entity_type": "company",
                "jurisdiction": "Netherlands",
                "status": "active",
                "country_code": "NL",
                "parent_entity_id": "omnivault-001",
                "industry": "Payment Processing",
            },
        ],
        "executives": [
            {
                "person_id": "omnivault-exec-001",
                "full_name": "Alex Rivera",
                "current_entity_id": "omnivault-001",
                "current_title": "CEO & Co-Founder",
                "nationalities": ["American"],
                "countries_of_residence": ["United States"],
                "is_pep": False,
                "is_sanctioned": False,
                "risk_score": 3.0,
                "bio_summary": "Stanford CS graduate, former engineer at Square and Coinbase. Founded OmniVault in 2018. No regulatory issues, active in fintech advocacy.",
                "data_sources": ["LinkedIn", "Crunchbase"],
            },
        ],
        "filings": [
            {"filing_id": "omnivault-f001", "entity_id": "omnivault-001", "entity_name": "OmniVault Technologies", "filing_type": "10-K", "filing_date": "2025-03-30T00:00:00Z", "revenue": 420000000, "net_income": 28000000, "total_assets": 1800000000, "total_debt": 200000000, "auditor": "Ernst & Young", "auditor_opinion": "clean", "going_concern": False, "restatement": False, "source": "SEC EDGAR"},
            {"filing_id": "omnivault-f002", "entity_id": "omnivault-001", "entity_name": "OmniVault Technologies", "filing_type": "10-K", "filing_date": "2024-03-30T00:00:00Z", "revenue": 350000000, "net_income": -15000000, "total_assets": 1600000000, "total_debt": 180000000, "auditor": "Ernst & Young", "auditor_opinion": "clean", "going_concern": False, "restatement": False, "source": "SEC EDGAR"},
            {"filing_id": "omnivault-f003", "entity_id": "omnivault-001", "entity_name": "OmniVault Technologies", "filing_type": "10-K", "filing_date": "2023-03-30T00:00:00Z", "revenue": 280000000, "net_income": -45000000, "total_assets": 1200000000, "total_debt": 150000000, "auditor": "Ernst & Young", "auditor_opinion": "clean", "going_concern": False, "restatement": False, "source": "SEC EDGAR"},
        ],
        "legal": [
            {"case_id": "omnivault-l001", "entity_ids": ["omnivault-001"], "entity_names": ["OmniVault Technologies"], "case_type": "regulatory", "case_name": "CFPB Investigation: OmniVault Consumer Practices", "case_summary": "Consumer Financial Protection Bureau reviewing OmniVault's lending practices for potential predatory lending in underserved communities.", "jurisdiction": "US Federal", "court": "CFPB", "filed_date": "2025-05-20T00:00:00Z", "status": "active", "regulator": "CFPB", "is_sanction": False, "source": "CFPB", "allegations": ["Predatory lending concerns"]},
            {"case_id": "omnivault-l002", "entity_ids": ["omnivault-002"], "entity_names": ["OmniVault Digital", "OmniVault Technologies"], "case_type": "regulatory", "case_name": "MAS Review: OmniVault Digital Singapore", "case_summary": "Monetary Authority of Singapore reviewing cryptocurrency exchange compliance. Standard review, no enforcement action yet.", "jurisdiction": "Singapore", "court": "MAS", "filed_date": "2025-08-01T00:00:00Z", "status": "active", "regulator": "MAS", "is_sanction": False, "source": "MAS Register", "allegations": ["Crypto compliance review"]},
        ],
        "news": [
            {"title": "OmniVault Technologies Reports First Profitable Year Since Founding", "source_name": "TechCrunch", "sentiment_score": 0.75, "sentiment_label": "positive", "published_at": _date(15)},
            {"title": "OmniVault Raises $200M Series D to Expand Global Payments", "source_name": "Bloomberg", "sentiment_score": 0.8, "sentiment_label": "positive", "published_at": _date(45)},
            {"title": "CFPB Opens Review Into OmniVault Lending Practices", "source_name": "American Banker", "sentiment_score": -0.5, "sentiment_label": "negative", "published_at": _date(60)},
            {"title": "OmniVault Partners with Visa for Cross-Border Payment Solution", "source_name": "Reuters", "sentiment_score": 0.6, "sentiment_label": "positive", "published_at": _date(30)},
            {"title": "Singapore Regulator Reviews OmniVault Crypto Exchange Operations", "source_name": "CoinDesk", "sentiment_score": -0.3, "sentiment_label": "negative", "published_at": _date(20)},
        ],
    },

    # ── 5. ZENITH DEFENSE SOLUTIONS (medium-high risk, defense) ─────
    {
        "entities": [
            {
                "entity_id": "zenith-001",
                "name": "Zenith Defense Solutions Corp",
                "aliases": ["Zenith Defense", "ZDS", "Zenith Solutions"],
                "entity_type": "company",
                "jurisdiction": "Virginia",
                "status": "active",
                "country_code": "US",
                "industry": "Defense & Aerospace",
                "risk_score": 5.5,
                "data_sources": ["SEC EDGAR", "FPDS"],
                "incorporation_date": "2001-09-01T00:00:00Z",
                "subsidiary_ids": ["zenith-002", "zenith-003", "zenith-004"],
            },
            {
                "entity_id": "zenith-002",
                "name": "Zenith Cybersecurity Ltd",
                "entity_type": "company",
                "jurisdiction": "Israel",
                "status": "active",
                "country_code": "IL",
                "parent_entity_id": "zenith-001",
                "industry": "Cybersecurity",
            },
            {
                "entity_id": "zenith-003",
                "name": "Zenith Logistics Saudi Arabia",
                "entity_type": "company",
                "jurisdiction": "Saudi Arabia",
                "status": "active",
                "country_code": "SA",
                "parent_entity_id": "zenith-001",
                "industry": "Defense Logistics",
                "risk_score": 5.0,
                "risk_flags": ["Arms export concerns"],
            },
            {
                "entity_id": "zenith-004",
                "name": "Zenith UAV Systems Pty",
                "entity_type": "company",
                "jurisdiction": "Australia",
                "status": "active",
                "country_code": "AU",
                "parent_entity_id": "zenith-001",
                "industry": "Drone Technology",
            },
        ],
        "executives": [
            {
                "person_id": "zenith-exec-001",
                "full_name": "General (Ret.) Robert Hayes",
                "current_entity_id": "zenith-001",
                "current_title": "CEO",
                "nationalities": ["American"],
                "countries_of_residence": ["United States"],
                "is_pep": True,
                "pep_details": "Former US Army Lieutenant General. Served on Senate Armed Services Committee as advisor 2015-2018.",
                "is_sanctioned": False,
                "risk_score": 4.0,
                "risk_flags": ["PEP - Revolving door military-industry"],
                "bio_summary": "Retired Lieutenant General with 30 years of service. Moved directly from Pentagon advisory role to defense contractor CEO. Known for aggressive international sales strategies.",
                "data_sources": ["LinkedIn", "FPDS", "Congressional Records"],
            },
            {
                "person_id": "zenith-exec-002",
                "full_name": "David Cohen",
                "current_entity_id": "zenith-002",
                "current_title": "CTO & Head of Israel Operations",
                "nationalities": ["Israeli", "American"],
                "countries_of_residence": ["Israel"],
                "is_pep": False,
                "is_sanctioned": False,
                "risk_score": 2.5,
                "bio_summary": "Former Unit 8200 member, cybersecurity expert. Founded Zenith Cybersecurity after 10 years in Israeli intelligence.",
                "data_sources": ["LinkedIn"],
            },
        ],
        "filings": [
            {"filing_id": "zenith-f001", "entity_id": "zenith-001", "entity_name": "Zenith Defense Solutions", "filing_type": "10-K", "filing_date": "2025-03-01T00:00:00Z", "revenue": 1500000000, "net_income": 120000000, "total_assets": 3200000000, "total_debt": 600000000, "auditor": "Deloitte", "auditor_opinion": "clean", "going_concern": False, "restatement": False, "source": "SEC EDGAR"},
            {"filing_id": "zenith-f002", "entity_id": "zenith-001", "entity_name": "Zenith Defense Solutions", "filing_type": "10-K", "filing_date": "2024-03-01T00:00:00Z", "revenue": 1350000000, "net_income": 95000000, "total_assets": 2900000000, "total_debt": 550000000, "auditor": "Deloitte", "auditor_opinion": "clean", "going_concern": False, "restatement": False, "source": "SEC EDGAR"},
        ],
        "legal": [
            {"case_id": "zenith-l001", "entity_ids": ["zenith-001"], "entity_names": ["Zenith Defense Solutions"], "case_type": "regulatory", "case_name": "DOD Inspector General: Zenith Cost Overruns", "case_summary": "Department of Defense IG investigation into $80M in cost overruns on Project Sentinel drone program. Allegations of inflated contractor billing.", "jurisdiction": "US Federal", "court": "DOD IG", "filed_date": "2025-01-15T00:00:00Z", "status": "active", "regulator": "DOD", "is_sanction": False, "source": "DOD IG Report", "allegations": ["Cost overruns", "Inflated billing"]},
            {"case_id": "zenith-l002", "entity_ids": ["zenith-003"], "entity_names": ["Zenith Logistics Saudi Arabia", "Zenith Defense Solutions"], "case_type": "regulatory", "case_name": "State Dept Review: Saudi Arms Export Compliance", "case_summary": "State Department reviewing whether Zenith properly obtained export licenses for advanced surveillance equipment sold to Saudi Arabia.", "jurisdiction": "US Federal", "court": "State Department", "filed_date": "2025-06-01T00:00:00Z", "status": "active", "regulator": "State Department", "is_sanction": False, "source": "State Dept", "allegations": ["Export control compliance", "Arms export concerns"]},
            {"case_id": "zenith-l003", "entity_ids": ["zenith-001"], "entity_names": ["Zenith Defense Solutions"], "case_type": "civil", "case_name": "Whistleblower v. Zenith Defense Solutions", "case_summary": "Former employee alleges retaliation after reporting concerns about foreign bribery in Middle East contracts.", "jurisdiction": "US Federal", "court": "E.D. Virginia", "filed_date": "2024-11-01T00:00:00Z", "status": "active", "is_sanction": False, "source": "Court Records", "allegations": ["Whistleblower retaliation", "FCPA concerns"]},
        ],
        "news": [
            {"title": "Zenith Defense Wins $800M Pentagon Drone Contract", "source_name": "Defense News", "sentiment_score": 0.6, "sentiment_label": "positive", "published_at": _date(20)},
            {"title": "DOD Inspector General Probes Zenith for $80M Cost Overruns", "source_name": "Washington Post", "sentiment_score": -0.65, "sentiment_label": "negative", "published_at": _date(40)},
            {"title": "State Department Reviews Zenith Saudi Arms Exports", "source_name": "Reuters", "sentiment_score": -0.5, "sentiment_label": "negative", "published_at": _date(55)},
            {"title": "Former Zenith Employee Files Whistleblower Suit Alleging Foreign Bribery", "source_name": "Politico", "sentiment_score": -0.7, "sentiment_label": "negative", "published_at": _date(90)},
            {"title": "Zenith Cybersecurity Unit Doubles Revenue Amid Global Threat Surge", "source_name": "Bloomberg", "sentiment_score": 0.5, "sentiment_label": "positive", "published_at": _date(30)},
            {"title": "Analysis: The Military-Industrial Revolving Door at Zenith Defense", "source_name": "The Intercept", "sentiment_score": -0.6, "sentiment_label": "negative", "published_at": _date(75)},
        ],
    },

    # ── 6. PACIFIC RIM TRADING CO (high risk, sanctions proximity) ─────
    {
        "entities": [
            {
                "entity_id": "pacific-001",
                "name": "Pacific Rim Trading Company",
                "aliases": ["Pacific Rim Trading", "PRTC", "Pacific Trading"],
                "entity_type": "company",
                "jurisdiction": "Hong Kong",
                "status": "active",
                "country_code": "HK",
                "industry": "International Trade",
                "risk_score": 7.0,
                "risk_flags": ["North Korea trade route proximity", "Iran-linked transactions"],
                "data_sources": ["HKICRIS", "OFAC Advisory"],
                "incorporation_date": "2010-06-15T00:00:00Z",
                "subsidiary_ids": ["pacific-002", "pacific-003"],
            },
            {
                "entity_id": "pacific-002",
                "name": "Pacific Rim Shipping Pte",
                "entity_type": "company",
                "jurisdiction": "Singapore",
                "status": "active",
                "country_code": "SG",
                "parent_entity_id": "pacific-001",
                "industry": "Shipping",
                "risk_score": 8.0,
                "risk_flags": ["Ship-to-ship transfers in sanctioned waters"],
            },
            {
                "entity_id": "pacific-003",
                "name": "Pacific Commodities Myanmar Ltd",
                "entity_type": "company",
                "jurisdiction": "Myanmar",
                "status": "active",
                "country_code": "MM",
                "parent_entity_id": "pacific-001",
                "industry": "Commodity Trading",
                "risk_score": 9.0,
                "risk_flags": ["Myanmar sanctioned regime", "Military junta connections"],
            },
        ],
        "executives": [
            {
                "person_id": "pacific-exec-001",
                "full_name": "Chen Wei Lin",
                "current_entity_id": "pacific-001",
                "current_title": "Chairman",
                "nationalities": ["Hong Kong", "Malaysian"],
                "countries_of_residence": ["Hong Kong", "Malaysia"],
                "is_pep": False,
                "is_sanctioned": False,
                "risk_score": 6.0,
                "risk_flags": ["Linked to entities in DPRK trade networks"],
                "bio_summary": "Hong Kong trader with 30 years in commodities. UN Panel of Experts mentioned his shipping networks in 2022 DPRK sanctions compliance report.",
                "data_sources": ["UN Panel of Experts", "Company filings"],
            },
        ],
        "filings": [
            {"filing_id": "pacific-f001", "entity_id": "pacific-001", "entity_name": "Pacific Rim Trading", "filing_type": "annual", "filing_date": "2025-04-30T00:00:00Z", "revenue": 890000000, "net_income": 35000000, "total_assets": 450000000, "total_debt": 280000000, "auditor": "HK Audit Services", "auditor_opinion": "qualified", "going_concern": False, "restatement": False, "source": "HKICRIS"},
        ],
        "legal": [
            {"case_id": "pacific-l001", "entity_ids": ["pacific-001"], "entity_names": ["Pacific Rim Trading"], "case_type": "sanction", "case_name": "OFAC Alert: Pacific Rim Trading Connections", "case_summary": "OFAC advisory regarding potential DPRK sanctions violations through ship-to-ship coal transfers. Investigation ongoing.", "jurisdiction": "US", "status": "active", "is_sanction": True, "sanction_list": "OFAC", "source": "US Treasury", "allegations": ["DPRK sanctions violations", "Ship-to-ship transfers"]},
            {"case_id": "pacific-l002", "entity_ids": ["pacific-003"], "entity_names": ["Pacific Commodities Myanmar", "Pacific Rim Trading"], "case_type": "sanction", "case_name": "EU Sanctions: Myanmar Military-Linked Entities", "case_summary": "EU sanctions package targeting entities connected to Myanmar military junta. Pacific Commodities Myanmar identified as supplier to military-controlled mining operations.", "jurisdiction": "EU", "status": "active", "is_sanction": True, "sanction_list": "EU", "source": "EU Council", "allegations": ["Myanmar military support", "Sanctioned regime dealings"]},
        ],
        "news": [
            {"title": "UN Report Links Pacific Rim Trading to North Korean Coal Shipments", "source_name": "Reuters", "sentiment_score": -0.9, "sentiment_label": "negative", "published_at": _date(30)},
            {"title": "Pacific Rim Shipping Vessels Detected in Sanctioned Waters Near DPRK", "source_name": "Financial Times", "sentiment_score": -0.85, "sentiment_label": "negative", "published_at": _date(45)},
            {"title": "EU Sanctions Hit Pacific Rim's Myanmar Operations", "source_name": "Bloomberg", "sentiment_score": -0.7, "sentiment_label": "negative", "published_at": _date(60)},
            {"title": "Hong Kong Regulator Questions Pacific Rim Trading Compliance", "source_name": "South China Morning Post", "sentiment_score": -0.55, "sentiment_label": "negative", "published_at": _date(15)},
        ],
    },
]


async def ingest_synthetic_data():
    """Load rich synthetic data for multiple companies."""
    print("\n" + "=" * 60)
    print("  LOADING SYNTHETIC DATA")
    print("=" * 60)

    es = get_es_client()
    now = datetime.now(timezone.utc).isoformat()

    for company in SYNTHETIC_COMPANIES:
        company_name = company["entities"][0]["name"]
        print(f"\n--- {company_name} ---")

        # Entities
        for entity in company.get("entities", []):
            entity["ingested_at"] = now
            entity["updated_at"] = now
            await es.index(
                index="meridian-entities",
                id=entity["entity_id"],
                document=entity,
            )
        print(f"  Loaded {len(company.get('entities', []))} entities")

        # Executives
        for exec_data in company.get("executives", []):
            exec_data["ingested_at"] = now
            await es.index(
                index="meridian-executives",
                id=exec_data["person_id"],
                document=exec_data,
            )
        print(f"  Loaded {len(company.get('executives', []))} executives")

        # Filings
        for filing in company.get("filings", []):
            filing["ingested_at"] = now
            await es.index(
                index="meridian-filings",
                id=filing["filing_id"],
                document=filing,
            )
        print(f"  Loaded {len(company.get('filings', []))} filings")

        # Legal cases
        for case in company.get("legal", []):
            case["ingested_at"] = now
            await es.index(
                index="meridian-legal",
                id=case["case_id"],
                document=case,
            )
        print(f"  Loaded {len(company.get('legal', []))} legal cases")

        # News articles
        for i, article in enumerate(company.get("news", [])):
            entity_id = company["entities"][0]["entity_id"]
            article_id = hashlib.md5(f"{company_name}-{i}".encode()).hexdigest()
            doc = {
                "article_id": article_id,
                "entity_ids": [entity_id],
                "entity_names": [company_name, company["entities"][0].get("aliases", [""])[0]],
                "title": article["title"],
                "content": article["title"],
                "source_name": article["source_name"],
                "source_url": f"https://{article['source_name'].lower().replace(' ', '')}.com/article/{article_id[:8]}",
                "published_at": article["published_at"],
                "sentiment_score": article["sentiment_score"],
                "sentiment_label": article["sentiment_label"],
                "language": "English",
                "ingested_at": now,
            }
            await es.index(
                index="meridian-news",
                id=article_id,
                document=doc,
            )
        print(f"  Loaded {len(company.get('news', []))} news articles")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="Comprehensive MERIDIAN data ingestion")
    parser.add_argument("--real-only", action="store_true", help="Only ingest real API data")
    parser.add_argument("--synthetic-only", action="store_true", help="Only load synthetic data")
    args = parser.parse_args()

    es = get_es_client()
    try:
        info = await es.info()
        print(f"Connected to Elasticsearch {info['version']['number']}")
    except Exception as e:
        print(f"Failed to connect to Elasticsearch: {e}")
        sys.exit(1)

    await create_all_indices(es)

    if not args.real_only:
        await ingest_synthetic_data()

    if not args.synthetic_only:
        await ingest_real_data()

    # Final counts
    print("\n" + "=" * 60)
    print("  FINAL INDEX COUNTS")
    print("=" * 60)
    for idx in ["meridian-entities", "meridian-filings", "meridian-legal",
                "meridian-news", "meridian-executives", "meridian-investigations"]:
        try:
            count = await es.count(index=idx)
            print(f"  {idx}: {count['count']} documents")
        except Exception:
            print(f"  {idx}: (error counting)")

    await close_es_client()
    print("\nIngestion complete!")


if __name__ == "__main__":
    asyncio.run(main())
