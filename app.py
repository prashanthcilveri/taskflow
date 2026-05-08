from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'taskflow-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taskflow.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='member')
    projects = db.relationship('Project', backref='owner', lazy=True)
    tasks = db.relationship('Task', backref='assignee', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tasks = db.relationship('Task', backref='project', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='todo')
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    projects = Project.query.filter_by(owner_id=current_user.id).all()
    tasks = Task.query.filter_by(assigned_to=current_user.id).all()
    return render_template('index.html', projects=projects, tasks=tasks)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'member')
        if User.query.filter_by(email=email).first():
            flash('Email already exists!')
            return redirect(url_for('signup'))
        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_password, role=role)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please login.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid email or password!')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        project = Project(name=name, description=description, owner_id=current_user.id)
        db.session.add(project)
        db.session.commit()
        flash('Project created!')
        return redirect(url_for('index'))
    return render_template('new_project.html')

@app.route('/projects/<int:project_id>')
@login_required
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    tasks = Task.query.filter_by(project_id=project_id).all()
    users = User.query.all()
    return render_template('view_project.html', project=project, tasks=tasks, users=users)

@app.route('/tasks/new/<int:project_id>', methods=['GET', 'POST'])
@login_required
def new_task(project_id):
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        assigned_to = request.form.get('assigned_to')
        due_date_str = request.form.get('due_date')
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None
        task = Task(title=title, description=description, project_id=project_id, assigned_to=assigned_to, due_date=due_date)
        db.session.add(task)
        db.session.commit()
        flash('Task created!')
        return redirect(url_for('view_project', project_id=project_id))
    users = User.query.all()
    return render_template('new_task.html', project_id=project_id, users=users)

@app.route('/tasks/<int:task_id>/update', methods=['POST'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.status = request.form['status']
    db.session.commit()
    flash('Task updated!')
    return redirect(url_for('view_project', project_id=task.project_id))

@app.route('/dashboard')
@login_required
def dashboard():
    total_tasks = Task.query.filter_by(assigned_to=current_user.id).count()
    done_tasks = Task.query.filter_by(assigned_to=current_user.id, status='done').count()
    overdue_tasks = Task.query.filter(Task.assigned_to==current_user.id, Task.due_date < datetime.utcnow(), Task.status != 'done').all()
    projects = Project.query.filter_by(owner_id=current_user.id).all()
    return render_template('dashboard.html', total_tasks=total_tasks, done_tasks=done_tasks, overdue_tasks=overdue_tasks, projects=projects)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)