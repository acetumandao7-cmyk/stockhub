from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(
            full_name='System Admin',
            username='admin',
            password_hash=generate_password_hash('admin123', method='scrypt'),
            role='Admin',
            status='Active'
        )
        db.session.add(admin)
        db.session.commit()
        print("Default admin created: Username: admin | Password: admin123")
    else:
        print("Admin user already exists.")