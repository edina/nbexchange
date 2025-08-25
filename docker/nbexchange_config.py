from nbexchange.handlers.auth.user_handler import BaseUserHandler

class MyUserHandler(BaseUserHandler):

    def get_current_user(self, request) -> dict:
        return {
            "name": "1-kiz",
            "full_name": "",
            "email": "",
            "lms_user_id": "",
            "course_id": "Made up2",
            "course_title": "Made up2",
            "course_role": "Instructor",
            "org_id": 1,
        }

c = get_config()  # noqa

c.NbExchange.user_plugin_class = MyUserHandler

c.NbExchange.base_url = "/services/nbexchange"

c.NbExchange.base_storage_location = "/var/data/exchange/storage"

# jdbc:postgresql://naas-db-dev.edina.ac.uk/nbexchange-dev
c.NbExchange.db_url = 'postgresql://myuser@db:5432/nbexchange'


