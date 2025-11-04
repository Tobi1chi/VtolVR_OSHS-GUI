from typing import Callable, Dict, Any, List, Optional, Tuple


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
            # 单一条件名称（向后兼容）
            cond_name = t.get("cond")
            if cond_name:
                func = self.condition_registry.get(cond_name)
                try:
                    matched = func(context) if func else False
                except Exception:
                    matched = False
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
                    self.current_key = next_key
                    return next_key, t.get("actuator_cmd")
                return None

        if else_target is not None:
            self.current_key = else_target
            return else_target, else_actuator

        return None

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
            # 条件名称
            name = consume()
            if name is None:
                raise ValueError('unexpected end')
            func = self.condition_registry.get(name)
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
            if c in '()':
                out.append(c)
                i += 1
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


