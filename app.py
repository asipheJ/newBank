import random
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime

app = Flask(__name__, template_folder='templates')
app.secret_key = 'your_secret_key'

USER_FILE = "users.json"
MAX_AMOUNT = 70000

# Utility functions
def generate_account_number():
    return random.randint(1000000000, 9999999999)

def read_users():
    try:
        with open(USER_FILE, "r") as file:
            users = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        users = {}
    return users

def save_users(users):
    with open(USER_FILE, "w") as file:
        json.dump(users, file, indent=4)

def find_user_by_username_and_password(username, password):
    users = read_users()
    for account_number, user in users.items():
        if user.get('username', '').lower() == username.lower() and user['password'] == password:
            user['account_number'] = account_number
            return user
    return None

def find_user(account_number):
    users = read_users()
    return users.get(str(account_number))

def check_existing_user(phone_number, id_number, username=None):
    users = read_users()
    for user in users.values():
        if user['phone_number'] == phone_number or user['id_number'] == id_number:
            return True
        if username and user.get('username', '').lower() == username.lower():
            return True
    return False

# Routes
@app.route('/')
def homepage():
    return render_template('base.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        username = request.form['username']
        phone_number = request.form['phone_number']
        id_number = request.form['id_number']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if check_existing_user(phone_number, id_number, username=username):
            flash("An account with this username, phone number, or ID number already exists.", 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match!", 'error')
            return render_template('register.html')

        account_number = generate_account_number()
        users = read_users()
        users[str(account_number)] = {
            "name": name,
            "surname": surname,
            "username": username,
            "phone_number": phone_number,
            "id_number": id_number,
            "password": password,
            "balance": 0.0,
            "transaction_history": []
        }
        save_users(users)

        session['account_number'] = account_number
        session['user_name'] = name
        session['user_surname'] = surname
        flash(f"Account created successfully! Your account number is {account_number}.", 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = find_user_by_username_and_password(username, password)

        if user:
            session['account_number'] = user['account_number']
            session['user_name'] = user['name']
            session['user_surname'] = user['surname']
            flash("Login successful!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password", 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", 'success')
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    account_number = session.get('account_number')
    if not account_number:
        flash("Please log in first.", 'error')
        return redirect(url_for('login'))

    user = find_user(account_number)
    if user:
        balance = round(user['balance'], 2)
        return render_template(
            'dashboard.html',
            balance=balance,
            account_number=account_number,
            user_name=session.get('user_name'),
            user_surname=session.get('user_surname')
        )
    else:
        flash("User not found", 'error')
        return redirect(url_for('login'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("Passwords do not match!", 'error')
            return render_template('forgot_password.html')

        users = read_users()
        user_found = False
        for account_number, user in users.items():
            if user.get('username', '').lower() == username.lower():
                user['password'] = new_password
                save_users(users)
                flash("Your password has been updated successfully.", 'success')
                user_found = True
                break

        if not user_found:
            flash("User not found.", 'error')

        return redirect(url_for('login'))

    return render_template('forgot_password.html')

@app.route('/transaction_history')
def transaction_history():
    account_number = session.get('account_number')
    if not account_number:
        flash("Please log in first.", 'error')
        return redirect(url_for('login'))

    user = find_user(account_number)
    if user and isinstance(user['transaction_history'], list):
        filtered_transactions = [
            t for t in user['transaction_history'] if isinstance(t, dict) and t.get('amount', 0) > 0
        ]
        return render_template('transaction_history.html', transactions=filtered_transactions)

    flash("Transaction history is corrupted.", 'error')
    return redirect(url_for('dashboard'))

@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    account_number = session.get('account_number')
    if not account_number:
        flash("Please log in first.", 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
        except ValueError:
            flash("Invalid deposit amount!", 'error')
            return render_template('deposit.html')

        if amount <= 0:
            flash("Deposit amount must be greater than 0.", 'error')
        elif amount > MAX_AMOUNT:
            flash(f"Deposit amount cannot exceed R{MAX_AMOUNT}. Please visit the nearest branch.", 'error')
        else:
            user = find_user(account_number)
            if user:
                user['balance'] += amount
                user['balance'] = round(user['balance'], 2)
                user['transaction_history'].append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Deposit",
                    "amount": amount
                })
                users = read_users()
                users[str(account_number)] = user
                save_users(users)
                flash(f"Deposited R{amount}. New balance: R{user['balance']}", 'success')
                return redirect(url_for('dashboard'))

    return render_template('deposit.html')

@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    account_number = session.get('account_number')
    if not account_number:
        flash("Please log in first.", 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
        except ValueError:
            flash("Invalid withdraw amount!", 'error')
            return render_template('withdraw.html')

        user = find_user(account_number)
        if user:
            if user['balance'] >= amount:
                user['balance'] -= amount
                user['balance'] = round(user['balance'], 2)
                user['transaction_history'].append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Withdraw",
                    "amount": amount
                })
                users = read_users()
                users[str(account_number)] = user
                save_users(users)
                flash(f"Withdrew R{amount}. New balance: R{user['balance']}", 'success')
            else:
                flash("Insufficient funds", 'error')

            return redirect(url_for('dashboard'))

    return render_template('withdraw.html')

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    account_number = session.get('account_number')
    if not account_number:
        flash("Please log in first.", 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            recipient_account = request.form['recipient_account']
        except ValueError:
            flash("Invalid transfer details.", 'error')
            return render_template('transfer.html')

        if amount <= 0:
            flash("Transfer amount must be greater than 0.", 'error')
        elif amount > MAX_AMOUNT:
            flash(f"Transfer amount cannot exceed R{MAX_AMOUNT}. Please visit the nearest branch.", 'error')
        elif recipient_account == str(account_number):
            flash("You cannot transfer money to your own account.", 'error')
        else:
            user = find_user(account_number)
            recipient_user = find_user(recipient_account)
            if not user:
                flash("Your account is not found.", 'error')
            elif not recipient_user:
                flash("Recipient account not found.", 'error')
            elif user['balance'] < amount:
                flash("Insufficient funds", 'error')
            else:
                # Perform the transfer
                user['balance'] -= amount
                recipient_user['balance'] += amount
                user['transaction_history'].append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Transfer Out",
                    "amount": amount,
                    "to_account": recipient_account
                })
                recipient_user['transaction_history'].append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Transfer In",
                    "amount": amount,
                    "from_account": account_number
                })
                users = read_users()
                users[str(account_number)] = user
                users[str(recipient_account)] = recipient_user
                save_users(users)
                flash(f"Transferred R{amount} to account {recipient_account}.", 'success')

                return redirect(url_for('dashboard'))

    return render_template('transfer.html')

# Flask app entry point
if __name__ == '__main__':
    app.run(debug=True)
