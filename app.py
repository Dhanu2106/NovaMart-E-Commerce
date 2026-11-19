
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "novamart-development-secret-change-before-deployment"
)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///novamart.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# User database model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)


# Product database model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


# Order database model
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default="Pending", nullable=False)

    product = db.relationship("Product", foreign_keys=[product_id])
    buyer = db.relationship("User", foreign_keys=[buyer_id])


# Role protection
def role_required(required_role):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))

            if session.get("role") != required_role:
                flash("You are not authorized to access this page.")
                return redirect(url_for("login"))

            return function(*args, **kwargs)
        return wrapper
    return decorator


# Home page
@app.route("/")
def home():
    return render_template("index.html")


# Registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        if not name or not email or not password:
            flash("Please fill all the fields.")
            return redirect(url_for("register"))

        if role not in ["buyer", "seller"]:
            flash("Please select a valid account type.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for("register"))

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session.clear()
            session["user_id"] = user.id
            session["name"] = user.name
            session["role"] = user.role
            session["cart"] = {}

            if user.role == "buyer":
                return redirect(url_for("buyer_dashboard"))
            elif user.role == "seller":
                return redirect(url_for("seller_dashboard"))
            elif user.role == "admin":
                return redirect(url_for("admin_dashboard"))

        flash("Invalid email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")

# Buyer dashboard
@app.route("/buyer")
@role_required("buyer")
def buyer_dashboard():

    selected_category = request.args.get("category", "").strip()

    # Get all available categories
    categories = [
        row[0] for row in
        db.session.query(Product.category)
        .filter(Product.stock > 0)
        .distinct()
        .order_by(Product.category)
        .all()
    ]

    # Get available products
    product_query = Product.query.filter(Product.stock > 0)

    # Filter products by selected category
    if selected_category:
        product_query = product_query.filter(
            Product.category.ilike(selected_category)
        )

    products = product_query.all()

    return render_template(
        "dashboard.html",
        role="Buyer",
        products=products,
        categories=categories,
        selected_category=selected_category
    )


# Seller dashboard
@app.route("/seller")
@app.route("/seller_dashboard")
@role_required("seller")
def seller_dashboard():
    return render_template(
        "seller_dashboard.html",
        name=session.get("name")
    )


# Add Product
@app.route("/add_product", methods=["GET", "POST"])
@role_required("seller")
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()

        try:
            price = float(request.form.get("price", 0))
            stock = int(request.form.get("stock", 0))
        except ValueError:
            flash("Enter valid price and stock.")
            return redirect(url_for("add_product"))

        if not name or not description or not category:
            flash("Please fill all fields.")
            return redirect(url_for("add_product"))

        if price <= 0 or stock < 0:
            flash("Enter a valid price and stock.")
            return redirect(url_for("add_product"))

        product = Product(
            name=name,
            description=description,
            price=price,
            category=category,
            stock=stock,
            seller_id=session["user_id"]
        )

        db.session.add(product)
        db.session.commit()

        flash("Product added successfully!")
        return redirect(url_for("seller_dashboard"))

    return render_template("add_product.html")


# My Products
@app.route("/my_products")
@role_required("seller")
def my_products():
    products = Product.query.filter_by(
        seller_id=session["user_id"]
    ).all()

    return render_template("my_products.html", products=products)


# Add product to cart
@app.route("/add_to_cart/<int:product_id>", methods=["POST"])
@role_required("buyer")
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)

    if product.stock <= 0:
        flash("This product is out of stock.")
        return redirect(url_for("buyer_dashboard"))

    cart = session.get("cart", {})
    product_key = str(product_id)
    current_quantity = int(cart.get(product_key, 0))

    if current_quantity >= product.stock:
        flash("You cannot add more than the available stock.")
    else:
        cart[product_key] = current_quantity + 1
        session["cart"] = cart
        flash("Product added to cart!")

    return redirect(url_for("buyer_dashboard"))


# View cart
@app.route("/cart")
@role_required("buyer")
def view_cart():
    cart = session.get("cart", {})
    cart_items = []
    grand_total = 0

    for product_id, quantity in cart.items():
        product = db.session.get(Product, int(product_id))

        if product:
            subtotal = product.price * int(quantity)
            cart_items.append({
                "product": product,
                "quantity": int(quantity),
                "subtotal": subtotal
            })
            grand_total += subtotal

    return render_template(
        "cart.html",
        cart_items=cart_items,
        grand_total=grand_total
    )


# Remove item from cart
@app.route("/remove_from_cart/<int:product_id>", methods=["POST"])
@role_required("buyer")
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    cart.pop(str(product_id), None)
    session["cart"] = cart
    flash("Product removed from cart.")
    return redirect(url_for("view_cart"))


# Checkout and place orders
@app.route("/checkout", methods=["POST"])
@role_required("buyer")
def checkout():
    cart = session.get("cart", {})

    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for("view_cart"))

    for product_id, quantity in cart.items():
        product = db.session.get(Product, int(product_id))

        if product is None:
            flash("Product not found.")
            return redirect(url_for("view_cart"))

        quantity = int(quantity)

        if quantity <= 0 or product.stock < quantity:
            flash(f"Insufficient stock for {product.name}.")
            return redirect(url_for("view_cart"))

    try:
        for product_id, quantity in cart.items():
            product = db.session.get(Product, int(product_id))
            quantity = int(quantity)

            order = Order(
                buyer_id=session["user_id"],
                seller_id=product.seller_id,
                product_id=product.id,
                quantity=quantity,
                total=product.price * quantity,
                status="Pending"
            )

            product.stock -= quantity
            db.session.add(order)

        db.session.commit()
        session["cart"] = {}

        flash("Order placed successfully!")
        return redirect(url_for("buyer_dashboard"))

    except Exception as e:
        db.session.rollback()
        print("CHECKOUT ERROR:", e)
        flash("Unable to place order. Please try again.")
        return redirect(url_for("view_cart"))
# Seller Manage Orders
@app.route("/manage_orders")
@role_required("seller")
def manage_orders():
    orders = Order.query.filter_by(
        seller_id=session["user_id"]
    ).order_by(Order.id.desc()).all()

    return render_template("manage_orders.html", orders=orders)

# Buyer Order History
@app.route("/my_orders")
@role_required("buyer")
def my_orders():
    orders = Order.query.filter_by(
        buyer_id=session["user_id"]
    ).order_by(Order.id.desc()).all()

    return render_template(
        "my_orders.html",
        orders=orders
    )


# Update order status
@app.route("/update_order_status/<int:order_id>", methods=["POST"])
@role_required("seller")
def update_order_status(order_id):
    order = Order.query.filter_by(
        id=order_id,
        seller_id=session["user_id"]
    ).first_or_404()

    status = request.form.get("status", "")

    if status not in ["Pending", "Shipped", "Delivered", "Cancelled"]:
        flash("Invalid order status.")
    else:
        order.status = status
        db.session.commit()
        flash("Order status updated successfully!")

    return redirect(url_for("manage_orders"))

# Admin dashboard
# Admin dashboard
@app.route("/admin")
@role_required("admin")
def admin_dashboard():
    buyers = User.query.filter_by(role="buyer").all()
    sellers = User.query.filter_by(role="seller").all()
    products = Product.query.all()

    return render_template(
        "dashboard.html",
        role="Admin",
        products=products,
        buyers=buyers,
        sellers=sellers
    )


# Admin: Delete Product
@app.route("/admin/delete_product/<int:product_id>", methods=["POST"])
@role_required("admin")
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    existing_order = Order.query.filter_by(
        product_id=product.id
    ).first()

    if existing_order:
        flash("Cannot delete this product because it has order history.")
    else:
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted successfully!")

    return redirect(url_for("admin_dashboard"))


# Admin: Delete Buyer or Seller
@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@role_required("admin")
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.role not in ["buyer", "seller"]:
        flash("This account cannot be deleted.")
        return redirect(url_for("admin_dashboard"))

    existing_order = Order.query.filter(
        (Order.buyer_id == user.id) |
        (Order.seller_id == user.id)
    ).first()

    existing_product = Product.query.filter_by(
        seller_id=user.id
    ).first()

    if existing_order:
        flash("Cannot delete this user because they have order history.")
    elif existing_product:
        flash("Cannot delete this seller because they have products.")
    else:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully!")

    return redirect(url_for("admin_dashboard"))

# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out successfully.")
    return redirect(url_for("home"))


# Create database and demo admin account
with app.app_context():
    db.create_all()

    admin = User.query.filter_by(email="admin@novamart.com").first()

    if not admin:
        admin = User(
            name="NovaMart Admin",
            email="admin@novamart.com",
            password=generate_password_hash("Admin@12345"),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()


if __name__ == "__main__":
    app.run(debug=True)
