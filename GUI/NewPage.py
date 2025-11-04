import sys
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QListWidget, QLineEdit, QComboBox,
                             QTextEdit, QFileDialog, QMessageBox, QGroupBox,
                             QFormLayout, QFrame, QScrollArea, QSizePolicy,
                             QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QDialog)
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QFont, QRegularExpressionValidator
from PyQt6.QtGui import QPalette  # 导入 QPalette

# --- 示例地图信息数据文件名 ---
MAP_INFO_FILE = "map_info.json"
# --- 示例状态机数据文件名 ---
STATE_MACHINE_FILE = "state_machine.json"


class StateMachineEditorPage(QWidget):
    def __init__(self, back_callback):
        super().__init__()
        self.back_callback = back_callback
        self.map_info_data = {}  # 存储从 map_info.json 读取的数据
        self.config = []  # 存储 config 信息 ["Name of pkg", "Author"]
        self.states = []  # 存储状态机数据
        self.currently_selected_state_index = -1  # 当前选中的状态索引
        self.search_results = []  # 存储搜索结果

        self.init_ui()
        self.load_map_info()  # 初始化时加载地图信息

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # --- 1. 顶部工具栏 ---
        toolbar_layout = QHBoxLayout()

        self.load_btn = QPushButton("Load JSON")
        self.load_btn.clicked.connect(self.load_state_machine_from_file)

        self.save_btn = QPushButton("Save JSON")
        self.save_btn.clicked.connect(self.save_state_machine_to_file)

        self.add_state_btn = QPushButton("Add State")
        self.add_state_btn.clicked.connect(self.add_state)

        self.delete_state_btn = QPushButton("Delete State")
        self.delete_state_btn.clicked.connect(self.delete_selected_state)

        toolbar_layout.addWidget(self.load_btn)
        toolbar_layout.addWidget(self.save_btn)
        toolbar_layout.addWidget(self.add_state_btn)
        toolbar_layout.addWidget(self.delete_state_btn)
        toolbar_layout.addStretch()  # 推按钮到左边

        # --- 2. 主内容区 (左右分栏) ---
        main_content_layout = QHBoxLayout()

        # --- 2.1 左侧：状态列表 ---
        left_panel_layout = QVBoxLayout()
        left_label = QLabel("States")
        left_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        self.state_list_widget = QListWidget()
        self.state_list_widget.itemSelectionChanged.connect(self.on_state_selected)

        left_panel_layout.addWidget(left_label)
        left_panel_layout.addWidget(self.state_list_widget)

        # --- 2.2 右侧：状态详情编辑器 ---
        right_panel_layout = QVBoxLayout()

        # 状态详情组
        details_group = QGroupBox("State Details")
        details_layout = QVBoxLayout(details_group)

        # 表单区域
        form_layout = QFormLayout()

        # Key (序号)
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Enter state Key (number)")
        self.key_input.setReadOnly(True)  # Key 由系统生成和管理，用户不应手动编辑

        # Campaign Search (用于搜索 WS ID 和 Mission ID)
        self.campaign_search_input = QLineEdit()
        self.campaign_search_input.setPlaceholderText("Search for Campaign (Map Name)...")
        self.campaign_search_input.textChanged.connect(self.on_campaign_search_changed)

        # Search Results List (显示搜索结果, 扩大)
        self.search_results_list = QListWidget()
        # self.search_results_list.setMaximumHeight(100) # 移除最大高度限制
        self.search_results_list.itemClicked.connect(self.on_search_result_clicked)

        # Campaign Name (显示选中的结果)
        self.campaign_name_input = QLineEdit()
        self.campaign_name_input.setPlaceholderText("Selected Campaign Name")
        self.campaign_name_input.setReadOnly(True)

        # Campaign ID (WS ID) (显示选中的结果)
        self.campaign_id_input = QLineEdit()
        self.campaign_id_input.setPlaceholderText("Selected Campaign ID (WS ID)")
        self.campaign_id_input.setReadOnly(True)

        # Map Name (Mission ID) (显示选中的结果)
        self.map_name_input = QLineEdit()
        self.map_name_input.setPlaceholderText("Selected Map Name (Mission ID)")
        self.map_name_input.setReadOnly(True)

        form_layout.addRow("Key (Auto):", self.key_input)
        form_layout.addRow("Search Campaign:", self.campaign_search_input)
        form_layout.addRow("Search Results:", self.search_results_list)  # Search Results 现在占用更多空间
        form_layout.addRow("Campaign Name:", self.campaign_name_input)
        form_layout.addRow("Campaign ID (WS ID):", self.campaign_id_input)
        form_layout.addRow("Map Name (Mission ID):", self.map_name_input)


        # 将表单添加到 details_layout
        details_layout.addLayout(form_layout)
        # 删除 Legacy Linked State 区域（不再需要）

        # Transitions 编辑区
        transitions_label = QLabel("Transitions (ordered conditions):")
        transitions_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.docs_help_btn = QPushButton("?")
        self.docs_help_btn.setFixedWidth(28)
        self.docs_help_btn.clicked.connect(self.show_fsm_docs)

        self.transitions_table = QTableWidget(0, 4)
        self.transitions_table.setHorizontalHeaderLabels(["Target Key", "Condition", "Else", "Actuator Cmd"])
        header = self.transitions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        trans_btn_layout = QHBoxLayout()
        add_trans_btn = QPushButton("Add Transition")
        remove_trans_btn = QPushButton("Remove Selected")
        add_trans_btn.clicked.connect(self.add_transition_row)
        remove_trans_btn.clicked.connect(self.remove_selected_transition_rows)
        trans_btn_layout.addWidget(add_trans_btn)
        trans_btn_layout.addWidget(remove_trans_btn)
        trans_btn_layout.addStretch()

        trans_header_layout = QHBoxLayout()
        trans_header_layout.addWidget(transitions_label)
        trans_header_layout.addStretch()
        trans_header_layout.addWidget(self.docs_help_btn)

        details_layout.addLayout(trans_header_layout)
        details_layout.addWidget(self.transitions_table)
        details_layout.addLayout(trans_btn_layout)

        # Transitions 文本编辑（适合长命令）
        transitions_text_label = QLabel("Transitions Text (JSON array):")
        transitions_text_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.transitions_text = QTextEdit()
        self.transitions_text.setPlaceholderText('[{"to":"2","cond":"elapsed_ge_5s","actuator_cmd":"start_next"}, {"to":"3","else":true}]')
        sync_btns_layout = QHBoxLayout()
        btn_fill_from_table = QPushButton("Fill from Table")
        btn_apply_to_table = QPushButton("Apply to Table")
        btn_fill_from_table.clicked.connect(self.sync_transitions_text_from_table)
        btn_apply_to_table.clicked.connect(self.apply_transitions_text_to_table)
        sync_btns_layout.addWidget(btn_fill_from_table)
        sync_btns_layout.addWidget(btn_apply_to_table)
        sync_btns_layout.addStretch()

        details_layout.addWidget(transitions_text_label)
        details_layout.addWidget(self.transitions_text)
        details_layout.addLayout(sync_btns_layout)

        # 保存/取消按钮
        button_layout = QHBoxLayout()
        save_state_btn = QPushButton("Save Current State")
        save_state_btn.clicked.connect(self.save_current_state)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.cancel_editing)

        button_layout.addStretch()
        button_layout.addWidget(save_state_btn)
        button_layout.addWidget(cancel_btn)

        right_panel_layout.addWidget(details_group)
        right_panel_layout.addLayout(button_layout)

        # 将左右面板添加到主内容布局
        main_content_layout.addLayout(left_panel_layout, 1)  # 左侧比例为 1
        main_content_layout.addLayout(right_panel_layout, 2)  # 右侧比例为 2

        # --- 3. 底部返回按钮 ---
        back_btn_layout = QHBoxLayout()
        back_btn_layout.addStretch()
        back_btn = QPushButton("← Back to Main")
        back_btn.clicked.connect(self.back_callback)
        back_btn.setStyleSheet("font-size: 14px; padding: 8px;")
        back_btn_layout.addWidget(back_btn)

        # --- 将所有部分添加到主布局 ---
        layout.addLayout(toolbar_layout)
        layout.addLayout(main_content_layout)
        layout.addLayout(back_btn_layout)

        # 文档加载
        self.fsm_docs = {"conditions": [], "commands": []}
        self.load_fsm_docs()

    def load_map_info(self):
        """从 JSON 文件加载地图信息数据"""
        try:
            with open(MAP_INFO_FILE, 'r', encoding='utf-8') as f:
                self.map_info_data = json.load(f)
            print(f"Map info loaded from {MAP_INFO_FILE}")
        except FileNotFoundError:
            print(f"Warning: Map info file '{MAP_INFO_FILE}' not found.")
            self.map_info_data = {}
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{MAP_INFO_FILE}'.")
            self.map_info_data = {}

    def load_fsm_docs(self):
        """加载 FSM 可用条件与指令文档（可选）"""
        import os
        docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "fsm_docs.json")
        try:
            with open(docs_path, 'r', encoding='utf-8') as f:
                self.fsm_docs = json.load(f)
        except Exception:
            self.fsm_docs = {"conditions": [], "commands": []}

    def show_fsm_docs(self):
        """弹窗显示可用条件与指令文档"""
        fields = self.fsm_docs.get("fields", [])
        order = self.fsm_docs.get("evaluation_order", [])
        syntax = self.fsm_docs.get("syntax", {})
        conds = self.fsm_docs.get("conditions", [])
        cmds = self.fsm_docs.get("commands", [])
        examples = self.fsm_docs.get("transition_examples", [])

        lines = []
        if fields:
            lines.append("字段说明 (Transition fields):")
            for f in fields:
                lines.append(f" - {f.get('name','')} ({f.get('type','')}): {f.get('desc','')}")
            lines.append("")

        if order:
            lines.append("评估顺序 (Evaluation Order):")
            for step in order:
                lines.append(f" - {step}")
            lines.append("")

        if syntax:
            lines.append("逻辑表达式语法 (cond_expr):")
            ops = syntax.get("operators", [])
            if ops:
                lines.append(f" - 运算符: {', '.join(ops)}")
            paren = syntax.get("parentheses")
            if paren:
                lines.append(f" - 括号: {paren}")
            prec = syntax.get("precedence", [])
            if prec:
                lines.append(" - 优先级:")
                for p in prec:
                    lines.append(f"    * {p}")
            ident = syntax.get("identifiers")
            if ident:
                lines.append(f" - 标识符: {ident}")
            syn_examples = syntax.get("examples", [])
            if syn_examples:
                lines.append(" - 示例:")
                for ex in syn_examples:
                    lines.append(f"    * {ex}")
            lines.append("")

        if conds:
            lines.append("可用条件 (Conditions):")
            for c in conds:
                lines.append(f" - {c.get('name','')}：{c.get('desc','')}")
            lines.append("")

        if cmds:
            lines.append("可用指令 (Actuator Cmds):")
            for c in cmds:
                lines.append(f" - {c.get('name','')}：{c.get('desc','')}")
            lines.append("")

        if examples:
            lines.append("示例 (Transition Examples):")
            for e in examples:
                desc = e.get('desc','')
                val = e.get('value', {})
                try:
                    val_json = json.dumps(val, ensure_ascii=False)
                except Exception:
                    val_json = str(val)
                lines.append(f" - {desc}: {val_json}")
            lines.append("")
        # 使用可滚动、可调整大小的对话框显示长文本
        dlg = QDialog(self)
        dlg.setWindowTitle("FSM 文档")
        v = QVBoxLayout(dlg)
        text = QTextEdit(dlg)
        text.setReadOnly(True)
        text.setPlainText("\n".join(lines))
        v.addWidget(text)
        btns = QHBoxLayout()
        close_btn = QPushButton("Close", dlg)
        close_btn.clicked.connect(dlg.accept)
        btns.addStretch()
        btns.addWidget(close_btn)
        v.addLayout(btns)
        dlg.resize(600, 500)
        dlg.exec()

    # 移除 Legacy Linked State 切换（已废弃）

    def on_campaign_search_changed(self, text):
        """当搜索框内容改变时，更新搜索结果列表"""
        self.search_results_list.clear()
        self.search_results = []
        if not text:
            return

        text_lower = text.lower()
        by_wsid = self.map_info_data.get("by_wsid", {})
        for wsid, ws_data in by_wsid.items():
            maps = ws_data.get("maps", [])
            for map_obj in maps:
                map_name = map_obj.get("map_name", "")
                map_id = map_obj.get("map_id", "")
                if text_lower in map_name.lower():
                    result = {
                        "wsid": wsid,
                        "package_name": ws_data.get("package_name", ""),
                        "map_name": map_name,
                        "map_id": map_id
                    }
                    self.search_results.append(result)
                    # 显示 map_name，不显示括号内的信息
                    self.search_results_list.addItem(map_name)

    def on_search_result_clicked(self, item):
        """当点击搜索结果时，将选中的值填入对应的输入框"""
        row = self.search_results_list.row(item)
        if 0 <= row < len(self.search_results):
            result = self.search_results[row]
            self.campaign_name_input.setText(result["map_name"])
            self.campaign_id_input.setText(result["wsid"])
            self.map_name_input.setText(result["map_id"])

    def load_state_machine_from_file(self):
        """从 JSON 文件加载状态机数据"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Load State Machine", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 解析 JSON 结构
                self.config = data.get("config", [])
                raw_states = data.get("StateMachine", [])

                # 将原始状态数据转换为内部格式（已移除 Linked State）
                self.states = raw_states
                self.refresh_state_list()
                print(f"State machine loaded from {file_path}")
                print(f"Config: {self.config}")
            except Exception as e:
                QMessageBox.critical(self, "Error Loading", f"Failed to load state machine:\n{str(e)}")

    def save_state_machine_to_file(self):
        """将状态机数据保存到 JSON 文件"""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save State Machine", STATE_MACHINE_FILE,
                                                   "JSON Files (*.json)")
        if file_path:
            try:
                # 构造要保存的 JSON 结构
                # config 默认值 ["Default Package Name", "Default Author"] 如果未设置
                config_to_save = self.config if self.config else ["Default Package Name", "Default Author"]

                # StateMachine 就是 self.states 列表
                data_to_save = {
                    "config": config_to_save,
                    "StateMachine": self.states
                }

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=4, ensure_ascii=False)
                print(f"State machine saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error Saving", f"Failed to save state machine:\n{str(e)}")

    def refresh_state_list(self):
        """刷新左侧状态列表的显示"""
        self.state_list_widget.clear()
        for state in self.states:
            # 显示 Key: Campaign Name
            key = state.get("Key", "Unknown Key")
            cname = state.get("campaign name", "Unknown Campaign")
            self.state_list_widget.addItem(f"{key}: {cname}")

    def add_state(self):
        """添加一个新状态"""
        # 计算下一个 Key，基于现有状态的最大 Key
        existing_keys = [int(s.get("Key")) for s in self.states if str(s.get("Key")).isdigit()]
        next_key = max(existing_keys) + 1 if existing_keys else 1

        new_state = {
            "Key": str(next_key),  # Key 作为字符串存储
            "campaign name": f"Campaign_{next_key}",
            "campaign id": "",
            "mapname": "",
            "Transitions": []
        }
        self.states.append(new_state)
        self.refresh_state_list()
        # 选中新添加的状态
        self.state_list_widget.setCurrentRow(len(self.states) - 1)
        self.on_state_selected()  # 触发详情更新

    def delete_selected_state(self):
        """删除当前选中的状态"""
        current_row = self.state_list_widget.currentRow()
        if current_row >= 0 and current_row < len(self.states):
            # 询问确认
            key_to_delete = self.states[current_row].get("Key", "Unknown")
            reply = QMessageBox.question(self, 'Confirm Delete',
                                         f"Are you sure you want to delete state '{key_to_delete}'?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                # 从列表中移除
                del self.states[current_row]
                # 刷新列表
                self.refresh_state_list()
                # 清空右侧编辑区
                self.clear_state_details()

    def on_state_selected(self):
        """当左侧状态列表选中项改变时调用"""
        current_row = self.state_list_widget.currentRow()
        if current_row >= 0 and current_row < len(self.states):
            self.currently_selected_state_index = current_row
            state = self.states[current_row]
            self.populate_state_details(state)
        else:
            self.currently_selected_state_index = -1
            self.clear_state_details()

    def populate_state_details(self, state):
        """将状态数据填充到右侧编辑区"""
        self.key_input.setText(str(state.get("Key", "")))  # Key 可能是数字，转为字符串
        self.campaign_name_input.setText(state.get("campaign name", ""))
        self.campaign_id_input.setText(state.get("campaign id", ""))
        self.map_name_input.setText(state.get("mapname", ""))
        

        # 填充 Transitions
        self.fill_transitions_table(state.get("Transitions", []))
        try:
            self.transitions_text.setPlainText(json.dumps(state.get("Transitions", []), indent=2, ensure_ascii=False))
        except Exception:
            self.transitions_text.setPlainText("")

    def clear_state_details(self):
        """清空右侧编辑区"""
        self.key_input.clear()
        self.campaign_name_input.clear()
        self.campaign_id_input.clear()
        self.map_name_input.clear()
        
        self.search_results_list.clear()
        self.search_results = []
        # 清空 Transitions 表与文本
        self.transitions_table.setRowCount(0)
        self.transitions_text.clear()

    def save_current_state(self):
        """保存当前在右侧编辑的状态"""
        if self.currently_selected_state_index >= 0 and self.currently_selected_state_index < len(self.states):
            state = self.states[self.currently_selected_state_index]

            # 更新状态基本信息 (Key 由系统管理，不从UI更新)
            # state["Key"] = self.name_input.text().strip() # 不更新 Key
            state["campaign name"] = self.campaign_name_input.text().strip()
            state["campaign id"] = self.campaign_id_input.text().strip()
            state["mapname"] = self.map_name_input.text().strip()
            

            # 保存 Transitions：优先解析文本，其次回退表格
            text_val = self.transitions_text.toPlainText().strip()
            parsed = None
            if text_val:
                try:
                    parsed = json.loads(text_val)
                    if not isinstance(parsed, list):
                        parsed = None
                except Exception:
                    parsed = None
            state["Transitions"] = parsed if parsed is not None else self.collect_transitions_from_table()

            # 刷新列表显示（如果 Campaign Name 改变了）
            self.refresh_state_list()

            # 重新选中并加载，确保 UI 与数据同步
            self.state_list_widget.setCurrentRow(self.currently_selected_state_index)
            self.on_state_selected()

            print(f"State '{state['Key']}' saved.")

    def cancel_editing(self):
        """取消当前编辑，恢复到上次保存的状态"""
        self.on_state_selected()  # 重新加载当前选中状态的原始数据

    # Legacy Linked State 相关功能已移除

    # --- Transitions 编辑逻辑 ---
    def add_transition_row(self):
        row = self.transitions_table.rowCount()
        self.transitions_table.insertRow(row)
        # Target Key
        self.transitions_table.setItem(row, 0, QTableWidgetItem(""))
        # Condition
        self.transitions_table.setItem(row, 1, QTableWidgetItem(""))
        # Else (checkbox)
        checkbox = QCheckBox()
        checkbox.setChecked(False)
        checkbox.setStyleSheet("margin-left: 8px; margin-right: 8px;")
        self.transitions_table.setCellWidget(row, 2, checkbox)
        # Actuator Cmd
        self.transitions_table.setItem(row, 3, QTableWidgetItem(""))

    def remove_selected_transition_rows(self):
        selected = self.transitions_table.selectionModel().selectedRows()
        for idx in sorted([i.row() for i in selected], reverse=True):
            self.transitions_table.removeRow(idx)

    def fill_transitions_table(self, transitions_list):
        self.transitions_table.setRowCount(0)
        if not transitions_list:
            return
        for t in transitions_list:
            row = self.transitions_table.rowCount()
            self.transitions_table.insertRow(row)
            # Target Key
            self.transitions_table.setItem(row, 0, QTableWidgetItem(str(t.get("to", ""))))
            # Condition
            self.transitions_table.setItem(row, 1, QTableWidgetItem(str(t.get("cond", ""))))
            # Else
            checkbox = QCheckBox()
            checkbox.setChecked(bool(t.get("else", False)))
            checkbox.setStyleSheet("margin-left: 8px; margin-right: 8px;")
            self.transitions_table.setCellWidget(row, 2, checkbox)
            # Actuator Cmd
            self.transitions_table.setItem(row, 3, QTableWidgetItem(str(t.get("actuator_cmd", ""))))

    def collect_transitions_from_table(self):
        transitions = []
        rows = self.transitions_table.rowCount()
        for r in range(rows):
            to_item = self.transitions_table.item(r, 0)
            cond_item = self.transitions_table.item(r, 1)
            checkbox = self.transitions_table.cellWidget(r, 2)
            act_item = self.transitions_table.item(r, 3)

            to_val = (to_item.text().strip() if to_item else "")
            cond_val = (cond_item.text().strip() if cond_item else "")
            act_val = (act_item.text().strip() if act_item else "")
            else_val = bool(checkbox.isChecked()) if isinstance(checkbox, QCheckBox) else False

            entry = {}
            if to_val:
                entry["to"] = to_val
            if else_val:
                entry["else"] = True
            if cond_val:
                entry["cond"] = cond_val
            if act_val:
                entry["actuator_cmd"] = act_val

            if entry:
                transitions.append(entry)
        return transitions

    # --- Transitions 文本区与表格同步 ---
    def sync_transitions_text_from_table(self):
        data = self.collect_transitions_from_table()
        try:
            self.transitions_text.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            self.transitions_text.setPlainText("")

    def apply_transitions_text_to_table(self):
        text_val = self.transitions_text.toPlainText().strip()
        if not text_val:
            return
        try:
            data = json.loads(text_val)
            if isinstance(data, list):
                self.fill_transitions_table(data)
        except Exception as e:
            QMessageBox.critical(self, "Invalid Transitions Text", f"JSON 解析失败:\n{e}")


# --- 自定义标签组件 ---
class TagLabel(QLabel):
    pass


    
    


# --- 示例用法 ---
if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication


    def dummy_back():
        print("Back button clicked")


    app = QApplication(sys.argv)
    window = StateMachineEditorPage(dummy_back)
    window.show()
    sys.exit(app.exec())