import psycopg2
from datetime import datetime

class ArticleDb:
    def __init__(self, connection_string):
        self.con = psycopg2.connect(connection_string)
        self.cursor = self.con.cursor()
        self.create_article_table()
        self.create_gin_index()
        self.create_article_images_table()
        self.create_topic_assignments_table()
        self.create_likes_table()


    def create_article_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS articles( "
                            "article_id INT PRIMARY KEY, "
                            "status VARCHAR(50) NOT NULL, "
                            "date_created DATE NOT NULL, "
                            "time_created TIME NOT NULL, "
                            "date_updated DATE, "
                            "time_updated TIME, "
                            "title VARCHAR(100), "
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

    def create_topic_assignments_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS topic_assignments( "
                            "id SERIAL PRIMARY KEY, "
                            "article_id INT REFERENCES articles(article_id),"
                            "topic VARCHAR(20) NOT NULL)")

    def create_likes_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS article_likes( "
                            "like_id SERIAL PRIMARY KEY, "
                            "date_liked DATE NOT NULL, "
                            "article_id INT REFERENCES articles(article_id), "
                            "user_id INT)") # change user_id in final app to avoid errors

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
                            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s);",
                            (article_id, status, date_created, time_created, title, short_description, psycopg2.Binary(thumbnail), content, text_content))

        if topics[0] != '':
            self.add_topics(article_id, topics)
        self.con.commit()

    def update_article(self, article_id, status, date_updated, time_updated, title, short_description, topics, thumbnail, content, text_content):
        self.add_topics(article_id, topics)

        self.cursor.execute("UPDATE articles "
                            "SET status=%s, date_updated=%s, time_updated=%s, title=%s, short_description=%s, thumbnail=%s, content=%s, content_text=%s "
                            "WHERE article_id=%s;", (status, date_updated, time_updated, title, short_description, psycopg2.Binary(thumbnail), content, text_content, article_id))
        self.con.commit()

    def update_article_no_thumb(self, article_id, status, date_updated, time_updated, title, short_description, topics,
                       content, text_content):
        self.add_topics(article_id, topics)

        self.cursor.execute("UPDATE articles "
                            "SET status=%s, date_updated=%s, time_updated=%s, title=%s, short_description=%s, content=%s, content_text=%s "
                            "WHERE article_id=%s;", (
                            status, date_updated, time_updated, title, short_description,
                            content, text_content, article_id))
        self.con.commit()

    def get_articles(self, status):
        self.cursor.execute("SELECT x.article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, y.topics, thumbnail, content "
                                "FROM articles x "
                                "LEFT JOIN ( SELECT article_id, array_agg(topic) as topics "
                                    "FROM topic_assignments "
                                    "GROUP BY article_id) "
                                    "AS y ON x.article_id = y.article_id "
                                "WHERE status=%s ", (status,))
        results = self.cursor.fetchall()
        return results


    def query_articles_by_topic(self,status, topic):
        self.cursor.execute("WITH "
                                "articleTable (article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, topics, thumbnail, content) "
                                "AS ( "
                                    "SELECT x.article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, y.topics, thumbnail, content "
                                    "FROM articles x "
                                    "JOIN ( SELECT article_id, array_agg(topic) as topics " 
                                        "FROM topic_assignments "
                                        "GROUP BY article_id) "
                                        "AS y ON x.article_id = y.article_id "
                                    "WHERE status=%s "
                                    "), "
                                "topicTable (article_id) "
                                "AS ( "
                                    "SELECT article_id "
                                    "FROM topic_assignments "
                                    "WHERE topic = %s "
                                ") "
                            "SELECT tt.article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, topics, thumbnail, content "
                            "FROM topicTable AS tt "
                            "LEFT JOIN articleTable AS at ON at.article_id = tt.article_id", (status, topic))
        results = self.cursor.fetchall()
        return results

    def query_related_articles(self, status, topic, article_id):
        self.cursor.execute("WITH "
                                "articleTable (article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, topics, thumbnail, content) "
                                "AS ( "
                                    "SELECT x.article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, y.topics, thumbnail, content "
                                    "FROM articles x "
                                    "JOIN ( SELECT article_id, array_agg(topic) as topics " 
                                        "FROM topic_assignments "
                                        "GROUP BY article_id) "
                                        "AS y ON x.article_id = y.article_id "
                                    "WHERE status=%s "
                                    "), "
                                "topicTable (article_id) "
                                "AS ( "
                                    "SELECT article_id "
                                    "FROM topic_assignments "
                                    "WHERE topic = %s "
                                ") "
                            "SELECT tt.article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, topics, thumbnail, content "
                            "FROM topicTable AS tt "
                            "LEFT JOIN articleTable AS at ON at.article_id = tt.article_id "
                            "WHERE tt.article_id != %s"
                            "ORDER BY RANDOM() "
                            "LIMIT 5", (status, topic, article_id))
        results = self.cursor.fetchall()
        return results

    def search_articles(self, status, search):
        self.cursor.execute("SELECT x.article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, y.topics, thumbnail, content " 
                                "FROM articles AS x "
                                "LEFT JOIN (SELECT article_id, array_agg(topic) as topics "
                                    "FROM topic_assignments "
                                    "GROUP BY article_id) "
                                    "AS y ON x.article_id = y.article_id "
                                "WHERE status=%s AND x.text_searchable_index @@ phraseto_tsquery('english', %s) "
                                "ORDER BY date_created DESC ", (status, search))
        results = self.cursor.fetchall()
        return results

    def get_article(self, article_id):
        self.cursor.execute("SELECT x.article_id, status, date_created, time_created, date_updated, time_updated, title, short_description, y.topics, thumbnail, content "
                                "FROM articles x "
                                "LEFT JOIN ( SELECT article_id, array_agg(topic) as topics "
                                    "FROM topic_assignments "
                                    "GROUP BY article_id) "
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
                            "FROM topic_assignments "
                            "WHERE article_id=%s;", (article_id, ))
        self.con.commit()

        self.cursor.execute("DELETE "
                            "FROM articles "
                            "WHERE article_id=%s;", (article_id, ))
        self.con.commit()

    def add_topics(self, article_id, topics):
        # Get list of topics by article_id
        self.cursor.execute("SELECT topic "
                                  "FROM topic_assignments "
                                  "WHERE article_id=%s", (article_id))

        existing_topics = self.cursor.fetchall()
        existing_topics = [x[0] for x in existing_topics]
        topics = list(filter(None, [x.strip().lower().title() for x in topics]))

        topic_list = []  # list of topics that are the same
        arg_list = []  # list of topics to add
        for topic in topics:
            t = topic.strip().lower().title()

            if topic not in existing_topics:
                arg_list.append((article_id, t))
            else:
                topic_list.append(t)

        if len(arg_list) > 0:
            args = ','.join(self.cursor.mogrify("(%s, %s)", i).decode('utf-8')
                            for i in arg_list)

            self.cursor.execute("INSERT INTO topic_assignments(article_id, topic) "
                                "VALUES " + args)
            self.con.commit()

        # create list of topics to delete
        delete_list = [x for x in existing_topics if x not in topic_list]

        # delete if we need to
        if len(delete_list) > 0:
            arg_topic_list = []

            for delete_item in delete_list:
                arg_topic_list.append((delete_item,))

                args_t = ','.join(self.cursor.mogrify("%s", i).decode('utf-8')
                                for i in arg_topic_list)

            self.cursor.execute("DELETE FROM topic_assignments "
                                "WHERE article_id=" + article_id + " AND topic IN (" + args_t + ")")
            self.con.commit()



    def get_topics(self,):
        """Returns a list of topics and their count"""
        self.cursor.execute("SELECT topic, COUNT(topic) AS topic_count "
                            "FROM topic_assignments "
                            "LEFT JOIN articles ON articles.article_id = topic_assignments.article_id "
                            "WHERE articles.status = 'publish' "
                            "GROUP BY topic")
        results = self.cursor.fetchall()

        topic_list = []
        for result in results:
            topic_list.append([result[0], result[1]])

        return topic_list

    def add_like(self, article_id, user_id):
        """Adds a like to an article"""

        date = datetime.today()
        self.cursor.execute("INSERT INTO article_likes(date_liked, article_id, user_id) "
                            "SELECT %s, %s, %s "
                            "WHERE NOT EXISTS ("
                                "SELECT article_id, user_id "
                                "FROM article_likes "
                                "WHERE article_id = %s AND user_id = %s) ", (date, article_id, user_id, article_id, user_id))
        self.con.commit()

        result = self.get_like_count(article_id, user_id)

        return result

    def remove_like(self, article_id, user_id):
        """Subtracts a like from an article"""
        self.cursor.execute("DELETE "
                            "FROM article_likes "
                            "WHERE article_id = %s AND user_id = %s", (article_id, user_id))
        self.con.commit()

        result = self.get_like_count(article_id, user_id)

        return result

    def get_like_count(self, article_id, user_id=None):
        """Returns the count of  likes for specified article and if registered user is viewing return if user liked
        article"""
        self.cursor.execute("WITH "
                                "user_liked(article_id, liked_by_user) "
                            "AS ( "
                                "SELECT article_id, EXISTS( "
                                    "SELECT 1 "
                                    "FROM article_likes "
                                    "WHERE user_id = %s and article_id=%s ) "
                                "FROM article_likes "
                                "WHERE article_id=%s and user_id=%s) "
                            "SELECT COUNT(al.article_id), ul.liked_by_user "
                            "FROM article_likes AS al "
                            "LEFT JOIN user_liked AS ul ON al.article_id = ul.article_id "
                            "WHERE al.article_id = %s "
                            "GROUP BY ul.liked_by_user ", (user_id, article_id, article_id, user_id, article_id))

        result = self.cursor.fetchone()


        if result == None:
            result = (0, False)

        return result