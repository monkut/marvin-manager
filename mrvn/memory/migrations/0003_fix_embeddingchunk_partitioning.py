# Generated manually to fix EmbeddingChunk as partitioned table

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0004_add_tool_profiles_and_memory_search'),
        ('memory', '0002_add_pgvector_embeddings'),
    ]

    operations = [
        # Drop the incorrectly created regular table
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS memory_embeddingchunk CASCADE;",
            reverse_sql="",  # Will be recreated by the next statement
        ),
        # Recreate as partitioned table using raw SQL
        migrations.RunSQL(
            sql="""
            CREATE TABLE memory_embeddingchunk (
                id BIGSERIAL,
                agent_id BIGINT NOT NULL REFERENCES agents_agent(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
                source VARCHAR(20) NOT NULL DEFAULT 'message',
                source_id BIGINT NOT NULL,
                text TEXT NOT NULL,
                start_line INTEGER NOT NULL DEFAULT 0,
                end_line INTEGER NOT NULL DEFAULT 0,
                embedding vector(384) NOT NULL,
                embedding_model VARCHAR(100) NOT NULL DEFAULT 'all-MiniLM-L6-v2',
                content_hash VARCHAR(64) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                PRIMARY KEY (id, agent_id)
            ) PARTITION BY LIST (agent_id);
            """,
            reverse_sql="DROP TABLE IF EXISTS memory_embeddingchunk CASCADE;",
        ),
        # Create default partition for agents without specific partitions
        migrations.RunSQL(
            sql="""
            CREATE TABLE memory_embeddingchunk_default
            PARTITION OF memory_embeddingchunk DEFAULT;
            """,
            reverse_sql="DROP TABLE IF EXISTS memory_embeddingchunk_default;",
        ),
        # Create indexes
        migrations.RunSQL(
            sql="""
            CREATE INDEX memory_embeddingchunk_agent_id_idx
            ON memory_embeddingchunk (agent_id);
            """,
            reverse_sql="DROP INDEX IF EXISTS memory_embeddingchunk_agent_id_idx;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE INDEX memory_embeddingchunk_content_hash_idx
            ON memory_embeddingchunk (content_hash);
            """,
            reverse_sql="DROP INDEX IF EXISTS memory_embeddingchunk_content_hash_idx;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE INDEX memory_embe_agent_source_idx
            ON memory_embeddingchunk (agent_id, source, source_id);
            """,
            reverse_sql="DROP INDEX IF EXISTS memory_embe_agent_source_idx;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE INDEX memory_embe_agent_hash_idx
            ON memory_embeddingchunk (agent_id, content_hash);
            """,
            reverse_sql="DROP INDEX IF EXISTS memory_embe_agent_hash_idx;",
        ),
        # Create HNSW index for vector similarity search
        migrations.RunSQL(
            sql="""
            CREATE INDEX embedding_chunk_hnsw_idx
            ON memory_embeddingchunk
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
            """,
            reverse_sql="DROP INDEX IF EXISTS embedding_chunk_hnsw_idx;",
        ),
    ]
