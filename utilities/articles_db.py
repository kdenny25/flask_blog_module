import psycopg2

class ArticleDb:
    def __init__(self, connection_string):
        self.con = psycopg2.connect(connection_string)
        self.cursor = self.con.cursor()
        self.create_article_table()
        self.create_article_images_table()
        self.create_topics_table()


    def create_article_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS articles( "
                            "article_id INT PRIMARY KEY, "
                            "status VARCHAR(50) NOT NULL, "
                            "date_created DATE NOT NULL, "
                            "time_created TIME NOT NULL, "
                            "date_updated DATE, "
                            "time_updated TIME, "
                            "title VARCHAR(50) NOT NULL, "
                            "short_description VARCHAR(150), "
                            "topics TEXT[], "
                            "thumbnail BYTEA,"
                            "content TEXT)")

    def create_article_images_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS article_imgs( "
                            "image_id SERIAL PRIMARY KEY, "
                            "article_id INT,"
                            "file_name TEXT NOT NULL,"
                            "image BYTEA)")

    def create_topics_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS topics( "
                            "topic_id SERIAL PRIMARY KEY, "
                            "topic VARCHAR(20) UNIQUE)")


    def new_article_id(self):
        self.cursor.execute("SELECT max(article_id) "
                            "FROM articles ")

        results = self.cursor.fetchone()[0]
        if results == None:
            results = 0
        else:
            # increment new id by 1
            results = results + 1

        return results

    def add_article_image(self, article_id, file_name, image):
        self.cursor.execute("INSERT INTO article_imgs(article_id, file_name, image) "
                            "VALUES(%s, %s, %s);", (article_id, file_name, psycopg2.Binary(image)))

        self.con.commit()

    def get_article_images(self, article_id):
        self.cursor.execute("SELECT file_name, image "
                            "FROM article_imgs "
                            "WHERE article_id = %s; ", (article_id, ))

        results = self.cursor.fetchall()

        image_dict = {}

        for image in results:
            image_dict[image[0]] = bytes(image[1]).decode('utf-8')

        return image_dict

    def add_article(self, article_id, status, date_created, time_created, title, short_description, topics, thumbnail, content):
        self.cursor.execute("INSERT INTO articles(article_id, status, date_created, time_created, title, short_description, topics, thumbnail, content) "
                            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s);",
                            (article_id, status, date_created, time_created, title, short_description, topics, psycopg2.Binary(thumbnail), content))
        self.con.commit()

    def update_article(self, article_id, status, date_updated, time_updated, title, short_description, topics, thumbnail, content):
        self.cursor.execute("UPDATE articles "
                            "SET status=%s, date_updated=%s, time_updated=%s, title=%s, short_description=%s, topics=%s, thumbnail=%s, content=%s "
                            "WHERE article_id=%s;", (status, date_updated, time_updated, title, short_description, topics, psycopg2.Binary(thumbnail), content, article_id))
        self.con.commit()

    def update_article_no_thumb(self, article_id, status, date_updated, time_updated, title, short_description, topics,
                       content):
        self.cursor.execute("UPDATE articles "
                            "SET status=%s, date_updated=%s, time_updated=%s, title=%s, short_description=%s, topics=%s, content=%s "
                            "WHERE article_id=%s;", (
                            status, date_updated, time_updated, title, short_description, topics,
                            content, article_id))
        self.con.commit()

    def get_articles(self, status):
        self.cursor.execute("SELECT article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, topics, thumbnail, content "
                            "FROM articles "
                            "WHERE status=%s;", (status,))
        results = self.cursor.fetchall()
        return results

    def get_article(self, article_id):
        self.cursor.execute("SELECT article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, topics, thumbnail, content "
                            "FROM articles "
                            "WHERE article_id=%s;", (article_id,))
        results = self.cursor.fetchone()
        return results

    def check_article_exists(self, article_id):
        self.cursor.execute("SELECT EXISTS(SELECT 1 "
                            "FROM articles "
                            "WHERE article_id = %s);", (article_id,))
        result = self.cursor.fetchone()[0]

        return result

    def add_topics(self, topics):
        arg_list = []
        for topic in topics:
            arg_list.append((topic, ))
        # cursor.mogrify() to insert multiple values
        args = ','.join(self.cursor.mogrify("(%s)", i).decode('utf-8')
                        for i in arg_list)

        self.cursor.execute("INSERT INTO topics(topic) "
                            "VALUES " + args +
                            "ON CONFLICT (topic) DO NOTHING;")
        self.con.commit()

    def get_topics(self):
        self.cursor.execute("SELECT topic "
                            "FROM topics ")
        results = self.cursor.fetchall()

        topic_list = []
        for result in results:
            topic_list.append(result[0])
        return topic_list

