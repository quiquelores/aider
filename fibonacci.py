def fibonacci_sequence(n):
    sequence = []
    a, b = 0, 1
    while len(sequence) < n:
        sequence.append(a)
        a, b = b, a + b
    return sequence

def main():
    fib_numbers = fibonacci_sequence(10)
    print("The first 10 Fibonacci numbers are:")
    for number in fib_numbers:
        print(number)

if __name__ == "__main__":
    main()
