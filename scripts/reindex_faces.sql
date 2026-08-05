-- Run after enough face enrollments exist
CREATE INDEX IF NOT EXISTS ix_face_embedding_cosine
ON face_biometrics
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
