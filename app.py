import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
from config import Config
from tailscale_api import TailscaleAPI

app = Flask(__name__)
app.config.from_object(Config)

ts_api = TailscaleAPI(
    api_key=app.config['TAILSCALE_API_KEY'],
    tailnet=app.config['TAILNET']
)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not app.config.get('AUTH_ENABLED'):
            return f(*args, **kwargs)
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html',
                           title=app.config['APP_TITLE'],
                           auth_enabled=app.config['AUTH_ENABLED'],
                           refresh_interval=app.config['REFRESH_INTERVAL'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if not app.config.get('AUTH_ENABLED'):
        return redirect(url_for('dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if (username == app.config['AUTH_USERNAME'] and
                password == app.config['AUTH_PASSWORD']):
            session['authenticated'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials. Please try again.'

    return render_template('login.html',
                           title=app.config['APP_TITLE'], error=error)


@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))


@app.route('/api/nodes')
@login_required
def api_nodes():
    try:
        nodes = ts_api.get_devices()
        online = [n for n in nodes if n['is_online']]
        offline = [n for n in nodes if not n['is_online']]
        return jsonify({
            'status': 'ok',
            'nodes': nodes,
            'summary': {
                'total': len(nodes),
                'online': len(online),
                'offline': len(offline)
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html',
                           title=app.config['APP_TITLE'],
                           error_code=404,
                           error_message='Page not found.'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html',
                           title=app.config['APP_TITLE'],
                           error_code=500,
                           error_message='Internal server error.'), 500


if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'],
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)))
