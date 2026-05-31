PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  source_type TEXT NOT NULL UNIQUE,
  enabled INTEGER NOT NULL DEFAULT 1,
  last_synced_at TEXT
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL UNIQUE,
  pdf_url TEXT,
  fda_center TEXT,
  status TEXT NOT NULL DEFAULT 'unknown',
  topic TEXT,
  published_date TEXT,
  last_checked_at TEXT,
  content_hash TEXT NOT NULL,
  is_new INTEGER NOT NULL DEFAULT 0,
  is_updated INTEGER NOT NULL DEFAULT 0,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_versions (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  raw_text_snapshot TEXT,
  detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  change_type TEXT NOT NULL,
  FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sync_runs (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  source_type TEXT,
  items_found INTEGER NOT NULL DEFAULT 0,
  items_new INTEGER NOT NULL DEFAULT 0,
  items_updated INTEGER NOT NULL DEFAULT 0,
  error_message TEXT
);

CREATE TABLE IF NOT EXISTS supporting_documents (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  file_url TEXT,
  file_type TEXT,
  source_page_url TEXT NOT NULL,
  detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  content_hash TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
  UNIQUE(document_id, url)
);

CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_center ON documents(fda_center);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_published_date ON documents(published_date);
CREATE INDEX IF NOT EXISTS idx_documents_flags ON documents(is_new, is_updated);
CREATE INDEX IF NOT EXISTS idx_versions_document_id ON document_versions(document_id);
CREATE INDEX IF NOT EXISTS idx_sync_runs_started_at ON sync_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_supporting_documents_document_id ON supporting_documents(document_id);
CREATE INDEX IF NOT EXISTS idx_supporting_documents_type ON supporting_documents(type);

INSERT OR IGNORE INTO sources (id, name, url, source_type, enabled)
VALUES
  ('src_guidance', 'FDA Guidance Documents', 'https://www.fda.gov/regulatory-information/search-fda-guidance-documents', 'guidance', 1),
  ('src_press', 'FDA Press Announcements', 'https://www.fda.gov/news-events/fda-newsroom/press-announcements', 'press', 1),
  ('src_approvals', 'Approved Cellular and Gene Therapy Products', 'https://www.fda.gov/vaccines-blood-biologics/cellular-gene-therapy-products/approved-cellular-and-gene-therapy-products', 'approval', 1),
  ('src_advisory', 'Advisory Committees', 'TODO_PHASE_2', 'advisory', 0),
  ('src_oce_publications', 'OCE Publications', 'TODO_PHASE_2', 'oce_publication', 0),
  ('src_otp_events', 'OTP Events', 'TODO_PHASE_2', 'otp_event', 0),
  ('src_otp_learn', 'OTP Learn', 'TODO_PHASE_2', 'otp_learn', 0);
