"""Dashboard, Profile, Leaderboard and home."""
from flask import Blueprint, render_template, g
from app import db
from app.models import User, Bet, BetStatus
from app.auth import login_required, get_current_user_id

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if get_current_user_id():
        from flask import redirect
        return redirect("/dashboard")
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    open_bets = (
        Bet.query.filter_by(status=BetStatus.OPEN)
        .filter(Bet.report_count < 5)
        .order_by(Bet.created_at.desc())
        .all()
    )
    user = User.query.get_or_404(g.current_user_id)
    return render_template(
        "dashboard.html",
        user=user,
        bets=open_bets,
    )


@main_bp.route("/profile")
@login_required
def profile():
    user = User.query.get_or_404(g.current_user_id)
    from app.models import Participation
    participations = (
        db.session.query(Participation)
        .join(Bet, Participation.bet_id == Bet.id)
        .filter(Participation.user_id == user.id, Bet.status == BetStatus.OPEN)
        .all()
    )
    open_bets_joined = [p.bet for p in participations]
    return render_template(
        "profile.html",
        user=user,
        open_bets_joined=open_bets_joined,
    )


@main_bp.route("/leaderboard")
def leaderboard():
    users = User.query.order_by(User.aura.desc()).limit(100).all()
    return render_template("leaderboard.html", users=users)
