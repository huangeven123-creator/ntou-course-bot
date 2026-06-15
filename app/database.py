import json
import firebase_admin
from firebase_admin import credentials, firestore
from app import config

db = None

def init_db():
    global db
    if db is not None:
        return db

    # Check if Firebase App is already initialized
    try:
        app = firebase_admin.get_app()
    except ValueError:
        # Initialize
        cred = None
        import sys
        
        json_str = config.FIREBASE_SERVICE_ACCOUNT_JSON
        if json_str:
            try:
                sys.stderr.write(f"FIREBASE_SERVICE_ACCOUNT_JSON env var length: {len(json_str)}\n")
                
                # Check if it is base64 encoded (doesn't start with '{')
                json_str_stripped = json_str.strip()
                if not json_str_stripped.startswith("{"):
                    import base64
                    try:
                        decoded = base64.b64decode(json_str_stripped).decode('utf-8')
                        if decoded.strip().startswith("{"):
                            json_str = decoded
                            sys.stderr.write("Successfully decoded FIREBASE_SERVICE_ACCOUNT_JSON from base64.\n")
                    except Exception as b64_err:
                        sys.stderr.write(f"Attempted base64 decode but failed: {b64_err}\n")
                
                service_account_info = json.loads(json_str)
                if "private_key" in service_account_info:
                    service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(service_account_info)
                sys.stderr.write("Successfully initialized Firebase via service account JSON.\n")
            except Exception as e:
                sys.stderr.write(f"Error parsing FIREBASE_SERVICE_ACCOUNT_JSON: {e}\n")
                raise e
        
        if cred is None and config.FIREBASE_KEY_FILE_PATH:
            try:
                cred = credentials.Certificate(config.FIREBASE_KEY_FILE_PATH)
                sys.stderr.write(f"Initialized Firebase via file: {config.FIREBASE_KEY_FILE_PATH}\n")
            except Exception as e:
                sys.stderr.write(f"Error loading FIREBASE_KEY_FILE_PATH: {e}\n")
                
        if cred is None:
            try:
                cred = credentials.ApplicationDefault()
                sys.stderr.write("Initialized Firebase via Application Default Credentials.\n")
            except Exception as e:
                sys.stderr.write(f"WARNING: Firebase credentials could not be loaded: {e}\n")
        
        if cred:
            firebase_admin.initialize_app(cred)
        else:
            raise ValueError("No valid Firebase credentials provided. Service cannot start.")
            
    db = firestore.client()
    return db

# Initialize immediately when imported (if possible)
try:
    init_db()
except Exception as ex:
    print(f"Deferred DB initialization due to: {ex}")

# --- Subscription Operations ---

def get_db():
    global db
    if db is None:
        init_db()
    return db

def subscribe_course(user_id: str, course_code: str):
    """
    Subscribe a user to a course code.
    Updates both user and course documents.
    """
    client = get_db()
    course_code = course_code.upper()
    
    # 1. Update user document
    user_ref = client.collection("users").document(user_id)
    user_doc = user_ref.get()
    
    if user_doc.exists:
        user_data = user_doc.to_dict()
        subscribed_courses = user_data.get("subscribed_courses", [])
        if course_code not in subscribed_courses:
            subscribed_courses.append(course_code)
            user_ref.update({"subscribed_courses": subscribed_courses})
    else:
        user_ref.set({
            "subscribed_courses": [course_code],
            "created_at": firestore.SERVER_TIMESTAMP
        })
        
    # 2. Update course document
    course_ref = client.collection("courses").document(course_code)
    course_doc = course_ref.get()
    
    if course_doc.exists:
        course_data = course_doc.to_dict()
        subscribers = course_data.get("subscribers", [])
        if user_id not in subscribers:
            subscribers.append(user_id)
            course_ref.update({"subscribers": subscribers})
    else:
        course_ref.set({
            "subscribers": [user_id],
            "last_quota": -1,
            "last_max_quota": -1,
            "last_name": "",
            "last_updated": firestore.SERVER_TIMESTAMP
        })
        
    print(f"User {user_id} subscribed to {course_code}")

def unsubscribe_course(user_id: str, course_code: str):
    """
    Unsubscribe a user from a course code.
    Updates both user and course documents.
    """
    client = get_db()
    course_code = course_code.upper()
    
    # 1. Update user document
    user_ref = client.collection("users").document(user_id)
    user_doc = user_ref.get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        subscribed_courses = user_data.get("subscribed_courses", [])
        if course_code in subscribed_courses:
            subscribed_courses.remove(course_code)
            user_ref.update({"subscribed_courses": subscribed_courses})
            
    # 2. Update course document
    course_ref = client.collection("courses").document(course_code)
    course_doc = course_ref.get()
    if course_doc.exists:
        course_data = course_doc.to_dict()
        subscribers = course_data.get("subscribers", [])
        if user_id in subscribers:
            subscribers.remove(user_id)
            course_ref.update({"subscribers": subscribers})
            
    print(f"User {user_id} unsubscribed from {course_code}")

def get_user_subscriptions(user_id: str) -> list:
    """
    Get all course codes subscribed by a user.
    """
    client = get_db()
    user_ref = client.collection("users").document(user_id)
    user_doc = user_ref.get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        return user_data.get("subscribed_courses", [])
    return []

def get_all_subscribed_courses() -> list:
    """
    Get all courses that have at least 1 subscriber.
    Returns a list of dicts: [{"course_code": "...", "subscribers": [...], "last_quota": ...}]
    """
    client = get_db()
    courses_ref = client.collection("courses")
    docs = courses_ref.stream()
    
    active_courses = []
    for doc in docs:
        data = doc.to_dict()
        subscribers = data.get("subscribers", [])
        if subscribers: # Only include if there are active subscribers
            data["course_code"] = doc.id
            active_courses.append(data)
            
    return active_courses

def update_course_state(course_code: str, name: str, quota: int, max_quota: int, teacher: str = "", time_str: str = "", classroom: str = ""):
    """
    Update the last known state of a course.
    """
    client = get_db()
    course_code = course_code.upper()
    course_ref = client.collection("courses").document(course_code)
    
    data = {
        "last_name": name,
        "last_quota": quota,
        "last_max_quota": max_quota,
        "last_updated": firestore.SERVER_TIMESTAMP
    }
    if teacher:
        data["last_teacher"] = teacher
    if time_str:
        data["last_time"] = time_str
    if classroom:
        data["last_classroom"] = classroom
        
    course_ref.update(data)
    print(f"Updated course state for {course_code}: quota={quota}/{max_quota}, name={name}, teacher={teacher}, time={time_str}")

def get_course_details(course_code: str) -> dict:
    """
    Get the last known details of a course from the database.
    """
    client = get_db()
    course_code = course_code.upper()
    doc_ref = client.collection("courses").document(course_code)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {}

def remove_course_globally(course_code: str):
    """
    Remove a course completely from all subscribers and delete its document.
    """
    client = get_db()
    course_code = course_code.upper()
    course_ref = client.collection("courses").document(course_code)
    doc = course_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        subscribers = data.get("subscribers", [])
        for uid in subscribers:
            user_ref = client.collection("users").document(uid)
            user_doc = user_ref.get()
            if user_doc.exists:
                udata = user_doc.to_dict()
                sc = udata.get("subscribed_courses", [])
                if course_code in sc:
                    sc.remove(course_code)
                    user_ref.update({"subscribed_courses": sc})
        
        course_ref.delete()
        print(f"Removed course {course_code} globally from database and all subscribers.")
