        return redirect(url_for('main.transactions'))

    if quantity is None or quantity <= 0:
        flash('Quantity must be greater than zero!', 'danger')
        return redirect(url_for('main.transactions'))

    product = Product.query.get_or_404(product_id)
    product.quantity += quantity

    transaction = Transaction(
        product_id=product.id,
        transaction_type='STOCK_IN',
        quantity=quantity,
        user_id=current_user.id
    )

    db.session.add(transaction)
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

        admin_email = "ace.tumandao7@gmail.com"
        body = f"""[STOCKHUB TRANSACTION - STOCK OUT]
Product: {product.name}
Quantity Deducted: {quantity}
Remaining Stock: {product.quantity}
Executed By: {current_user.full_name} ({current_user.role})"""
        
        if product.quantity <= 5:
            body += f"\n\nCRITICAL WARNING: Product '{product.name}' has reached low stock level ({product.quantity} left)!"

        send_email_notification(f"Stock Out Alert: {product.name}", admin_email, body)

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