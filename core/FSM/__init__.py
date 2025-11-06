# FSM 模块导出
from core.FSM.fsm_engine import FSMEngine, ConditionFunc
from core.FSM.fsm_actuator import FSMActuator, fsm_actuator

# 导入统一函数配置
try:
    from core.FSM.fsm_functions_config import UNIFIED_FUNCTIONS, get_functions_doc
except ImportError:
    UNIFIED_FUNCTIONS = {}
    def get_functions_doc():
        return {}


def get_default_condition_registry():
    """
    获取默认的条件注册表（从统一函数配置加载）
    
    Returns:
        Dict[str, ConditionFunc]: 条件名称到条件函数的映射
    """
    return UNIFIED_FUNCTIONS.copy()


__all__ = ['FSMEngine', 'ConditionFunc', 'FSMActuator', 'fsm_actuator', 'get_default_condition_registry', 'UNIFIED_FUNCTIONS', 'get_functions_doc']

