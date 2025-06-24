import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import threading
import spacy
from datetime import datetime
import ttkbootstrap as tb

# Load NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    messagebox.showerror("Error", "SpaCy model not found! Please install it using:\npip install spacy\npython -m spacy download en_core_web_sm")
    exit()

class TaskScheduler:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Task Scheduler")
        self.root.geometry("950x650")
        self.root.resizable(False, False)

        self.style = tb.Style("superhero")
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.style.configure("Treeview", rowheight=30, font=("Segoe UI", 10))

        self.init_database()
        self.create_gui()

        self.checker_thread = threading.Thread(target=self.check_tasks, daemon=True)
        self.checker_thread.start()

    def init_database(self):
        self.conn = sqlite3.connect('tasks.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                due_date TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                ai_reason TEXT
            )
        ''')
        self.conn.commit()

    def ai_prioritize_task(self, description):
        doc = nlp(description.lower())
        priority = "Low"
        if any(word in description.lower() for word in ["urgent", "critical", "deadline", "important"]):
            priority = "High"
        elif any(token.lemma_ in ["soon", "priority", "major"] for token in doc):
            priority = "Medium"
        return priority, "NLP-based priority assignment"

    def validate_date(self, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def create_gui(self):
        frame = tb.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=False)

        # Title Label
        tb.Label(frame, text="AI Task Scheduler", font=("Segoe UI", 24, "bold"), anchor="center").grid(row=0, column=0, columnspan=4, pady=(0, 20))

        # Input Fields
        tb.Label(frame, text="Title:", font=("Segoe UI", 11)).grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.title_var = tk.StringVar()
        tb.Entry(frame, textvariable=self.title_var, width=45).grid(row=1, column=1, columnspan=3, sticky="w", padx=5, pady=5)

        tb.Label(frame, text="Description:", font=("Segoe UI", 11)).grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.desc_var = tk.StringVar()
        tb.Entry(frame, textvariable=self.desc_var, width=45).grid(row=2, column=1, columnspan=3, sticky="w", padx=5, pady=5)

        tb.Label(frame, text="Due Date (YYYY-MM-DD):", font=("Segoe UI", 11)).grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.date_var = tk.StringVar()
        tb.Entry(frame, textvariable=self.date_var, width=45).grid(row=3, column=1, columnspan=3, sticky="w", padx=5, pady=5)

        # Buttons Frame
        button_frame = tb.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=4, pady=15)

        tb.Button(button_frame, text="Add Task", bootstyle="success-outline", width=14, command=self.add_task).pack(side="left", padx=6)
        tb.Button(button_frame, text="Modify Task", bootstyle="primary-outline", width=14, command=self.modify_task).pack(side="left", padx=6)
        tb.Button(button_frame, text="Mark as Done", bootstyle="warning-outline", width=14, command=self.mark_task_done).pack(side="left", padx=6)
        tb.Button(button_frame, text="Delete Task", bootstyle="danger-outline", width=14, command=self.delete_task).pack(side="left", padx=6)
        tb.Button(button_frame, text="View in Console", bootstyle="info-outline", width=14, command=self.view_tasks_in_console).pack(side="left", padx=6)

        # Task List Frame
        list_frame = tb.Frame(self.root, padding=(20, 10))
        list_frame.pack(fill="both", expand=True)

        columns = ("ID", "Title", "Description", "Due Date", "Priority", "Status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)

        for col in columns:
            self.tree.heading(col, text=col, anchor="center")
            self.tree.column(col, width=120, anchor="center")

        self.tree.pack(fill="both", expand=True, pady=10)
        self.refresh_tasks()

    def add_task(self):
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
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, description, due_date, priority, "Pending", ai_reason))

        self.conn.commit()
        self.refresh_tasks()

    def modify_task(self):
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
        
        if not self.validate_date(new_due_date):
            messagebox.showerror("Error", "Invalid date format! Use YYYY-MM-DD.")
            return

        new_priority, ai_reason = self.ai_prioritize_task(new_description)

        self.cursor.execute('''
            UPDATE tasks SET title=?, description=?, due_date=?, priority=?, ai_reason=?
            WHERE id=?
        ''', (new_title, new_description, new_due_date, new_priority, ai_reason, task_id))

        self.conn.commit()
        self.refresh_tasks()

    def mark_task_done(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select a task to mark as done!")
            return

        task_id = self.tree.item(selected_item, "values")[0]
        self.cursor.execute("UPDATE tasks SET status='Completed' WHERE id=?", (task_id,))
        self.conn.commit()
        self.refresh_tasks()

    def delete_task(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select a task to delete!")
            return

        task_id = self.tree.item(selected_item, "values")[0]
        self.cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.conn.commit()
        self.refresh_tasks()

    def refresh_tasks(self):
        self.tree.delete(*self.tree.get_children())
        self.cursor.execute("""
            SELECT id, title, description, due_date, priority, status 
            FROM tasks 
            ORDER BY 
                CASE priority
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'Low' THEN 3
                END,
                due_date ASC
        """)
        for task in self.cursor.fetchall():
            self.tree.insert("", "end", values=task)

    def show_notification(self, message):
        def popup():
            messagebox.showwarning("Task Reminder", message)
        self.root.after(0, popup)

    def check_tasks(self):
        while True:
            try:
                conn = sqlite3.connect('tasks.db')
                cursor = conn.cursor()

                now = datetime.now()

                cursor.execute("SELECT title, due_date FROM tasks WHERE status='Pending'")
                tasks = cursor.fetchall()

                for title, due_date in tasks:
                    try:
                        due_datetime = datetime.strptime(due_date, "%Y-%m-%d")
                        delta = (due_datetime - now).days
                        if delta <= 0:
                            self.show_notification(f"Task Reminder: '{title}' is due or overdue!")
                    except Exception as e:
                        print(f"Error parsing task date: {e}")

                conn.close()
            except Exception as e:
                print(f"[Reminder Thread Error]: {e}")

            threading.Event().wait(3600)  # Wait for 1 hour

    def view_tasks_in_console(self):
        try:
            self.cursor.execute("SELECT * FROM tasks")
            rows = self.cursor.fetchall()
            print("\n=== Task List ===")
            for row in rows:
                print(f"ID: {row[0]}, Title: {row[1]}, Description: {row[2]}, Due Date: {row[3]}, Priority: {row[4]}, Status: {row[5]}, AI Reason: {row[6]}")
            print("=================\n")
        except Exception as e:
            print(f"[Error reading tasks]: {e}")

# Entry point
if __name__ == "__main__":
    root = tb.Window(themename="superhero")
    app = TaskScheduler(root)
    root.mainloop()
