import math
import statistics
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b. Returns error if b is zero."""
    if b == 0:
        return "Error: Division by zero is undefined."
    return a / b


@mcp.tool()
def power(base: float, exponent: float) -> float:
    """Raise base to the power of exponent."""
    return base ** exponent


@mcp.tool()
def square_root(n: float) -> str:
    """Calculate the square root of a number."""
    if n < 0:
        return "Error: Cannot take square root of a negative number."
    return str(math.sqrt(n))


@mcp.tool()
def factorial(n: int) -> str:
    """Calculate the factorial of a non-negative integer."""
    if n < 0:
        return "Error: Factorial is not defined for negative numbers."
    if n > 170:
        return "Error: Number too large (max 170)."
    return str(math.factorial(n))


@mcp.tool()
def log(n: float, base: float = math.e) -> str:
    """Calculate logarithm of n. Default base is e (natural log). Pass base=10 for log10."""
    if n <= 0:
        return "Error: Logarithm is only defined for positive numbers."
    if base <= 0 or base == 1:
        return "Error: Base must be positive and not equal to 1."
    return str(math.log(n, base))


@mcp.tool()
def sin(angle_degrees: float) -> float:
    """Calculate the sine of an angle given in degrees."""
    return math.sin(math.radians(angle_degrees))


@mcp.tool()
def cos(angle_degrees: float) -> float:
    """Calculate the cosine of an angle given in degrees."""
    return math.cos(math.radians(angle_degrees))


@mcp.tool()
def tan(angle_degrees: float) -> str:
    """Calculate the tangent of an angle given in degrees."""
    if angle_degrees % 180 == 90:
        return "Error: Tangent is undefined at 90 degrees."
    return str(math.tan(math.radians(angle_degrees)))


@mcp.tool()
def gcd(a: int, b: int) -> int:
    """Calculate the Greatest Common Divisor (GCD) of two integers."""
    return math.gcd(abs(a), abs(b))


@mcp.tool()
def lcm(a: int, b: int) -> int:
    """Calculate the Least Common Multiple (LCM) of two integers."""
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // math.gcd(abs(a), abs(b))


@mcp.tool()
def is_prime(n: int) -> str:
    """Check whether a given integer is a prime number."""
    if n < 2:
        return f"{n} is NOT prime."
    if n == 2:
        return f"{n} IS prime."
    if n % 2 == 0:
        return f"{n} is NOT prime."
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return f"{n} is NOT prime."
    return f"{n} IS prime."


@mcp.tool()
def fibonacci(n: int) -> str:
    """Return the first n Fibonacci numbers."""
    if n <= 0:
        return "Error: n must be a positive integer."
    if n > 100:
        return "Error: n is too large (max 100)."
    seq = [0, 1]
    for _ in range(2, n):
        seq.append(seq[-1] + seq[-2])
    return str(seq[:n])


@mcp.tool()
def solve_quadratic(a: float, b: float, c: float) -> str:
    """Solve quadratic equation ax² + bx + c = 0. Returns real roots."""
    if a == 0:
        if b == 0:
            return "Error: Not a valid equation."
        return f"Linear solution: x = {-c / b}"
    discriminant = b ** 2 - 4 * a * c
    if discriminant > 0:
        x1 = (-b + math.sqrt(discriminant)) / (2 * a)
        x2 = (-b - math.sqrt(discriminant)) / (2 * a)
        return f"Two real roots: x1 = {x1:.6f}, x2 = {x2:.6f}"
    elif discriminant == 0:
        x = -b / (2 * a)
        return f"One real root: x = {x:.6f}"
    else:
        real = -b / (2 * a)
        imag = math.sqrt(-discriminant) / (2 * a)
        return f"Complex roots: x1 = {real:.4f}+{imag:.4f}i, x2 = {real:.4f}-{imag:.4f}i"


@mcp.tool()
def mean(numbers: list[float]) -> float:
    """Calculate the arithmetic mean of a list of numbers."""
    return statistics.mean(numbers)


@mcp.tool()
def median(numbers: list[float]) -> float:
    """Calculate the median of a list of numbers."""
    return statistics.median(numbers)


@mcp.tool()
def std_deviation(numbers: list[float]) -> float:
    """Calculate the standard deviation of a list of numbers."""
    if len(numbers) < 2:
        return 0.0
    return statistics.stdev(numbers)


@mcp.tool()
def percentage(value: float, total: float) -> str:
    """Calculate what percentage value is of total."""
    if total == 0:
        return "Error: Total cannot be zero."
    return f"{(value / total) * 100:.4f}%"


@mcp.tool()
def percentage_change(old_value: float, new_value: float) -> str:
    """Calculate the percentage change from old_value to new_value."""
    if old_value == 0:
        return "Error: Old value cannot be zero."
    change = ((new_value - old_value) / abs(old_value)) * 100
    direction = "increase" if change >= 0 else "decrease"
    return f"{abs(change):.4f}% {direction}"


@mcp.tool()
def compound_interest(principal: float, rate: float, time: float, n: int = 12) -> str:
    """
    Calculate compound interest.
    principal: initial amount
    rate: annual interest rate as percentage (e.g., 5 for 5%)
    time: time in years
    n: compounding frequency per year (default 12 = monthly)
    """
    r = rate / 100
    amount = principal * (1 + r / n) ** (n * time)
    interest = amount - principal
    return f"Final Amount: {amount:.2f} | Interest Earned: {interest:.2f}"


if __name__ == "__main__":
    mcp.run(transport="stdio")