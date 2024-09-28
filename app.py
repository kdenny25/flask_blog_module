from flask import Blueprint, Flask, request, render_template, redirect, session, jsonify, flash
from flask_rollup import Bundle
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



@app.route('/')
def news_page():  # put application's code here
    return render_template('news_page.html')

@app.route('/articles/drafts')
def posts_drafts():
    drafts = db.get_articles('draft')
    return render_template('articles_drafts.html', drafts=drafts)

@app.route('/articles/published')
def posts_published():
    published = db.get_articles('published')
    return render_template('articles_published.html', published=published)

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

    article_topic = ""
    for topic in article[8]:
        article_topic = article_topic + topic + ', '

    return render_template('edit_article.html', article=article, topics=topics, images=images, article_topics=article_topic)

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
    article_id = request.form.get('articleId')
    title = request.form.get('title')
    status = request.form.get('status')
    description = request.form.get('description')
    topics = request.form.get('topics').split(',')
    thumbnail = request.files.get('thumbnail')
    content = request.form.get('content')
    date_created = datetime.today().strftime('%m/%d/%Y')
    time_created = datetime.now().time()

    #######################
    # Preprocessing data
    #######################
    if thumbnail != None:
        image = base64.b64encode(thumbnail.read())

        # with open(os.path.join(app.config['UPLOAD_FOLDER'], "article_thumbnail.jpg"), "wb") as fh:
        #     fh.write(base64.decodebytes(image))
    else:
        image = None

    # replace image filepath with jinja tag
    all_images = re.findall("src=\"(.*?)\">", content)
    oldDir = '/static/uploads/'

    for img in all_images:
        image_name = img.replace(oldDir, "")
        jinja_tag = "{{ image['" + image_name + "'] }}"
        content = re.sub(img, jinja_tag, content)

    ###########################
    # Add data to databases
    ###########################
    topic_list = []
    for topic in topics:
        topic_list.append(topic.strip().lower().title())
    db.add_topics(topic_list)

    if db.check_article_exists(article_id) == True:
        db.update_article(article_id, status, date_created, time_created, title, description, topic_list, image, content)
    else:
        db.add_article(article_id, status, date_created, time_created, title, description, topic_list, image, content)

    return jsonify(results=article_id)

if __name__ == '__main__':
    app.run()
