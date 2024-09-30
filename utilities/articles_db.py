import psycopg2

class ArticleDb:
    def __init__(self, connection_string):
        self.con = psycopg2.connect(connection_string)
        self.cursor = self.con.cursor()
        self.create_article_table()
        self.create_gin_index()
        self.create_article_images_table()
        self.create_topics_table()
        self.create_topic_assignments_table()


    def create_article_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS articles( "
                            "article_id INT PRIMARY KEY, "
                            "status VARCHAR(50) NOT NULL, "
                            "date_created DATE NOT NULL, "
                            "time_created TIME NOT NULL, "
                            "date_updated DATE, "
                            "time_updated TIME, "
                            "title VARCHAR(100) NOT NULL, "
                            "short_description VARCHAR(150), "
                            "thumbnail BYTEA,"
                            "content TEXT,"
                            "content_text TEXT,"
                            "text_searchable_index tsvector "
                            "GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content_text, ''))) STORED)")

    def create_article_images_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS article_imgs( "
                            "image_id SERIAL PRIMARY KEY, "
                            "article_id INT,"
                            "id_fn TEXT UNIQUE, "
                            "file_name TEXT NOT NULL,"
                            "image BYTEA)")

    def create_topics_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS topics( "
                            "topic_id SERIAL PRIMARY KEY, "
                            "topic VARCHAR(20) UNIQUE)")

    def create_topic_assignments_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS topic_assignments( "
                            "id SERIAL PRIMARY KEY, "
                            "article_id INT REFERENCES articles(article_id),"
                            "topic_id INT REFERENCES topics(topic_id) )")


    def create_gin_index(self):
        """creates the gin index on articles table to improve article search speeds"""

        self.cursor.execute("CREATE INDEX IF NOT EXISTS textsearch_idx ON articles USING GIN(text_searchable_index);")
        self.con.commit()


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

    def add_article_image(self, article_id, unique_identifier, file_name, image):
        """Adds article image to database and avoids adding duplicate images"""
        self.cursor.execute("INSERT INTO article_imgs(article_id, id_fn, file_name, image) "
                            "VALUES(%s, %s, %s, %s) "
                            "ON CONFLICT (id_fn) DO NOTHING;", (article_id, unique_identifier, file_name, psycopg2.Binary(image)))

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

    def add_article(self, article_id, status, date_created, time_created, title, short_description, topics, thumbnail, content, text_content):
        self.cursor.execute("INSERT INTO articles(article_id, status, date_created, time_created, title, short_description, thumbnail, content, content_text) "
                            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
                            (article_id, status, date_created, time_created, title, short_description, psycopg2.Binary(thumbnail), content, text_content))
        self.con.commit()

    def update_article(self, article_id, status, date_updated, time_updated, title, short_description, topics, thumbnail, content, text_content):
        self.cursor.execute("UPDATE articles "
                            "SET status=%s, date_updated=%s, time_updated=%s, title=%s, short_description=%s, thumbnail=%s, content=%s, content_text=%s "
                            "WHERE article_id=%s;", (status, date_updated, time_updated, title, short_description, psycopg2.Binary(thumbnail), content, text_content, article_id))
        self.con.commit()

    def update_article_no_thumb(self, article_id, status, date_updated, time_updated, title, short_description, topics,
                       content, text_content):
        self.cursor.execute("UPDATE articles "
                            "SET status=%s, date_updated=%s, time_updated=%s, title=%s, short_description=%s, content=%s, content_text=%s "
                            "WHERE article_id=%s;", (
                            status, date_updated, time_updated, title, short_description,
                            content, text_content, article_id))
        self.con.commit()

    def get_articles(self, status):
        self.cursor.execute("SELECT x.article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, y.topics, thumbnail, content "
                                "FROM articles x "
                                "JOIN ( SELECT topic_assignments.article_id, array_agg(topic) as topics "
                                    "FROM topic_assignments "
                                    "JOIN topics ON topics.topic_id = topic_assignments.topic_id "
                                    "GROUP BY topic_assignments.article_id) "
                                    "AS y ON x.article_id = y.article_id "
                                "WHERE status=%s ", (status,))
        results = self.cursor.fetchall()
        return results


    #todo: fix this
    def query_articles_by_topic(self,status, topic):
        self.cursor.execute("WITH "
                                "articleTable (article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, topics, thumbnail, content) "
                                "AS ( "
                                    "SELECT x.article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, y.topics, thumbnail, content "
                                    "FROM articles x "
                                    "JOIN ( SELECT topic_assignments.article_id, array_agg(topic) as topics " 
                                        "FROM topic_assignments "
                                        "JOIN topics ON topics.topic_id = topic_assignments.topic_id "
                                        "GROUP BY topic_assignments.article_id) "
                                        "AS y ON x.article_id = y.article_id "
                                    "WHERE status=%s "
                                    "), "
                                "topicTable (article_id) "
                                "AS ( "
                                    "SELECT ta.article_id "
                                    "FROM topic_assignments AS ta "
                                    "JOIN topics ON topics.topic_id = ta.topic_id "
                                    "WHERE topic = %s "
                                ") "
                            "SELECT tt.article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, topics, thumbnail, content "
                            "FROM topicTable AS tt "
                            "LEFT JOIN articleTable AS at ON at.article_id = tt.article_id", (status, topic))
        results = self.cursor.fetchall()
        return results

    def get_article(self, article_id):
        self.cursor.execute("SELECT x.article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, y.topics, thumbnail, content "
                                "FROM articles x "
                                "JOIN ( SELECT topic_assignments.article_id, array_agg(topic) as topics "
                                    "FROM topic_assignments "
                                    "JOIN topics ON topics.topic_id = topic_assignments.topic_id "
                                    "GROUP BY topic_assignments.article_id) "
                                    "AS y ON x.article_id = y.article_id "
                                "WHERE x.article_id=%s ", (article_id,))
        results = self.cursor.fetchone()
        return results

    def check_article_exists(self, article_id):
        self.cursor.execute("SELECT EXISTS(SELECT 1 "
                            "FROM articles "
                            "WHERE article_id = %s);", (article_id,))
        result = self.cursor.fetchone()[0]

        return result

    def set_article_status(self, article_id, status):
        self.cursor.execute("UPDATE articles "
                            "SET status=%s "
                            "WHERE article_id=%s;", (status, article_id))
        self.con.commit()

    def delete_article(self, article_id):
        self.cursor.execute("DELETE "
                            "FROM articles "
                            "WHERE article_id=%s;", (article_id, ))
        self.con.commit()

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

