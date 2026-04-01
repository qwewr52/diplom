import sys
import csv
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QMessageBox, QLabel, QComboBox, QSpinBox, QHeaderView, 
                             QFileDialog, QTabWidget, QLineEdit, QGroupBox, QFormLayout,
                             QStackedWidget, QRadioButton, QScrollArea, QButtonGroup)
from PyQt5.QtCore import Qt

# ИМПОРТИРУЕМ НАШУ БАЗУ ДАННЫХ ИЗ ФАЙЛА database.py
from database import DatabaseManager, GeneratorCore

class ExportModule:
    @staticmethod
    def export_to_txt(test_data, filepath):
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write("Сгенерированный тест\n======================\n\n")
            for index, item in enumerate(test_data, 1):
                file.write(f"Вопрос {index}: {item['question']}\n")
                for ans_idx, ans in enumerate(item['answers'], 1):
                    marker = "[X]" if ans['is_correct'] else "[ ]"
                    file.write(f"  {ans_idx}. {marker} {ans['text']}\n")
                file.write("\n")

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.generator = GeneratorCore(self.db)
        self.current_user_id = None
        
        # Переменные античита
        self.exam_mode_active = False
        self.cheat_warnings = 0
        self.is_showing_warning = False
        
        self.initUI()
        QApplication.instance().applicationStateChanged.connect(self.check_window_focus)

    def initUI(self):
        self.setWindowTitle('ИС «Генератор тестов» (Ultimate Edition)')
        self.resize(950, 750)
        
        self.layout = QVBoxLayout()
        self.stacked_widget = QStackedWidget()
        
        self.page_login = self.create_login_page()
        self.page_admin = self.create_admin_page()
        self.page_teacher = self.create_teacher_page()
        self.page_student = self.create_student_page()
        
        self.stacked_widget.addWidget(self.page_login)    # 0
        self.stacked_widget.addWidget(self.page_admin)    # 1
        self.stacked_widget.addWidget(self.page_teacher)  # 2
        self.stacked_widget.addWidget(self.page_student)  # 3
        
        self.layout.addWidget(self.stacked_widget)
        self.setLayout(self.layout)

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    # ================= ЛОГИН =================
    def create_login_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(QLabel("<h2>Добро пожаловать в систему</h2>"), alignment=Qt.AlignCenter)
        
        form_layout = QFormLayout()
        self.user_combo = QComboBox()
        self.load_users_to_combo()
        form_layout.addRow("Выберите профиль:", self.user_combo)
        
        btn_login = QPushButton("Войти")
        btn_login.setMinimumHeight(40)
        btn_login.clicked.connect(self.process_login)
        
        layout.addLayout(form_layout)
        layout.addWidget(btn_login)
        page.setLayout(layout)
        return page

    def load_users_to_combo(self):
        self.user_combo.clear()
        for u_id, login, role in self.db.get_all_users():
            role_rus = {"admin": "Админ", "teacher": "Преподаватель", "student": "Студент"}.get(role, role)
            self.user_combo.addItem(f"{login} [{role_rus}]", (u_id, role))

    def process_login(self):
        user_data = self.user_combo.currentData()
        if not user_data: return
        user_id, role = user_data
        self.current_user_id = user_id
        self.load_all_combo_boxes() 
        
        if role == 'admin': self.stacked_widget.setCurrentIndex(1)
        elif role == 'teacher': 
            self.load_statistics()
            self.stacked_widget.setCurrentIndex(2)
        elif role == 'student':
            self.update_student_xp_display()
            self.stacked_widget.setCurrentIndex(3)

    def logout(self):
        self.current_user_id = None
        self.exam_mode_active = False
        self.load_users_to_combo()
        self.stacked_widget.setCurrentIndex(0)

    def load_all_combo_boxes(self):
        combos = []
        if hasattr(self, 'combo_topic_add'): combos.append(self.combo_topic_add)
        if hasattr(self, 'combo_topic_student'): combos.append(self.combo_topic_student)
        if hasattr(self, 'combo_topic_teacher'): combos.append(self.combo_topic_teacher)
        if hasattr(self, 'combo_topic_teacher_add'): combos.append(self.combo_topic_teacher_add)

        for combo in combos: combo.clear()
        for t_id, t_name in self.db.get_topics():
            for combo in combos: combo.addItem(t_name, t_id)

    # ================= АДМИН (ПОЛНАЯ ПАНЕЛЬ) =================
    def create_admin_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        group_user = QGroupBox("Управление пользователями")
        u_layout = QFormLayout()
        self.new_u_login = QLineEdit()
        self.new_u_role = QComboBox()
        self.new_u_role.addItems(['student', 'teacher', 'admin'])
        btn_add_u = QPushButton("Создать пользователя")
        btn_add_u.clicked.connect(self.add_user)
        u_layout.addRow("Имя / Логин:", self.new_u_login)
        u_layout.addRow("Роль:", self.new_u_role)
        u_layout.addRow("", btn_add_u)
        group_user.setLayout(u_layout)
        
        group_q = QGroupBox("Ручное наполнение базы знаний")
        q_layout = QFormLayout()
        
        topic_hl = QHBoxLayout()
        self.input_new_topic = QLineEdit()
        btn_add_topic = QPushButton("Создать тему")
        btn_add_topic.clicked.connect(self.add_topic)
        topic_hl.addWidget(self.input_new_topic)
        topic_hl.addWidget(btn_add_topic)
        q_layout.addRow("Новая тема:", topic_hl)
        
        self.combo_topic_add = QComboBox()
        self.input_q_text = QLineEdit()
        self.input_correct = QLineEdit()
        self.input_wrong1 = QLineEdit()
        self.input_wrong2 = QLineEdit()
        self.input_wrong3 = QLineEdit()
        
        btn_add_q = QPushButton("Добавить вопрос в базу")
        btn_add_q.clicked.connect(self.add_question)
        
        q_layout.addRow("Выбрать тему:", self.combo_topic_add)
        q_layout.addRow("Текст вопроса:", self.input_q_text)
        q_layout.addRow("Правильный ответ:", self.input_correct)
        q_layout.addRow("Дистрактор 1 (Обяз.):", self.input_wrong1)
        q_layout.addRow("Дистрактор 2 (Обяз.):", self.input_wrong2)
        q_layout.addRow("Дистрактор 3 (Необяз.):", self.input_wrong3)
        q_layout.addRow("", btn_add_q)
        group_q.setLayout(q_layout)
        
        btn_exit = QPushButton("Сменить профиль")
        btn_exit.clicked.connect(self.logout)
        
        layout.addWidget(group_user)
        layout.addWidget(group_q)
        layout.addWidget(btn_exit)
        page.setLayout(layout)
        return page

    def add_user(self):
        login = self.new_u_login.text().strip()
        role = self.new_u_role.currentText()
        if not login: return
        if self.db.add_user(login, role):
            QMessageBox.information(self, "Успех", "Пользователь создан")
            self.new_u_login.clear()
        else:
            QMessageBox.warning(self, "Ошибка", "Такое имя уже существует")

    def add_topic(self):
        new_topic = self.input_new_topic.text().strip()
        if not new_topic: return
        if self.db.insert_topic(new_topic):
            self.load_all_combo_boxes()
            self.input_new_topic.clear()
            QMessageBox.information(self, "Успех", f"Тема «{new_topic}» добавлена!")
        else:
            QMessageBox.warning(self, "Ошибка", "Такая тема уже существует")

    def add_question(self):
        topic_id = self.combo_topic_add.currentData()
        q_text = self.input_q_text.text().strip()
        correct = self.input_correct.text().strip()
        w1 = self.input_wrong1.text().strip()
        w2 = self.input_wrong2.text().strip()
        w3 = self.input_wrong3.text().strip()
        
        if not all([topic_id, q_text, correct, w1, w2]):
            QMessageBox.warning(self, "Ошибка", "Заполните вопрос, правильный ответ и минимум 2 дистрактора.")
            return

        q_id = self.db.insert_question(topic_id, q_text)
        self.db.insert_answer(q_id, correct, True)
        self.db.insert_answer(q_id, w1, False)
        self.db.insert_answer(q_id, w2, False)
        if w3: self.db.insert_answer(q_id, w3, False)
            
        self.input_q_text.clear()
        self.input_correct.clear()
        self.input_wrong1.clear()
        self.input_wrong2.clear()
        self.input_wrong3.clear()
        QMessageBox.information(self, "Успех", "Вопрос добавлен в базу")

    # ================= ПРЕПОДАВАТЕЛЬ =================
    def create_teacher_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h3>Панель преподавателя</h3>"))
        
        tabs = QTabWidget()
        tab_gen = QWidget()
        tab_add = QWidget()
        tab_ai = QWidget()
        tab_stats = QWidget()
        
        self.setup_teacher_gen_tab(tab_gen)
        self.setup_teacher_add_tab(tab_add)
        self.setup_teacher_ai_tab(tab_ai)
        self.setup_teacher_stats_tab(tab_stats)
        
        tabs.addTab(tab_gen, "Генерация и Экспорт")
        tabs.addTab(tab_add, "Ручное добавление")
        tabs.addTab(tab_ai, "ИИ-Генератор (JSON)")
        tabs.addTab(tab_stats, "Статистика студентов")
        
        btn_exit = QPushButton("Сменить профиль")
        btn_exit.clicked.connect(self.logout)
        
        layout.addWidget(tabs)
        layout.addWidget(btn_exit)
        page.setLayout(layout)
        return page

    def setup_teacher_gen_tab(self, tab):
        layout = QVBoxLayout()
        settings_layout = QHBoxLayout()
        
        self.combo_topic_teacher = QComboBox()
        settings_layout.addWidget(QLabel("Выберите тему:"))
        settings_layout.addWidget(self.combo_topic_teacher)

        self.spin_q_count_teacher = QSpinBox()
        self.spin_q_count_teacher.setMinimum(1)
        self.spin_q_count_teacher.setMaximum(50)
        self.spin_q_count_teacher.setValue(5)
        settings_layout.addWidget(QLabel("Количество вопросов:"))
        settings_layout.addWidget(self.spin_q_count_teacher)

        btn_generate = QPushButton('Сгенерировать тест')
        btn_generate.clicked.connect(self.teacher_generate_test)
        settings_layout.addWidget(btn_generate)
        layout.addLayout(settings_layout)

        self.table_output = QTableWidget(0, 2)
        self.table_output.setHorizontalHeaderLabels(['Текст вопроса', 'Варианты ответов'])
        self.table_output.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.table_output)

        self.btn_export_txt = QPushButton('Экспорт в TXT для печати')
        self.btn_export_txt.clicked.connect(self.teacher_export_txt)
        self.btn_export_txt.setEnabled(False)
        layout.addWidget(self.btn_export_txt)
        tab.setLayout(layout)

    def teacher_generate_test(self):
        topic_id = self.combo_topic_teacher.currentData()
        count = self.spin_q_count_teacher.value()
        self.teacher_current_test_data = self.generator.generate_test(topic_id, count)
        
        self.table_output.setRowCount(0)
        if not self.teacher_current_test_data:
            QMessageBox.warning(self, 'Внимание', 'В базе данных нет достаточного количества вопросов по теме.')
            return

        for row_idx, item in enumerate(self.teacher_current_test_data):
            self.table_output.insertRow(row_idx)
            self.table_output.setItem(row_idx, 0, QTableWidgetItem(item['question']))
            answers_text = "\n".join([f"• {ans['text']} {'(Верно)' if ans['is_correct'] else ''}" for ans in item['answers']])
            self.table_output.setItem(row_idx, 1, QTableWidgetItem(answers_text))
            self.table_output.resizeRowToContents(row_idx)

        self.btn_export_txt.setEnabled(True)

    def teacher_export_txt(self):
        options = QFileDialog.Options()
        filepath, _ = QFileDialog.getSaveFileName(self, "Сохранить тест", "", "Text Files (*.txt);;All Files (*)", options=options)
        if filepath:
            ExportModule.export_to_txt(self.teacher_current_test_data, filepath)
            QMessageBox.information(self, 'Экспорт завершен', f'Тест сохранен в файл:\n{filepath}')

    def setup_teacher_add_tab(self, tab):
        layout = QVBoxLayout()
        group_q = QGroupBox("Создание новых учебных материалов вручную")
        q_layout = QFormLayout()
        
        topic_hl = QHBoxLayout()
        self.teacher_input_new_topic = QLineEdit()
        btn_add_topic = QPushButton("Создать тему")
        btn_add_topic.clicked.connect(self.teacher_add_topic)
        topic_hl.addWidget(self.teacher_input_new_topic)
        topic_hl.addWidget(btn_add_topic)
        q_layout.addRow("Новая тема:", topic_hl)
        
        self.combo_topic_teacher_add = QComboBox()
        self.teacher_input_q_text = QLineEdit()
        self.teacher_input_correct = QLineEdit()
        self.teacher_input_wrong1 = QLineEdit()
        self.teacher_input_wrong2 = QLineEdit()
        self.teacher_input_wrong3 = QLineEdit()
        
        btn_add_q = QPushButton("Добавить вопрос в базу")
        btn_add_q.clicked.connect(self.teacher_add_question)
        
        q_layout.addRow("Выбрать тему:", self.combo_topic_teacher_add)
        q_layout.addRow("Текст вопроса:", self.teacher_input_q_text)
        q_layout.addRow("Правильный ответ:", self.teacher_input_correct)
        q_layout.addRow("Дистрактор 1 (Обяз.):", self.teacher_input_wrong1)
        q_layout.addRow("Дистрактор 2 (Обяз.):", self.teacher_input_wrong2)
        q_layout.addRow("Дистрактор 3 (Необяз.):", self.teacher_input_wrong3)
        q_layout.addRow("", btn_add_q)
        group_q.setLayout(q_layout)
        
        layout.addWidget(group_q)
        layout.addStretch()
        tab.setLayout(layout)

    def teacher_add_topic(self):
        new_topic = self.teacher_input_new_topic.text().strip()
        if not new_topic: return
        if self.db.insert_topic(new_topic):
            self.load_all_combo_boxes()
            self.teacher_input_new_topic.clear()
            QMessageBox.information(self, "Успех", f"Тема «{new_topic}» добавлена!")
        else:
            QMessageBox.warning(self, "Ошибка", "Такая тема уже существует")

    def teacher_add_question(self):
        topic_id = self.combo_topic_teacher_add.currentData()
        q_text = self.teacher_input_q_text.text().strip()
        correct = self.teacher_input_correct.text().strip()
        w1 = self.teacher_input_wrong1.text().strip()
        w2 = self.teacher_input_wrong2.text().strip()
        w3 = self.teacher_input_wrong3.text().strip()
        
        if not all([topic_id, q_text, correct, w1, w2]):
            QMessageBox.warning(self, "Ошибка", "Заполните вопрос, правильный ответ и минимум 2 дистрактора.")
            return

        q_id = self.db.insert_question(topic_id, q_text)
        self.db.insert_answer(q_id, correct, True)
        self.db.insert_answer(q_id, w1, False)
        self.db.insert_answer(q_id, w2, False)
        if w3: self.db.insert_answer(q_id, w3, False)
            
        self.teacher_input_q_text.clear()
        self.teacher_input_correct.clear()
        self.teacher_input_wrong1.clear()
        self.teacher_input_wrong2.clear()
        self.teacher_input_wrong3.clear()
        QMessageBox.information(self, "Успех", "Вопрос добавлен в базу")

    def setup_teacher_ai_tab(self, tab):
        layout = QVBoxLayout()
        group_ai = QGroupBox("Автоматическое создание тестов через API Нейросети")
        form_ai = QFormLayout()
        
        self.ai_topic_input = QLineEdit()
        self.ai_topic_input.setPlaceholderText("Например: Декораторы в Python")
        self.ai_count_spin = QSpinBox()
        self.ai_count_spin.setRange(1, 20)
        self.ai_count_spin.setValue(3)
        
        btn_generate_ai = QPushButton("Сгенерировать базу через ИИ (Имитация API)")
        btn_generate_ai.setStyleSheet("background-color: #8E44AD; color: white; font-weight: bold; padding: 10px;")
        btn_generate_ai.clicked.connect(self.mock_ai_generation)
        
        form_ai.addRow("Тема генерации:", self.ai_topic_input)
        form_ai.addRow("Кол-во вопросов:", self.ai_count_spin)
        form_ai.addRow("", btn_generate_ai)
        group_ai.setLayout(form_ai)
        
        layout.addWidget(group_ai)
        layout.addStretch()
        tab.setLayout(layout)

    def mock_ai_generation(self):
        topic_name = self.ai_topic_input.text().strip()
        if not topic_name:
            QMessageBox.warning(self, "Ошибка", "Укажите тему для ИИ.")
            return
            
        dummy_json_response = f"""
        [
            {{ "question": "Что такое декоратор в Python?", "options": ["Функция, принимающая функцию", "Тип данных", "Оператор цикла", "Модуль"], "correct": 0 }},
            {{ "question": "Какой символ используется для применения декоратора?", "options": ["$", "#", "@", "&"], "correct": 2 }}
        ]
        """
        try:
            parsed_data = json.loads(dummy_json_response)
            self.db.insert_topic(topic_name)
            topic_id = self.db.get_topic_id(topic_name)
            
            for item in parsed_data:
                q_id = self.db.insert_question(topic_id, item['question'])
                for i, option_text in enumerate(item['options']):
                    is_correct = (i == item['correct'])
                    self.db.insert_answer(q_id, option_text, is_correct)
                    
            self.load_all_combo_boxes()
            QMessageBox.information(self, "ИИ Успех", f"ИИ успешно сгенерировал {len(parsed_data)} вопросов!\nТема «{topic_name}» добавлена в базу.")
            self.ai_topic_input.clear()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка ИИ", f"Ошибка обработки JSON: {str(e)}")

    def setup_teacher_stats_tab(self, tab):
        layout = QVBoxLayout()
        self.table_stats = QTableWidget(0, 5)
        self.table_stats.setHorizontalHeaderLabels(['Студент', 'Тема', 'Балл', 'Всего вопросов', 'Дата'])
        self.table_stats.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        btn_export = QPushButton("Выгрузить отчет в CSV")
        btn_export.clicked.connect(self.export_csv)
        
        layout.addWidget(self.table_stats)
        layout.addWidget(btn_export)
        tab.setLayout(layout)

    def load_statistics(self):
        results = self.db.get_results()
        self.table_stats.setRowCount(0)
        for row_idx, row_data in enumerate(results):
            self.table_stats.insertRow(row_idx)
            for col_idx, data in enumerate(row_data):
                self.table_stats.setItem(row_idx, col_idx, QTableWidgetItem(str(data)))

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить отчет", "Отчет_по_тестам.csv", "CSV Files (*.csv)")
        if path:
            with open(path, mode='w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow(['Студент', 'Тема', 'Балл', 'Всего вопросов', 'Дата'])
                for row_data in self.db.get_results():
                    writer.writerow(row_data)

    # ================= СТУДЕНТ =================
    def create_student_page(self):
        page = QWidget()
        self.student_layout = QVBoxLayout()
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h3>Портал студента</h3>"))
        self.label_xp = QLabel("Твой опыт: 0 XP")
        self.label_xp.setStyleSheet("font-weight: bold; color: #2E86C1; font-size: 14px;")
        header_layout.addWidget(self.label_xp, alignment=Qt.AlignRight)
        self.student_layout.addLayout(header_layout)
        
        self.panel_select = QWidget()
        sel_layout = QHBoxLayout()
        self.combo_topic_student = QComboBox()
        self.spin_q_count = QSpinBox()
        self.spin_q_count.setValue(5)
        
        btn_start = QPushButton("Начать тест")
        btn_start.setStyleSheet("background-color: #27AE60; color: white; font-weight: bold;")
        btn_start.clicked.connect(self.start_test)
        
        btn_mistakes = QPushButton("Работа над ошибками")
        btn_mistakes.setStyleSheet("background-color: #F39C12; color: white; font-weight: bold;")
        btn_mistakes.clicked.connect(self.start_mistakes_test)
        
        sel_layout.addWidget(QLabel("Тема:"))
        sel_layout.addWidget(self.combo_topic_student)
        sel_layout.addWidget(QLabel("Вопросов:"))
        sel_layout.addWidget(self.spin_q_count)
        sel_layout.addWidget(btn_start)
        sel_layout.addWidget(btn_mistakes)
        self.panel_select.setLayout(sel_layout)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.test_container = QWidget()
        self.test_layout = QVBoxLayout()
        self.test_container.setLayout(self.test_layout)
        self.scroll_area.setWidget(self.test_container)
        
        self.btn_submit_test = QPushButton("Завершить тест")
        self.btn_submit_test.clicked.connect(self.submit_test)
        self.btn_submit_test.hide()
        
        btn_exit = QPushButton("Сменить профиль")
        btn_exit.clicked.connect(self.logout)
        
        self.student_layout.addWidget(self.panel_select)
        self.student_layout.addWidget(self.scroll_area)
        self.student_layout.addWidget(self.btn_submit_test)
        self.student_layout.addWidget(btn_exit)
        page.setLayout(self.student_layout)
        return page

    def update_student_xp_display(self):
        xp = self.db.get_user_xp(self.current_user_id)
        self.label_xp.setText(f"Опыт: {xp} XP")

    def check_window_focus(self, state):
        if self.exam_mode_active:
            if self.is_showing_warning: return
            if state != Qt.ApplicationActive:
                self.is_showing_warning = True
                self.cheat_warnings += 1
                if self.cheat_warnings >= 3:
                    QMessageBox.critical(self, "Экзамен провален", "Вы покинули окно теста 3 раза. Тест завершен досрочно!")
                    self.submit_test()
                else:
                    QMessageBox.warning(self, "Нарушение!", f"Поиск ответов запрещен.\nНарушение ({self.cheat_warnings}/3).")
                self.is_showing_warning = False

    def render_test_ui(self, test_data):
        self.clear_layout(self.test_layout)
        self.answer_groups = [] 
        for idx, q_item in enumerate(test_data):
            box = QGroupBox(f"Вопрос {idx + 1}: {q_item['question']}")
            box.setProperty("question_id", q_item['question_id'])
            box_layout = QVBoxLayout()
            btn_group = QButtonGroup(self)
            
            for ans in q_item['answers']:
                rb = QRadioButton(ans['text'])
                rb.setProperty("is_correct", ans['is_correct']) 
                btn_group.addButton(rb)
                box_layout.addWidget(rb)
                
            box.setLayout(box_layout)
            self.test_layout.addWidget(box)
            self.answer_groups.append((box, btn_group))
            
        self.test_layout.addStretch()
        self.btn_submit_test.show()
        self.panel_select.setDisabled(True)
        self.exam_mode_active = True
        self.cheat_warnings = 0

    def start_test(self):
        self.current_topic_id = self.combo_topic_student.currentData()
        test_data = self.generator.generate_test(self.current_topic_id, self.spin_q_count.value())
        if not test_data:
            QMessageBox.warning(self, "Ошибка", "Нет вопросов по этой теме.")
            return
        self.render_test_ui(test_data)

    def start_mistakes_test(self):
        self.current_topic_id = self.combo_topic_student.currentData()
        test_data = self.generator.generate_mistakes_test(self.current_user_id, self.current_topic_id)
        if not test_data:
            QMessageBox.information(self, "Отлично!", "У вас нет нерешенных ошибок по этой теме!")
            return
        self.render_test_ui(test_data)

    def submit_test(self):
        self.exam_mode_active = False 
        score = 0
        total = len(self.answer_groups)
        
        for box, group in self.answer_groups:
            q_id = box.property("question_id")
            checked_btn = group.checkedButton()
            
            is_correct = False
            if checked_btn and checked_btn.property("is_correct"):
                score += 1
                is_correct = True
                
            self.db.log_attempt(self.current_user_id, q_id, is_correct)
                
        self.db.execute_query(
            "INSERT INTO Test_Results (student_id, topic_id, score, total_questions) VALUES (?, ?, ?, ?)",
            (self.current_user_id, self.current_topic_id, score, total)
        )
        
        gained_xp = score * 10
        self.db.add_user_xp(self.current_user_id, gained_xp)
        self.update_student_xp_display()
        
        QMessageBox.information(self, "Результат", f"Тест завершен!\nПравильных: {score} из {total}\nОпыт: +{gained_xp} XP")
        
        self.clear_layout(self.test_layout)
        self.btn_submit_test.hide()
        self.panel_select.setDisabled(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())