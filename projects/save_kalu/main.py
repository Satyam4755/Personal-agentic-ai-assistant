class BankAccount:
    def __init__(self, account_number, account_balance):
        self.account_number = account_number
        self.account_balance = account_balance

    def deposit(self, amount):
        self.account_balance += amount
        print(f"Deposited ${amount} into account {self.account_number}. New balance is ${self.account_balance}.")

    def withdraw(self, amount):
        if amount > self.account_balance:
            print("Insufficient funds.")
        else:
            self.account_balance -= amount
            print(f"Withdrew ${amount} from account {self.account_number}. New balance is ${self.account_balance}.")

    def check_balance(self):
        print(f"Current balance for account {self.account_number} is ${self.account_balance}.")

def main():
    accounts = {}

    while True:
        print("\nBanking Menu:")
        print("1. Create account")
        print("2. Deposit")
        print("3. Withdraw")
        print("4. Check balance")
        print("5. Exit")
        
        choice = input("\nChoose an option: ")

        if choice == "1":
            account_number = input("Enter account number: ")
            account_balance = float(input("Enter initial balance: "))
            accounts[account_number] = BankAccount(account_number, account_balance)
            print(f"Account {account_number} created with initial balance ${account_balance}")
        elif choice == "2":
            account_number = input("Enter account number: ")
            if account_number in accounts:
                amount = float(input("Enter deposit amount: "))
                accounts[account_number].deposit(amount)
            else:
                print("Account not found. Please try again.")
        elif choice == "3":
            account_number = input("Enter account number: ")
            if account_number in accounts:
                amount = float(input("Enter withdrawal amount: "))
                accounts[account_number].withdraw(amount)
            else:
                print("Account not found. Please try again.")
        elif choice == "4":
            account_number = input("Enter account number: ")
            if account_number in accounts:
                accounts[account_number].check_balance()
            else:
                print("Account not found. Please try again.")
        elif choice == "5":
            print("Exiting bank system.")
            break
        else:
            print("Invalid option. Please choose a valid option.")

if __name__ == "__main__":
    main()
