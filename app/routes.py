from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from app import db, mail
from app.models import User, Product, Category, Supplier, Transaction
from datetime import date
from sqlalchemy import func

main = Blueprint('main', __name__)

def send_notification_email(subject, recipient, body):
    """Helper function para magpadala ng email notification"""
    try:
        msg = Message(subject, sender=('StockHub Admin', 'noreply@stockhub.com'), recipients=[recipient])
        msg.body = body
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")

@main.route('/')
@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please fill in both username and password fields.', 'danger')
            return redirect(url_for('main.login'))

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            if user.status == 'Inactive':
                flash('Your account is inactive. Please contact the administrator.', 'danger')
                return redirect(url_for('main.login'))

            login_user(user)
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.login'))

# --- DASHBOARD ---

@main.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    
    total_products = Product.query.count()
    low_stock_count = Product.query.filter(Product.quantity <= 5).count()
    
    stock_in_today = db.session.query(func.coalesce(func.sum(Transaction.quantity), 0)).filter(
        Transaction.transaction_type == 'STOCK_IN',
        func.date(Transaction.timestamp) == today
    ).scalar()

    stock_out_today = db.session.query(func.coalesce(func.sum(Transaction.quantity), 0)).filter(
        Transaction.transaction_type == 'STOCK_OUT',
        func.date(Transaction.timestamp) == today
    ).scalar()

    recent_txns = Transaction.query.order_by(Transaction.timestamp.desc()).limit(5).all()
    low_stock_items = Product.query.filter(Product.quantity <= 5).all()
    
    return render_template('dashboard.html', 
                           total_products=total_products, 
                           low_stock_count=low_stock_count,
                           stock_in_today=stock_in_today,
                           stock_out_today=stock_out_today,
                           recent_txns=recent_txns,
                           low_stock_items=low_stock_items)

@main.route('/products')
@login_required
def products():
    all_products = Product.query.all()
    categories = Category.query.all()
    suppliers = Supplier.query.all()
    return render_template('products.html', products=all_products, categories=categories, suppliers=suppliers)

@main.route('/products/add', methods=['POST'])
@login_required
def add_product():
    name = request.form.get('name', '').strip()
    category_id = request.form.get('category_id')
    supplier_id = request.form.get('supplier_id')
    quantity = request.form.get('quantity', type=int)
    price = request.form.get('price', type=float)

    if not name:
        flash('Product name is required!', 'danger')
        return redirect(url_for('main.products'))
    
    if Product.query.filter(func.lower(Product.name) == func.lower(name)).first():
        flash(f'Product "{name}" already exists!', 'warning')
        return redirect(url_for('main.products'))

    if quantity is None or quantity < 0:
        flash('Quantity cannot be empty or negative!', 'danger')
        return redirect(url_for('main.products'))

    if price is None or price < 0:
        flash('Price cannot be empty or negative!', 'danger')
        return redirect(url_for('main.products'))

    new_product = Product(
        name=name,
        category_id=int(category_id) if category_id else None,
        supplier_id=int(supplier_id) if supplier_id else None,
        quantity=quantity,
        price=price
    )
    db.session.add(new_product)
    db.session.commit()

    if quantity <= 5:
        send_notification_email(
            subject=f'Low Stock Alert: {name}',
            recipient='admin@stockhub.com',
            body=f'The newly added product "{name}" has a low stock level of {quantity} units.'
        )

    flash(f'Product "{name}" added successfully!', 'success')
    return redirect(url_for('main.products'))

@main.route('/products/edit/<int:id>', methods=['POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    name = request.form.get('name', '').strip()
    category_id = request.form.get('category_id')
    supplier_id = request.form.get('supplier_id')
    quantity = request.form.get('quantity', type=int)
    price = request.form.get('price', type=float)

    if not name:
        flash('Product name cannot be blank!', 'danger')
        return redirect(url_for('main.products'))

    if quantity is None or quantity < 0:
        flash('Quantity cannot be negative!', 'danger')
        return redirect(url_for('main.products'))

    if price is None or price < 0:
        flash('Price cannot be negative!', 'danger')
        return redirect(url_for('main.products'))

    product.name = name
    product.category_id = int(category_id) if category_id else None
    product.supplier_id = int(supplier_id) if supplier_id else None
    product.quantity = quantity
    product.price = price

    db.session.commit()

    if quantity <= 5:
        send_notification_email(
            subject=f'Low Stock Alert: {name}',
            recipient='admin@stockhub.com',
            body=f'Product "{name}" updated. Current stock level is now critical at {quantity} units.'
        )

    flash(f'Product "{name}" updated successfully!', 'success')
    return redirect(url_for('main.products'))

@main.route('/products/delete/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    product_name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{product_name}" has been deleted.', 'success')
    return redirect(url_for('main.products'))

@main.route('/categories')
@login_required
def categories():
    all_categories = Category.query.all()
    return render_template('categories.html', categories=all_categories)

@main.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    category_name = request.form.get('category_name', '').strip()
    description = request.form.get('description', '').strip()

    if not category_name:
        flash('Category name is required!', 'danger')
        return redirect(url_for('main.categories'))

    existing = Category.query.filter(func.lower(Category.category_name) == func.lower(category_name)).first()
    if existing:
        flash(f'Category "{category_name}" already exists!', 'warning')
        return redirect(url_for('main.categories'))

    new_category = Category(category_name=category_name, description=description)
    db.session.add(new_category)
    db.session.commit()
    flash(f'Category "{category_name}" added successfully!', 'success')
    return redirect(url_for('main.categories'))

@main.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    cat_name = category.category_name
    db.session.delete(category)
    db.session.commit()
    flash(f'Category "{cat_name}" deleted successfully.', 'success')
    return redirect(url_for('main.categories'))

@main.route('/suppliers')
@login_required
def suppliers():
    all_suppliers = Supplier.query.all()
    return render_template('suppliers.html', suppliers=all_suppliers)

@main.route('/suppliers/add', methods=['POST'])
@login_required
def add_supplier():
    supplier_name = request.form.get('supplier_name', '').strip()
    contact_person = request.form.get('contact_person', '').strip()
    contact_no = request.form.get('contact_no', '').strip()

    if not supplier_name:
        flash('Supplier name is required!', 'danger')
        return redirect(url_for('main.suppliers'))

    existing = Supplier.query.filter(func.lower(Supplier.supplier_name) == func.lower(supplier_name)).first()
    if existing:
        flash(f'Supplier "{supplier_name}" already exists!', 'warning')
        return redirect(url_for('main.suppliers'))

    new_supplier = Supplier(
        supplier_name=supplier_name,
        contact_person=contact_person,
        contact_no=contact_no
    )
    db.session.add(new_supplier)
    db.session.commit()
    flash(f'Supplier "{supplier_name}" added successfully!', 'success')
    return redirect(url_for('main.suppliers'))

@main.route('/suppliers/delete/<int:id>', methods=['POST'])
@login_required
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    sup_name = supplier.supplier_name
    db.session.delete(supplier)
    db.session.commit()
    flash(f'Supplier "{sup_name}" deleted successfully.', 'success')
    return redirect(url_for('main.suppliers'))

@main.route('/transactions')
@login_required
def transactions():
    all_txns = Transaction.query.order_by(Transaction.timestamp.desc()).all()
    products = Product.query.all()
    return render_template('transactions.html', transactions=all_txns, products=products)

@main.route('/transactions/stock_in', methods=['POST'])
@login_required
def stock_in():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int)

    if not product_id:
        flash('Please select a product!', 'danger')
        return redirect(url_for('main.transactions'))

    if quantity is None or quantity <= 0:
        flash('Quantity must be greater than zero!', 'danger')
        return redirect(url_for('main.transactions'))

    product = Product.query.get_or_404(product_id)
    product.quantity += quantity

    txn = Transaction(
        transaction_type='STOCK_IN',
        quantity=quantity,
        product_id=product.id,
        user_id=current_user.id
    )
    db.session.add(txn)
    db.session.commit()
    flash(f'Successfully added {quantity} unit(s) to "{product.name}".', 'success')
    return redirect(url_for('main.transactions'))

@main.route('/transactions/stock_out', methods=['POST'])
@login_required
def stock_out():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int)

    if not product_id:
        flash('Please select a product!', 'danger')
        return redirect(url_for('main.transactions'))

    if quantity is None or quantity <= 0:
        flash('Quantity must be greater than zero!', 'danger')
        return redirect(url_for('main.transactions'))

    product = Product.query.get_or_404(product_id)
    if product.quantity >= quantity:
        product.quantity -= quantity

        txn = Transaction(
            transaction_type='STOCK_OUT',
            quantity=quantity,
            product_id=product.id,
            user_id=current_user.id
        )
        db.session.add(txn)
        db.session.commit()

        if product.quantity <= 5:
            send_notification_email(
                subject=f'CRITICAL: Low Stock Warning for {product.name}',
                recipient='admin@stockhub.com',
                body=f'A stock out transaction triggered a low stock warning. Product: "{product.name}" now has only {product.quantity} remaining unit(s).'
            )

        flash(f'Successfully deducted {quantity} unit(s) from "{product.name}".', 'success')
    else:
        flash(f'Insufficient stock for "{product.name}"! Current stock is only {product.quantity}.', 'danger')
    return redirect(url_for('main.transactions'))

@main.route('/users')
@login_required
def users():
    all_users = User.query.all()
    return render_template('users.html', users=all_users)

@main.route('/users/add', methods=['POST'])
@login_required
def add_user():
    full_name = request.form.get('full_name', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role')
    contact_no = request.form.get('contact_no', '').strip()

    if not full_name or not username or not password:
        flash('Full Name, Username, and Password are required!', 'danger')
        return redirect(url_for('main.users'))

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash(f'Username "{username}" is already taken!', 'warning')
        return redirect(url_for('main.users'))

    hashed_password = generate_password_hash(password, method='scrypt')
    new_user = User(
        full_name=full_name,
        username=username,
        password_hash=hashed_password,
        role=role,
        contact_no=contact_no
    )
    db.session.add(new_user)
    db.session.commit()

    send_notification_email(
        subject='New User Account Created',
        recipient='admin@stockhub.com',
        body=f'A new account for {full_name} ({username}) with role {role} has been successfully created.'
    )

    flash(f'User account for "{full_name}" created successfully!', 'success')
    return redirect(url_for('main.users'))

@main.route('/users/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if id == current_user.id:
        flash('Action denied: You cannot delete your own logged-in account!', 'danger')
        return redirect(url_for('main.users'))

    user = User.query.get_or_404(id)
    uname = user.full_name
    db.session.delete(user)
    db.session.commit()
    flash(f'User account "{uname}" has been deleted.', 'success')
    return redirect(url_for('main.users'))

@main.route('/reports')
@login_required
def reports():
    products = Product.query.all()
    total_inventory_value = sum(p.quantity * p.price for p in products)
    total_units_in_stock = sum(p.quantity for p in products)
    
    total_stock_in_txns = Transaction.query.filter_by(transaction_type='STOCK_IN').count()
    total_stock_out_txns = Transaction.query.filter_by(transaction_type='STOCK_OUT').count()
    
    return render_template('reports.html', 
                           products=products,
                           total_inventory_value=total_inventory_value,
                           total_units_in_stock=total_units_in_stock,
                           total_stock_in_txns=total_stock_in_txns,
                           total_stock_out_txns=total_stock_out_txns)