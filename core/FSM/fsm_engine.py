from typing import Callable, Dict, Any, List, Optional, Tuple, Union

# Import unified function registry
try:
    from core.FSM.fsm_functions_config import UNIFIED_FUNCTIONS
except ImportError:
    UNIFIED_FUNCTIONS = {}


ConditionFunc = Callable[[dict], bool]


class FSMEngine:
    """
    Lightweight Finite State Machine Engine:
    - States are given as a list of dictionaries (containing Key).
    - Supports `Transitions`: [{"to": "2", "cond": "need_players_ge_8"}, {"to": "3", "else": true, "actuator_cmd": "start"}]
    - Compatible with old format: If no `Transitions`, tries to use the first element of `Linked State` as an unconditional transition.
    - Condition functions are registered in `condition_registry`, names correspond to JSON.
    - `step(context)` evaluates conditions in order, if matched, transitions and returns (next_key, actuator_cmd).
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

        # Compatible with old format: if no Transitions, use first element of Linked State
        if not transitions:
            linked = state.get("Linked State", [])
            if linked:
                next_key = str(linked[0])
                # Unconditional transition, apply immediately
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
            # Single condition name (backward compatible, supports function calls)
            cond_name = t.get("cond")
            if cond_name:
                matched = self._evaluate_condition(cond_name, context)
            # Logical expression: supports and/or/not with parentheses
            cond_expr = t.get("cond_expr")
            if cond_expr and not matched:
                try:
                    matched = self._eval_condition_expr(str(cond_expr), context)
                except Exception:
                    matched = False

            if matched:
                next_key = str(t.get("to")) if t.get("to") is not None else None
                if next_key is not None:
                    # Do not transition immediately, return transition info for external decision
                    return next_key, t.get("actuator_cmd")
                return None

        if else_target is not None:
            # Do not transition immediately, return transition info for external decision
            return else_target, else_actuator

        return None
    
    def apply_transition(self, next_key: str) -> None:
        """
        Apply state transition (called after action execution completes)
        
        Args:
            next_key: State Key to transition to
        """
        if next_key is not None:
            self.current_key = str(next_key)
    
    def get_state_entry_action(self, state_key: str) -> Optional[str]:
        """
        Get state Entry action (if exists)
        
        Args:
            state_key: State Key
            
        Returns:
            Entry action string, returns init action if state has campaign id and mapname
        """
        state = self.state_by_key.get(str(state_key))
        if not state:
            return None
        
        campaign_id = state.get("campaign id") or state.get("campaign_id")
        mapname = state.get("mapname")
        
        if campaign_id and mapname:
            return f"init:{campaign_id},{mapname}"
        
        return None
    
    def _evaluate_condition(self, cond_expr: str, context: dict) -> bool:
        """
        Evaluate a single condition expression (supports function calls)
        
        Args:
            cond_expr: Condition expression, like "players_ge(3)" or "server_ready"
            context: Context dictionary
        
        Returns:
            bool: Whether the condition is satisfied
        """
        # Check if it's a function call
        if '(' in cond_expr and cond_expr.endswith(')'):
            # Parse function call
            func_name = cond_expr[:cond_expr.index('(')].strip()
            args_str = cond_expr[cond_expr.index('(')+1:-1].strip()
            
            # Parse arguments
            args = []
            if args_str:
                # Simple argument parsing (supports comma separation)
                tokens = self._tokenize(args_str)
                i = 0
                while i < len(tokens):
                    token = tokens[i]
                    if token == ',':
                        i += 1
                        continue
                    # String literal (with quotes)
                    if (token.startswith('"') and token.endswith('"')) or \
                       (token.startswith("'") and token.endswith("'")):
                        args.append(token[1:-1])  # Remove quotes
                        i += 1
                    # Number
                    elif token.replace('.', '').replace('-', '').isdigit():
                        try:
                            args.append(float(token) if '.' in token else int(token))
                        except ValueError:
                            args.append(token)
                        i += 1
                    # Boolean
                    elif token.lower() == 'true':
                        args.append(True)
                        i += 1
                    elif token.lower() == 'false':
                        args.append(False)
                        i += 1
                    else:
                        args.append(token)
                        i += 1
            
            # Call function
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
            # No-argument call
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

    # ===== Internal: Boolean expression parsing (and/or/not with parentheses) =====
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
            # Condition name or function call
            name = consume()
            if name is None:
                raise ValueError('unexpected end')
            
            # Check if it's a function call (with parentheses)
            if peek() == '(':
                consume('(')
                # Parse function arguments
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
                
                # Call function (with arguments)
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
                # No-argument call
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
            # Recognize string literals (single or double quotes)
            if c in '\'"':
                quote = c
                j = i + 1
                while j < n and s[j] != quote:
                    if s[j] == '\\' and j + 1 < n:
                        j += 2  # Skip escape characters
                    else:
                        j += 1
                if j < n:
                    out.append(s[i:j+1])  # Include quotes
                    i = j + 1
                    continue
            # Recognize numbers
            if c.isdigit() or (c == '-' and i + 1 < n and s[i+1].isdigit()):
                j = i + 1
                while j < n and (s[j].isdigit() or s[j] == '.'):
                    j += 1
                out.append(s[i:j])
                i = j
                continue
            # Recognize identifiers (condition names or and/or/not)
            j = i
            while j < n and (s[j].isalnum() or s[j] == '_' or s[j] == '.'):  # Allow underscores and dots
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
        """Parse function argument (supports numbers, strings, booleans)"""
        token = peek()
        if token is None:
            raise ValueError('unexpected end in function argument')
        
        # String literal
        if (token.startswith('"') and token.endswith('"')) or \
           (token.startswith("'") and token.endswith("'")):
            consume()
            # Remove quotes and handle escapes
            s = token[1:-1]
            s = s.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
            return s
        
        # Number
        try:
            if '.' in token:
                return float(token)
            else:
                return int(token)
        except ValueError:
            pass
        
        # Boolean
        if token.lower() == 'true':
            consume()
            return True
        if token.lower() == 'false':
            consume()
            return False
        
        # Default as string (without quotes)
        consume()
        return token


