from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import os
import subprocess

port = int(os.environ.get('PORT', 5001))

app = Flask(__name__)

REPO_URL = 'https://github.com/Janldeboer/ReDeploy'
CLONE_DIR = 'cloned_repo'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    prompt = request.form['prompt']
    # Process the prompt (this will be more complex later)
    return redirect(url_for('index'))


@app.route('/fetch_repo')
def fetch_repo():
    if os.path.exists(CLONE_DIR):
        subprocess.run(['rm', '-rf', CLONE_DIR])
    subprocess.run(['git', 'clone', REPO_URL, CLONE_DIR])
    return redirect(url_for('view_repo'))


@app.route('/view_repo')
def view_repo():
    if not os.path.exists(CLONE_DIR):
        return "Repository not cloned yet. Please fetch the repository first."
    
    files = os.listdir(CLONE_DIR)
    return render_template('view_repo.html', files=files)


@app.route('/cloned_repo/<path:filename>')
def serve_file(filename):
    return send_from_directory(CLONE_DIR, filename)


def main():
    app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
