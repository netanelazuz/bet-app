"""Dashboard, Profile, Leaderboard, bet CRUD and Aura flows."""
from datetime import datetime
from flask import Blueprint, render_template, g, redirect, url_for, request, flash
from app import db
from app.models import User, Bet, BetStatus, Difficulty, Participation
from app.auth import login_required, get_current_user_id
from app.aura import redistribute_aura

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
    # Win/loss notification: bets that closed after last dashboard visit
    recent_results = []
    if user.last_login_at:
        recent_results = (
            db.session.query(Participation)
            .join(Bet, Participation.bet_id == Bet.id)
            .filter(
                Participation.user_id == user.id,
                Bet.status == BetStatus.CLOSED,
                Bet.closed_at >= user.last_login_at,
            )
            .order_by(Bet.closed_at.desc())
            .all()
        )
    user.last_login_at = datetime.utcnow()
    db.session.commit()
    return render_template(
        "dashboard.html",
        user=user,
        bets=open_bets,
        recent_results=recent_results,
    )


@main_bp.route("/profile")
@login_required
def profile():
    user = User.query.get_or_404(g.current_user_id)
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


# ---- Bet create ----

@main_bp.route("/bets/create", methods=["GET", "POST"])
@login_required
def create_bet():
    if request.method == "GET":
        return render_template("create_bet.html", difficulties=Difficulty)
    topic = (request.form.get("topic") or "").strip()
    description = (request.form.get("description") or "").strip()
    difficulty_str = (request.form.get("difficulty") or "medium").strip().lower()
    end_date_str = (request.form.get("end_date") or "").strip()
    end_condition = (request.form.get("end_condition") or "").strip()[:200]
    if not topic or len(topic) > 200:
        flash("Topic is required (max 200 characters).", "error")
        return render_template("create_bet.html", difficulties=Difficulty)
    try:
        difficulty = Difficulty(difficulty_str)
    except ValueError:
        difficulty = Difficulty.MEDIUM
    end_date = None
    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
        except ValueError:
            pass
    bet = Bet(
        topic=topic,
        description=description or None,
        difficulty=difficulty,
        end_date=end_date,
        end_condition=end_condition or None,
        status=BetStatus.OPEN,
        created_by_id=g.current_user_id,
    )
    db.session.add(bet)
    db.session.commit()
    flash("Bet created.", "success")
    return redirect(url_for("main.bet_detail", bet_id=bet.id))


# ---- Bet detail and join ----

@main_bp.route("/bets/<int:bet_id>")
@login_required
def bet_detail(bet_id):
    bet = Bet.query.get_or_404(bet_id)
    if bet.report_count >= 5:
        flash("This bet is no longer available.", "error")
        return redirect(url_for("main.dashboard"))
    user = User.query.get_or_404(g.current_user_id)
    participation = Participation.query.filter_by(bet_id=bet.id, user_id=user.id).first()
    can_join = (
        bet.status == BetStatus.OPEN
        and bet.created_by_id != user.id
        and participation is None
        and user.aura is not None
    )
    participations = list(bet.participations.all())
    return render_template(
        "bet_detail.html",
        bet=bet,
        user=user,
        participation=participation,
        can_join=can_join,
        participations=participations,
    )


@main_bp.route("/bets/<int:bet_id>/join", methods=["POST"])
@login_required
def join_bet(bet_id):
    bet = Bet.query.get_or_404(bet_id)
    if bet.status != BetStatus.OPEN or bet.report_count >= 5:
        flash("This bet is not open for participation.", "error")
        return redirect(url_for("main.bet_detail", bet_id=bet.id))
    user = User.query.get_or_404(g.current_user_id)
    if bet.created_by_id == user.id:
        flash("Creator cannot participate in their own bet.", "error")
        return redirect(url_for("main.bet_detail", bet_id=bet.id))
    if Participation.query.filter_by(bet_id=bet.id, user_id=user.id).first():
        flash("You already joined this bet.", "error")
        return redirect(url_for("main.bet_detail", bet_id=bet.id))
    try:
        stake = int(request.form.get("stake") or 0)
    except (TypeError, ValueError):
        stake = 0
    side = (request.form.get("side") or "yes").strip().lower()
    if side not in ("yes", "no"):
        side = "yes"
    if stake < 1:
        flash("Stake must be at least 1 Aura.", "error")
        return redirect(url_for("main.bet_detail", bet_id=bet.id))
    if (user.aura or 0) < stake:
        flash("Not enough Aura.", "error")
        return redirect(url_for("main.bet_detail", bet_id=bet.id))
    user.aura = (user.aura or 0) - stake
    user.open_bets = (user.open_bets or 0) + 1
    p = Participation(bet_id=bet.id, user_id=user.id, stake=stake, side=side)
    db.session.add(p)
    db.session.commit()
    flash("You joined the bet.", "success")
    return redirect(url_for("main.bet_detail", bet_id=bet.id))


# ---- Close bet ----

@main_bp.route("/bets/<int:bet_id>/close", methods=["POST"])
@login_required
def close_bet(bet_id):
    bet = Bet.query.get_or_404(bet_id)
    if bet.status != BetStatus.OPEN:
        flash("Bet is not open.", "error")
        return redirect(url_for("main.bet_detail", bet_id=bet.id))
    if bet.created_by_id != g.current_user_id:
        flash("Only the creator can close this bet.", "error")
        return redirect(url_for("main.bet_detail", bet_id=bet.id))
    winning_side = (request.form.get("winning_side") or "").strip().lower()
    if winning_side not in ("yes", "no"):
        flash("Choose winning side: Yes or No.", "error")
        return redirect(url_for("main.bet_detail", bet_id=bet.id))
    bet.status = BetStatus.CLOSED
    bet.winning_side = winning_side
    bet.closed_at = datetime.utcnow()
    redistribute_aura(bet)
    db.session.commit()
    flash("Bet closed. Aura has been redistributed.", "success")
    return redirect(url_for("main.bet_detail", bet_id=bet.id))
