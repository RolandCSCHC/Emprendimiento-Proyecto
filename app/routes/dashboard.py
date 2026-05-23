from flask import Blueprint, abort, current_app, render_template

from app.services.session_store import get_session, list_sessions

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
def dashboard():
    sessions = list_sessions()
    return render_template("dashboard.html", sessions=sessions)


@dashboard_bp.route("/<session_id>")
def session_detail(session_id: str):
    session = get_session(session_id)
    if session is None:
        abort(404)

    metric_labels = current_app.config["METRIC_LABELS"]
    metrics = [
        {
            "key": key,
            "label": metric_labels.get(key, key),
            "info": session.metricas.get(key),
        }
        for key in current_app.config["METRIC_KEYS"]
    ]

    return render_template(
        "session_detail.html",
        session=session,
        metrics=metrics,
    )
