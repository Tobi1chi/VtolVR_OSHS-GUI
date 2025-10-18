import sys
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QListWidget, QLineEdit, QComboBox,
                             QTextEdit, QFileDialog, QMessageBox, QGroupBox,
                             QFormLayout, QFrame, QScrollArea, QSizePolicy)
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

        # Entry Condition
        self.entry_cond_input = QLineEdit()
        self.entry_cond_input.setPlaceholderText("Enter entry condition number")

        form_layout.addRow("Key (Auto):", self.key_input)
        form_layout.addRow("Search Campaign:", self.campaign_search_input)
        form_layout.addRow("Search Results:", self.search_results_list)  # Search Results 现在占用更多空间
        form_layout.addRow("Campaign Name:", self.campaign_name_input)
        form_layout.addRow("Campaign ID (WS ID):", self.campaign_id_input)
        form_layout.addRow("Map Name (Mission ID):", self.map_name_input)
        form_layout.addRow("Entry Condition:", self.entry_cond_input)

        # Condition Functions (扩大)
        condition_funcs_label = QLabel("Condition Functions:")
        condition_funcs_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.condition_funcs_input = QTextEdit()
        self.condition_funcs_input.setPlaceholderText("Enter condition functions here...")

        # Linked States as Tags
        linked_states_label = QLabel("Linked States (Tags - Numbers Only):")
        linked_states_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))

        # 使用一个滚动区域来容纳动态添加的标签
        self.linked_states_scroll_area = QScrollArea()
        self.linked_states_scroll_area.setWidgetResizable(True)
        self.linked_states_container = QWidget()
        self.linked_states_scroll_area.setWidget(self.linked_states_container)
        self.linked_states_layout = QHBoxLayout(self.linked_states_container)
        self.linked_states_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # self.linked_states_scroll_area.setMaximumHeight(100) # 移除最大高度限制

        # 添加 Linked State 的输入框和按钮 (只允许数字输入)
        self.add_linked_state_input = QLineEdit()
        self.add_linked_state_input.setPlaceholderText("Enter Linked State Key (Number)")
        # 设置验证器，只允许数字
        validator = QRegularExpressionValidator(QRegularExpression(r"^\d*$"), self.add_linked_state_input)
        self.add_linked_state_input.setValidator(validator)

        add_linked_state_btn = QPushButton("Add Tag")
        add_linked_state_btn.clicked.connect(self.add_linked_state_tag)

        # 将表单和扩展区域添加到 details_layout
        details_layout.addLayout(form_layout)
        details_layout.addWidget(condition_funcs_label)
        details_layout.addWidget(self.condition_funcs_input)
        details_layout.addWidget(linked_states_label)
        details_layout.addWidget(self.linked_states_scroll_area)

        # 将输入框和按钮放在标签下方
        add_tag_layout = QHBoxLayout()
        add_tag_layout.addWidget(self.add_linked_state_input)
        add_tag_layout.addWidget(add_linked_state_btn)
        details_layout.addLayout(add_tag_layout)

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

                # 将原始状态数据转换为内部格式
                # 内部格式：{"Key": ..., "campaign name": ..., "campaign id": ..., "mapname": ..., "Entry cond": ..., "Condition funcs": ..., "Linked State": [...]}
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
            "Entry cond": "0",
            "Condition funcs": "",
            "Linked State": []  # Linked State 现在是字符串列表
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
        self.entry_cond_input.setText(str(state.get("Entry cond", "0")))  # Entry cond 可能是数字，转为字符串
        self.condition_funcs_input.setPlainText(state.get("Condition funcs", ""))

        # 填充 Linked States Tags
        self.update_linked_state_tags(state.get("Linked State", []))

    def clear_state_details(self):
        """清空右侧编辑区"""
        self.key_input.clear()
        self.campaign_name_input.clear()
        self.campaign_id_input.clear()
        self.map_name_input.clear()
        self.entry_cond_input.clear()
        self.condition_funcs_input.clear()
        self.search_results_list.clear()
        self.search_results = []
        self.add_linked_state_input.clear()
        # 清空标签
        for i in reversed(range(self.linked_states_layout.count())):
            widget = self.linked_states_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

    def save_current_state(self):
        """保存当前在右侧编辑的状态"""
        if self.currently_selected_state_index >= 0 and self.currently_selected_state_index < len(self.states):
            state = self.states[self.currently_selected_state_index]

            # 更新状态基本信息 (Key 由系统管理，不从UI更新)
            # state["Key"] = self.name_input.text().strip() # 不更新 Key
            state["campaign name"] = self.campaign_name_input.text().strip()
            state["campaign id"] = self.campaign_id_input.text().strip()
            state["mapname"] = self.map_name_input.text().strip()
            state["Entry cond"] = self.entry_cond_input.text().strip()
            state["Condition funcs"] = self.condition_funcs_input.toPlainText().strip()

            # 更新链接状态信息 (Linked State) 从标签中获取
            linked_states = []
            for i in range(self.linked_states_layout.count()):
                widget = self.linked_states_layout.itemAt(i).widget()
                if widget and hasattr(widget, 'linked_state_key'):
                    linked_states.append(widget.linked_state_key)
            state["Linked State"] = linked_states

            # 刷新列表显示（如果 Campaign Name 改变了）
            self.refresh_state_list()

            # 重新选中并加载，确保 UI 与数据同步
            self.state_list_widget.setCurrentRow(self.currently_selected_state_index)
            self.on_state_selected()

            print(f"State '{state['Key']}' saved.")

    def cancel_editing(self):
        """取消当前编辑，恢复到上次保存的状态"""
        self.on_state_selected()  # 重新加载当前选中状态的原始数据

    def add_linked_state_tag(self):
        """添加一个 Linked State Tag"""
        linked_key = self.add_linked_state_input.text().strip()
        if linked_key and not any(tag.linked_state_key == linked_key for tag in self.findChildren(TagLabel) if
                                  hasattr(tag, 'linked_state_key')):
            tag = TagLabel(linked_key, self.remove_linked_state_tag)
            # 将 key 信息存储为标签对象的属性
            tag.linked_state_key = linked_key
            self.linked_states_layout.addWidget(tag)
            self.add_linked_state_input.clear()

    def update_linked_state_tags(self, linked_keys_list):
        """根据给定的列表更新 Linked State Tags 显示"""
        # 清空现有标签
        for i in reversed(range(self.linked_states_layout.count())):
            widget = self.linked_states_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 重新添加标签
        for key in linked_keys_list:
            tag = TagLabel(key, self.remove_linked_state_tag)
            tag.linked_state_key = key
            self.linked_states_layout.addWidget(tag)

    def remove_linked_state_tag(self, tag_widget):
        """移除指定的 Linked State Tag"""
        tag_widget.setParent(None)
        tag_widget.deleteLater()  # 确保对象被删除


# --- 自定义标签组件 ---
class TagLabel(QLabel):
    def __init__(self, text, remove_callback):
        super().__init__(text)
        self.remove_callback = remove_callback
        self.setStyleSheet(
            "QLabel { "
            "   background-color: #e0e0e0; "
            "   border: 1px solid #a0a0a0; "
            "   border-radius: 4px; "
            "   padding: 2px 8px; "
            "   margin: 2px; "
            "} "
            "QLabel:hover { "
            "   background-color: #d0d0d0; "
            "}"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 添加删除按钮
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 调用父级的删除回调函数
            self.remove_callback(self)
        else:
            super().mousePressEvent(event)


# --- 示例用法 ---
if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication


    def dummy_back():
        print("Back button clicked")


    app = QApplication(sys.argv)
    window = StateMachineEditorPage(dummy_back)
    window.show()
    sys.exit(app.exec())