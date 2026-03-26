# app.py

def get_number_input(prompt):
    while True:
        try:
            num_str = input(prompt)
            return float(num_str)
        except ValueError:
            print("Invalid input. Please enter a valid number.")

def get_operator_input():
    while True:
        operator = input("Enter operator (+, -, *, /): ").strip()
        if operator in ['+', '-', '*', '/']:
            return operator
        else:
            print("Invalid operator. Please choose from +, -, *, /.")

def calculate(num1, num2, operator):
    if operator == '+':
        return num1 + num2
    elif operator == '-':
        return num1 - num2
    elif operator == '*':
        return num1 * num2
    elif operator == '/':
        if num2 == 0:
            raise ZeroDivisionError("Cannot divide by zero!")
        return num1 / num2
    else:
        # This case should ideally not be reached due to get_operator_input validation
        raise ValueError("Unknown operator.")

def main():
    print("Welcome to Of Simple Calculator!")

    while True:
        num1 = get_number_input("Enter first number: ")
        operator = get_operator_input()
        num2 = get_number_input("Enter second number: ")

        try:
            result = calculate(num1, num2, operator)
            print(f"Result: {num1} {operator} {num2} = {result}")
        except ZeroDivisionError as e:
            print(f"Error: {e}")
        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        while True:
            continue_calculation = input("Do you want to perform another calculation? (yes/no): ").strip().lower()
            if continue_calculation in ['yes', 'y']:
                break
            elif continue_calculation in ['no', 'n']:
                print("Thank you for using Of Simple Calculator. Goodbye!")
                return
            else:
                print("Invalid input. Please enter 'yes' or 'no'.")

if __name__ == "__main__":
    main()
