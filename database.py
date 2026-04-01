import sqlite3
import random

class DatabaseManager:
    def __init__(self, db_name="lms_generator.db"):
        self.db_name = db_name
        self.create_tables()
        self.seed_dummy_data()

    def execute_query(self, query, parameters=()):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(query, parameters)
            conn.commit()
            return cursor.fetchall()

    def create_tables(self):
        self.execute_query('''CREATE TABLE IF NOT EXISTS Topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)''')
        self.execute_query('''CREATE TABLE IF NOT EXISTS Questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, topic_id INTEGER NOT NULL,
            text TEXT NOT NULL, difficulty INTEGER DEFAULT 1,
            FOREIGN KEY (topic_id) REFERENCES Topics(id))''')
        self.execute_query('''CREATE TABLE IF NOT EXISTS Answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, question_id INTEGER NOT NULL,
            text TEXT NOT NULL, is_correct BOOLEAN NOT NULL CHECK (is_correct IN (0, 1)),
            FOREIGN KEY (question_id) REFERENCES Questions(id))''')
        self.execute_query('''CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL, xp INTEGER DEFAULT 0)''')
        self.execute_query('''CREATE TABLE IF NOT EXISTS Test_Results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL,
            topic_id INTEGER NOT NULL, score INTEGER NOT NULL, total_questions INTEGER NOT NULL,
            date_completed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES Users(id), FOREIGN KEY (topic_id) REFERENCES Topics(id))''')
        self.execute_query('''CREATE TABLE IF NOT EXISTS Attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL, is_correct BOOLEAN NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES Users(id), FOREIGN KEY (question_id) REFERENCES Questions(id))''')

    def seed_dummy_data(self):
        users = self.execute_query("SELECT * FROM Users")
        if not users:
            self.add_user('Администратор (admin)', 'admin')
            self.add_user('Иван Петров (teacher)', 'teacher')
            self.add_user('Студент Сидоров (student)', 'student')

        topics = self.execute_query("SELECT * FROM Topics")
        if not topics:
            self.insert_topic("Основы баз данных")
            t_id = self.get_topics()[0][0]
            
            q1 = self.insert_question(t_id, "Что означает аббревиатура SQL?")
            self.insert_answer(q1, "Structured Query Language", True)
            self.insert_answer(q1, "Simple Question Logic", False)
            self.insert_answer(q1, "System Query Level", False)
            self.insert_answer(q1, "Standard Query List", False)
            
            q2 = self.insert_question(t_id, "Команда для выборки данных?")
            self.insert_answer(q2, "SELECT", True)
            self.insert_answer(q2, "UPDATE", False)
            self.insert_answer(q2, "DELETE", False)
            self.insert_answer(q2, "INSERT", False)

    def add_user(self, login, role):
        try:
            self.execute_query("INSERT INTO Users (login, role, xp) VALUES (?, ?, 0)", (login, role))
            return True
        except sqlite3.IntegrityError: return False

    def get_user_xp(self, user_id):
        res = self.execute_query("SELECT xp FROM Users WHERE id = ?", (user_id,))
        return res[0][0] if res else 0

    def add_user_xp(self, user_id, xp_to_add):
        self.execute_query("UPDATE Users SET xp = xp + ? WHERE id = ?", (xp_to_add, user_id))

    def insert_topic(self, name):
        try:
            self.execute_query("INSERT INTO Topics (name) VALUES (?)", (name,))
            return True
        except sqlite3.IntegrityError: return False

    def get_topic_id(self, name):
        res = self.execute_query("SELECT id FROM Topics WHERE name = ?", (name,))
        return res[0][0] if res else None

    def get_all_users(self):
        return self.execute_query("SELECT id, login, role FROM Users")

    def insert_question(self, topic_id, text):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Questions (topic_id, text) VALUES (?, ?)", (topic_id, text))
            conn.commit()
            return cursor.lastrowid

    def insert_answer(self, question_id, text, is_correct):
        self.execute_query("INSERT INTO Answers (question_id, text, is_correct) VALUES (?, ?, ?)", 
                           (question_id, text, 1 if is_correct else 0))

    def log_attempt(self, student_id, question_id, is_correct):
        self.execute_query("INSERT INTO Attempts (student_id, question_id, is_correct) VALUES (?, ?, ?)",
                           (student_id, question_id, 1 if is_correct else 0))

    def get_topics(self):
        return self.execute_query("SELECT id, name FROM Topics")
    
    def get_results(self):
        return self.execute_query('''
            SELECT Users.login, Topics.name, Test_Results.score, Test_Results.total_questions, Test_Results.date_completed
            FROM Test_Results
            JOIN Users ON Test_Results.student_id = Users.id
            JOIN Topics ON Test_Results.topic_id = Topics.id
            ORDER BY Test_Results.date_completed DESC
        ''')

class GeneratorCore:
    def __init__(self, db_manager):
        self.db = db_manager

    def generate_test(self, topic_id, count):
        questions_data = self.db.execute_query("SELECT id, text FROM Questions WHERE topic_id = ?", (topic_id,))
        if not questions_data: return []
        random.shuffle(questions_data)
        selected_questions = questions_data[:count]
        
        test_material = []
        for q_id, q_text in selected_questions:
            answers_data = self.db.execute_query("SELECT id, text, is_correct FROM Answers WHERE question_id = ?", (q_id,))
            answers = [{"id": ans[0], "text": ans[1], "is_correct": bool(ans[2])} for ans in answers_data]
            random.shuffle(answers)
            test_material.append({"question_id": q_id, "question": q_text, "answers": answers})
        return test_material

    def generate_mistakes_test(self, student_id, topic_id):
        query = """
            SELECT DISTINCT q.id, q.text 
            FROM Attempts a
            JOIN Questions q ON a.question_id = q.id
            WHERE a.student_id = ? AND q.topic_id = ? AND a.is_correct = 0
        """
        questions_data = self.db.execute_query(query, (student_id, topic_id))
        if not questions_data: return []

        test_material = []
        for q_id, q_text in questions_data:
            answers_data = self.db.execute_query("SELECT id, text, is_correct FROM Answers WHERE question_id = ?", (q_id,))
            answers = [{"id": ans[0], "text": ans[1], "is_correct": bool(ans[2])} for ans in answers_data]
            random.shuffle(answers)
            test_material.append({"question_id": q_id, "question": q_text, "answers": answers})
        return test_material