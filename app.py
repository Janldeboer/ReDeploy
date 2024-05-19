from flask import Flask, request, render_template, redirect, url_for
import os
import subprocess
import requests
import logging
import urllib.parse
from base64 import b64encode
from openai import OpenAI
import patch

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = 'Janldeboer/ReDeploy'
GITHUB_BRANCH = 'main'

REPO_URL = 'https://github.com/Janldeboer/ReDeploy'
CLONE_DIR = 'cloned_repo'

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('app.log'),
                        logging.StreamHandler()
                    ])

logger = logging.getLogger(__name__)

port = int(os.environ.get('PORT', 5001))

openai = OpenAI()

app = Flask(__name__)

with open('prompt.txt', 'r') as f:
    prompt_template = f.read()

def call_openai_api(prompt):
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = completion.choices[0].message.content
        logger.info(f'Answer from OpenAI: {answer}')
        return answer
    except Exception as e:
        logger.error(f'Error calling OpenAI API: {e}')
        logger.error(f'Completion attributes: {completion.model_dump()}')
        return "No changes"
    
def apply_answer_to_git(answer):
    changes = retrieve_file_changes(answer)
    for file_path, patch_content in changes.items():
        apply_patch_to_file(file_path, patch_content)
    logger.info('Changes applied and pushed to GitHub.')

def apply_patch_to_file(file_path, patch_content):
    patch_set = patch.fromstring(patch_content)
    if patch_set.apply():
        logger.info(f'Patch applied successfully to {file_path}.')
        update_file_on_github(file_path, patch_content)
    else:
        logger.error(f'Failed to apply patch to {file_path}.')

def update_file_on_github(file_path, new_content):
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{urllib.parse.quote(file_path)}'
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        # Get the SHA of the file to update it
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        sha = response.json()['sha']
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            sha = None
        else:
            logger.error(f'Error getting file SHA: {e}')
            return

    # Prepare the data for the commit
    data = {
        'message': 'AI generated changes',
        'content': b64encode(new_content.encode()).decode(),
        'branch': GITHUB_BRANCH
    }
    if sha:
        data['sha'] = sha

    # Push the commit
    response = requests.put(url, json=data, headers=headers)
    response.raise_for_status()
    
    logger.info(f'Updated {file_path} successfully.')

def retrieve_file_changes(answer):
    changes = {}
    lines = answer.split('\n')
    patch_content = []
    in_patch_block = False
    
    for line in lines:
        if line.startswith('diff --git'):
            if in_patch_block:
                changes[file_path] = '\n'.join(patch_content)
            in_patch_block = True
            patch_content = [line]
            file_path = line.split(' ')[2][2:]  # Extract the file path from the diff line
        elif in_patch_block:
            patch_content.append(line)
    
    if in_patch_block:
        changes[file_path] = '\n'.join(patch_content)
    
    return changes

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    user_prompt = request.form['prompt']
    code = concatenate_files_content(CLONE_DIR)
    prompt = prompt_template.format(prompt=user_prompt, code=code)
    answer = call_openai_api(prompt)
    apply_answer_to_git(answer)
    return redirect(url_for('index'))

def concatenate_files_content(dir_path):
    concatenated_content = []
    for root, dirs, files in os.walk(dir_path):
        for _file in files:
            if _file.startswith('.'):
                continue
            file_path = os.path.join(root, _file)
            try: 
                with open(file_path, 'r') as f:
                    content = f.read()
                file_rel_path = os.path.relpath(file_path, dir_path)
                concatenated_content.append(f'```{file_rel_path}\n{content}\n```\n')
            except Exception as e:
                logger.error(f'Error reading file {file_path}: {e}')
    return '\n'.join(concatenated_content)

def main():
    if not os.path.exists(CLONE_DIR):
        os.makedirs(CLONE_DIR, exist_ok=True)
        subprocess.run(['git', 'clone', REPO_URL, CLONE_DIR])
    
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()
