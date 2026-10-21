"""
matches.py - the Potential Match page: view a match, then confirm or deny it.

Endpoints:
    GET  /api/matches/<id>            -> {match, lostReport, foundReport}
    POST /api/matches/<id>/respond    {confirmed: true | false}  -> {match}

Only the owner of the LOST report can see or answer a match. Anyone else gets
"not found" (404, not 403) so match ids can't be probed. The finder's name and
email are never included.

Match status:  pending -> confirmed | rejected | closed
  confirmed  the owner said "this is my item"
  rejected   the owner said "this isn't my item"
  closed     the item was claimed by someone else first
"""
from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from auth import current_user, error, login_required
from models import Match, Report, db

matches_bp = Blueprint("matches", __name__, url_prefix="/api/matches")


def public_match(match):
    return {"id": match.id, "status": match.status}


def get_own_match(match_id):
    """The match, but only if the logged-in user owns its lost report."""
    match = db.session.get(Match, match_id)
    if match is None or match.lost_report.owner_id != current_user().id:
        return None
    return match


def settle(report):
    """If nothing is waiting on this report any more, put it back to 'searching'."""
    if report.status != "potential_match":
        return
    column = Match.lost_report_id if report.kind == "lost" else Match.found_report_id
    still_waiting = Match.query.filter(column == report.id, Match.status == "pending").first()
    if still_waiting is None:
        report.status = "searching"


@matches_bp.get("/<int:match_id>")
@login_required
def view_match(match_id):
    match = get_own_match(match_id)
    if match is None:
        return error("This match link is no longer valid.", 404)
    return jsonify(
        match=public_match(match),
        lostReport=match.lost_report.to_dict(),
        foundReport=match.found_report.to_dict(),
    )


@matches_bp.post("/<int:match_id>/respond")
@login_required
def respond(match_id):
    match = get_own_match(match_id)
    if match is None:
        return error("This match link is no longer valid.", 404)

    confirmed = (request.get_json(silent=True) or {}).get("confirmed")
    if not isinstance(confirmed, bool):
        return error("Please answer yes or no.", 400)

    if match.status != "pending":
        if match.status == "closed":
            return error("This item has already been claimed by someone else.", 409)
        return error("You've already answered this one.", 409)

    lost, found = match.lost_report, match.found_report

    if confirmed:
        # Claim the found item in ONE database step, so if two owners press the
        # button at the same moment only one of them can win it.
        won = Report.query.filter(Report.id == found.id, Report.status == "potential_match") \
            .update({"status": "claimed"}, synchronize_session=False)
        if not won:
            match.status = "closed"
            db.session.flush()
            settle(lost)
            db.session.commit()
            return jsonify(match=public_match(match))

        db.session.refresh(found)
        match.status = "confirmed"
        lost.status = "claimed"

        # Anything else waiting on this lost report or this found item is now moot.
        others = Match.query.filter(
            Match.status == "pending",
            Match.id != match.id,
            or_(Match.found_report_id == found.id, Match.lost_report_id == lost.id),
        ).all()
        for other in others:
            other.status = "closed"
        db.session.flush()
        for other in others:
            settle(other.lost_report)
            settle(other.found_report)
    else:
        match.status = "rejected"
        db.session.flush()
        settle(lost)
        settle(found)

    db.session.commit()
    return jsonify(match=public_match(match))
