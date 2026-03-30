# calculator.py

def get_number(prompt):
    """
    Prompts the user for a number and handles invalid input until a valid number is provided.
    """
    while True:
        try:
            num_str = input(prompt)
            return float(num_str)
        except ValueError:
            print("Invalid input. Please enter a valid number.")

print("Welcome to Simple Calculator!")

while True:
    print("\n--- Calculator Menu ---")
    print("1. Add (+)")
    print("2. Subtract (-)")
    print("3. Multiply (*)")
    print("4. Divide (/)")
    print("5. Exit")

    choice = input("Enter your choice (1/2/3/4/5): ")

    if choice == '5':
        print("Exiting calculator. Goodbye!")
        break
    elif choice in ('1', '2', '3', '4'):
        num1 = get_number("Enter first number: ")
        num2 = get_number("Enter second number: ")

        if choice == '1':
            result = num1 + num2
            print(f"{num1} + {num2} = {result}")
        elif choice == '2':
            result = num1 - num2
            print(f"{num1} - {num2} = {result}")
        elif choice == '3':
            result = num1 * num2
            print(f"{num1} * {num2} = {result}")
        elif choice == '4':
            if num2 == 0:
                print("Error: Cannot divide by zero!")
            else:
                result = num1 / num2
                print(f"{num1} / {num2} = {result}")
    else:
        print("Invalid choice. Please enter a number between 1 and 5.")
