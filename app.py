from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import os
import subprocess
import logging
from openai import OpenAI

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

REPO_URL = 'https://github.com/Janldeboer/ReDeploy'
CLONE_DIR = 'cloned_repo'

prompt_template = """You are a software developer, improving a web app by executing new requests.

Below, you find a prompt of code changes and the available files, in code blocks, e.g.
```topfolder/subdir/file.py
# code may be here
```
One code block per file, with the filename in the header.
To change files, answer with code blocks in the same format.
Make sure to use the correct file names and folders and not to leave any placeholders in the code, as it will be deployed as is.


Prompt:
"{prompt}"

Code:
{code}"""

def call_openai_api(prompt):
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].text.strip()
    except Exception as e:
        logger.error(f'Error calling OpenAI API: {e}')
        logger.error(f'Completion attributes: {completion.model_dump()}')
        return "No changes"

def apply_answer_to_git(answer):
    changes = retrieve_file_changes(answer)
    for file_path, new_content in changes.items():
        with open(os.path.join(CLONE_DIR, file_path), 'w') as file:
            file.write(new_content)
    subprocess.run(['git', '-C', CLONE_DIR, 'add', '.'])
    subprocess.run(['git', '-C', CLONE_DIR, 'commit', '-m', 'Applied changes from OpenAI API'])

def retrieve_file_changes(answer):
    changes = {}
    lines = answer.split('\n')
    file_path = None
    content = []
    in_code_block = False
    
    for line in lines:
        if line.startswith('```') and not in_code_block:
            in_code_block = True
            file_path = line[3:].strip()
            content = []
        elif line.startswith('```') and in_code_block:
            in_code_block = False
            changes[file_path] = '\n'.join(content)
        elif in_code_block:
            content.append(line)
    
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
    combined = concatenate_files_content(CLONE_DIR)
    return render_template('view_repo.html', files=files, combined=combined)


@app.route('/cloned_repo/<path:filename>')
def serve_file(filename):
    return send_from_directory(CLONE_DIR, filename)

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
    app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
