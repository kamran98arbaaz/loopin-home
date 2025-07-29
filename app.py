import os
import json
import uuid
import pytz
IST = pytz.timezone('Asia/Kolkata')

from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = 'replace-this-with-a-secure-random-string'
app.config['APP_NAME'] = 'LoopIn'

# where we'll store the updates
UPDATES_FILE = os.path.join(app.root_path, 'updates.json')

# helpers to load & save from JSON
def load_updates():
    if not os.path.exists(UPDATES_FILE):
        # create the file if it's not there
        with open(UPDATES_FILE, 'w') as f:
            json.dump([], f)
        return []
    with open(UPDATES_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_updates(updates_list):
    with open(UPDATES_FILE, 'w') as f:
        json.dump(updates_list, f, indent=2)


# who’s allowed to post
authorized_users = ['Kamran Arbaz', 'Drishya CM', 'Abigail Das']


@app.route('/')
def home():
    return render_template('home.html', app_name=app.config['APP_NAME'])


@app.route('/updates')
def show_updates():
    updates = load_updates()
    current_user = session.get('username')
    return render_template(
        'show.html',
        app_name=app.config['APP_NAME'],
        updates=updates,
        current_user=current_user
    )


@app.route('/post', methods=['GET', 'POST'])
def post_update():
    if request.method == 'POST':
        name = request.form['name']
        message = request.form['message'].strip()

        if name not in authorized_users:
            flash('🚫 You are not authorized to post updates.')
            return redirect(url_for('post_update'))

        # remember who’s posting
        session['username'] = name

        # load existing, prepend new, save
        updates = load_updates()
        updates.insert(0, {
            'id': uuid.uuid4().hex,
            'name': name,
            'message': message,
            'timestamp': datetime.now(IST).strftime('%d/%m/%Y, %H:%M:%S')
        })
        save_updates(updates)

        flash('✅ Update posted.')
        return redirect(url_for('show_updates'))

    current_user = session.get('username')
    return render_template(
        'post.html',
        app_name=app.config['APP_NAME'],
        authorized_users=authorized_users,
        current_user=current_user
    )


@app.route('/edit/<update_id>', methods=['GET', 'POST'])
def edit_update(update_id):
    updates = load_updates()
    # find the update
    update = next((u for u in updates if u['id'] == update_id), None)
    if not update:
        flash('⚠️ Update not found.')
        return redirect(url_for('show_updates'))

    current_user = session.get('username')
    if update['name'] != current_user:
        flash('🚫 You can only edit your own updates.')
        return redirect(url_for('show_updates'))

    if request.method == 'POST':
        update['message'] = request.form['message'].strip()
        update['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_updates(updates)
        flash('✏️ Update edited successfully.')
        return redirect(url_for('show_updates'))

    return render_template(
        'edit.html',
        app_name=app.config['APP_NAME'],
        update=update
    )


@app.route('/delete/<update_id>', methods=['POST'])
def delete_update(update_id):
    updates = load_updates()
    update = next((u for u in updates if u['id'] == update_id), None)
    if not update:
        flash('⚠️ Update not found.')
        return redirect(url_for('show_updates'))

    current_user = session.get('username')
    if update['name'] != current_user:
        flash('🚫 You can only delete your own updates.')
        return redirect(url_for('show_updates'))

    # remove & persist
    updates.remove(update)
    save_updates(updates)
    flash('🗑️ Update deleted.')
    return redirect(url_for('show_updates'))


if __name__ == '__main__':
    app.run(debug=True)
