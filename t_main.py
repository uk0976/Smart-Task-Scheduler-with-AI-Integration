import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
import threading
import spacy
from datetime import datetime
import ttkbootstrap as tb  # Modern UI

# Load NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    messagebox.showerror("Error", "SpaCy model not found! Run: python -m spacy download en_core_web_sm")
    exit()

# MySQL Database Connection
def connect_database():
    try:
        conn = mysql.connector.connect(
            host="localhost",        # Change if your MySQL server is remote
            user="root",             # Replace with your MySQL username
            password="password",     # Replace with your MySQL password
            database="task_scheduler"
        )
        return conn
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", f"Error: {err}")
        exit()

class TaskScheduler:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Task Scheduler")
        self.root.geometry("900x600")
        self.root.resizable(False, False)

        # Set theme
        self.style = tb.Style("darkly")

        self.init_database()
        self.create_gui()

        # Start background thread for checking tasks
        self.checker_thread = threading.Thread(target=self.check_tasks, daemon=True)
        self.checker_thread.start()

    def init_database(self):
        """Initialize MySQL Database"""
        self.conn = connect_database()
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                due_date DATE NOT NULL,
                priority VARCHAR(50) NOT NULL,
                status VARCHAR(50) DEFAULT 'Pending',
                ai_reason TEXT
            )
        ''')
        self.conn.commit()

    def ai_prioritize_task(self, description):
        """Use NLP to determine task priority"""
        doc = nlp(description.lower())
        priority = "Low"
        if any(word in description.lower() for word in ["urgent", "critical", "deadline", "important"]):
            priority = "High"
        elif any(token.lemma_ in ["soon", "priority", "major"] for token in doc):
            priority = "Medium"
        return priority, "NLP-based priority assignment"

    def validate_date(self, date_str):
        """Validate date format (YYYY-MM-DD)"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def create_gui(self):
        """Create the GUI"""
        frame = tb.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)

        tb.Label(frame, text="AI Task Scheduler", font=("Helvetica", 20, "bold")).grid(row=0, column=0, columnspan=4, pady=10)

        # Input Fields
        tb.Label(frame, text="Title:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.title_var = tk.StringVar()
        tb.Entry(frame, textvariable=self.title_var, width=40).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        tb.Label(frame, text="Description:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.desc_var = tk.StringVar()
        tb.Entry(frame, textvariable=self.desc_var, width=40).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        tb.Label(frame, text="Due Date (YYYY-MM-DD):").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.date_var = tk.StringVar()
        tb.Entry(frame, textvariable=self.date_var, width=40).grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Buttons
        tb.Button(frame, text="Add Task", bootstyle="success", command=self.add_task).grid(row=4, column=0, padx=5, pady=10)
        tb.Button(frame, text="Modify Task", bootstyle="primary", command=self.modify_task).grid(row=4, column=1, padx=5, pady=10)
        tb.Button(frame, text="Mark as Done", bootstyle="warning", command=self.mark_task_done).grid(row=4, column=2, padx=5, pady=10)
        tb.Button(frame, text="Delete Task", bootstyle="danger", command=self.delete_task).grid(row=4, column=3, padx=5, pady=10)

        # Task List
        list_frame = tb.Frame(self.root, padding=10)
        list_frame.pack(fill="both", expand=True)

        columns = ("ID", "Title", "Description", "Due Date", "Priority", "Status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)

        for col in columns:
            self.tree.heading(col, text=col, anchor="center")
            self.tree.column(col, width=120, anchor="center")

        self.tree.pack(fill="both", expand=True, pady=10)
        self.refresh_tasks()

    def add_task(self):
        """Add new task to the database"""
        title = self.title_var.get().strip()
        description = self.desc_var.get().strip()
        due_date = self.date_var.get().strip()

        if not title or not due_date:
            messagebox.showerror("Error", "Title and Due Date are required!")
            return
        
        if not self.validate_date(due_date):
            messagebox.showerror("Error", "Invalid date format! Use YYYY-MM-DD.")
            return

        priority, ai_reason = self.ai_prioritize_task(description)

        self.cursor.execute('''
            INSERT INTO tasks (title, description, due_date, priority, status, ai_reason)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (title, description, due_date, priority, "Pending", ai_reason))

        self.conn.commit()
        self.refresh_tasks()

    def modify_task(self):
        """Modify an existing task"""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select a task to modify!")
            return

        task_id = self.tree.item(selected_item, "values")[0]
        new_title = self.title_var.get().strip()
        new_description = self.desc_var.get().strip()
        new_due_date = self.date_var.get().strip()

        if not new_title or not new_due_date:
            messagebox.showerror("Error", "Title and Due Date are required!")
            return

        self.cursor.execute('''
            UPDATE tasks SET title=%s, description=%s, due_date=%s WHERE id=%s
        ''', (new_title, new_description, new_due_date, task_id))

        self.conn.commit()
        self.refresh_tasks()

    def refresh_tasks(self):
        """Refresh task list"""
        self.tree.delete(*self.tree.get_children())
        self.cursor.execute("SELECT id, title, description, due_date, priority, status FROM tasks ORDER BY priority DESC, due_date ASC")
        for task in self.cursor.fetchall():
            self.tree.insert("", "end", values=task)

if __name__ == "__main__":
    root = tb.Window(themename="superhero")
    app = TaskScheduler(root)
    root.mainloop()
