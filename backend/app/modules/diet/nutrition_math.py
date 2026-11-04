from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_UP
import math
from app.modules.diet.library_service import LibraryError

NUTRIENTS = ('calories_kcal','protein_g','fat_g','carbohydrate_g')
PER100 = ('calories_per_100g','protein_g_per_100g','fat_g_per_100g','carbohydrate_g_per_100g')

def number(value):
    try:
        with localcontext() as ctx:
            ctx.prec = 340
            result = float(value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
        if not math.isfinite(result):
            raise ValueError()
        return result
    except (InvalidOperation, ValueError, OverflowError):
        raise LibraryError(422, 'NUTRITION_OVERFLOW', '营养计算结果过大，请减小输入数值')

def scale(value, amount):
    if value is None:
        return None
    with localcontext() as ctx:
        ctx.prec = 340
        return number(Decimal(str(value)) * Decimal(str(amount)) / 100)

def total(values, rounded=True):
    with localcontext() as ctx:
        ctx.prec = 340
        value = sum((Decimal(str(v)) for v in values), Decimal(0))
        if rounded:
            return number(value)
        result = float(value)
        if not math.isfinite(result):
            raise LibraryError(422, 'NUTRITION_OVERFLOW', '目标累计值过大')
        return result

def percent(value, target):
    with localcontext() as ctx:
        ctx.prec = 340
        return number(Decimal(str(value)) / Decimal(str(target)) * 100)
