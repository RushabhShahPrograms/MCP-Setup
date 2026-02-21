from mcp.server.fastmcp import FastMCP

mcp = FastMCP("UnitConversion")

# ─── Length ───────────────────────────────────────────────────────────────────

LENGTH_TO_METER = {
    "m": 1.0,
    "km": 1000.0,
    "cm": 0.01,
    "mm": 0.001,
    "mile": 1609.344,
    "mi": 1609.344,
    "yard": 0.9144,
    "yd": 0.9144,
    "foot": 0.3048,
    "ft": 0.3048,
    "inch": 0.0254,
    "in": 0.0254,
    "nautical_mile": 1852.0,
    "nm": 1852.0,
    "light_year": 9.461e15,
}

WEIGHT_TO_KG = {
    "kg": 1.0,
    "g": 0.001,
    "mg": 1e-6,
    "lb": 0.453592,
    "pound": 0.453592,
    "oz": 0.0283495,
    "ounce": 0.0283495,
    "ton": 1000.0,
    "tonne": 1000.0,
    "stone": 6.35029,
}

VOLUME_TO_LITER = {
    "l": 1.0,
    "liter": 1.0,
    "ml": 0.001,
    "milliliter": 0.001,
    "gallon": 3.78541,
    "gal": 3.78541,
    "quart": 0.946353,
    "qt": 0.946353,
    "pint": 0.473176,
    "pt": 0.473176,
    "cup": 0.236588,
    "fl_oz": 0.0295735,
    "fluid_ounce": 0.0295735,
    "m3": 1000.0,
    "cm3": 0.001,
}

SPEED_TO_MPS = {
    "m/s": 1.0,
    "mps": 1.0,
    "km/h": 1 / 3.6,
    "kmh": 1 / 3.6,
    "kph": 1 / 3.6,
    "mph": 0.44704,
    "knot": 0.514444,
    "ft/s": 0.3048,
    "fps": 0.3048,
}

AREA_TO_M2 = {
    "m2": 1.0,
    "km2": 1e6,
    "cm2": 1e-4,
    "mm2": 1e-6,
    "ft2": 0.092903,
    "sq_ft": 0.092903,
    "in2": 6.4516e-4,
    "sq_in": 6.4516e-4,
    "acre": 4046.86,
    "hectare": 10000.0,
    "ha": 10000.0,
    "mile2": 2.59e6,
    "sq_mi": 2.59e6,
}

TIME_TO_SECONDS = {
    "second": 1.0,
    "s": 1.0,
    "minute": 60.0,
    "min": 60.0,
    "hour": 3600.0,
    "hr": 3600.0,
    "day": 86400.0,
    "week": 604800.0,
    "month": 2592000.0,   # 30-day month
    "year": 31536000.0,   # 365-day year
    "millisecond": 0.001,
    "ms": 0.001,
    "microsecond": 1e-6,
    "us": 1e-6,
}

PRESSURE_TO_PA = {
    "pa": 1.0,
    "pascal": 1.0,
    "kpa": 1000.0,
    "kilopascal": 1000.0,
    "mpa": 1e6,
    "bar": 100000.0,
    "mbar": 100.0,
    "millibar": 100.0,
    "psi": 6894.76,
    "atm": 101325.0,
    "atmosphere": 101325.0,
    "torr": 133.322,
    "mmhg": 133.322,
}

ENERGY_TO_JOULE = {
    "j": 1.0,
    "joule": 1.0,
    "kj": 1000.0,
    "kilojoule": 1000.0,
    "cal": 4.184,
    "calorie": 4.184,
    "kcal": 4184.0,
    "kilocalorie": 4184.0,
    "wh": 3600.0,
    "watt_hour": 3600.0,
    "kwh": 3.6e6,
    "kilowatt_hour": 3.6e6,
    "ev": 1.602e-19,
    "electron_volt": 1.602e-19,
    "btu": 1055.06,
}


def _convert(value: float, from_unit: str, to_unit: str, table: dict) -> str:
    f = from_unit.lower().replace(" ", "_")
    t = to_unit.lower().replace(" ", "_")
    if f not in table:
        return f"Error: Unknown unit '{from_unit}'. Available: {', '.join(table.keys())}"
    if t not in table:
        return f"Error: Unknown unit '{to_unit}'. Available: {', '.join(table.keys())}"
    result = value * table[f] / table[t]
    return f"{value} {from_unit} = {result:.6g} {to_unit}"


@mcp.tool()
def convert_length(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert length units.
    Supported: m, km, cm, mm, mile/mi, yard/yd, foot/ft, inch/in, nautical_mile/nm, light_year
    Example: convert_length(5, "km", "mile")
    """
    return _convert(value, from_unit, to_unit, LENGTH_TO_METER)


@mcp.tool()
def convert_weight(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert weight/mass units.
    Supported: kg, g, mg, lb/pound, oz/ounce, ton/tonne, stone
    Example: convert_weight(70, "kg", "lb")
    """
    return _convert(value, from_unit, to_unit, WEIGHT_TO_KG)


@mcp.tool()
def convert_temperature(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert temperature units.
    Supported: celsius/c, fahrenheit/f, kelvin/k
    Example: convert_temperature(100, "celsius", "fahrenheit")
    """
    f = from_unit.lower()[0]
    t = to_unit.lower()[0]
    valid = {"c", "f", "k"}
    if f not in valid or t not in valid:
        return f"Error: Unsupported unit. Use celsius (c), fahrenheit (f), or kelvin (k)."

    # Convert to Celsius first
    if f == "c":
        celsius = value
    elif f == "f":
        celsius = (value - 32) * 5 / 9
    else:  # kelvin
        celsius = value - 273.15

    # Convert Celsius to target
    if t == "c":
        result = celsius
    elif t == "f":
        result = celsius * 9 / 5 + 32
    else:  # kelvin
        result = celsius + 273.15

    return f"{value}° {from_unit.capitalize()} = {result:.4f}° {to_unit.capitalize()}"


@mcp.tool()
def convert_volume(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert volume units.
    Supported: l/liter, ml/milliliter, gallon/gal, quart/qt, pint/pt, cup, fl_oz, m3, cm3
    Example: convert_volume(1, "gallon", "liter")
    """
    return _convert(value, from_unit, to_unit, VOLUME_TO_LITER)


@mcp.tool()
def convert_speed(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert speed units.
    Supported: m/s, km/h (kmh/kph), mph, knot, ft/s (fps)
    Example: convert_speed(100, "kmh", "mph")
    """
    return _convert(value, from_unit, to_unit, SPEED_TO_MPS)


@mcp.tool()
def convert_area(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert area units.
    Supported: m2, km2, cm2, mm2, ft2/sq_ft, in2/sq_in, acre, hectare/ha, sq_mi
    Example: convert_area(1, "acre", "m2")
    """
    return _convert(value, from_unit, to_unit, AREA_TO_M2)


@mcp.tool()
def convert_time(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert time units.
    Supported: second/s, minute/min, hour/hr, day, week, month, year, millisecond/ms, microsecond/us
    Example: convert_time(2, "hour", "minute")
    """
    return _convert(value, from_unit, to_unit, TIME_TO_SECONDS)


@mcp.tool()
def convert_pressure(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert pressure units.
    Supported: pa/pascal, kpa, mpa, bar, mbar, psi, atm/atmosphere, torr/mmhg
    Example: convert_pressure(1, "atm", "psi")
    """
    return _convert(value, from_unit, to_unit, PRESSURE_TO_PA)


@mcp.tool()
def convert_energy(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert energy units.
    Supported: j/joule, kj, cal/calorie, kcal, wh, kwh, ev, btu
    Example: convert_energy(1, "kwh", "kj")
    """
    return _convert(value, from_unit, to_unit, ENERGY_TO_JOULE)


@mcp.tool()
def list_conversion_categories() -> str:
    """List all available unit conversion categories and their supported units."""
    categories = {
        "Length": list(LENGTH_TO_METER.keys()),
        "Weight": list(WEIGHT_TO_KG.keys()),
        "Temperature": ["celsius/c", "fahrenheit/f", "kelvin/k"],
        "Volume": list(VOLUME_TO_LITER.keys()),
        "Speed": list(SPEED_TO_MPS.keys()),
        "Area": list(AREA_TO_M2.keys()),
        "Time": list(TIME_TO_SECONDS.keys()),
        "Pressure": list(PRESSURE_TO_PA.keys()),
        "Energy": list(ENERGY_TO_JOULE.keys()),
    }
    result = []
    for cat, units in categories.items():
        result.append(f"{cat}: {', '.join(units)}")
    return "\n".join(result)


if __name__ == "__main__":
    mcp.run(transport="stdio")