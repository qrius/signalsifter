# Telegram Crypto Channel Monitoring Bot — Design Summary

Purpose
- Passively monitor specified Telegram channels for crypto project announcements.
- Extract structured entities (projects, tokens, wallet addresses, dates).
- Summarize activity, identify contributors, and generate alerts.

Core components
- Ingestion: Telethon (MTProto) or Bot API for streaming messages.
- Queue: Redis Streams / RabbitMQ.
- Workers: Celery / FastAPI workers for processing (NER, OCR, embeddings).
- Storage: S3 for raw data, Postgres for metadata, Qdrant/Pinecone for embeddings.
- Analysis: spaCy + LLM extracts, BERTopic for topic modeling, sentence-transformers for embeddings.
- Interface: Telegram commands, optional web dashboard.

Key pipelines
- Deterministic extraction (regex) -> OCR -> LLM NER -> embeddings -> index -> alert rules.
- Summaries via LLM (batched per time window).
- On-chain verification via Etherscan/Alchemy for contract addresses.

Security & compliance
- Encrypt secrets; store only necessary PII; respect channel privacy/perms.

Milestones
- Week 0–6 plan from PoC to initial production as described in the main plan.

Next actions
- Answer clarifying questions in the primary message.
- I will generate starter code: Telethon ingestion + worker skeleton + sample LLM prompts and deployment Dockerfiles.