import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/customer_order", methods=["GET"])
def customer_order():
    """Show Order Form"""
    if request.method == "GET":
        return render_template("customer_order")


@app.route("/", methods=["GET"])
@login_required
def index():
    """Show portfolio of stocks"""
    if request.method == "GET":
        # Get list of symbols that we have shares of
        db.execute("delete from current_price;")
        symbol = db.execute("SELECT symbol FROM stock GROUP BY symbol;")
        # Lookup current price of those shares
        for row in symbol:
            get = row["symbol"]
            current = lookup(get)
            # set the database with the current price
            db.execute(
                "INSERT INTO current_price (symbol, current) values (?,?);",
                current["symbol"],
                current["price"],
            )
        # get total list of everything
        set_up_stock = db.execute(
            "SELECT history.symbol,current,sum(shares) AS [total_shares] FROM history JOIN current_price ON history.symbol = lower(current_price.symbol) WHERE user_id = (?) GROUP BY history.symbol;",
            session["user_id"],
        )
        for row in set_up_stock:
            price = row["current"]
            symbol = row["symbol"]
            Quant = row["total_shares"]
            Amount = Quant * price
            db.execute(
                "UPDATE stock SET amount = (?), Shares_tot = (?) WHERE symbol = (?);",
                Amount,
                Quant,
                symbol,
            )
        db.execute("UPDATE stock SET amount = 0 WHERE Shares_tot <= 0;")
        all = db.execute(
            "SELECT stock.symbol, current, Shares_tot, amount, name, cash FROM stock JOIN current_price ON lower(current_price.symbol) = stock.symbol JOIN users ON user_id = stock.user_id WHERE Shares_tot > 0 AND stock.symbol IN (SELECT symbol FROM (SELECT Shares_tot, symbol FROM stock WHERE user_id = (?) GROUP BY symbol) WHERE Shares_tot > 0) GROUP BY stock.symbol;",
            session["user_id"],
        )
        cash = db.execute("SELECT cash FROM users WHERE id = (?);", session["user_id"])
        Cash_in_bank = 0
        for row in cash:
            Cash_in_bank = row["cash"]
        final = db.execute(
            "select current_price.symbol,current,name,Shares_tot,amount from current_price JOIN stock on lower(current_price.symbol)=stock.symbol WHERE Shares_tot > 0 group by current_price.symbol;"
        )
        Final_tot = 0
        for row in final:
            hold_tot = row["amount"]
            Final_tot += hold_tot
        Final_tot += Cash_in_bank
        current_stock = db.execute("SELECT symbol FROM stock GROUP BY symbol;")
        return render_template(
            "index.html",
            all=all,
            cash=Cash_in_bank,
            current_stock=current_stock,
            Final_tot=Final_tot,
            final=final,
        )
