last_project_path = None

def set_last_project(path):
    global last_project_path
    last_project_path = path

def get_last_project():
    return last_project_path
