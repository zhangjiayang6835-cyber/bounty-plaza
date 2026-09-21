To solve this problem, we need to create a function that validates a list of bounty files and returns the total value, total lines, and average validation score.

### Approach
The task is to compute the total value, total lines, and average validation score from a list of bounty files. Each file contains specific data in a table format, and we need to extract the relevant information to compute the required totals.

1. **Initialization**: Start by initializing variables to accumulate the total value, total lines, and total scores.
2. **Iterate through each file**: For each file, read the content and extract the Reward, Lines, and Validation Score from the table.
3. **Accumulate values**: Sum up the rewards, lines, and scores from each file.
4. **Compute totals**: Calculate the total value, total lines, and average validation score.
5. **Format the output**: Return the formatted string with the computed totals.

### Solution Code
```python
def validate_bounties(file_paths):
    total_value = 0.0
    total_lines = 0
    total_scores = 0

    for file_path in file_paths:
        with open(file_path, 'r') as file:
            content = file.read().splitlines()
            for line in content:
                if line.strip().startswith('Bounty'):
                    parts = line.strip().split('|')
                    if len(parts) >= 5:
                        reward = parts[1].strip()
                        if reward.startswith('$'):
                            total_value += float(reward[1:])
                        lines = int(parts[2].strip())
                        total_lines += lines
                        score = parts[3].strip()
                        if '/' in score:
                            total_scores += int(score.split('/')[0])

    average_score = total_scores / len(file_paths)
    total_value = f"${total_value:.0f}" if total_value.is_integer() else f"${total_value:.2f}"
    return f"Total Value: {total_value}\nTotal Lines: {total_lines}\nAverage Validation Score: {average_score:.1f}%"
```

### Explanation
The function `validate_bounties` reads each file path, extracts the relevant data from each file, and computes the total value, total lines, and average validation score. The total value is formatted as a currency value, the total lines are summed up, and the average score is calculated and formatted to one decimal place. The result is returned as a formatted string.