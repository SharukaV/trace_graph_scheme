import math, sys


def calculateKID(data) -> int:
    try:
        время_реал = data[0].msecsSinceStartOfDay()
        время_отбой_по_связи = data[1].msecsSinceStartOfDay()
        время_выхода_из_строя = data[2].msecsSinceStartOfDay()
        время_восстановления = data[3].msecsSinceStartOfDay()

        result = 100 - int(100*(время_восстановления - время_выхода_из_строя) \
                 / (время_отбой_по_связи - время_реал))
        return result

    except Exception as ex:
        print(f'Error in {sys._getframe().f_code.co_filename} line: {sys._getframe().f_lineno} func: {sys._getframe().f_code.co_name}(...)')
        print(f'An exception {type(ex).__name__} occurred. Arguments:\n{ex.args}')
        return -1
