from flask import Blueprint, Flask, request, render_template, redirect, session, jsonify, flash
from flask_rollup import Bundle
from flask_ckeditor import CKEditor
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from dotenv import dotenv_values
from urllib.request import urlopen
from urllib.parse import urlencode
from utilities import ArticleDb
import os
import base64

# os.system("npm run")
config = dotenv_values('.env')

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ckeditor = CKEditor(app)
# Use when implementing module
# budgets = Blueprint('budgets', __name__,
#                            template_folder='templates',
#                            static_folder='static',
#                            static_url_path='/static/budgets')

# initialize CSRF protection
csrf = CSRFProtect(app)

# checks if working in local development environment or production environment
if 'PUBLIC' in os.environ:
    # if connection string is not in local environment variables then we are working in local environment
    db = ArticleDb(config['LOCAL_DB'])
    app.secret_key = config['SECRET_KEY']
else:
    # production
    print('Loading config.production.')

    # conn_str = current_app.config.get('CONN_STRING')

    db = ArticleDb(os.environ['CONN_STRING'])



@app.route('/')
def news_page():  # put application's code here
    return render_template('news_page.html')

@app.route('/articles/drafts')
def posts_drafts():
    return render_template('articles_drafts.html')

@app.route('/articles/published')
def posts_published():
    return render_template('articles_published.html')

@app.route('/articles/new_article')
def new_article():
    new_id = db.new_article_id()

    return render_template('new_article.html', article_id=new_id)

@app.route('/articles/save_draft')
def save_draft():
    print("Test")

@app.post('/uploadimage')
def upload_image():
    image_load = request.files.get('image')

    filename = secure_filename(image_load.filename)
    print(filename)
    image = base64.b64encode(image_load.read())

    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "wb") as fh:
        fh.write(base64.decodebytes(image))


    article_id = request.form.get('articleId')

    db.add_article_image(article_id, filename, image)

    return jsonify({'location': "/static/uploads/"+filename})

@app.post('/articles/publish')
def publish_article():
    title = request.form.get('title')
    thumbnail = request.files.get('thumbnail')

    image = base64.b64encode(thumbnail.read())

    with open(os.path.join(app.config['UPLOAD_FOLDER'], "article_thumbnail.jpg"), "wb") as fh:
        fh.write(base64.decodebytes(image))

    print(title)
    print(thumbnail)

    return jsonify(results="Complete")

if __name__ == '__main__':
    app.run()
