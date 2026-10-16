"""Stable English names for known parametric resource sets."""
NAMES={'门把手':'handle','门框':'frame','竖格栅':'vertical_bars','横格栅':'horizontal_bars',
       '玻璃':'glass','调整宽度对应的点':'resize_width_vertices',
       '调整高度对应的点':'resize_height_vertices','长度调整点':'resize_length_vertices'}

def names(record):
    result={}
    for key,value in record.items():
        target=NAMES.get(key,key)
        if target in result and value and result[target]:
            raise ValueError('Conflicting legacy and current named set: '+target)
        if target not in result or value:result[target]=value
    return result

def recipe(value):
    if isinstance(value,str):return NAMES.get(value,value)
    if isinstance(value,list):return [recipe(v) for v in value]
    if isinstance(value,dict):return {NAMES.get(k,k):recipe(v) for k,v in value.items()}
    return value
