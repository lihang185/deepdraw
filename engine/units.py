"""All model coordinates and lengths are centimetres; display is a conversion only."""
import math
import re
INTERNAL_UNIT = 'cm'
FACTORS = {'cm':1.0, 'mm':0.1, 'm':100.0, 'in':2.54, 'ft':30.48}

def parse_length(text, display_unit='cm'):
    match=re.fullmatch(r'\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*(cm|mm|m|in|ft)?\s*', str(text), re.I)
    if not match: raise ValueError('请输入长度，例如 120、120cm、1.2m 或 1200mm')
    value=float(match.group(1))*FACTORS[(match.group(2) or display_unit).lower()]
    if not math.isfinite(value): raise ValueError('长度必须为有限数值')
    return value

def format_length(cm, display_unit='cm'):
    return '{:.6g} {}'.format(cm/FACTORS[display_unit], display_unit)

def snap_integer(value):
    return math.copysign(math.floor(abs(value)+0.5),value)
