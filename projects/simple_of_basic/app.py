def add(x, y):
    return x + y

def subtract(x, y):
    return x - y

def multiply(x, y):
    return x * y

def divide(x, y):
    if y == 0:
        return "Error: Division by zero is not allowed"
    return x / y

def calculator():
    print("Simple Calculator")
    while True:
        print("1. Addition")
        print("2. Subtraction")
        print("3. Multiplication")
        print("4. Division")
        print("5. Exit")
        choice = input("Enter your choice (1/2/3/4/5): ")

        if choice in ['1', '2', '3', '4']:
            try:
                num1 = float(input("Enter first number: "))
                num2 = float(input("Enter second number: "))

                if choice == '1':
                    print("Result: ", add(num1, num2))
                elif choice == '2':
                    print("Result: ", subtract(num1, num2))
                elif choice == '3':
                    print("Result: ", multiply(num1, num2))
                elif choice == '4':
                    print("Result: ", divide(num1, num2))
            except ValueError:
                print("Error: Invalid input. Please enter a number.")
            except Exception as e:
                print("Error: ", str(e))
        elif choice == '5':
            print("Exiting calculator. Goodbye!")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")

calculator()
