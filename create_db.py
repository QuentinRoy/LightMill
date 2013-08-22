__author__ = 'Quentin Roy'


from expserver.model import db

def create_db():
    db.create_all()


if __name__ == "__main__":
    create_db()