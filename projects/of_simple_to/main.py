class ToDoList:
    def __init__(self):
        self.tasks = {}

    def add_task(self, task, description):
        if task in self.tasks:
            print("Task already exists. Please update the existing task or delete it first.")
            return
        else:
            self.tasks[task] = description
            print(f"Task '{task}' added successfully.")

    def delete_task(self, task):
        if task in self.tasks:
            del self.tasks[task]
            print(f"Task '{task}' deleted successfully.")
        else:
            print("Task does not exist.")

    def update_task(self, task, description):
        if task in self.tasks:
            self.tasks[task] = description
            print(f"Task '{task}' updated successfully.")
        else:
            print("Task does not exist.")

    def view_tasks(self):
        if self.tasks:
            print("Your tasks:")
            for task, description in self.tasks.items():
                print(f"Task: {task} - Description: {description}")
        else:
            print("No tasks available.")

    def save_tasks(self):
        with open("tasks.txt", "w") as f:
            for task, description in self.tasks.items():
                f.write(f"{task}:{description}\n")
        print("Tasks saved successfully.")

    def load_tasks(self):
        try:
            with open("tasks.txt", "r") as f:
                for line in f.readlines():
                    task, description = line.strip().split(":")
                    self.tasks[task] = description
            print("Tasks loaded successfully.")
        except FileNotFoundError:
            print("No tasks available.")

def main():
    todo_list = ToDoList()
    todo_list.load_tasks()

    while True:
        print("\nTo-Do List Menu:")
        print("1. Add task")
        print("2. Delete task")
        print("3. Update task")
        print("4. View tasks")
        print("5. Save tasks")
        print("6. Quit")

        choice = input("Enter your choice (1-6): ")

        if choice == "1":
            task = input("Enter the task name: ")
            description = input("Enter the task description: ")
            todo_list.add_task(task, description)
        elif choice == "2":
            task = input("Enter the task name to delete: ")
            todo_list.delete_task(task)
        elif choice == "3":
            task = input("Enter the task name to update: ")
            description = input("Enter the new task description: ")
            todo_list.update_task(task, description)
        elif choice == "4":
            todo_list.view_tasks()
        elif choice == "5":
            todo_list.save_tasks()
        elif choice == "6":
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
