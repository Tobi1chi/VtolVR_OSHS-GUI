from typing import Callable, Dict, Any, List, Optional, Tuple, Union

# 导入统一函数注册表
try:
    from core.FSM.fsm_functions_config import UNIFIED_FUNCTIONS
except ImportError:
    UNIFIED_FUNCTIONS = {}


ConditionFunc = Callable[[dict], bool]


class FSMEngine:
    """
    轻量级有限状态机引擎：
    - 状态以字典列表给出（含 Key）。
    - 支持 `Transitions`: [{"to": "2", "cond": "need_players_ge_8"}, {"to": "3", "else": true, "actuator_cmd": "start"}]
    - 兼容旧格式：若无 `Transitions`，则尝试使用 `Linked State` 的第一个元素作为无条件转移。
    - `condition_registry` 中注册条件函数，名称对应 JSON。
    - `step(context)` 会按顺序评估条件，命中则转移并返回 (next_key, actuator_cmd)。
    """

    def __init__(self, states: List[dict], condition_registry: Dict[str, ConditionFunc]):
        self.state_by_key: Dict[str, dict] = {str(s.get("Key")): s for s in states}
        self.condition_registry: Dict[str, ConditionFunc] = condition_registry
        self.current_key: Optional[str] = None

    def start(self, start_key: str) -> None:
        self.current_key = str(start_key) if start_key is not None else None

    def reset(self) -> None:
        self.current_key = None

    def get_current(self) -> Optional[str]:
        return self.current_key

    def step(self, context: dict) -> Optional[Tuple[str, Optional[str]]]:
        if self.current_key is None:
            return None

        state = self.state_by_key.get(self.current_key)
        if not state:
            return None

        transitions = state.get("Transitions")

        # 兼容老格式：没有 Transitions，则使用 Linked State 的第一个元素
        if not transitions:
            linked = state.get("Linked State", [])
            if linked:
                next_key = str(linked[0])
                # 无条件转移，立即应用
                self.current_key = next_key
                return next_key, None
            return None

        else_target: Optional[str] = None
        else_actuator: Optional[str] = None

        for t in transitions:
            if t.get("else"):
                else_target = str(t.get("to")) if t.get("to") is not None else None
                else_actuator = t.get("actuator_cmd")
                continue

            matched = False
            # 单一条件名称（向后兼容，支持函数调用）
            cond_name = t.get("cond")
            if cond_name:
                matched = self._evaluate_condition(cond_name, context)
            # 逻辑表达式：支持 and/or/not 与括号
            cond_expr = t.get("cond_expr")
            if cond_expr and not matched:
                try:
                    matched = self._eval_condition_expr(str(cond_expr), context)
                except Exception:
                    matched = False

            if matched:
                next_key = str(t.get("to")) if t.get("to") is not None else None
                if next_key is not None:
                    # 不立即转移状态，返回转移信息让外部决定何时转移
                    return next_key, t.get("actuator_cmd")
                return None

        if else_target is not None:
            # 不立即转移状态，返回转移信息让外部决定何时转移
            return else_target, else_actuator

        return None
    
    def apply_transition(self, next_key: str) -> None:
        """
        应用状态转移（在 action 执行完成后调用）
        
        Args:
            next_key: 要转移到的状态 Key
        """
        if next_key is not None:
            self.current_key = str(next_key)
    
    def _evaluate_condition(self, cond_expr: str, context: dict) -> bool:
        """
        评估单个条件表达式（支持函数调用）
        
        Args:
            cond_expr: 条件表达式，如 "players_ge(3)" 或 "server_ready"
            context: 上下文字典
        
        Returns:
            bool: 条件是否满足
        """
        # 检查是否是函数调用
        if '(' in cond_expr and cond_expr.endswith(')'):
            # 解析函数调用
            func_name = cond_expr[:cond_expr.index('(')].strip()
            args_str = cond_expr[cond_expr.index('(')+1:-1].strip()
            
            # 解析参数
            args = []
            if args_str:
                # 简单的参数解析（支持逗号分隔）
                tokens = self._tokenize(args_str)
                i = 0
                while i < len(tokens):
                    token = tokens[i]
                    if token == ',':
                        i += 1
                        continue
                    # 字符串字面量（带引号）
                    if (token.startswith('"') and token.endswith('"')) or \
                       (token.startswith("'") and token.endswith("'")):
                        args.append(token[1:-1])  # 移除引号
                        i += 1
                    # 数字
                    elif token.replace('.', '').replace('-', '').isdigit():
                        try:
                            args.append(float(token) if '.' in token else int(token))
                        except ValueError:
                            args.append(token)
                        i += 1
                    # 布尔值
                    elif token.lower() == 'true':
                        args.append(True)
                        i += 1
                    elif token.lower() == 'false':
                        args.append(False)
                        i += 1
                    else:
                        args.append(token)
                        i += 1
            
            # 调用函数
            func = self.condition_registry.get(func_name)
            if func is None:
                unified_func = UNIFIED_FUNCTIONS.get(func_name)
                if unified_func:
                    try:
                        result = unified_func(context, *args)
                        return bool(result) if not isinstance(result, dict) else bool(result.get("ok", False))
                    except Exception:
                        return False
                return False
            else:
                try:
                    result = func(context, *args) if args else func(context)
                    return bool(result) if not isinstance(result, dict) else bool(result.get("ok", False))
                except Exception:
                    return False
        else:
            # 无参数调用
            func = self.condition_registry.get(cond_expr)
            if func is None:
                unified_func = UNIFIED_FUNCTIONS.get(cond_expr)
                if unified_func:
                    try:
                        result = unified_func(context)
                        return bool(result) if not isinstance(result, dict) else bool(result.get("ok", False))
                    except Exception:
                        return False
                return False
            else:
                try:
                    matched = func(context)
                    return bool(matched) if not isinstance(matched, dict) else bool(matched.get("ok", False))
                except Exception:
                    return False

    # ===== 内部：布尔表达式解析（and/or/not 与括号） =====
    def _eval_condition_expr(self, expr: str, context: dict) -> bool:
        tokens = self._tokenize(expr)
        pos = 0

        def peek() -> Optional[str]:
            return tokens[pos] if pos < len(tokens) else None

        def consume(expected: Optional[str] = None) -> Optional[str]:
            nonlocal pos
            if pos < len(tokens):
                t = tokens[pos]
                if expected is None or t == expected:
                    pos += 1
                    return t
            return None

        def parse_expr() -> bool:
            val = parse_term()
            while True:
                t = peek()
                if t == 'or':
                    consume('or')
                    rhs = parse_term()
                    val = bool(val or rhs)
                else:
                    break
            return val

        def parse_term() -> bool:
            val = parse_factor()
            while True:
                t = peek()
                if t == 'and':
                    consume('and')
                    rhs = parse_factor()
                    val = bool(val and rhs)
                else:
                    break
            return val

        def parse_factor() -> bool:
            t = peek()
            if t == 'not':
                consume('not')
                return not parse_factor()
            if t == '(':
                consume('(')
                val = parse_expr()
                if not consume(')'):
                    raise ValueError('missing closing )')
                return val
            # 条件名称或函数调用
            name = consume()
            if name is None:
                raise ValueError('unexpected end')
            
            # 检查是否是函数调用（有括号）
            if peek() == '(':
                consume('(')
                # 解析函数参数
                args = []
                if peek() != ')':
                    while True:
                        arg = self._parse_function_arg(consume, peek)
                        args.append(arg)
                        if peek() == ',':
                            consume(',')
                        else:
                            break
                if not consume(')'):
                    raise ValueError('missing closing ) for function call')
                
                # 调用函数（带参数）
                func = self.condition_registry.get(name)
                if func is None:
                    unified_func = UNIFIED_FUNCTIONS.get(name)
                    if unified_func:
                        try:
                            result = unified_func(context, *args)
                            return bool(result) if not isinstance(result, dict) else bool(result.get("ok", False))
                        except Exception:
                            return False
                else:
                    try:
                        result = func(context, *args) if args else func(context)
                        return bool(result) if not isinstance(result, dict) else bool(result.get("ok", False))
                    except Exception:
                        return False
                return False
            else:
                # 无参数调用
                func = self.condition_registry.get(name)
                if func is None:
                    unified_func = UNIFIED_FUNCTIONS.get(name)
                    if unified_func:
                        try:
                            result = unified_func(context)
                            return bool(result) if not isinstance(result, dict) else bool(result.get("ok", False))
                        except Exception:
                            return False
                return bool(func(context) if func else False)

        result = parse_expr()
        if pos != len(tokens):
            raise ValueError('unexpected token at end')
        return bool(result)

    def _tokenize(self, s: str) -> List[str]:
        out: List[str] = []
        i = 0
        n = len(s)
        while i < n:
            c = s[i]
            if c.isspace():
                i += 1
                continue
            if c in '(),':
                out.append(c)
                i += 1
                continue
            # 识别字符串字面量（单引号或双引号）
            if c in '\'"':
                quote = c
                j = i + 1
                while j < n and s[j] != quote:
                    if s[j] == '\\' and j + 1 < n:
                        j += 2  # 跳过转义字符
                    else:
                        j += 1
                if j < n:
                    out.append(s[i:j+1])  # 包含引号
                    i = j + 1
                    continue
            # 识别数字
            if c.isdigit() or (c == '-' and i + 1 < n and s[i+1].isdigit()):
                j = i + 1
                while j < n and (s[j].isdigit() or s[j] == '.'):
                    j += 1
                out.append(s[i:j])
                i = j
                continue
            # 识别标识符（条件名或 and/or/not）
            j = i
            while j < n and (s[j].isalnum() or s[j] == '_' or s[j] == '.'):  # 允许下划线与点
                j += 1
            if j == i:
                raise ValueError(f'bad char: {s[i]!r}')
            ident = s[i:j]
            lw = ident.lower()
            if lw in ('and', 'or', 'not'):
                out.append(lw)
            else:
                out.append(ident)
            i = j
        return out
    
    def _parse_function_arg(self, consume, peek) -> Any:
        """解析函数参数（支持数字、字符串、布尔值）"""
        token = peek()
        if token is None:
            raise ValueError('unexpected end in function argument')
        
        # 字符串字面量
        if (token.startswith('"') and token.endswith('"')) or \
           (token.startswith("'") and token.endswith("'")):
            consume()
            # 移除引号并处理转义
            s = token[1:-1]
            s = s.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
            return s
        
        # 数字
        try:
            if '.' in token:
                return float(token)
            else:
                return int(token)
        except ValueError:
            pass
        
        # 布尔值
        if token.lower() == 'true':
            consume()
            return True
        if token.lower() == 'false':
            consume()
            return False
        
        # 默认作为字符串（无引号）
        consume()
        return token


