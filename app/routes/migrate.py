from flask import Blueprint, jsonify
from app.database import get_session
from sqlalchemy import text

migrate_bp = Blueprint('migrate', __name__)

@migrate_bp.route('/api/migrate', methods=['POST'])
def migrate():
    session = get_session()
    try:
        session.execute(text('ALTER TABLE businesses ADD COLUMN job_id VARCHAR(50)'))
        session.execute(text('ALTER TABLE businesses ADD COLUMN position INTEGER'))
        session.execute(text('CREATE INDEX idx_businesses_job_id ON businesses(job_id)'))
        session.commit()
        return jsonify({"status": "success", "message": "Database migrated!"})
    except Exception as e:
        session.rollback()
        return jsonify({"status": "error", "message": str(e)})
    finally:
        session.close()
