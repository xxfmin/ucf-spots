CREATE TABLE feedback (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  feedback_text TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  user_agent TEXT,
  ip_address TEXT
);

CREATE INDEX idx_feedback_created_at ON feedback(created_at DESC);
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public inserts" ON feedback
  FOR INSERT
  TO public
  WITH CHECK (true);