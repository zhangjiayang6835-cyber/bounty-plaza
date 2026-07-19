def verify_solution(solution):
    """Verify the solution provided by the user.
    
    :param solution: The solution to be verified.
    :return: True if the solution is correct, False otherwise.
    """
    # Example deterministic verification logic
    expected_output = "expected_output"
    return solution == expected_output

# Example usage
if __name__ == "__main__":
    user_solution = input("Enter your solution: ")
    if verify_solution(user_solution):
        print("Solution is correct!")
    else:
        print("Solution is incorrect.")