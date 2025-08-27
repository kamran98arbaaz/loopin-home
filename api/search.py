from flask import Blueprint, request, jsonify
from sqlalchemy import or_, and_, func
from models import Update, SOPSummary, LessonLearned, ReadLog
from extensions import db
import re

bp = Blueprint("search", __name__, url_prefix="/api")

@bp.route("/search")
def search_api():
    """Enhanced search API with filters and real-time results"""
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    process = request.args.get("process", "").strip()
    department = request.args.get("department", "").strip()
    tags = request.args.get("tags", "").strip()
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    
    if not query:
        return jsonify({
            "error": "Query parameter 'q' is required",
            "results": {"updates": [], "sops": [], "lessons": []},
            "total": 0,
            "page": page,
            "per_page": per_page
        })
    
    # Parse tags into list
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    
    # Build search query with filters
    results = {"updates": [], "sops": [], "lessons": []}
    
    # Search Updates
    if category in ["", "updates", "all"]:
        updates_query = Update.query
        
        # Apply process filter
        if process:
            updates_query = updates_query.filter(Update.process.ilike(f"%{process}%"))
        
        # Apply text search
        updates_query = updates_query.filter(
            or_(
                Update.message.ilike(f"%{query}%"),
                Update.name.ilike(f"%{query}%"),
                Update.process.ilike(f"%{query}%")
            )
        )
        
        # Get total count for pagination
        total_updates = updates_query.count()
        
        # Apply pagination
        updates = updates_query.order_by(Update.timestamp.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        for upd in updates:
            results["updates"].append({
                "id": upd.id,
                "title": upd.message[:100] + ("..." if len(upd.message) > 100 else ""),
                "content": upd.message,
                "timestamp": upd.timestamp.isoformat(),
                "name": upd.name,
                "process": upd.process,
                "url": f"/updates#update-{upd.id}",
                "type": "update"
            })
    
    # Search SOP Summaries
    if category in ["", "sops", "all"]:
        sops_query = SOPSummary.query
        
        # Apply department filter
        if department:
            sops_query = sops_query.filter(SOPSummary.department.ilike(f"%{department}%"))
        
        # Apply tags filter
        if tag_list:
            for tag in tag_list:
                sops_query = sops_query.filter(SOPSummary.tags.contains([tag]))
        
        # Apply text search
        sops_query = sops_query.filter(
            or_(
                SOPSummary.title.ilike(f"%{query}%"),
                SOPSummary.summary_text.ilike(f"%{query}%"),
                SOPSummary.department.ilike(f"%{query}%")
            )
        )
        
        # Get total count for pagination
        total_sops = sops_query.count()
        
        # Apply pagination
        sops = sops_query.order_by(SOPSummary.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        for sop in sops:
            results["sops"].append({
                "id": sop.id,
                "title": sop.title,
                "content": sop.summary_text,
                "timestamp": sop.created_at.isoformat(),
                "department": sop.department,
                "tags": sop.tags or [],
                "url": f"/sop_summaries/{sop.id}",
                "type": "sop"
            })
    
    # Search Lessons Learned
    if category in ["", "lessons", "all"]:
        lessons_query = LessonLearned.query
        
        # Apply department filter
        if department:
            lessons_query = lessons_query.filter(LessonLearned.department.ilike(f"%{department}%"))
        
        # Apply tags filter
        if tag_list:
            for tag in tag_list:
                lessons_query = lessons_query.filter(LessonLearned.tags.contains([tag]))
        
        # Apply text search
        lessons_query = lessons_query.filter(
            or_(
                LessonLearned.title.ilike(f"%{query}%"),
                LessonLearned.content.ilike(f"%{query}%"),
                LessonLearned.summary.ilike(f"%{query}%"),
                LessonLearned.author.ilike(f"%{query}%"),
                LessonLearned.department.ilike(f"%{query}%")
            )
        )
        
        # Get total count for pagination
        total_lessons = lessons_query.count()
        
        # Apply pagination
        lessons = lessons_query.order_by(LessonLearned.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        for lesson in lessons:
            results["lessons"].append({
                "id": lesson.id,
                "title": lesson.title,
                "content": lesson.content,
                "summary": lesson.summary,
                "timestamp": lesson.created_at.isoformat(),
                "author": lesson.author,
                "department": lesson.department,
                "tags": lesson.tags or [],
                "url": f"/lessons_learned/{lesson.id}",
                "type": "lesson"
            })
    
    # Calculate total results
    total_results = len(results["updates"]) + len(results["sops"]) + len(results["lessons"])
    
    return jsonify({
        "query": query,
        "filters": {
            "category": category,
            "process": process,
            "department": department,
            "tags": tag_list
        },
        "results": results,
        "total": total_results,
        "page": page,
        "per_page": per_page,
        "has_more": total_results == per_page
    })

@bp.route("/search/suggestions")
def search_suggestions():
    """Get search suggestions based on partial query"""
    query = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 10)), 50)
    
    if not query or len(query) < 2:
        return jsonify({"suggestions": []})
    
    suggestions = []
    
    # Get suggestions from updates
    update_suggestions = db.session.query(
        Update.message,
        func.count(Update.id).label('count')
    ).filter(
        Update.message.ilike(f"%{query}%")
    ).group_by(Update.message).order_by(func.count(Update.id).desc()).limit(limit).all()
    
    for msg, count in update_suggestions:
        suggestions.append({
            "text": msg[:100] + ("..." if len(msg) > 100 else ""),
            "type": "update",
            "count": count
        })
    
    # Get suggestions from SOP titles
    sop_suggestions = db.session.query(
        SOPSummary.title,
        func.count(SOPSummary.id).label('count')
    ).filter(
        SOPSummary.title.ilike(f"%{query}%")
    ).group_by(SOPSummary.title).order_by(func.count(SOPSummary.id).desc()).limit(limit).all()
    
    for title, count in sop_suggestions:
        suggestions.append({
            "text": title,
            "type": "sop",
            "count": count
        })
    
    # Get suggestions from lesson titles
    lesson_suggestions = db.session.query(
        LessonLearned.title,
        func.count(LessonLearned.id).label('count')
    ).filter(
        LessonLearned.title.ilike(f"%{query}%")
    ).group_by(LessonLearned.title).order_by(func.count(LessonLearned.id).desc()).limit(limit).all()
    
    for title, count in lesson_suggestions:
        suggestions.append({
            "text": title,
            "type": "lesson",
            "count": count
        })
    
    # Sort by count and limit results
    suggestions.sort(key=lambda x: x['count'], reverse=True)
    suggestions = suggestions[:limit]
    
    return jsonify({
        "query": query,
        "suggestions": suggestions
    })

@bp.route("/search/filters")
def get_search_filters():
    """Get available search filters"""
    # Get unique processes
    processes = db.session.query(Update.process).distinct().all()
    processes = [p[0] for p in processes if p[0]]
    
    # Get unique departments
    departments = db.session.query(SOPSummary.department).distinct().all()
    departments.extend(db.session.query(LessonLearned.department).distinct().all())
    departments = list(set([d[0] for d in departments if d[0]]))
    
    # Get all tags
    sop_tags = db.session.query(SOPSummary.tags).filter(SOPSummary.tags.isnot(None)).all()
    lesson_tags = db.session.query(LessonLearned.tags).filter(LessonLearned.tags.isnot(None)).all()
    
    all_tags = []
    for tags in sop_tags + lesson_tags:
        if tags[0]:
            all_tags.extend(tags[0])
    
    # Get unique tags with counts
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Sort tags by frequency
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    
    return jsonify({
        "processes": processes,
        "departments": departments,
        "tags": [{"tag": tag, "count": count} for tag, count in sorted_tags[:50]]  # Top 50 tags
    })

@bp.route("/search/recent")
def get_recent_searches():
    """Get recent search queries (this would typically be stored per user)"""
    # For now, return some common searches
    # In a real implementation, this would track user search history
    return jsonify({
        "recent_searches": [
            "process improvement",
            "bug fix",
            "deployment",
            "testing",
            "documentation"
        ]
    })
