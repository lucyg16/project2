import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp


from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached, disable caching
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    rows= db.execute("SELECT * FROM purchase WHERE id=:user", user= session["user_id"])
    print(rows)
    index={}
    index["symbol"]=[]
    index["name"]=[]
    index["share"]=[]
    index["price"]=[]
    index["total"]=[]
    rows1=db.execute("SELECT * FROM users WHERE id=:user", user=session["user_id"])
    print(rows1)
    print("CASH.......{:.2f}".format(rows1[0]["cash"]))
    cash = float(rows1[0]["cash"])
    total = cash
    print("Total")
    print(str(total))
    if len(rows)!= 0:
        for row in rows:
            index["symbol"].append(row["symbol"])
            index["share"].append(int(row["shares"]))
            price2= lookup(row['symbol'])
            index["name"].append(price2["name"])
            index["price"].append(usd(price2["price"]))
            total= total + price2["price"]
            index["total"].append(usd(int(row["shares"])*float(price2["price"])))
    else:
        index["symbol"].append(" ")
        index["share"].append(" ")
        index["price"].append(" ")
        index["total"].append(" ")
    leng=len(rows)
    

    total=usd(total)
    return render_template("index.html", index=index, leng=leng, cash= usd(cash), total=total, )

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        #correct symbol
        stock  = lookup(request.form.get("symbol"))
        if not stock:
            return apology("Invalid symbol")
        shares = int(request.form.get("shares"))    
        #correct number of shares
        try:
            if shares < 0:
                return apology("Shares must be positive integer")
        
        except:
            return apology("Shares must be positive integer")
        
        # select user's cash
        money = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        
        # check if enough money to buy
        if not money or float(money[0]["cash"]) < stock["price"] * shares: 
            return apology("Not enough money")
            
        #update user cash
        subCash=stock["price"]*float(shares)
        print("{:.2f}".format(subCash))
        db.execute("UPDATE users SET cash = :cash1 WHERE id = :id" , \
            id=session["user_id"], \
        cash1=float(money[0]["cash"]-subCash))
        # print("{:.2}".format(cash1))    
        #select user shares of symbol
        user_shares = db.execute("SELECT * FROM purchase \
            WHERE id = :id AND symbol=:symbol", \
            id=session["user_id"], symbol=stock["symbol"])
            
        #if user doesn't have shares of that symbol, create new stock object
        if len(user_shares)==0:
            db.execute("INSERT INTO purchase (name, shares, price, symbol, id) \
            VALUES(:name, :shares, :price, :symbol, :id)", \
            name=stock["name"], shares=shares, price=usd(stock["price"]), \
            symbol=stock["symbol"], id=session["user_id"])
            rows = db.execute("SELECT * FROM purchase \
            WHERE id = :id AND symbol=:symbol", \
            id=session["user_id"], symbol=stock["symbol"])
            print(rows)
            
        #Else increment the shares count
        else:
            shares_total = user_shares[0]["shares"] + shares
            db.execute("UPDATE purchase SET shares=:shares \
            WHERE id=:id AND symbol=:symbol", \
            shares=shares_total, id=session["user_id"], \
            symbol=stock["symbol"])
            
        #return to index
        return redirect(url_for("index"))

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    
    if request.method == "POST":
        rows = lookup(request.form.get("symbol"))
        
        if not rows:
            return apology("Invalid Symbol")
            
        return render_template("quoted.html", stock=rows)
    
    else:
        return render_template("quote.html")
    

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    
    if request.method == "POST":
        
        # ensure first_name was submitted
        if not request.form.get("first_name"):
            return apology("Must provide first_name")
            
        # ensure last_name was submitted    
        elif not request.form.get("last_name"):
            return apology("Must provide last_name")
        
         # ensure email was submitted    
        elif not request.form.get("email"):
            return apology("Must provide email")
        
        # ensure username was submitted
        elif not request.form.get("username"):
            return apology("Must provide username")
            
        #ensure username is unique
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
            
        # ensure password was submitted    
        if not request.form.get("password"):
            return apology("Must provide password")
            
        #ensure username exists and password is correct
        if len(rows) != 0:
            return apology("this username already exists")
        
        # ensure password and verified password is the same
        elif request.form.get("password") != request.form.get("password2"):
            return apology("password doesn't match")
    
        Hash=pwd_context.hash(request.form.get("password"))
    
        # insert the new user into users, storing the hash of the user's password
        result = db.execute("INSERT INTO users (first_name, last_name, email, username, hash) \
                             VALUES(:first_name, :last_name, :email, :username, :hash)", \
                             first_name=request.form.get("first_name"), \
                             last_name=request.form.get("last_name"), \
                             email=request.form.get("email"), \
                             username=request.form.get("username"), \
                             hash= Hash)
                             
        
        # remember which user has logged in
        session["user_id"] = result
                 
      
        # redirect user to home page
        return redirect(url_for("index"))
    
    else:
        return render_template("register.html")    

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    
    if request.method == "GET" :
        return render_template("sell.html")
        
    else:
        #ensure proper symbol
        purchase = lookup(request.form.get("symbol"))
        if not purchase:
            return apology("Invalid Symbol")
            
        #ensure proper number of shares
        try: 
            shares = int(request.form.get("shares"))
            if shares < 0:
                return apology("Shares must be positive integer")
        except:
            return apology("Shares must be positive integer")
            
        stock  = lookup(request.form.get("symbol"))
            
        #select the symbol shares of that user
        user_shares = db.execute("SELECT shares FROM purchase \
        WHERE id = :user_id AND symbol=:symbol", \
        user_id =session["user_id"], symbol=purchase["symbol"])
        
        #check if enough shares to sell
        if int(user_shares[0]["shares"]) < shares:
            return apology("Not enough shares")
        
        #update user cash (increase)
        db.execute("UPDATE users SET cash=cash + :purchase WHERE id = :id", \
            id=session["user_id"], \
            purchase=stock["price"] * float(shares))
            
        #decrement the shares count
        shares_total = user_shares[0]["shares"] - shares
        
        #if after decrement is zero, delete shares from purchase
        if shares_total == 0:
            db.execute("DELETE FROM purchase WHERE id=:id AND symbol=:symbol", id=session["user_id"], symbol=stock["symbol"])
            
        #otherwise, update purchase shares
        else:
            db.execute("UPDATE purchase SET shares=:shares WHERE id=:id AND symbol=:symbol", shares=shares_total, id=session["user_id"], symbol=stock["symbol"])
            
        #return to index
        return redirect(url_for("index"))

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """Deposit more cash."""
    
    if request.method == "GET" :
        return render_template("deposit.html")
    
    #select user's cash
    money = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
    print("CASH.......{:.2f}".format(money[0]["cash"]))
    cash = float(money[0]["cash"])
    c=float(request.form.get("cash"))
    cash = cash + c
        
    #update cash
    db.execute("UPDATE users SET cash=:cash WHERE id = :id", \
        id=session["user_id"], cash=cash)


    #return to index
    return redirect(url_for("index"))
  
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
    