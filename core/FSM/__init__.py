# FSM Module Exports
from core.FSM.fsm_engine import FSMEngine, ConditionFunc
from core.FSM.fsm_actuator import FSMActuator, fsm_actuator

# Import unified function configuration
try:
    from core.FSM.fsm_functions_config import UNIFIED_FUNCTIONS, get_functions_doc
except ImportError:
    UNIFIED_FUNCTIONS = {}
    def get_functions_doc():
        return {}


def get_default_condition_registry():
    """
    Get default condition registry (loaded from unified function configuration)
    
    Returns:
        Dict[str, ConditionFunc]: Mapping from condition names to condition functions
    """
    return UNIFIED_FUNCTIONS.copy()


__all__ = ['FSMEngine', 'ConditionFunc', 'FSMActuator', 'fsm_actuator', 'get_default_condition_registry', 'UNIFIED_FUNCTIONS', 'get_functions_doc']

