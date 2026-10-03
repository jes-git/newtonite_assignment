import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, g, jsonify, render_template, request

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['DATABASE'] = os.environ.get('DATABASE_PATH', os.path.join(os.getcwd(), 'data', 'work_items.db'))


def get_db():
    if 'db' not in g:
        db = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
        g.db = db
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    database_path = app.config['DATABASE']
    if database_path != ':memory:':
        db_dir = os.path.dirname(database_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    db = sqlite3.connect(database_path)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS user_teams (
            user_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            PRIMARY KEY (user_id, team_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS work_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'New',
            priority TEXT NOT NULL DEFAULT 'Medium',
            team_id INTEGER NOT NULL,
            assignee_id INTEGER,
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (team_id) REFERENCES teams(id),
            FOREIGN KEY (assignee_id) REFERENCES users(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS item_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            actor_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (item_id) REFERENCES work_items(id),
            FOREIGN KEY (actor_id) REFERENCES users(id)
        );
        """
    )

    seed_default_data(db)
    db.commit()
    db.close()


def seed_default_data(db):
    default_users = [
        (1, 'Ava Patel', 'ava@newtonite.local'),
        (2, 'Leo Chen', 'leo@newtonite.local'),
        (3, 'Mia Gomez', 'mia@newtonite.local'),
        (4, 'Noah Smith', 'noah@newtonite.local'),
    ]
    db.executemany(
        'INSERT OR IGNORE INTO users (id, name, email) VALUES (?, ?, ?)',
        default_users,
    )

    default_teams = [
        (1, 'Operations'),
        (2, 'Platform'),
        (3, 'Compliance'),
    ]
    db.executemany(
        'INSERT OR IGNORE INTO teams (id, name) VALUES (?, ?)',
        default_teams,
    )

    default_memberships = [
        (1, 1, 'admin'),
        (2, 1, 'member'),
        (3, 1, 'member'),
        (4, 2, 'lead'),
        (2, 2, 'member'),
        (3, 3, 'admin'),
        (4, 3, 'member'),
    ]
    db.executemany(
        'INSERT OR IGNORE INTO user_teams (user_id, team_id, role) VALUES (?, ?, ?)',
        default_memberships,
    )

    item_count = db.execute('SELECT COUNT(*) FROM work_items').fetchone()[0]
    if item_count == 0:
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        db.execute(
            """
            INSERT INTO work_items (
                title, description, status, priority, team_id, assignee_id,
                created_by, created_at, updated_at, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                'Payment investigation',
                'Investigate a failed customer payment before end of business day.',
                'In Progress',
                'High',
                1,
                1,
                1,
                now,
                now,
            ),
        )
        db.execute(
            """
            INSERT INTO item_history (item_id, action, details, actor_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, 'created', 'Initial item created by Ava Patel', 1, now),
        )
        db.execute(
            """
            INSERT INTO work_items (
                title, description, status, priority, team_id, assignee_id,
                created_by, created_at, updated_at, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                'Compliance review',
                'Check customer data export policy before release.',
                'New',
                'Medium',
                3,
                3,
                3,
                now,
                now,
            ),
        )
        db.execute(
            """
            INSERT INTO item_history (item_id, action, details, actor_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (2, 'created', 'Compliance item opened for review', 3, now),
        )


def current_user_id():
    user_id = request.args.get('user_id') or request.cookies.get('user_id') or 1
    return int(user_id)


@app.before_request
def set_current_user():
    g.user_id = current_user_id()


def user_can_access_team(user_id, team_id):
    row = get_db().execute(
        'SELECT 1 FROM user_teams WHERE user_id = ? AND team_id = ?',
        (user_id, team_id),
    ).fetchone()
    return row is not None


def fetch_item(item_id):
    item = get_db().execute(
        """
        SELECT wi.*, t.name AS team_name, a.name AS assignee_name, c.name AS creator_name
        FROM work_items wi
        LEFT JOIN teams t ON wi.team_id = t.id
        LEFT JOIN users a ON wi.assignee_id = a.id
        LEFT JOIN users c ON wi.created_by = c.id
        WHERE wi.id = ?
        """,
        (item_id,),
    ).fetchone()
    return dict(item) if item else None


def fetch_users():
    rows = get_db().execute('SELECT id, name, email FROM users ORDER BY name').fetchall()
    return [dict(row) for row in rows]


def fetch_teams():
    rows = get_db().execute('SELECT id, name FROM teams ORDER BY name').fetchall()
    return [dict(row) for row in rows]


def fetch_history(item_id):
    rows = get_db().execute(
        """
        SELECT h.*, u.name AS actor_name
        FROM item_history h
        LEFT JOIN users u ON h.actor_id = u.id
        WHERE h.item_id = ?
        ORDER BY h.created_at DESC, h.id DESC
        """,
        (item_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_items_for_user(user_id):
    rows = get_db().execute(
        """
        SELECT wi.*, t.name AS team_name, a.name AS assignee_name, c.name AS creator_name
        FROM work_items wi
        INNER JOIN user_teams ut ON ut.team_id = wi.team_id AND ut.user_id = ?
        LEFT JOIN teams t ON wi.team_id = t.id
        LEFT JOIN users a ON wi.assignee_id = a.id
        LEFT JOIN users c ON wi.created_by = c.id
        ORDER BY wi.updated_at DESC, wi.id DESC
        """,
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]


@app.route('/')
def index():
    items = fetch_items_for_user(g.user_id)
    return render_template('index.html', items=items, users=fetch_users(), teams=fetch_teams(), current_user_id=g.user_id)


@app.route('/api/users')
def api_users():
    return jsonify({'users': fetch_users()})


@app.route('/api/teams')
def api_teams():
    return jsonify({'teams': fetch_teams()})


@app.route('/api/items')
def list_items():
    items = fetch_items_for_user(g.user_id)
    return jsonify({'items': items})


@app.route('/api/items', methods=['POST'])
def create_item():
    payload = request.get_json(silent=True) or {}
    title = (payload.get('title') or '').strip()
    description = (payload.get('description') or '').strip()
    team_id = payload.get('team_id')
    assignee_id = payload.get('assignee_id', g.user_id)
    status = payload.get('status', 'New').strip() or 'New'
    priority = payload.get('priority', 'Medium').strip() or 'Medium'

    if not title or not team_id:
        return jsonify({'error': 'title and team_id are required'}), 400

    if not user_can_access_team(g.user_id, int(team_id)):
        return jsonify({'error': 'user is not authorized to work in this team'}), 403

    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO work_items (
            title, description, status, priority, team_id, assignee_id,
            created_by, created_at, updated_at, version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (title, description, status, priority, int(team_id), assignee_id, g.user_id, now, now),
    )
    item_id = cursor.lastrowid
    db.execute(
        "INSERT INTO item_history (item_id, action, details, actor_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (item_id, 'created', f'Item created by user {g.user_id}', g.user_id, now),
    )
    db.commit()
    item = fetch_item(item_id)
    return jsonify({'item': item, 'history': fetch_history(item_id)})


@app.route('/api/items/<int:item_id>')
def item_detail(item_id):
    item = fetch_item(item_id)
    if item is None:
        return jsonify({'error': 'item not found'}), 404
    if not user_can_access_team(g.user_id, item['team_id']):
        return jsonify({'error': 'user is not authorized to view this item'}), 403
    return jsonify({'item': item, 'history': fetch_history(item_id)})


@app.route('/api/items/<int:item_id>/update', methods=['POST'])
def update_item(item_id):
    payload = request.get_json(silent=True) or {}
    item = fetch_item(item_id)
    if item is None:
        return jsonify({'error': 'item not found'}), 404
    if not user_can_access_team(g.user_id, item['team_id']):
        return jsonify({'error': 'user is not authorized to update this item'}), 403

    incoming_version = payload.get('version')
    if incoming_version is None or int(incoming_version) != int(item['version']):
        return jsonify({'error': 'stale update: item version no longer matches the current value'}), 409

    db = get_db()
    title = payload.get('title', item['title'])
    description = payload.get('description', item['description'])
    status = payload.get('status', item['status'])
    priority = payload.get('priority', item['priority'])
    team_id = payload.get('team_id', item['team_id'])
    assignee_id = payload.get('assignee_id', item['assignee_id'])

    if not user_can_access_team(g.user_id, int(team_id)):
        return jsonify({'error': 'user is not authorized to move this item to the selected team'}), 403

    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    new_version = int(item['version']) + 1
    db.execute(
        """
        UPDATE work_items
        SET title = ?, description = ?, status = ?, priority = ?, team_id = ?, assignee_id = ?,
            updated_at = ?, version = ?
        WHERE id = ?
        """,
        (title, description, status, priority, int(team_id), assignee_id, now, new_version, item_id),
    )

    changes = []
    for field_name, new_value in {
        'title': title,
        'description': description,
        'status': status,
        'priority': priority,
        'team_id': int(team_id),
        'assignee_id': assignee_id,
    }.items():
        old_value = item.get(field_name)
        if field_name == 'assignee_id' and old_value is None and new_value is None:
            continue
        if old_value != new_value:
            changes.append(f'{field_name}: {old_value} -> {new_value}')

    if not changes:
        changes.append('metadata refreshed')

    db.execute(
        "INSERT INTO item_history (item_id, action, details, actor_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (item_id, 'updated', '; '.join(changes), g.user_id, now),
    )
    db.commit()

    refreshed_item = fetch_item(item_id)
    return jsonify({'item': refreshed_item, 'history': fetch_history(item_id)}), 200


@app.route('/health')
def health_check():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
