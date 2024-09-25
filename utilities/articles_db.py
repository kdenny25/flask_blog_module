import psycopg2

class ArticleDb:
    def __init__(self, connection_string):
        self.con = psycopg2.connect(connection_string)
        self.cursor = self.con.cursor()
        self.create_article_table()
        self.create_article_images_table()


    def create_article_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS articles( "
                            "article_id INT PRIMARY KEY, "
                            "date_created DATE NOT NULL, "
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

        print(image_dict)
        return image_dict