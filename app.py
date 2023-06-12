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
uri = os.getenv("postgres://vezemflpyalorw:af8515cc5d0852fe1a172ff6a77d0ddbb363b652442ad9e1b8083a35c4249cc4@ec2-3-93-160-246.compute-1.amazonaws.com:5432/d9r1kob4b0jdvc")
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://")
db = SQL(uri)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows = db.execute("SELECT * FROM transactions WHERE user_id = :id", id=session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])

    # get cash value float
    cash = cash[0]['cash']
    # this will be total value of all stock holdings and cash
    sum = cash
    totalPrice = 0

    for price in rows:
        totalPrice += price['total_price']

    # add stock name, add current lookup value, add total value
    for row in rows:
        look = lookup(row['symbol'])
        row['name'] = look['name']
        row['price'] = look['price']
        row['total'] = int(row['price'] * row['quantity'])

        # increment sum
        sum += row['total']

        # convert price and total to usd format
        row['price'] = usd(row['price'])
        row['total'] = usd(row['total'])

    return render_template("index.html", rows=rows, cash=usd(cash), sum=usd(sum), totalPrice=usd(totalPrice))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol_lookup = lookup(request.form.get("symbol"))


        quantity = int(request.form.get("shares"))
        name = symbol_lookup["name"]
        price = float(symbol_lookup["price"])
        symbol = symbol_lookup["symbol"]
        total = price * quantity
        users_money = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"] )

        #make sure symbol exists or is not null
        if not symbol_lookup:
            return apology("Symbol does not exists",403)

        #Check to see if shares is positive
        if quantity < 0:
            return apology("Please enter a positive number for shares")

        #Check to see if user has enough money for purchase
        if total <= users_money[0]["cash"]:
            db.execute("INSERT INTO transactions(user_id, symbol, stock_price, total_price,name,quantity) VALUES (?,?,?,?,?,?)",session["user_id"], symbol, price, total,name,quantity)
            db.execute("UPDATE users SET cash = ? WHERE id = ?",users_money[0]["cash"] - total, session["user_id"])
        else:
            return apology("Cannot afford number of shares at current price",403)
        return redirect("/")
    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol_lookup = lookup(request.form.get("symbol"))
        name = symbol_lookup["name"]
        price = symbol_lookup["price"]
        symbol = symbol_lookup["symbol"]
        if symbol != None:
            return render_template("quoted.html", name=name, price=price, symbol=symbol)
        else:
            return apology("Stock Symbol does not exist",403)

    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    username = request.form.get("username")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")
    rows = len(db.execute("SELECT * from users"))

    if request.method == "POST":

        #Check to make sure passwords match and no fields are blank
        if password != confirmation:
            return apology("Passwords do not match", 403)
        if not username:
            return apology("Username must not be blank", 403)
        if not password:
            return apology("Password must not be blank", 403)
        if not confirmation:
            return apology("Retype Password must not be blank", 403)

        #Check to make sure username is not already taken
        check_username = db.execute("SELECT * FROM users WHERE username = ?", username )
        if len(check_username) != 0:
            return apology("Username already exists", 403)

        hash = generate_password_hash(password)
        db.execute("INSERT INTO users(id,username, hash) VALUES(?,?,?)",rows+1,username,hash)

        #log user in
        check2=db.execute("SELECT * FROM users WHERE username= ?",username)
        session["user_id"] = check2[0]["id"]

        return redirect("/")
    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    sell = db.execute("SELECT symbol,quantity FROM transactions WHERE user_id = ? GROUP BY symbol",session["user_id"] )
    currentCash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

    print(sell)

    if request.method == "GET":
        return render_template("sell.html",sell=sell)
    else:
        symbol_lookup = lookup(request.form.get("sell"))
        quantity = request.form.get("shares")
        price = symbol_lookup["price"]
        symbol = symbol_lookup["symbol"]
        total = float(price) * int(quantity)
        newCashBalance = float(currentCash[0]['cash']) + total
        sellSymbol = db.execute("SELECT quantity FROM transactions WHERE symbol = ?",symbol)


        if not request.form.get("sell"):
            return apology("Please select a share to sell",403)
        if int(request.form.get("shares")) <=0:
            return apology("Please enter a number greater than 0",403)
        db.execute("INSERT INTO sell(user_id,symbol, stock_price, quantity,total_price) VALUES(?,?,?,?,?)",session["user_id"], symbol,price,quantity, total)
        db.execute("UPDATE users SET cash = ? WHERE id = ?",newCashBalance,session["user_id"])
        db.execute("UPDATE transactions SET quantity = ? WHERE user_id = ? AND symbol = ?",int(sellSymbol[0]['quantity'])-int(quantity),session["user_id"],symbol)

        return redirect("/")

