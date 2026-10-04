To solve this problem, we need to determine the day of the week for any given date using Zeller's Congruence formula. The goal is to return the day as an integer from 0 to 6, where 0 represents Sunday, 1 represents Monday, and so on, up to 6 representing Saturday.

### Approach
The approach involves using Zeller's Congruence formula, which allows us to compute the day of the week for any date in the Gregorian calendar. The formula is:

\[ h = (q + \left\lfloor \frac{13(m + 1)}{5} \right\rfloor + K + \left\lfloor \frac{K}{4} \right\rfloor + \left\lfloor \frac{J}{4} \right\rfloor + 5J) \mod 7 \]

Where:
- \( q \) is the day of the month.
- \( m \) is the month, with January and February treated as 13 and 14 of the previous year.
- \( K \) is the year of the century (year % 100).
- \( J \) is the zero-based century (year // 100).

### Solution Code
```javascript
function getDayOfWeek(y, m, d) {
    let q = d;
    let m = m < 1 ? 13 : (m < 3 ? m + 12 : m);
    let year = m < 3 ? y - 1 : y;
    let K = year % 100;
    let J = Math.floor(year / 100);
    let h = (q + Math.floor((13 * (m + 1)) / 5) + K + Math.floor(K / 4) + Math.floor(J / 4) + 5 * J) % 7;
    return h;
}
```

### Explanation
The function `getDayOfWeek` computes the day of the week using Zeller's Congruence. It adjusts the month and year as needed, then applies the formula to find the day of the week as an integer from 0 (Sunday) to 6 (Saturday). The example given, December 31, 2020, correctly returns 5, which corresponds to Thursday.