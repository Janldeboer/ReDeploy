from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    prompt = request.form['prompt']
    # Process the prompt (this will be more complex later)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
