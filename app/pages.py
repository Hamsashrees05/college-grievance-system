from flask import Blueprint, render_template

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    return render_template("home.html")


@bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@bp.route("/accessibility")
def accessibility():
    return render_template("accessibility.html")


@bp.route("/help")
def help_page():
    return render_template("help.html")
