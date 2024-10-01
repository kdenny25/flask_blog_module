from flask import Blueprint, Flask, request, render_template, redirect, session, jsonify, flash
from flask_rollup import Bundle
from jinja2 import Environment, BaseLoader
from flask_ckeditor import CKEditor
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from dotenv import dotenv_values
from urllib.request import urlopen
from urllib.parse import urlencode
from utilities import ArticleDb
from datetime import datetime
import re
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



@app.route('/articles/browse')
def browse_articles():  # put application's code here
    topics = db.get_topics()
    articles = [list(draft) for draft in db.get_articles('publish')]
    images = []
    for idx, draft in enumerate(articles):
        images.append(bytes(draft[9]).decode('utf-8'))
    return render_template('browse_articles.html', articles=articles, thumbnails=images, topics=topics)

@app.route('/articles/read/<id>')
def read_article(id):
    article = db.get_article(id)
    images = db.get_article_images(id)
    thumbnail = bytes(article[9]).decode('utf-8')

    article_con = Environment(loader=BaseLoader).from_string(article[10])
    content = render_template(article_con, image=images)

    return render_template('article_view.html', article=article, thumbnail=thumbnail, image=images, content=content)
@app.route('/articles/drafts')
def posts_drafts():
    drafts = [list(draft) for draft in db.get_articles('draft')]
    images = []
    for idx, draft in enumerate(drafts):
        images.append(bytes(draft[9]).decode('utf-8'))

    return render_template('articles_drafts.html', drafts=drafts, images=images)

@app.route('/articles/published')
def posts_published():
    published = [list(draft) for draft in db.get_articles('publish')]
    images = []
    for idx, draft in enumerate(published):
        images.append(bytes(draft[9]).decode('utf-8'))

    return render_template('articles_published.html', published=published, images=images)

@app.route('/articles/new_article')
def new_article():
    new_id = db.new_article_id()
    try:
        topics = db.get_topics()
    except:
        topics = []
    return render_template('new_article.html', article_id=new_id, topics=topics)

@app.route('/articles/edit_article/<id>')
def edit_article(id):
    article = db.get_article(id)
    images = db.get_article_images(id)

    try:
        topics = db.get_topics()
    except:
        topics = []

    article_con = Environment(loader=BaseLoader).from_string(article[10])
    content = render_template(article_con, image=images)
    thumbnail = bytes(article[9]).decode('utf-8')

    return render_template('edit_article.html', article=article, thumbnail=thumbnail, topics=topics, image=images, content=content)

@app.route('/articles/preview/<id>')
def preview_article(id):
    article = db.get_article(id)
    images = db.get_article_images(id)
    thumbnail = bytes(article[9]).decode('utf-8')

    article_con = Environment(loader=BaseLoader).from_string(article[10])
    content = render_template(article_con, image=images)

    return render_template('preview.html', article=article, thumbnail=thumbnail, image=images, content=content)


@app.post('/uploadimage')
def upload_image():
    image_load = request.files.get('image')

    filename = secure_filename(image_load.filename)

    image = base64.b64encode(image_load.read())

    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "wb") as fh:
        fh.write(base64.decodebytes(image))

    article_id = request.form.get('articleId')
    unique_identifier = filename + str(article_id)
    db.add_article_image(article_id, unique_identifier, filename, image)

    return jsonify({'location': "/static/uploads/"+filename})

@app.post('/articles/set_published/<id>')
def set_published(id):
    db.set_article_status(id, 'publish')

    return jsonify(results="Success")

@app.post('/articles/delete_article/<id>')
def delete_article(id):
    db.delete_article(id)

    return jsonify(results="Success")

@app.post('/articles/publish')
def publish_article():
    article_id = request.form.get('articleId')
    title = request.form.get('title')
    status = request.form.get('status')
    description = request.form.get('description')
    topics = request.form.get('topics').split(',')
    thumbnail = request.files.get('thumbnail')
    content = request.form.get('content')
    text_content = request.form.get('text_content')
    date_created = datetime.today().strftime('%m/%d/%Y')
    time_created = datetime.now().time()

    #######################
    # Preprocessing data
    #######################
    if thumbnail != None:
        image = base64.b64encode(thumbnail.read())

        # image = thumbnail.read()
        # print(type(image))

        with open(os.path.join(app.config['UPLOAD_FOLDER'], "article_thumbnail.jpg"), "wb") as fh:
            fh.write(base64.decodebytes(image))
    else:
        image = None

    # replace image filepath with jinja tag
    all_images = re.findall("src=\"(.*?)\"", content)
    oldDir = '/static/uploads/'

    for img in all_images:
        if oldDir in img:
            image_name = img.replace(oldDir, "")
            jinja_tag = "data:image/jpeg;base64,{{ image['" + image_name + "'] }}"
            content = re.sub(img, jinja_tag, content)

    ###########################
    # Add data to databases
    ###########################

    if db.check_article_exists(article_id) == True:
        if image != None:
            db.update_article(article_id, status, date_created, time_created, title, description, topics, image,
                              content, text_content)
        else:
            db.update_article_no_thumb(article_id, status, date_created, time_created, title, description, topics,
                                       content, text_content)
    else:
        db.add_article(article_id, status, date_created, time_created, title, description, topics, image, content,
                       text_content)


    return jsonify(results=article_id)

if __name__ == '__main__':
    app.run()
