# simple_calculator.py

def add(num1, num2):
    return num1 + num2

def subtract(num1, num2):
    return num1 - num2

def multiply(num1, num2):
    return num1 * num2

def divide(num1, num2):
    if num2 != 0:
        return num1 / num2
    else:
        return "Error! Divisor cannot be zero."

def main():
    print("सादा गणित का कैलकुलेटर")
    while True:
        print("विकल्प:")
        print("1. जोड़ने के लिए +")
        print("2. घटाने के लिए -")
        print("3. गुणा करने के लिए *")
        print("4. भाजन के लिए /")
        print("5. निकास")
        
        try:
            choice = int(input("इच्छित कार्य का यौगिक कुंजी : "))
        except ValueError:
            print("गलत यौगिक में")
            continue
        
        if choice in [1, 2, 3, 4]:
            try:
                num1 = float(input("पहला संख्या: "))
                num2 = float(input("दूसरा संख्या : "))
                
                if choice == 1:
                    print(f"{num1} + {num2} = {add(num1, num2)}")
                elif choice == 2:
                    print(f"{num1} - {num2} = {subtract(num1, num2)}")
                elif choice == 3:
                    print(f"{num1} * {num2} = {multiply(num1, num2)}")
                elif choice == 4:
                    print(f"{num1} / {num2} = {divide(num1, num2)}")
                    
            except ValueError:
                print("संख्या में गलत है")
                
        elif choice == 5:
            break
        else:
            print("वैध कुंजी में")
            
if __name__ == "__main__":
    main()
