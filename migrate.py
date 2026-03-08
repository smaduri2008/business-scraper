from app.database import get_session
from sqlalchemy import text

session = get_session()

try:
    session.execute(text('ALTER TABLE businesses ADD COLUMN IF NOT EXISTS job_id VARCHAR(50)'))
    session.execute(text('ALTER TABLE businesses ADD COLUMN IF NOT EXISTS position INTEGER'))
    session.execute(text('CREATE INDEX IF NOT EXISTS idx_businesses_job_id ON businesses(job_id)'))
    session.commit()
    print("✅ Database migration successful!")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    session.close()
