# main.py
import json

TODO_FILE = "todo.json"

def load_todos():
    try:
        with open(TODO_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_todos(todos):
    with open(TODO_FILE, 'w') as f:
        json.dump(todos, f, indent=4)

def display_todos(todos):
    if not todos:
        print("Your to-do list is empty!")
        return
    print("\n--- To-Do List ---")
    for index, todo in enumerate(todos):
        status = "[x]" if todo["completed"] else "[ ]"
        print(f"{index + 1}. {status} {todo['task']}")
    print("------------------\n")

def add_todo(todos, task):
    todos.append({"task": task, "completed": False})
    save_todos(todos)
    print(f"Added: '{task}'")

def mark_complete(todos, index):
    if 0 <= index < len(todos):
        todos[index]["completed"] = True
        save_todos(todos)
        print(f"Marked as complete: '{todos[index]['task']}'")
    else:
        print("Invalid to-do index.")

def delete_todo(todos, index):
    if 0 <= index < len(todos):
        removed_task = todos.pop(index)
        save_todos(todos)
        print(f"Deleted: '{removed_task['task']}'")
    else:
        print("Invalid to-do index.")

def main():
    todos = load_todos()

    while True:
        print("1. View To-Dos")
        print("2. Add To-Do")
        print("3. Mark To-Do as Complete")
        print("4. Delete To-Do")
        print("5. Exit")

        choice = input("Enter your choice: ")

        if choice == '1':
            display_todos(todos)
        elif choice == '2':
            task = input("Enter the to-do task: ")
            if task:
                add_todo(todos, task)
            else:
                print("Task cannot be empty.")
        elif choice == '3':
            display_todos(todos)
            try:
                index = int(input("Enter the number of the to-do to mark as complete: ")) - 1
                mark_complete(todos, index)
            except ValueError:
                print("Invalid input. Please enter a number.")
        elif choice == '4':
            display_todos(todos)
            try:
                index = int(input("Enter the number of the to-do to delete: ")) - 1
                delete_todo(todos, index)
            except ValueError:
                print("Invalid input. Please enter a number.")
        elif choice == '5':
            print("Exiting to-do list. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
