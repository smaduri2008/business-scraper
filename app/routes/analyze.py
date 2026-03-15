"""
Business analysis routes with pagination support.
"""
import time
import json
import logging
import uuid
from threading import Thread
from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Business, InstagramData, Analysis
from app.scrapers.google_maps import scrape_google_maps
from app.scrapers.website import scrape_website
from app.scrapers.instagram import scrape_instagram
from app.analyzers.ai_analyzer import analyze_business
from app.analyzers.lead_ranker import rank_leads, compute_lead_score

logger = logging.getLogger(__name__)
analyze_bp = Blueprint("analyze", __name__)

# In-memory storage for active jobs (use Redis in production)
active_jobs = {}


@analyze_bp.route("/analyze", methods=["POST"])
def analyze():
    """
    Analyze businesses with pagination support.
    Returns first 10 results immediately + job_id for more.
    """
    body = request.get_json(silent=True) or {}
    
    niche = (body.get("niche") or "").strip()
    location = (body.get("location") or "").strip()
    max_results = int(body.get("max_results", 50))
    
    if not niche or not location:
        return jsonify({"error": "niche and location required"}), 400
    
    if max_results > 100:
        return jsonify({"error": "max_results cannot exceed 100"}), 400
    
    start_time = time.time()
    job_id = str(uuid.uuid4())
    
    logger.info(f"Starting analysis job {job_id}: {niche} in {location} (max: {max_results})")
    
    # Get initial batch of raw businesses from Google Maps
    raw_businesses = scrape_google_maps(niche, location, max_results)
    
    if not raw_businesses:
        return jsonify({
            "error": "No businesses found",
            "niche": niche,
            "location": location,
            "results_count": 0,
            "businesses": []
        }), 404
    
    # Process first 10 immediately for fast response
    quick_batch = raw_businesses[:10]
    businesses_output = []
    
    session = get_session()
    
    try:
        for idx, raw in enumerate(quick_batch):
            try:
                business_result = _analyze_single_business(raw, niche, location, job_id, idx, session)
                businesses_output.append(business_result)
            except Exception as exc:
                logger.error(f"Failed to process business {idx}: {exc}")
                session.rollback()
        
        # ── Lead-mode: rank first page by opportunity score ────────────────
        businesses_output = rank_leads(businesses_output)
        _update_positions_in_db(session, businesses_output, job_id, start=0)

        session.commit()
    finally:
        session.close()
    
    elapsed = round(time.time() - start_time, 2)
    
    # Start background job for remaining businesses
    has_more = len(raw_businesses) > 10
    if has_more:
        active_jobs[job_id] = {
            "status": "processing",
            "total": len(raw_businesses),
            "processed": 10,
            "niche": niche,
            "location": location
        }
        
        thread = Thread(
            target=_background_analyze,
            args=(job_id, niche, location, raw_businesses[10:])
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Background job {job_id} started for {len(raw_businesses) - 10} remaining businesses")
    
    return jsonify({
        "job_id": job_id,
        "niche": niche,
        "location": location,
        "results_count": len(businesses_output),
        "total_found": len(raw_businesses),
        "processing_time_seconds": elapsed,
        "has_more": has_more,
        "businesses": businesses_output
    })


@analyze_bp.route('/migrate-db-columns', methods=['GET'])
def migrate_db_columns():
    """Temporary migration endpoint - delete after use"""
    from sqlalchemy import text, inspect
    try:
        session = get_session()
        engine = session.get_bind()
        inspector = inspect(engine)
        
        # Get existing columns
        columns = [col['name'] for col in inspector.get_columns('businesses')]
        
        results = []
        
        # Add job_id if missing
        if 'job_id' not in columns:
            session.execute(text('ALTER TABLE businesses ADD COLUMN job_id VARCHAR(50)'))
            session.commit()
            results.append("job_id column added")
        else:
            results.append("job_id already exists")
        
        # Add position if missing
        if 'position' not in columns:
            session.execute(text('ALTER TABLE businesses ADD COLUMN position INTEGER'))
            session.commit()
            results.append("position column added")
        else:
            results.append("position already exists")

        # Add website_grade_score if missing
        if 'website_grade_score' not in columns:
            session.execute(text('ALTER TABLE businesses ADD COLUMN website_grade_score FLOAT'))
            session.commit()
            results.append("website_grade_score column added")
        else:
            results.append("website_grade_score already exists")

        # Add website_grade (JSON) if missing
        if 'website_grade' not in columns:
            session.execute(text('ALTER TABLE businesses ADD COLUMN website_grade TEXT'))
            session.commit()
            results.append("website_grade column added")
        else:
            results.append("website_grade already exists")

        # Add opportunity_score to analyses if missing
        analysis_columns = [col['name'] for col in inspector.get_columns('analyses')]
        if 'opportunity_score' not in analysis_columns:
            session.execute(text('ALTER TABLE analyses ADD COLUMN opportunity_score FLOAT'))
            session.commit()
            results.append("analyses.opportunity_score column added")
        else:
            results.append("analyses.opportunity_score already exists")

        session.close()
        return {"status": "success", "message": ", ".join(results), "columns": columns}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


@analyze_bp.route("/analyze/<job_id>/status", methods=["GET"])
def job_status(job_id):
    """
    Get status of background processing job.
    """
    if job_id not in active_jobs:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify(active_jobs[job_id])


@analyze_bp.route("/analyze/<job_id>/more", methods=["GET"])
def get_more_results(job_id):
    """
    Get additional results for a job (paginated).
    """
    offset = int(request.args.get("offset", 10))
    limit = int(request.args.get("limit", 10))
    
    session = get_session()
    
    try:
        # Query businesses from database by job_id
        businesses = session.query(Business).filter(
            Business.job_id == job_id
        ).order_by(Business.position).offset(offset).limit(limit).all()
        
        businesses_output = []
        for business in businesses:
            business_dict = business.to_dict()
            businesses_output.append(business_dict)
        
        # Check if there are more results
        total_count = session.query(Business).filter(
            Business.job_id == job_id
        ).count()
        
        has_more = (offset + limit) < total_count
        
        return jsonify({
            "job_id": job_id,
            "offset": offset,
            "limit": limit,
            "results_count": len(businesses_output),
            "total_count": total_count,
            "has_more": has_more,
            "businesses": businesses_output
        })
        
    finally:
        session.close()


def _analyze_single_business(raw, niche, location, job_id, position, session):
    """
    Analyze a single business with all enrichment steps.
    """
    business_result = dict(raw)
    business_result["niche"] = niche
    business_result["location"] = location
    
    # 1. Scrape website
    website_data = {}
    if raw.get("website"):
        try:
            website_data = scrape_website(raw["website"]) or {}
        except Exception as exc:
            logger.error(f"Website scraper failed for {raw.get('website')}: {exc}")
    
    business_result["services"] = website_data.get("services", [])
    business_result["prices"] = website_data.get("prices", [])
    business_result["team_members"] = website_data.get("team_members", [])
    
    # 2. Grade website
    website_grade = {}
    if website_data:
        try:
            from app.analyzers.website_grader import grade_website
            website_grade = grade_website(website_data)
        except Exception as exc:
            logger.error(f"Website grading failed for {raw.get('website')}: {exc}")
    
    business_result["website_grade"] = website_grade
    
    # 3. Scrape Instagram
    ig_data = None
    try:
        ig_data = scrape_instagram(
            raw.get("name", ""),
            website_data.get("instagram_url"),
        )
    except Exception as exc:
        logger.error(f"Instagram scraper failed for {raw.get('name')}: {exc}")
    
    business_result["instagram"] = ig_data
    
    # 4. AI analysis
    analysis_result = {}
    try:
        analysis_result = analyze_business(business_result, niche)
    except Exception as exc:
        logger.error(f"AI analysis failed for {raw.get('name')}: {exc}")
    
    business_result["analysis"] = analysis_result
    
    # 5. Save to database
    try:
        _save_to_db(session, business_result, ig_data, analysis_result, website_grade, job_id, position)
    except Exception as exc:
        logger.error(f"DB save failed for {raw.get('name')}: {exc}")
        session.rollback()
    
    return business_result


def _background_analyze(job_id, niche, location, raw_businesses):
    """
    Background job to process remaining businesses.
    """
    logger.info(f"Background job {job_id} processing {len(raw_businesses)} businesses")
    
    session = get_session()
    
    try:
        background_results = []
        for idx, raw in enumerate(raw_businesses, start=10):
            try:
                business_result = _analyze_single_business(raw, niche, location, job_id, idx, session)
                session.commit()
                background_results.append(business_result)
                
                # Update job status
                if job_id in active_jobs:
                    active_jobs[job_id]["processed"] = idx + 1
                
                logger.info(f"Job {job_id}: Processed {idx + 1}/{active_jobs[job_id]['total']}")
                
            except Exception as exc:
                logger.error(f"Error processing business {idx} in job {job_id}: {exc}")
                session.rollback()

        # ── Lead-mode: rank background batch, then do a full job re-rank ──
        if background_results:
            ranked_background = rank_leads(background_results)
            _update_positions_in_db(session, ranked_background, job_id, start=10)
            session.commit()

        # Full re-rank: pull ALL businesses for the job from DB, reorder, and
        # write back positions so that pagination across all pages is lead-ordered.
        _rerank_job(session, job_id)
        session.commit()
        
        # Mark job as complete
        if job_id in active_jobs:
            active_jobs[job_id]["status"] = "complete"
            
        logger.info(f"Background job {job_id} completed successfully")
        
    except Exception as exc:
        logger.error(f"Background job {job_id} failed: {exc}")
        if job_id in active_jobs:
            active_jobs[job_id]["status"] = "failed"
            active_jobs[job_id]["error"] = str(exc)
    finally:
        session.close()


def _save_to_db(session, business_data, ig_data, analysis_data, website_grade, job_id, position):
    """
    Save business and related data to database.
    """
    wg_score = website_grade.get("total_score") if website_grade else None
    business = Business(
        job_id=job_id,
        position=position,
        name=business_data.get("name", ""),
        niche=business_data.get("niche"),
        location=business_data.get("location"),
        website=business_data.get("website"),
        phone=business_data.get("phone"),
        address=business_data.get("address"),
        rating=business_data.get("rating"),
        reviews_count=business_data.get("reviews_count"),
        hours=business_data.get("hours"),
        scraped_at=datetime.utcnow(),
        website_grade_score=wg_score,
        website_grade=json.dumps(website_grade) if website_grade else None,
    )
    session.add(business)
    session.flush()
    
    if ig_data:
        ig = InstagramData(
            business_id=business.id,
            username=ig_data.get("username"),
            followers=ig_data.get("followers"),
            following=ig_data.get("following"),
            posts=ig_data.get("posts"),
            engagement_rate=ig_data.get("engagement_rate"),
            bio=ig_data.get("bio"),
            is_verified=ig_data.get("is_verified", False),
            is_business=ig_data.get("is_business", False),
        )
        session.add(ig)
    
    if analysis_data:
        opportunity_score = analysis_data.get("opportunity_score")
        # Fall back to server-side score if AI didn't produce one
        if opportunity_score is None:
            opportunity_score = compute_lead_score(business_data)
        analysis = Analysis(
            business_id=business.id,
            revenue_streams=json.dumps(analysis_data.get("revenue_streams", [])),
            estimated_revenue_tier=analysis_data.get("estimated_revenue_tier"),
            pricing_strategy=analysis_data.get("pricing_strategy"),
            service_quality_score=analysis_data.get("service_quality_score"),
            service_quality_reasoning=analysis_data.get("service_quality_reasoning"),
            competitive_assessment=analysis_data.get("competitive_assessment"),
            niche_specific_insights=analysis_data.get("niche_specific_insights"),
            opportunity_score=opportunity_score,
        )
        session.add(analysis)

def _update_positions_in_db(session, ranked_businesses: list, job_id: str, start: int = 0):
    """
    Update the ``position`` column for each business in *ranked_businesses*
    according to its rank-order index.

    *ranked_businesses* is an in-memory list already sorted by lead score.
    Each element must contain either ``"id"`` (DB primary key) or ``"name"``
    to look up the matching row.
    """
    for offset, biz in enumerate(ranked_businesses):
        position = start + offset
        biz_id = biz.get("id")
        if biz_id:
            row = session.query(Business).filter(
                Business.id == biz_id,
                Business.job_id == job_id,
            ).first()
        else:
            row = session.query(Business).filter(
                Business.job_id == job_id,
                Business.name == biz.get("name", ""),
            ).first()
        if row:
            row.position = position


def _rerank_job(session, job_id: str):
    """
    Pull every Business for *job_id* from the DB, sort them by
    opportunity_score (lead-mode ranking), and write back updated
    ``position`` values so pagination is globally consistent.
    """
    businesses = session.query(Business).filter(
        Business.job_id == job_id
    ).all()

    if not businesses:
        return

    # Build dict representation for rank_leads (same shape as in-memory dicts)
    def _biz_to_dict(b: Business) -> dict:
        wg = None
        if b.website_grade:
            try:
                wg = json.loads(b.website_grade)
            except (json.JSONDecodeError, TypeError):
                wg = None
        analysis_score = None
        if b.analysis:
            analysis_score = b.analysis.opportunity_score
        return {
            "id": b.id,
            "name": b.name,
            "phone": b.phone,
            "address": b.address,
            "website": b.website,
            "rating": b.rating,
            "reviews_count": b.reviews_count,
            "website_grade": wg,
            "analysis": {"opportunity_score": analysis_score} if analysis_score is not None else {},
        }

    biz_dicts = [_biz_to_dict(b) for b in businesses]
    ranked = rank_leads(biz_dicts)

    id_to_row = {b.id: b for b in businesses}
    for new_position, biz_dict in enumerate(ranked):
        row = id_to_row.get(biz_dict["id"])
        if row:
            row.position = new_position

    logger.info(f"Re-ranked {len(businesses)} businesses for job {job_id}")
